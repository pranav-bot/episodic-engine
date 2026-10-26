"""In-memory adjacency graph. Neighbors are map lookups, not edge scans."""

from __future__ import annotations

from episodic.model.types import Edge, HotNode, MergeConflict, Provenance


class MemoryGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, HotNode] = {}
        self.edges: dict[str, Edge] = {}
        self.outgoing: dict[str, dict[str, dict[str, str]]] = {}
        self.incoming: dict[str, dict[str, dict[str, str]]] = {}
        self.payloads: dict[str, bytes] = {}
        self.extra_provenance: dict[str, list[Provenance]] = {}
        self.conflicts: list[MergeConflict] = []

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
        if direction not in ("out", "in"):
            raise ValueError(f"unknown direction: {direction}")
        table = self.outgoing if direction == "out" else self.incoming
        bucket = table[node_id]
        if edge_type is None:
            ids = [item for group in bucket.values() for item in group]
        else:
            ids = list(bucket.get(edge_type, ()))
        return tuple(sorted(set(ids)))

    def put_payload(self, node_id: str, body: bytes) -> None:
        if node_id not in self.nodes:
            raise KeyError(node_id)
        self.payloads[node_id] = body

    def get_payload(self, node_id: str) -> bytes:
        return self.payloads[node_id]

    def merge(self, source: MemoryGraph) -> None:
        """Union source into this graph. source is left unchanged."""
        for node in source.nodes.values():
            current = self.nodes.get(node.id)
            if current is None:
                self.add_node(node)
            else:
                if current.label != node.label:
                    self._record_clash(node, "label", current.label, node.label)
                if current.type != node.type:
                    self._record_clash(node, "type", current.type, node.type)
            body = source.payloads.get(node.id)
            if body is not None and node.id not in self.payloads:
                self.payloads[node.id] = body
        for edge in source.edges.values():
            if edge.id not in self.edges:
                self.add_edge(edge)

    def _record_clash(self, node: HotNode, field: str, destination: str, source: str) -> None:
        if any(item.node_id == node.id and item.field == field for item in self.conflicts):
            return
        self.conflicts.append(MergeConflict(node.id, field, destination, source))
        recorded = self.extra_provenance.setdefault(node.id, [])
        if node.provenance_ref not in recorded:
            recorded.append(node.provenance_ref)
