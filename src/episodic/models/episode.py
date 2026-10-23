"""Episode models for versioned graph history.

An Episode represents one snapshot in the timeline - it contains the diff
(operations) from the previous snapshot plus metadata and auto-computed stats.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from episodic.models.operations import Operation


class EpisodeStats(BaseModel):
    """Statistics about operations in an episode."""

    ops_total: int = 0           # Total number of operations
    nodes_added: int = 0         # Number of ASSERT_NODE operations
    nodes_retracted: int = 0     # Number of RETRACT_NODE operations
    nodes_updated: int = 0       # Number of UPDATE_NODE operations
    edges_added: int = 0         # Number of ASSERT_EDGE operations
    edges_retracted: int = 0     # Number of RETRACT_EDGE operations


class Episode(BaseModel):
    """A versioned snapshot/diff in the episodic timeline.

    Each episode represents one regeneration of a graphify subgraph.
    For the first snapshot it's a bootstrap (all asserts). For subsequent
    snapshots it's a diff (adds/updates/retracts).
    """

    episode_id: str                    # Unique ID like "subgraph__ep_000001"
    sequence: int                      # Sequence number per subgraph (1, 2, 3...)
    recorded_at: str                   # UTC timestamp in ISO format with Z suffix
    subgraph_id: str                   # ID of the tracked subgraph
    snapshot_hash: str                 # SHA256 hash of full snapshot blob (sha256:...)
    trigger_type: str = "graphify_regen"  # What triggered this episode
    operations: list[Operation] = Field(default_factory=list)  # List of changes
    stats: EpisodeStats = Field(default_factory=EpisodeStats)  # Auto-computed stats
    parent_episode_id: str | None = None  # Previous episode in timeline

    def model_post_init(self, __context: Any) -> None:
        """Auto-compute stats from operations if not explicitly set."""
        if not self.stats.ops_total:
            self.stats = compute_stats(self.operations)


def compute_stats(operations: list[Operation]) -> EpisodeStats:
    """Compute statistics by counting operations by type.

    Args:
        operations: List of operations to analyze

    Returns:
        EpisodeStats with counts of each operation type
    """
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
