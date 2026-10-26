import json

import pytest

from episodic.ingest.markdown_node import ingest_markdown_node, parse_markdown_node
from episodic.model.document import load_graph
from episodic.model.identity import node_id


def test_parse_markdown_node_uses_a_fingerprint(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("# Authentication\n\nDetails\n", encoding="utf-8")

    node = parse_markdown_node(path)

    assert node.id == node_id("document", str(path.resolve()), "note.md")
    assert node.type == "document"
    assert node.label == "Authentication"
    assert not hasattr(node, "content")


def test_ingest_markdown_node_stores_headings_as_chunks(tmp_path):
    markdown = tmp_path / "note.md"
    markdown.write_text("# Authentication\n\nDetails\n\n# Tokens\n\nBudget\n", encoding="utf-8")
    graph = tmp_path / "graph.json"
    graph.write_text(
        '{"name": "notes", "nodes": [], "edges": [], "payloads": {}}\n',
        encoding="utf-8",
    )

    node = ingest_markdown_node(markdown, graph)

    saved = json.loads(graph.read_text(encoding="utf-8"))
    document = next(item for item in saved["nodes"] if item["type"] == "document")
    chunks = [item for item in saved["nodes"] if item["type"] == "chunk"]
    assert node["id"] == document["id"]
    assert document["label"] == "Authentication"
    assert {item["label"] for item in chunks} == {"Authentication", "Tokens"}
    assert saved["payloads"][document["id"]] == {"text": markdown.read_text(encoding="utf-8")}
    assert "content" not in document
    assert {edge["type"] for edge in saved["edges"]} == {"contains"}
    assert {edge["source"] for edge in saved["edges"]} == {document["id"]}


def test_ingest_markdown_node_uses_a_chosen_link_type(tmp_path):
    markdown = tmp_path / "note.md"
    markdown.write_text("# Login\n\nsecret\n\n# Tokens {describes}\n\nBudget\n", encoding="utf-8")
    graph = tmp_path / "graph.json"
    graph.write_text(
        '{"name": "notes", "nodes": [], "edges": [], "payloads": {}}\n',
        encoding="utf-8",
    )

    ingest_markdown_node(markdown, graph, edge_type="calls")

    saved = json.loads(graph.read_text(encoding="utf-8"))
    kinds = {edge["target"]: edge["type"] for edge in saved["edges"]}
    labels = {item["label"]: item["id"] for item in saved["nodes"] if item["type"] == "chunk"}
    assert kinds[labels["Login"]] == "calls"
    assert kinds[labels["Tokens"]] == "describes"


def test_ingest_markdown_node_updates_the_same_file_in_place(tmp_path):
    markdown = tmp_path / "note.md"
    markdown.write_text("# Authentication\n\nDetails\n", encoding="utf-8")
    graph = tmp_path / "graph.json"
    graph.write_text(
        '{"name": "notes", "nodes": [], "edges": [], "payloads": {}}\n',
        encoding="utf-8",
    )

    first = ingest_markdown_node(markdown, graph)
    markdown.write_text("# Authentication\n\nChanged\n", encoding="utf-8")
    second = ingest_markdown_node(markdown, graph)

    saved = json.loads(graph.read_text(encoding="utf-8"))
    assert second["id"] == first["id"]
    assert second["created"] is False
    assert sum(item["type"] == "document" for item in saved["nodes"]) == 1
    assert saved["payloads"][first["id"]]["text"] == "# Authentication\n\nChanged\n"


def test_load_graph_rejects_a_legacy_node(tmp_path):
    graph = tmp_path / "graph.json"
    graph.write_text(
        '{"name": "notes", "nodes": [{"id": "auth-note", "label": "Authentication", "content": "Details"}], "links": []}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid graph.json"):
        load_graph(graph)
