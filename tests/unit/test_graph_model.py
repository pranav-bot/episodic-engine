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


def test_payload_change_does_not_change_neighbors():
    graph = memory_graph()
    caller = graph.add_node(hot_node("login", "login"))
    callee = graph.add_node(hot_node("check", "check"))
    graph.add_edge(Edge(edge_id(caller.id, callee.id, "calls"), "calls", caller.id, callee.id))
    before = graph.neighbors(caller.id, edge_type="calls")

    graph.put_payload(caller.id, b"source bytes")

    assert graph.neighbors(caller.id, edge_type="calls") == before
    assert set(HotNode.__dataclass_fields__) == {"id", "type", "label", "provenance_ref"}
    assert caller.provenance_ref.source_path == "src/auth.py"


def test_neighbors_does_not_read_payload():
    graph = memory_graph()
    caller = graph.add_node(hot_node("login", "login"))
    graph.put_payload(caller.id, b"source bytes")

    def fail(_node_id: str) -> bytes:
        raise AssertionError("payload read")

    graph.get_payload = fail
    assert graph.neighbors(caller.id, edge_type="calls") == ()


def test_merge_copies_nodes_and_edges_that_exist_only_on_source():
    into = memory_graph()
    source = memory_graph()
    login = into.add_node(hot_node("login", "login"))
    check = source.add_node(hot_node("check", "check"))
    source.add_node(hot_node("login", "login"))
    source.add_edge(Edge(edge_id(login.id, check.id, "calls"), "calls", login.id, check.id))
    source_labels = {node.label for node in source.nodes.values()}

    into.merge(source)

    assert check.id in into.nodes
    assert into.neighbors(login.id, edge_type="calls") == (check.id,)
    assert {node.label for node in source.nodes.values()} == source_labels


def test_merge_keeps_destination_label_and_records_the_clash():
    into = memory_graph()
    source = memory_graph()
    kept = into.add_node(hot_node("login", "login"))
    source.add_node(HotNode(kept.id, "file", "renamed", Provenance("docs/login.md", None)))

    into.merge(source)

    assert into.nodes[kept.id].label == "login"
    assert into.nodes[kept.id].type == "symbol"
    assert into.nodes[kept.id].provenance_ref.source_path == "src/auth.py"
    assert {item.field for item in into.conflicts} == {"label", "type"}
    assert into.extra_provenance[kept.id][0].source_path == "docs/login.md"
    assert source.nodes[kept.id].label == "renamed"
