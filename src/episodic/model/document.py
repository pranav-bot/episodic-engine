"""Read and write a MemoryGraph as graph.json."""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
from typing import Any

from episodic.model.identity import edge_id
from episodic.model.types import EDGE_TYPES, Edge, HotNode, MergeConflict, Provenance

_MEMORY = None


def memory_graph_class():
    """Load the shipped adjacency graph. This folder name is not a package."""
    global _MEMORY
    if _MEMORY is None:
        path = Path(__file__).resolve().parents[3] / "demo-graph" / "test-graph" / "adjacency.py"
        spec = importlib.util.spec_from_file_location("test_graph_adjacency", path)
        if spec is None or spec.loader is None:
            raise FileNotFoundError(f"graph model is missing: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _MEMORY = module.MemoryGraph
    return _MEMORY


def empty_graph_text(name: str) -> str:
    return json.dumps(_document(name, memory_graph_class()()), indent=2) + "\n"


def load_graph(path: Path) -> tuple[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("nodes"), list):
        raise ValueError(f"invalid graph.json: {path}")
    try:
        graph = memory_graph_class()()
        for raw in data["nodes"]:
            provenance = raw["provenance"]
            graph.add_node(
                HotNode(
                    str(raw["id"]),
                    str(raw["type"]),
                    str(raw["label"]),
                    Provenance(str(provenance["source_path"]), provenance.get("locator")),
                )
            )
        for node_id, payload in (data.get("payloads") or {}).items():
            graph.put_payload(str(node_id), _decode_payload(payload))
        for raw in data.get("edges") or []:
            kind = str(raw["type"])
            if kind not in EDGE_TYPES:
                raise ValueError(f"unknown edge type: {kind}")
            source = str(raw["source"])
            target = str(raw["target"])
            graph.add_edge(
                Edge(str(raw.get("id") or edge_id(source, target, kind)), kind, source, target)
            )
        for raw in data.get("conflicts") or []:
            graph.conflicts.append(
                MergeConflict(
                    str(raw["node_id"]),
                    str(raw["field"]),
                    str(raw["destination"]),
                    str(raw["source"]),
                )
            )
        for node_id, refs in (data.get("extra_provenance") or {}).items():
            graph.extra_provenance[str(node_id)] = [
                Provenance(str(ref.get("source_path") or ""), ref.get("locator")) for ref in refs
            ]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"invalid graph.json: {path}") from exc
    name = data.get("name")
    return (name if isinstance(name, str) else path.parent.name), graph


def save_graph(path: Path, name: str, graph: Any) -> None:
    from episodic.graph import write_text_atomic

    write_text_atomic(path, json.dumps(_document(name, graph), ensure_ascii=False, indent=2) + "\n")


def _document(name: str, graph: Any) -> dict[str, Any]:
    return {
        "name": name,
        "nodes": [
            {
                "id": node.id,
                "type": node.type,
                "label": node.label,
                "provenance": {
                    "source_path": node.provenance_ref.source_path,
                    "locator": node.provenance_ref.locator,
                },
            }
            for node in graph.nodes.values()
        ],
        "edges": [
            {"id": edge.id, "type": edge.type, "source": edge.source, "target": edge.target}
            for edge in graph.edges.values()
        ],
        "payloads": {node_id: _encode_payload(body) for node_id, body in graph.payloads.items()},
        "conflicts": [
            {
                "node_id": item.node_id,
                "field": item.field,
                "destination": item.destination,
                "source": item.source,
            }
            for item in graph.conflicts
        ],
        "extra_provenance": {
            node_id: [
                {"source_path": ref.source_path, "locator": ref.locator} for ref in refs
            ]
            for node_id, refs in graph.extra_provenance.items()
        },
    }


def _encode_payload(body: bytes) -> dict[str, str]:
    try:
        return {"text": body.decode("utf-8")}
    except UnicodeDecodeError:
        return {"base64": base64.b64encode(body).decode("ascii")}


def _decode_payload(payload: dict[str, str]) -> bytes:
    if "text" in payload:
        return payload["text"].encode("utf-8")
    return base64.b64decode(payload["base64"])
