from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from episodic.config import EpisodicConfig, validate_subgraph_id
from episodic.drivers.local_blob_store import LocalBlobStore
from episodic.drivers.sqlite_episode_store import SQLiteEpisodeStore
from episodic.ingest.differ import (
    bootstrap_operations,
    build_fingerprint_map_from_bootstrap,
    diff_snapshots,
)
from episodic.ingest.graphify_adapter import parse_graph_json
from episodic.models.episode import Episode
from episodic.models.subgraph import SubgraphRegistration


class GraphifyRunError(RuntimeError):
    pass


@dataclass
class SaveResult:
    subgraph_id: str
    status: str
    snapshot_hash: str | None = None
    episode_id: str | None = None
    ops_total: int = 0
    node_count: int = 0
    edge_count: int = 0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_graphify(source: Path, binary: str) -> None:
    source = source.resolve()
    if not source.exists():
        raise FileNotFoundError(f"source not found: {source}")

    if shutil.which(binary) is None:
        raise GraphifyRunError(
            f"{binary!r} not found on PATH. Run `episodic init` to install graphify."
        )

    cmd = [binary, "extract", str(source)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        cmd_fallback = [binary, str(source)]
        result = subprocess.run(cmd_fallback, capture_output=True, text=True)
        if result.returncode != 0:
            raise GraphifyRunError(
                "graphify failed:\n"
                f"  tried: {' '.join(cmd)}\n"
                f"  tried: {' '.join(cmd_fallback)}\n"
                f"  stderr: {result.stderr.strip()}"
            )


def ensure_graphify_installed(config: EpisodicConfig) -> None:
    binary = config.graphify.binary
    if shutil.which(binary) is not None:
        return
    install_cmd = config.graphify.install_via.split()
    if not install_cmd:
        raise GraphifyRunError("graphify not found and no install_via configured")
    if shutil.which(install_cmd[0]) is None:
        raise GraphifyRunError(
            f"graphify not found and installer {install_cmd[0]!r} not on PATH"
        )
    result = subprocess.run(install_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise GraphifyRunError(
            f"failed to install graphify: {' '.join(install_cmd)}\n{result.stderr}"
        )
    if shutil.which(binary) is None:
        raise GraphifyRunError(
            f"graphify install completed but {binary!r} still not on PATH"
        )


def read_graph_counts(content: bytes) -> tuple[int, int]:
    data = json.loads(content.decode("utf-8"))
    nodes = data.get("nodes") or []
    links = data.get("links") or data.get("edges") or []
    return len(nodes), len(links)


class SavePipeline:
    def __init__(self, config: EpisodicConfig) -> None:
        self.config = config
        self.store = SQLiteEpisodeStore(config.episode_db_path)
        self.blobs = LocalBlobStore(config.snapshots_dir)

    def save(
        self,
        subgraph_id: str,
        source: Path,
        graphify_out: Path | None = None,
        *,
        skip_graphify: bool = False,
        graph_json_path: Path | None = None,
    ) -> SaveResult:
        subgraph_id = validate_subgraph_id(subgraph_id)
        source = source.resolve()
        out_dir = (graphify_out or source / "graphify-out").resolve()
        graph_path = graph_json_path or (out_dir / "graph.json")

        if not skip_graphify:
            run_graphify(source, self.config.graphify.binary)
        if not graph_path.is_file():
            raise FileNotFoundError(f"graph.json not found: {graph_path}")

        content = graph_path.read_bytes()
        snapshot_hash = self.blobs.put(content)
        node_count, edge_count = read_graph_counts(content)
        now = utc_now_iso()

        existing = self.store.get_subgraph(subgraph_id)
        if existing and existing.latest_snapshot_hash == snapshot_hash:
            self.store.touch_subgraph(subgraph_id, now)
            return SaveResult(
                subgraph_id=subgraph_id,
                status="unchanged",
                snapshot_hash=snapshot_hash,
                node_count=node_count,
                edge_count=edge_count,
            )

        new_nodes, new_edges = parse_graph_json(json.loads(content.decode("utf-8")))

        if existing is None:
            operations, _ = bootstrap_operations(new_nodes, new_edges, subgraph_id)
            sequence = 1
            parent = None
        else:
            old_content = self.blobs.get(existing.latest_snapshot_hash)
            old_nodes, old_edges = parse_graph_json(
                json.loads(old_content.decode("utf-8"))
            )
            prior = self.store.latest_episode(subgraph_id)
            if prior is None:
                raise RuntimeError(f"missing episodes for subgraph {subgraph_id}")
            fp_map = build_fingerprint_map_from_bootstrap(prior.operations)
            operations, _ = diff_snapshots(
                old_nodes,
                old_edges,
                new_nodes,
                new_edges,
                subgraph_id,
                fp_map,
            )
            sequence = self.store.next_sequence(subgraph_id)
            parent = prior.episode_id

        episode_id = f"{subgraph_id}__ep_{sequence:06d}"
        episode = Episode(
            episode_id=episode_id,
            sequence=sequence,
            recorded_at=now,
            subgraph_id=subgraph_id,
            snapshot_hash=snapshot_hash,
            operations=operations,
            parent_episode_id=parent,
        )

        registration = SubgraphRegistration(
            subgraph_id=subgraph_id,
            source_path=str(source),
            graphify_out_path=str(out_dir),
            latest_snapshot_hash=snapshot_hash,
            registered_at=existing.registered_at if existing else now,
            last_seen_at=now,
        )
        self.store.upsert_subgraph(registration)
        self.store.append_episode(episode)

        return SaveResult(
            subgraph_id=subgraph_id,
            status="saved",
            snapshot_hash=snapshot_hash,
            episode_id=episode_id,
            ops_total=len(operations),
            node_count=node_count,
            edge_count=edge_count,
        )
