"""Hot-graph identity. Layout is part of the id, so do not reorder the fields."""

from __future__ import annotations

import hashlib

def _digest(parts: tuple[str, ...]) -> str:
    raw = "\0".join(("v1", *parts))
    return hashlib.sha256(raw.encode()).hexdigest()


def node_id(node_type: str, source_path: str, symbol: str) -> str:
    """sha256 of v1, node type, source path, and symbol or heading or span."""
    return _digest((node_type, source_path, symbol))


def edge_id(source: str, target: str, edge_type: str) -> str:
    """sha256 of v1, source id, target id, and edge type."""
    return _digest((source, target, edge_type))
