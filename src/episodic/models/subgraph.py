from __future__ import annotations

from pydantic import BaseModel


class SubgraphRegistration(BaseModel):
    subgraph_id: str
    source_path: str
    graphify_out_path: str
    latest_snapshot_hash: str | None = None
    registered_at: str
    last_seen_at: str


class SubgraphStatus(BaseModel):
    subgraph_id: str
    latest_snapshot_hash: str | None
    episode_count: int
    last_seen_at: str | None
    source_path: str
