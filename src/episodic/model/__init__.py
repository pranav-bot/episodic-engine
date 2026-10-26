"""Hot graph contract. Adjacency lives in demo-graph/test-graph."""

from episodic.model.identity import edge_id, node_id
from episodic.model.types import EDGE_TYPES, Edge, HotNode, MergeConflict, Provenance

__all__ = [
    "EDGE_TYPES",
    "Edge",
    "HotNode",
    "MergeConflict",
    "Provenance",
    "edge_id",
    "node_id",
]
