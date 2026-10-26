"""Hot graph records. Bodies do not belong on these types."""

from __future__ import annotations

from dataclasses import dataclass

EDGE_TYPES = frozenset({"contains", "imports", "calls", "references", "describes"})


@dataclass(frozen=True)
class Provenance:
    source_path: str
    locator: str | None = None


@dataclass(frozen=True)
class HotNode:
    id: str
    type: str
    label: str
    provenance_ref: Provenance


@dataclass(frozen=True)
class Edge:
    id: str
    type: str
    source: str
    target: str

    def __post_init__(self) -> None:
        if self.type not in EDGE_TYPES:
            raise ValueError(f"unknown edge type: {self.type}")


@dataclass(frozen=True)
class MergeConflict:
    node_id: str
    field: str
    destination: str
    source: str
