import json

import pytest

from episodic.ingest.markdown_node import ingest_markdown_node, parse_markdown_node


def test_parse_markdown_node_reads_frontmatter_and_body(tmp_path):
    path = tmp_path / "note.md"
    path.write_text(
        "---\nid: auth-note\ntype: concept\ntitle: Authentication\n---\nDetails\n",
        encoding="utf-8",
    )

    node = parse_markdown_node(path)

    assert node["id"] == "auth-note"
    assert node["label"] == "Authentication"
    assert node["content"] == "Details"


def test_ingest_markdown_node_updates_graph_file(tmp_path):
    markdown = tmp_path / "note.md"
    markdown.write_text(
        "---\nid: auth-note\ntype: concept\ntitle: Authentication\n---\nDetails\n",
        encoding="utf-8",
    )
    graph = tmp_path / "graph.json"
    graph.write_text('{"nodes": [], "links": []}', encoding="utf-8")

    node = ingest_markdown_node(markdown, graph)

    assert node["id"] == "auth-note"
    assert json.loads(graph.read_text(encoding="utf-8"))["nodes"] == [node]


def test_ingest_markdown_node_rejects_duplicate_id(tmp_path):
    markdown = tmp_path / "note.md"
    markdown.write_text(
        "---\nid: auth-note\ntype: concept\ntitle: Authentication\n---\n",
        encoding="utf-8",
    )
    graph = tmp_path / "graph.json"
    graph.write_text(
        '{"nodes": [{"id": "auth-note"}], "links": []}', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="node already exists"):
        ingest_markdown_node(markdown, graph)
