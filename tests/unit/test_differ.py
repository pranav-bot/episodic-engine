import json
from pathlib import Path

from episodic.ingest.differ import bootstrap_operations, diff_snapshots
from episodic.ingest.graphify_adapter import parse_graph_json

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load_fixture(name: str):
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return parse_graph_json(data)


def test_bootstrap_creates_assert_ops():
    nodes, edges = load_fixture("graph_v1.json")
    ops, mapping = bootstrap_operations(nodes, edges, "test-repo")
    assert len(ops) == len(nodes) + len(edges)
    assert len(mapping) == len(nodes)


def test_diff_detects_added_and_removed():
    old_nodes, old_edges = load_fixture("graph_v1.json")
    new_nodes, new_edges = load_fixture("graph_v2.json")
    bootstrap_ops, fp_map = bootstrap_operations(old_nodes, old_edges, "test-repo")
    assert bootstrap_ops

    delta, _ = diff_snapshots(
        old_nodes, old_edges, new_nodes, new_edges, "test-repo", fp_map
    )
    op_types = {op.op.value for op in delta}
    assert "ASSERT_NODE" in op_types
    assert "RETRACT_NODE" in op_types
    assert "RETRACT_EDGE" in op_types
    assert "ASSERT_EDGE" in op_types


def test_identical_snapshots_produce_no_delta_ops():
    nodes, edges = load_fixture("graph_v1.json")
    bootstrap_ops, fp_map = bootstrap_operations(nodes, edges, "test-repo")
    assert bootstrap_ops

    delta, _ = diff_snapshots(nodes, edges, nodes, edges, "test-repo", fp_map)
    assert delta == []
