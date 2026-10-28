import json

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
