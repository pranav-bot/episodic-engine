"""SQLite episode store.

Persistent storage for subgraph registrations and episodes using SQLite.
Handles schema creation, serialization/deserialization of operations and stats.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterator

from episodic.models.episode import Episode
from episodic.models.subgraph import SubgraphRegistration, SubgraphStatus


class InitNotCompleteError(RuntimeError):
    """Raised when initialization is not complete."""
    pass


class SQLiteEpisodeStore:
    """SQLite-backed store for episodes and subgraph registrations."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS subgraphs (
        subgraph_id TEXT PRIMARY KEY,
        source_path TEXT NOT NULL,
        graphify_out_path TEXT NOT NULL,
        latest_snapshot_hash TEXT,
        registered_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS episodes (
        episode_id TEXT PRIMARY KEY,
        sequence INTEGER NOT NULL,
        recorded_at TEXT NOT NULL,
        subgraph_id TEXT NOT NULL,
        snapshot_hash TEXT NOT NULL,
        trigger_type TEXT NOT NULL,
        operations_json TEXT NOT NULL,
        stats_json TEXT NOT NULL,
        parent_episode_id TEXT,
        UNIQUE(subgraph_id, sequence),
        FOREIGN KEY (subgraph_id) REFERENCES subgraphs(subgraph_id)
    );

    CREATE INDEX IF NOT EXISTS idx_episodes_subgraph
        ON episodes(subgraph_id, sequence);
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize store and create schema if needed.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        """Create database connection with row factory and foreign keys enabled.

        Returns:
            SQLite connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        """Initialize database schema."""
        with self._connect() as conn:
            conn.executescript(self.SCHEMA)

    def upsert_subgraph(self, reg: SubgraphRegistration) -> None:
        """Insert or update a subgraph registration.

        On conflict, updates source_path, graphify_out_path, latest_snapshot_hash, last_seen_at.

        Args:
            reg: Subgraph registration to store
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO subgraphs (
                    subgraph_id, source_path, graphify_out_path,
                    latest_snapshot_hash, registered_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(subgraph_id) DO UPDATE SET
                    source_path = excluded.source_path,
                    graphify_out_path = excluded.graphify_out_path,
                    latest_snapshot_hash = excluded.latest_snapshot_hash,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    reg.subgraph_id,
                    reg.source_path,
                    reg.graphify_out_path,
                    reg.latest_snapshot_hash,
                    reg.registered_at,
                    reg.last_seen_at,
                ),
            )

    def touch_subgraph(self, subgraph_id: str, last_seen_at: str) -> None:
        """Update last_seen_at for a subgraph.

        Args:
            subgraph_id: Subgraph to update
            last_seen_at: New timestamp

        Raises:
            KeyError: If subgraph doesn't exist
        """
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE subgraphs SET last_seen_at = ? WHERE subgraph_id = ?",
                (last_seen_at, subgraph_id),
            )
            if cur.rowcount == 0:
                raise KeyError(f"unknown subgraph: {subgraph_id}")

    def get_subgraph(self, subgraph_id: str) -> SubgraphRegistration | None:
        """Get subgraph registration by ID.

        Args:
            subgraph_id: Subgraph ID

        Returns:
            Registration or None if not found
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM subgraphs WHERE subgraph_id = ?",
                (subgraph_id,),
            ).fetchone()
        if row is None:
            return None
        return SubgraphRegistration(**dict(row))

    def delete_subgraph(self, subgraph_id: str) -> bool:
        """Delete a subgraph registration and all of its episodes.

        Returns:
            True if the subgraph existed, otherwise False.
        """
        with self._connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM subgraphs WHERE subgraph_id = ?",
                (subgraph_id,),
            ).fetchone()
            if exists is None:
                return False
            conn.execute("DELETE FROM episodes WHERE subgraph_id = ?", (subgraph_id,))
            conn.execute("DELETE FROM subgraphs WHERE subgraph_id = ?", (subgraph_id,))
        return True

    def list_subgraphs(self) -> list[SubgraphRegistration]:
        """List all subgraph registrations.

        Returns:
            List of registrations ordered by subgraph_id
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM subgraphs ORDER BY subgraph_id"
            ).fetchall()
        return [SubgraphRegistration(**dict(row)) for row in rows]

    def append_episode(self, episode: Episode) -> None:
        """Append an episode to the store.

        Serializes operations as JSON array and stats as JSON.

        Args:
            episode: Episode to store
        """
        ops_json = json.dumps(
            [op.model_dump(mode="json") for op in episode.operations]
        )
        stats_json = episode.stats.model_dump_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO episodes (
                    episode_id, sequence, recorded_at, subgraph_id,
                    snapshot_hash, trigger_type, operations_json,
                    stats_json, parent_episode_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    episode.episode_id,
                    episode.sequence,
                    episode.recorded_at,
                    episode.subgraph_id,
                    episode.snapshot_hash,
                    episode.trigger_type,
                    ops_json,
                    stats_json,
                    episode.parent_episode_id,
                ),
            )

    def get_episode(self, episode_id: str) -> Episode | None:
        """Get episode by ID.

        Args:
            episode_id: Episode ID

        Returns:
            Episode or None if not found
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM episodes WHERE episode_id = ?",
                (episode_id,),
            ).fetchone()
        return self._row_to_episode(row) if row else None

    def latest_episode(self, subgraph_id: str) -> Episode | None:
        """Get latest episode for a subgraph.

        Args:
            subgraph_id: Subgraph ID

        Returns:
            Latest episode or None if no episodes
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM episodes
                WHERE subgraph_id = ?
                ORDER BY sequence DESC
                LIMIT 1
                """,
                (subgraph_id,),
            ).fetchone()
        return self._row_to_episode(row) if row else None

    def next_sequence(self, subgraph_id: str) -> int:
        """Get next sequence number for a subgraph.

        Args:
            subgraph_id: Subgraph ID

        Returns:
            Next sequence number (1 if no episodes)
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT MAX(sequence) FROM episodes WHERE subgraph_id = ?",
                (subgraph_id,),
            ).fetchone()
        current = row[0] if row and row[0] is not None else 0
        return current + 1

    def episode_count(self, subgraph_id: str) -> int:
        """Count episodes for a subgraph.

        Args:
            subgraph_id: Subgraph ID

        Returns:
            Number of episodes
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE subgraph_id = ?",
                (subgraph_id,),
            ).fetchone()
        return int(row[0]) if row else 0

    def list_status(self) -> list[SubgraphStatus]:
        """List status for all subgraphs.

        Returns:
            List of SubgraphStatus
        """
        statuses: list[SubgraphStatus] = []
        for reg in self.list_subgraphs():
            statuses.append(
                SubgraphStatus(
                    subgraph_id=reg.subgraph_id,
                    latest_snapshot_hash=reg.latest_snapshot_hash,
                    episode_count=self.episode_count(reg.subgraph_id),
                    last_seen_at=reg.last_seen_at,
                    source_path=reg.source_path,
                )
            )
        return statuses

    def episodes_for_subgraph(self, subgraph_id: str) -> Iterator[Episode]:
        """Iterate episodes for a subgraph in order.

        Args:
            subgraph_id: Subgraph ID

        Yields:
            Episodes in ascending sequence order
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM episodes
                WHERE subgraph_id = ?
                ORDER BY sequence ASC
                """,
                (subgraph_id,),
            ).fetchall()
        for row in rows:
            episode = self._row_to_episode(row)
            if episode:
                yield episode

    @staticmethod
    def _row_to_episode(row: sqlite3.Row | None) -> Episode | None:
        """Convert database row to Episode model.

        Deserializes operations_json and stats_json.

        Args:
            row: Database row

        Returns:
            Episode or None
        """
        if row is None:
            return None
        data = dict(row)
        operations = json.loads(data.pop("operations_json"))
        stats = json.loads(data.pop("stats_json"))
        return Episode.model_validate(
            {
                **data,
                "operations": operations,
                "stats": stats,
            }
        )
