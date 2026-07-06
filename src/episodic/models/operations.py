from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


class OpType(StrEnum):
    ASSERT_NODE = "ASSERT_NODE"
    UPDATE_NODE = "UPDATE_NODE"
    RETRACT_NODE = "RETRACT_NODE"
    ASSERT_EDGE = "ASSERT_EDGE"
    RETRACT_EDGE = "RETRACT_EDGE"


class LocalRef(BaseModel):
    subgraph_id: str
    local_id: str
    fingerprint: str


class AssertNodeOp(BaseModel):
    op: Literal[OpType.ASSERT_NODE] = OpType.ASSERT_NODE
    global_id: str
    local_ref: LocalRef
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class UpdateNodeOp(BaseModel):
    op: Literal[OpType.UPDATE_NODE] = OpType.UPDATE_NODE
    global_id: str
    local_ref: LocalRef
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class RetractNodeOp(BaseModel):
    op: Literal[OpType.RETRACT_NODE] = OpType.RETRACT_NODE
    global_id: str
    fingerprint: str
    reason: str = "removed_in_snapshot_diff"


class AssertEdgeOp(BaseModel):
    op: Literal[OpType.ASSERT_EDGE] = OpType.ASSERT_EDGE
    global_id: str
    source_global_id: str
    target_global_id: str
    edge_type: str
    source_fingerprint: str
    target_fingerprint: str
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class RetractEdgeOp(BaseModel):
    op: Literal[OpType.RETRACT_EDGE] = OpType.RETRACT_EDGE
    global_id: str
    edge_key: str
    reason: str = "removed_in_snapshot_diff"


Operation = Annotated[
    Union[AssertNodeOp, UpdateNodeOp, RetractNodeOp, AssertEdgeOp, RetractEdgeOp],
    Field(discriminator="op"),
]
