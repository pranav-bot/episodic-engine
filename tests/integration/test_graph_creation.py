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


def test_delete_graph_keeps_a_directory_that_holds_other_files(tmp_path):
    graph = create_graph(tmp_path / "knowledge", "Knowledge")
    extra = graph.parent / "notes.txt"
    extra.write_text("keep\n", encoding="utf-8")
    registry = tmp_path / "graphs.json"
    register_graph(graph, registry)

    delete_graph("Knowledge", registry)

    assert extra.is_file()
    assert not graph.exists()
    assert graph.parent.is_dir()
    assert list_registered_graphs(registry) == []


def test_missing_graph_file_is_listed_by_folder_name(tmp_path):
    graph = create_graph(tmp_path / "knowledge", "Knowledge")
    registry = tmp_path / "graphs.json"
    register_graph(graph, registry)
    graph.unlink()

    listed = list_registered_graphs(registry)

    assert listed[0][0] == "knowledge"
    assert listed[0][2] is None


def test_register_graph_leaves_no_temporary_file(tmp_path):
    graph = create_graph(tmp_path / "knowledge", "Knowledge")
    registry = tmp_path / "graphs.json"

    register_graph(graph, registry)

    assert list(tmp_path.glob(".graphs.json.*.tmp")) == []
    assert json.loads(registry.read_text(encoding="utf-8")) == [str(graph.resolve())]
