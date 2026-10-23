"""Save pipeline orchestrator."""

from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from episodic.config import EpisodicConfig, validate_subgraph_id
from episodic.drivers.sqlite_episode_store import SQLiteEpisodeStore
from episodic.ingest.differ import bootstrap_operations
from episodic.ingest.graphify_adapter import parse_graph_json
from episodic.models.episode import Episode
from episodic.models.subgraph import SubgraphRegistration


class GraphifyRunError(RuntimeError):
    """Raised when graphify fails to run or install."""
    pass


@dataclass
class SaveResult:
    """Result of a save operation."""

    subgraph_id: str
    status: str                # "saved" or "unchanged"
    snapshot_hash: str | None = None
    episode_id: str | None = None
    ops_total: int = 0
    node_count: int = 0
    edge_count: int = 0


def utc_now_iso() -> str:
    """Get current UTC time in ISO format with Z suffix.

    Returns:
        Timestamp like "2026-10-23T20:39:44Z"
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_graphify(source: Path, binary: str) -> None:
    """Run graphify on source to generate graph.json.

    Tries "graphify extract <source>" first, falls back to "graphify <source>".

    Args:
        source: Source directory/file to analyze
        binary: Name of graphify binary

    Raises:
        FileNotFoundError: If source doesn't exist
        GraphifyRunError: If binary not found or graphify fails
    """
    source = source.resolve()
    if not source.exists():
        raise FileNotFoundError(f"source not found: {source}")

    if shutil.which(binary) is None:
        raise GraphifyRunError(
            f"{binary!r} not found on PATH. Run `episodic init` to install graphify."
        )

    # Try first form: graphify extract <source>
    cmd = [binary, "extract", str(source)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Try fallback form: graphify <source>
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
    """Ensure graphify binary is installed.

    Checks if binary exists on PATH, installs via config.graphify.install_via if not.

    Args:
        config: Configuration

    Raises:
        GraphifyRunError: If binary not found and cannot install
    """
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
    """Read node and edge counts from graph JSON.

    Args:
        content: Raw JSON bytes

    Returns:
        Tuple of (node_count, edge_count)
    """
    data = json.loads(content.decode("utf-8"))
    nodes = data.get("nodes") or []
    links = data.get("links") or data.get("edges") or []
    return len(nodes), len(links)


class SavePipeline:
    """Orchestrates saving graph snapshots as episodes."""

    def __init__(self, config: EpisodicConfig) -> None:
        """Initialize save pipeline.

        Args:
            config: Configuration
        """
        self.config = config
        self.store = SQLiteEpisodeStore(config.episode_db_path, create=False)

    def save(
        self,
        subgraph_id: str,
        source: Path,
        graphify_out: Path | None = None,
        *,
        skip_graphify: bool = False,
        graph_json_path: Path | None = None,
    ) -> SaveResult:
        """Save a graph snapshot as an episode.

        Flow:
        1. Validate subgraph_id and resolve paths
        2. Run graphify (unless skipped) to generate graph.json
        3. Read graph.json and compute its hash
        4. If snapshot unchanged, touch subgraph and return unchanged
        5. Parse graph, compute operations (bootstrap or diff)
        6. Create episode, update registration, persist

        Args:
            subgraph_id: Subgraph identifier (slug)
            source: Source path for graphify
            graphify_out: Override for graphify output directory
            skip_graphify: Skip running graphify
            graph_json_path: Path to existing graph.json (used if skip_graphify)

        Returns:
            SaveResult

        Raises:
            ValueError: If subgraph_id invalid
            FileNotFoundError: If source or graph.json not found
            GraphifyRunError: If graphify fails
            RuntimeError: If missing episodes for existing subgraph
        """
        # 1. Validate and resolve paths
        subgraph_id = validate_subgraph_id(subgraph_id)
        source = source.resolve()
        out_dir = (graphify_out or source / "graphify-out").resolve()
        graph_path = graph_json_path or (out_dir / "graph.json")

        # 2. Run graphify if not skipped
        if not skip_graphify:
            run_graphify(source, self.config.graphify.binary)
        if not graph_path.is_file():
            raise FileNotFoundError(f"graph.json not found: {graph_path}")

        # 3. Read and store snapshot
        content = graph_path.read_bytes()
        snapshot_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
        node_count, edge_count = read_graph_counts(content)
        now = utc_now_iso()

        # 4. Check if unchanged
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

        # 5. Parse new graph
        new_nodes, new_edges = parse_graph_json(json.loads(content.decode("utf-8")))

        # 6. Compute operations (bootstrap or diff)
        if existing is None:
            # First time seeing this subgraph - bootstrap
            operations, _ = bootstrap_operations(new_nodes, new_edges, subgraph_id)
            sequence = 1
            parent = None
        else:
            raise RuntimeError(
                "changed graph saves are unavailable until snapshot storage is added"
            )

        # 7. Create episode and persist
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

        # Update registration
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
