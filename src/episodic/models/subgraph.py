"""Subgraph models for registration and status.

Represents tracked subgraphs and their status in the system.
"""

from __future__ import annotations

from pydantic import BaseModel


class SubgraphRegistration(BaseModel):
    """Registration record for a tracked subgraph.

    Stored in the subgraphs table to track metadata about each subgraph
    being monitored for changes.
    """

    subgraph_id: str                # Unique identifier (slug like "myrepo-code")
    source_path: str                # Path to source corpus analyzed by graphify
    graphify_out_path: str          # Path to graphify output directory
    latest_snapshot_hash: str | None = None  # Hash of most recent snapshot
    registered_at: str              # When first registered (UTC ISO format)
    last_seen_at: str               # Last time we saw this subgraph (UTC ISO format)


class SubgraphStatus(BaseModel):
    """Status summary for a subgraph (used by status command)."""

    subgraph_id: str                # Unique identifier
    latest_snapshot_hash: str | None  # Hash of most recent snapshot
    episode_count: int              # Number of episodes in history
    last_seen_at: str | None        # Last time we saw this subgraph
    source_path: str                # Path to source corpus
