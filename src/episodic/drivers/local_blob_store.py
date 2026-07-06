from __future__ import annotations

import hashlib
from pathlib import Path


class LocalBlobStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def hash_content(content: bytes) -> str:
        digest = hashlib.sha256(content).hexdigest()
        return f"sha256:{digest}"

    def _path_for_hash(self, content_hash: str) -> Path:
        hex_digest = content_hash.removeprefix("sha256:")
        shard = hex_digest[:2]
        return self.base_dir / shard / f"{content_hash}.json"

    def put(self, content: bytes) -> str:
        content_hash = self.hash_content(content)
        target = self._path_for_hash(content_hash)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return content_hash

    def get(self, content_hash: str) -> bytes:
        path = self._path_for_hash(content_hash)
        if not path.is_file():
            raise FileNotFoundError(f"snapshot not found: {content_hash}")
        return path.read_bytes()

    def exists(self, content_hash: str) -> bool:
        return self._path_for_hash(content_hash).is_file()
