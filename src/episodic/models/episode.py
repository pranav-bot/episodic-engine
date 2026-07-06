from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from episodic.models.operations import Operation


class EpisodeStats(BaseModel):
    ops_total: int = 0
    nodes_added: int = 0
    nodes_retracted: int = 0
    nodes_updated: int = 0
    edges_added: int = 0
    edges_retracted: int = 0


class Episode(BaseModel):
    episode_id: str
    sequence: int
    recorded_at: str
    subgraph_id: str
    snapshot_hash: str
    trigger_type: str = "graphify_regen"
    operations: list[Operation] = Field(default_factory=list)
    stats: EpisodeStats = Field(default_factory=EpisodeStats)
    parent_episode_id: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if not self.stats.ops_total:
            self.stats = compute_stats(self.operations)


def compute_stats(operations: list[Operation]) -> EpisodeStats:
    stats = EpisodeStats(ops_total=len(operations))
    for op in operations:
        match op.op.value:
            case "ASSERT_NODE":
                stats.nodes_added += 1
            case "UPDATE_NODE":
                stats.nodes_updated += 1
            case "RETRACT_NODE":
                stats.nodes_retracted += 1
            case "ASSERT_EDGE":
                stats.edges_added += 1
            case "RETRACT_EDGE":
                stats.edges_retracted += 1
    return stats
