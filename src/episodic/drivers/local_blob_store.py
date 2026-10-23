"""Local blob store for content-addressed snapshots.

Stores full graph JSON snapshots by SHA256 hash with sharding
(first 2 hex chars) to avoid large flat directories.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


class LocalBlobStore:
    """Content-addressed storage for graph snapshots."""

    def __init__(self, base_dir: Path) -> None:
        """Initialize blob store.

        Args:
            base_dir: Base directory for storing blobs
        """
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def hash_content(content: bytes) -> str:
        """Compute SHA256 hash of content.

        Args:
            content: Raw bytes to hash

        Returns:
            Hash string in format "sha256:<hex>"
        """
        digest = hashlib.sha256(content).hexdigest()
        return f"sha256:{digest}"

    def _path_for_hash(self, content_hash: str) -> Path:
        """Get file path for a content hash with sharding.

        Uses first 2 hex chars as subdirectory to avoid huge flat dirs.

        Args:
            content_hash: Hash string like "sha256:..."

        Returns:
            Path to blob file
        """
        hex_digest = content_hash.removeprefix("sha256:")
        shard = hex_digest[:2]
        return self.base_dir / shard / f"{content_hash}.json"

    def put(self, content: bytes) -> str:
        """Store content if not already present (deduplication).

        Args:
            content: Raw bytes to store

        Returns:
            Content hash of stored blob
        """
        content_hash = self.hash_content(content)
        target = self._path_for_hash(content_hash)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return content_hash

    def get(self, content_hash: str) -> bytes:
        """Retrieve content by hash.

        Args:
            content_hash: Hash string like "sha256:..."

        Returns:
            Raw bytes of stored content

        Raises:
            FileNotFoundError: If blob doesn't exist
        """
        path = self._path_for_hash(content_hash)
        if not path.is_file():
            raise FileNotFoundError(f"snapshot not found: {content_hash}")
        return path.read_bytes()

    def exists(self, content_hash: str) -> bool:
        """Check if blob exists.

        Args:
            content_hash: Hash string like "sha256:..."

        Returns:
            True if blob exists
        """
        return self._path_for_hash(content_hash).is_file()
