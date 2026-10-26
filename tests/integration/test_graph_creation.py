import json

import pytest

from episodic.graph import (
    create_graph,
    delete_graph,
    list_registered_graphs,
    register_graph,
)


def test_create_graph_writes_empty_graph(tmp_path):
    path = create_graph(tmp_path / "knowledge", "Knowledge")

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "name": "Knowledge",
        "nodes": [],
        "links": [],
    }


def test_create_graph_does_not_overwrite_existing_graph(tmp_path):
    create_graph(tmp_path, "Knowledge")

    with pytest.raises(FileExistsError):
        create_graph(tmp_path, "Other")


def test_registered_graphs_are_read_from_central_registry(tmp_path):
    graph = create_graph(tmp_path / "elsewhere", "Elsewhere")
    registry = tmp_path / "home" / ".episodic" / "graphs.json"
    register_graph(graph, registry)

    listed = list_registered_graphs(registry)
    assert listed[0][:3] == ("Elsewhere", graph.resolve(), 0)
    assert listed[0][3]


def test_delete_graph_removes_folder_and_registry_entry(tmp_path):
    graph = create_graph(tmp_path / "knowledge", "Knowledge")
    registry = tmp_path / "home" / ".episodic" / "graphs.json"
    register_graph(graph, registry)

    delete_graph("Knowledge", registry)

    assert not graph.parent.exists()
    assert list_registered_graphs(registry) == []
