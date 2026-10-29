import json

import pytest

from episodic.ingest.folder import create_context_graph
from episodic.model.identity import node_id


def test_create_context_graph_maps_calls_imports_and_markdown(tmp_path):
    folder = tmp_path / "repo"
    (folder / "backend").mkdir(parents=True)
    (folder / "backend" / "b.py").write_text("def ping():\n    return 1\n", encoding="utf-8")
    (folder / "backend" / "a.py").write_text(
        "from b import ping\n\ndef start():\n    ping()\n",
        encoding="utf-8",
    )
    (folder / "backend" / "note.md").write_text("# Auth\n\nDetails\n", encoding="utf-8")
    registry = tmp_path / "home" / "graphs.json"

    result = create_context_graph(folder, "Todo", registry=registry)

    labels = {node["label"]: node for node in result["nodes"]}
    assert labels["backend"]["type"] == "directory"
    assert labels["a.py"]["type"] == "file"
    assert labels["start"]["type"] == "symbol"
    assert labels["Auth"]["type"] == "chunk"
    kinds = {(edge["source"], edge["type"], edge["target"]) for edge in result["edges"]}
    start = labels["start"]["id"]
    ping = labels["ping"]["id"]
    a_file = labels["a.py"]["id"]
    b_file = labels["b.py"]["id"]
    assert (start, "calls", ping) in kinds
    assert (a_file, "imports", b_file) in kinds
    assert (labels["backend"]["id"], "contains", a_file) in kinds
    note = folder / "backend" / "note.md"
    document = node_id("document", str(note.resolve()), "note.md")
    assert (labels["backend"]["id"], "contains", document) in kinds
    saved = json.loads((tmp_path / "home" / "graphs" / "Todo" / "graph.json").read_text(encoding="utf-8"))
    assert "payloads" in saved
    assert "text" not in json.dumps(result["nodes"])
    assert result["name"] == "Todo"


def test_create_context_graph_skips_a_call_through_a_variable(tmp_path):
    folder = tmp_path / "repo"
    folder.mkdir()
    (folder / "a.py").write_text("def run(fn):\n    fn()\n", encoding="utf-8")
    registry = tmp_path / "graphs.json"

    result = create_context_graph(folder, "Repo", registry=registry)

    assert all(edge["type"] != "calls" for edge in result["edges"])


def test_same_function_name_stays_two_nodes(tmp_path):
    folder = tmp_path / "repo"
    folder.mkdir()
    source = folder / "a.py"
    source.write_text(
        "def outer():\n    def helper():\n        return 1\n    helper()\n\ndef helper():\n    return 2\n",
        encoding="utf-8",
    )
    registry = tmp_path / "graphs.json"

    result = create_context_graph(folder, "Repo", registry=registry)

    resolved = str(source.resolve())
    nested = node_id("symbol", resolved, "outer.helper")
    module = node_id("symbol", resolved, "helper")
    outer = node_id("symbol", resolved, "outer")
    kinds = {(edge["source"], edge["type"], edge["target"]) for edge in result["edges"]}
    assert (outer, "calls", nested) in kinds
    assert (outer, "calls", module) not in kinds
    assert sum(node["label"] == "helper" for node in result["nodes"]) == 2


def test_graph_name_cannot_escape_the_graphs_directory(tmp_path):
    folder = tmp_path / "repo"
    folder.mkdir()
    (folder / "a.py").write_text("def start():\n    return 1\n", encoding="utf-8")
    registry = tmp_path / "home" / "graphs.json"

    with pytest.raises(ValueError, match="graphs directory"):
        create_context_graph(folder, "../../outside", registry=registry)

    assert not (tmp_path / "outside").exists()
    assert not registry.exists()


def test_bad_python_encoding_does_not_register_a_graph(tmp_path):
    folder = tmp_path / "repo"
    folder.mkdir()
    (folder / "a.py").write_bytes(b"\xff")
    registry = tmp_path / "graphs.json"

    with pytest.raises(ValueError, match="a.py"):
        create_context_graph(folder, "Bad", registry=registry)

    assert not registry.exists()
    assert not (tmp_path / "graphs").exists()
