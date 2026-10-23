"""Graphify JSON adapter.

Normalizes graphify's output (which may vary in field names/structure)
into GraphNode and GraphEdge objects for diffing.
"""

from __future__ import annotations

from typing import Any

from episodic.ingest.fingerprint import GraphEdge, GraphNode, compute_fingerprint


def _node_props(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract properties from raw node, excluding reserved keys.

    Reserved keys (id, source, target, key, type, label) are handled separately.
    Copies back label, type, file/path as file, qualified_name as properties.

    Args:
        raw: Raw node dict from graphify

    Returns:
        Properties dict
    """
    reserved = {"id", "source", "target", "key", "type", "label"}
    props = {k: v for k, v in raw.items() if k not in reserved and v is not None}
    if "label" in raw:
        props.setdefault("label", raw["label"])
    if "type" in raw:
        props.setdefault("type", raw["type"])
    if raw.get("file"):
        props.setdefault("file", raw["file"])
    if raw.get("path"):
        props.setdefault("file", raw["path"])
    if raw.get("qualified_name"):
        props.setdefault("qualified_name", raw["qualified_name"])
    return props


def parse_graph_json(data: dict[str, Any]) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Parse graphify JSON into normalized GraphNode and GraphEdge lists.

    Accepts nodes and links or edges. Resolves edges by local node IDs.
    Skips edges with missing source/target nodes.

    Args:
        data: Graphify JSON dict

    Returns:
        Tuple of (nodes, edges)
    """
    raw_nodes = data.get("nodes") or []
    raw_links = data.get("links") or data.get("edges") or []

    nodes: list[GraphNode] = []
    node_by_id: dict[str, GraphNode] = {}

    # Parse nodes
    for raw in raw_nodes:
        local_id = str(raw.get("id"))
        props = _node_props(raw)
        # Compute fingerprint using raw + props for extra context
        fingerprint = compute_fingerprint({**raw, **props})
        node = GraphNode(local_id=local_id, fingerprint=fingerprint, properties=props)
        nodes.append(node)
        node_by_id[local_id] = node

    # Parse edges
    edges: list[GraphEdge] = []
    for idx, raw in enumerate(raw_links):
        source_id = str(raw.get("source"))
        target_id = str(raw.get("target"))
        source = node_by_id.get(source_id)
        target = node_by_id.get(target_id)
        if source is None or target is None:
            continue  # Skip edges with missing nodes
        # Determine edge type
        edge_type = str(raw.get("type") or raw.get("label") or raw.get("key") or "related")
        props = _node_props(raw)
        edge = GraphEdge(
            local_id=str(raw.get("id") or f"edge_{idx}"),
            source_local_id=source_id,
            target_local_id=target_id,
            source_fingerprint=source.fingerprint,
            target_fingerprint=target.fingerprint,
            edge_type=edge_type,
            properties=props,
        )
        edges.append(edge)

    return nodes, edges
