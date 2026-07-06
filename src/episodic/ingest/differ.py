from __future__ import annotations

import uuid
from typing import Any

from episodic.ingest.fingerprint import GraphEdge, GraphNode
from episodic.models.operations import (
    AssertEdgeOp,
    AssertNodeOp,
    LocalRef,
    Operation,
    RetractEdgeOp,
    RetractNodeOp,
    UpdateNodeOp,
)


def _new_global_id() -> str:
    return f"gn_{uuid.uuid4().hex[:12]}"


def _props_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    keys = set(a) | set(b)
    for key in keys:
        if a.get(key) != b.get(key):
            return False
    return True


def bootstrap_operations(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    subgraph_id: str,
    fingerprint_to_global: dict[str, str] | None = None,
) -> tuple[list[Operation], dict[str, str]]:
    mapping = dict(fingerprint_to_global or {})
    operations: list[Operation] = []

    for node in nodes:
        global_id = mapping.setdefault(node.fingerprint, _new_global_id())
        operations.append(
            AssertNodeOp(
                global_id=global_id,
                local_ref=LocalRef(
                    subgraph_id=subgraph_id,
                    local_id=node.local_id,
                    fingerprint=node.fingerprint,
                ),
                properties=node.properties,
            )
        )

    for edge in edges:
        src_gid = mapping[edge.source_fingerprint]
        tgt_gid = mapping[edge.target_fingerprint]
        operations.append(
            AssertEdgeOp(
                global_id=_new_global_id(),
                source_global_id=src_gid,
                target_global_id=tgt_gid,
                edge_type=edge.edge_type,
                source_fingerprint=edge.source_fingerprint,
                target_fingerprint=edge.target_fingerprint,
                properties=edge.properties,
            )
        )

    return operations, mapping


def diff_snapshots(
    old_nodes: list[GraphNode],
    old_edges: list[GraphEdge],
    new_nodes: list[GraphNode],
    new_edges: list[GraphEdge],
    subgraph_id: str,
    fingerprint_to_global: dict[str, str],
) -> tuple[list[Operation], dict[str, str]]:
    mapping = dict(fingerprint_to_global)
    operations: list[Operation] = []

    old_node_map = {n.fingerprint: n for n in old_nodes}
    new_node_map = {n.fingerprint: n for n in new_nodes}
    old_edge_map = {e.edge_key: e for e in old_edges}
    new_edge_map = {e.edge_key: e for e in new_edges}

    for fp, node in new_node_map.items():
        if fp not in old_node_map:
            global_id = mapping.setdefault(fp, _new_global_id())
            operations.append(
                AssertNodeOp(
                    global_id=global_id,
                    local_ref=LocalRef(
                        subgraph_id=subgraph_id,
                        local_id=node.local_id,
                        fingerprint=fp,
                    ),
                    properties=node.properties,
                )
            )
        elif not _props_equal(old_node_map[fp].properties, node.properties):
            global_id = mapping[fp]
            operations.append(
                UpdateNodeOp(
                    global_id=global_id,
                    local_ref=LocalRef(
                        subgraph_id=subgraph_id,
                        local_id=node.local_id,
                        fingerprint=fp,
                    ),
                    properties=node.properties,
                )
            )

    for fp, node in old_node_map.items():
        if fp not in new_node_map:
            operations.append(
                RetractNodeOp(
                    global_id=mapping[fp],
                    fingerprint=fp,
                )
            )

    for key, edge in new_edge_map.items():
        if key not in old_edge_map:
            src_gid = mapping[edge.source_fingerprint]
            tgt_gid = mapping[edge.target_fingerprint]
            operations.append(
                AssertEdgeOp(
                    global_id=_new_global_id(),
                    source_global_id=src_gid,
                    target_global_id=tgt_gid,
                    edge_type=edge.edge_type,
                    source_fingerprint=edge.source_fingerprint,
                    target_fingerprint=edge.target_fingerprint,
                    properties=edge.properties,
                )
            )

    for key in old_edge_map:
        if key not in new_edge_map:
            operations.append(
                RetractEdgeOp(
                    global_id=_new_global_id(),
                    edge_key=key,
                )
            )

    return operations, mapping


def build_fingerprint_map_from_bootstrap(
    operations: list[Operation],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for op in operations:
        if op.op.value == "ASSERT_NODE":
            mapping[op.local_ref.fingerprint] = op.global_id
    return mapping
