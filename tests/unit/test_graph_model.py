import importlib.util
from pathlib import Path

import pytest

from episodic.model import EDGE_TYPES, Edge, HotNode, Provenance, edge_id, node_id


def memory_graph():
    path = Path(__file__).resolve().parents[2] / "demo-graph" / "test-graph" / "adjacency.py"
    spec = importlib.util.spec_from_file_location("test_graph_adjacency", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.MemoryGraph()


def hot_node(name: str, symbol: str) -> HotNode:
    return HotNode(
        node_id("symbol", "src/auth.py", symbol),
        "symbol",
        name,
        Provenance("src/auth.py", symbol),
    )


def test_node_id_is_stable_hex():
    first = node_id("symbol", "src/auth.py", "login")
    second = node_id("symbol", "src/auth.py", "login")

    assert first == second
    assert len(first) == 64
    assert first != node_id("symbol", "src/auth.py", "logout")


@pytest.mark.parametrize("edge_type", sorted(EDGE_TYPES))
def test_locked_edge_types_construct(edge_type):
    Edge(edge_id("a", "b", edge_type), edge_type, "a", "b")


def test_unknown_edge_type_is_rejected():
    with pytest.raises(ValueError):
        Edge(edge_id("a", "b", "mentions"), "mentions", "a", "b")


def test_neighbors_returns_only_the_requested_type():
    graph = memory_graph()
    caller = hot_node("login", "login")
    callee = hot_node("check", "check")
    other = hot_node("format", "format")
    graph.add_node(caller)
    graph.add_node(callee)
    graph.add_node(other)
    graph.add_edge(Edge(edge_id(caller.id, callee.id, "calls"), "calls", caller.id, callee.id))
    graph.add_edge(Edge(edge_id(caller.id, other.id, "imports"), "imports", caller.id, other.id))

    assert graph.neighbors(caller.id, edge_type="calls") == (callee.id,)
    assert graph.neighbors(callee.id, edge_type="calls", direction="in") == (caller.id,)


def test_same_pair_can_have_two_edge_types():
    graph = memory_graph()
    left = hot_node("left", "left")
    right = hot_node("right", "right")
    graph.add_node(left)
    graph.add_node(right)
    calls = graph.add_edge(Edge(edge_id(left.id, right.id, "calls"), "calls", left.id, right.id))
    refs = graph.add_edge(
        Edge(edge_id(left.id, right.id, "references"), "references", left.id, right.id)
    )

    assert calls.id != refs.id


def test_readding_the_same_fingerprint_keeps_one_node():
    graph = memory_graph()
    first = graph.add_node(hot_node("login", "login"))
    second = graph.add_node(hot_node("renamed", "login"))

    assert first.id == second.id
    assert len(graph.nodes) == 1
    assert graph.nodes[first.id].label == "login"


def test_neighbors_missing_node_raises():
    graph = memory_graph()
    with pytest.raises(KeyError):
        graph.neighbors("missing")


def test_typed_neighbors_do_not_scan_the_adjacency_map():
    graph = memory_graph()
    caller = graph.add_node(hot_node("login", "login"))
    callee = graph.add_node(hot_node("check", "check"))
    graph.add_edge(Edge(edge_id(caller.id, callee.id, "calls"), "calls", caller.id, callee.id))

    class NoScan(dict):
        def __iter__(self):
            raise AssertionError("scanned adjacency")

    graph.outgoing[caller.id] = NoScan(graph.outgoing[caller.id])

    assert graph.neighbors(caller.id, edge_type="calls") == (callee.id,)
