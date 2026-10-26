import pytest

from episodic.model import EDGE_TYPES, Edge, edge_id, node_id


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
