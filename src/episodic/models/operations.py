"""Operation models for episodic memory.

Defines the 5 operation types that describe changes between graph snapshots:
- ASSERT_NODE: create a node
- UPDATE_NODE: change node properties
- RETRACT_NODE: remove a node
- ASSERT_EDGE: create an edge/relationship
- RETRACT_EDGE: remove an edge/relationship

All operations use a discriminated union on the 'op' field so Pydantic can
deserialize JSON from SQLite back to the correct concrete model.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


class OpType(StrEnum):
    """Enumeration of all possible graph operations."""

    ASSERT_NODE = "ASSERT_NODE"      # Create a new node
    UPDATE_NODE = "UPDATE_NODE"      # Update properties of existing node
    RETRACT_NODE = "RETRACT_NODE"    # Remove/delete a node
    ASSERT_EDGE = "ASSERT_EDGE"      # Create a new edge/relationship
    RETRACT_EDGE = "RETRACT_EDGE"    # Remove/delete an edge/relationship


class LocalRef(BaseModel):
    """Reference tying an operation back to graphify's local view.

    Used to track where we saw the node in a specific subgraph/snapshot.
    """

    subgraph_id: str      # ID of the tracked subgraph
    local_id: str         # ID assigned by graphify in this snapshot
    fingerprint: str      # Stable fingerprint computed from node semantics


class AssertNodeOp(BaseModel):
    """Create a new node in the global graph."""

    op: Literal[OpType.ASSERT_NODE] = OpType.ASSERT_NODE
    global_id: str                        # Episodic-assigned stable global ID (gn_...)
    local_ref: LocalRef                   # Reference to local graphify node
    properties: dict[str, Any] = Field(default_factory=dict)  # Node properties
    confidence: float = 1.0               # Confidence score (default 1.0)


class UpdateNodeOp(BaseModel):
    """Update properties of an existing node.

    The node is identified by global_id; properties are merged/updated.
    """

    op: Literal[OpType.UPDATE_NODE] = OpType.UPDATE_NODE
    global_id: str                        # Must match existing node's global_id
    local_ref: LocalRef                   # Reference to local graphify node
    properties: dict[str, Any] = Field(default_factory=dict)  # Updated properties
    confidence: float = 1.0               # Confidence score (default 1.0)


class RetractNodeOp(BaseModel):
    """Remove/tombstone an existing node."""

    op: Literal[OpType.RETRACT_NODE] = OpType.RETRACT_NODE
    global_id: str                        # Must match existing node's global_id
    fingerprint: str                      # Fingerprint of removed node (for traceability)
    reason: str = "removed_in_snapshot_diff"  # Why it was removed


class AssertEdgeOp(BaseModel):
    """Create a new edge/relationship between two nodes."""

    op: Literal[OpType.ASSERT_EDGE] = OpType.ASSERT_EDGE
    global_id: str                        # Episodic-assigned global ID for this edge
    source_global_id: str                 # global_id of source node
    target_global_id: str                 # global_id of target node
    edge_type: str                        # Type of relationship (e.g., CALLS, IMPORTS)
    source_fingerprint: str               # Fingerprint of source node
    target_fingerprint: str               # Fingerprint of target node
    properties: dict[str, Any] = Field(default_factory=dict)  # Edge properties
    confidence: float = 1.0               # Confidence score (default 1.0)


class RetractEdgeOp(BaseModel):
    """Remove/tombstone an existing edge."""

    op: Literal[OpType.RETRACT_EDGE] = OpType.RETRACT_EDGE
    global_id: str                        # Global ID for this retract op
    edge_key: str                         # Key identifying the edge (src_fp|type|tgt_fp)
    reason: str = "removed_in_snapshot_diff"  # Why it was removed


# Discriminated union - Pydantic uses 'op' field to select correct model
Operation = Annotated[
    Union[AssertNodeOp, UpdateNodeOp, RetractNodeOp, AssertEdgeOp, RetractEdgeOp],
    Field(discriminator="op"),
]

