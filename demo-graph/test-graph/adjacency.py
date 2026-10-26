"""In-memory adjacency graph. Neighbors are map lookups, not edge scans."""

from __future__ import annotations

from episodic.model.types import Edge, HotNode


class MemoryGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, HotNode] = {}
        self.edges: dict[str, Edge] = {}
        self.outgoing: dict[str, dict[str, dict[str, str]]] = {}
        self.incoming: dict[str, dict[str, dict[str, str]]] = {}
        self.payloads: dict[str, bytes] = {}

    def add_node(self, node: HotNode) -> HotNode:
        found = self.nodes.get(node.id)
        if found is not None:
            return found
        self.nodes[node.id] = node
        self.outgoing[node.id] = {}
        self.incoming[node.id] = {}
        return node

    def add_edge(self, edge: Edge) -> Edge:
        if edge.source not in self.nodes:
            raise KeyError(edge.source)
        if edge.target not in self.nodes:
            raise KeyError(edge.target)
        found = self.edges.get(edge.id)
        if found is not None:
            return found
        self.edges[edge.id] = edge
        self.outgoing[edge.source].setdefault(edge.type, {})[edge.target] = edge.id
        self.incoming[edge.target].setdefault(edge.type, {})[edge.source] = edge.id
        return edge

    def neighbors(
        self,
        node_id: str,
        *,
        edge_type: str | None = None,
        direction: str = "out",
    ) -> tuple[str, ...]:
        if node_id not in self.nodes:
            raise KeyError(node_id)
        table = self.outgoing if direction == "out" else self.incoming
        bucket = table[node_id]
        if edge_type is None:
            ids = [item for group in bucket.values() for item in group]
        else:
            ids = list(bucket.get(edge_type, ()))
        return tuple(sorted(ids))

    def put_payload(self, node_id: str, body: bytes) -> None:
        if node_id not in self.nodes:
            raise KeyError(node_id)
        self.payloads[node_id] = body

    def get_payload(self, node_id: str) -> bytes:
        return self.payloads[node_id]
