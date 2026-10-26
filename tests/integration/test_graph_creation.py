import json

import pytest

from episodic.graph import (
    create_graph,
    delete_graph,
    list_registered_graphs,
    register_graph,
)


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


def test_registered_graphs_are_read_from_central_registry(tmp_path):
    graph = create_graph(tmp_path / "elsewhere")
    registry = tmp_path / "home" / ".episodic" / "graphs.json"
    register_graph(graph, registry)

    assert list_registered_graphs(registry) == [(graph.resolve(), 0, 0)]


def test_delete_graph_removes_folder_and_registry_entry(tmp_path):
    graph = create_graph(tmp_path / "knowledge")
    registry = tmp_path / "home" / ".episodic" / "graphs.json"
    register_graph(graph, registry)

    delete_graph(graph, registry)

    assert not graph.parent.exists()
    assert list_registered_graphs(registry) == []
