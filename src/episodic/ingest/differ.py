"""Graph diffing engine.

Computes operations (bootstrap or incremental diff) between graph snapshots.
Uses fingerprints for stable identity and assigns episodic global IDs.
"""

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
    """Generate a new episodic global ID.

    Returns:
        ID in format "gn_<12 hex chars>"
    """
    return f"gn_{uuid.uuid4().hex[:12]}"


def _props_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Compare two property dicts for equality.

    Args:
        a: First dict
        b: Second dict

    Returns:
        True if all keys/values are equal
    """
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
    """Create bootstrap operations for first snapshot.

    Assigns global IDs to all nodes/edges and creates ASSERT operations.

    Args:
        nodes: List of graph nodes
        edges: List of graph edges
        subgraph_id: ID of the subgraph
        fingerprint_to_global: Optional existing mapping to reuse

    Returns:
        Tuple of (operations list, updated fingerprint->global_id mapping)
    """
    mapping = dict(fingerprint_to_global or {})
    operations: list[Operation] = []

    # Create ASSERT_NODE for all nodes
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

    # Create ASSERT_EDGE for all edges
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
    """Compute diff operations between old and new snapshots.

    Uses fingerprints for identity. Nodes/edges with same fingerprint that
    existed before keep their global IDs. New ones get new global IDs.

    Args:
        old_nodes: Nodes from previous snapshot
        old_edges: Edges from previous snapshot
        new_nodes: Nodes from new snapshot
        new_edges: Edges from new snapshot
        subgraph_id: ID of the subgraph
        fingerprint_to_global: Mapping from previous episode (must know existing global IDs)

    Returns:
        Tuple of (operations list, updated fingerprint->global_id mapping)
    """
    mapping = dict(fingerprint_to_global)
    operations: list[Operation] = []

    # Build maps by fingerprint/edge_key
    old_node_map = {n.fingerprint: n for n in old_nodes}
    new_node_map = {n.fingerprint: n for n in new_nodes}
    old_edge_map = {e.edge_key: e for e in old_edges}
    new_edge_map = {e.edge_key: e for e in new_edges}

    # Process nodes
    # 1. New nodes or updated nodes
    for fp, node in new_node_map.items():
        if fp not in old_node_map:
            # New node - assign global ID
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
            # Existing node with changed properties
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

    # 2. Removed nodes
    for fp, node in old_node_map.items():
        if fp not in new_node_map:
            operations.append(
                RetractNodeOp(
                    global_id=mapping[fp],
                    fingerprint=fp,
                )
            )

    # Process edges
    # 1. New edges
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

    # 2. Removed edges
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
    """Build fingerprint->global_id mapping from a prior episode's operations.

    Extracts mappings from ASSERT_NODE operations in the episode.

    Args:
        operations: Operations from prior episode

    Returns:
        Mapping of fingerprint to global_id
    """
    mapping: dict[str, str] = {}
    for op in operations:
        if op.op.value == "ASSERT_NODE":
            mapping[op.local_ref.fingerprint] = op.global_id
    return mapping
