import json

import pytest

from episodic.graph import create_graph, list_graphs


def test_create_graph_writes_empty_graph(tmp_path):
    path = create_graph(tmp_path / "knowledge")

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "nodes": [],
        "links": [],
    }


def test_create_graph_does_not_overwrite_existing_graph(tmp_path):
    create_graph(tmp_path)

    with pytest.raises(FileExistsError):
        create_graph(tmp_path)


def test_list_graphs_finds_graphs_and_counts_contents(tmp_path):
    graph = create_graph(tmp_path / "knowledge")
    graph.write_text(
        '{"nodes": [{"id": "root"}], "links": [{"source": "root", "target": "child"}]}',
        encoding="utf-8",
    )

    assert list_graphs(tmp_path) == [(graph.resolve(), 1, 1)]
