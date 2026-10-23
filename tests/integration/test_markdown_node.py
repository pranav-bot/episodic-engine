import json

import pytest

from episodic.ingest.markdown_node import ingest_markdown_node, parse_markdown_node


def test_parse_markdown_node_reads_frontmatter_and_body(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("Details\n", encoding="utf-8")

    node = parse_markdown_node(
        path,
        node_id="auth-note",
        node_type="concept",
        title="Authentication",
    )

    assert node["id"] == "auth-note"
    assert node["label"] == "Authentication"
    assert node["content"] == "Details\n"


def test_ingest_markdown_node_updates_graph_file(tmp_path):
    markdown = tmp_path / "note.md"
    markdown.write_text("Details\n", encoding="utf-8")
    graph = tmp_path / "graph.json"
    graph.write_text('{"nodes": [], "links": []}', encoding="utf-8")

    node = ingest_markdown_node(
        markdown,
        graph,
        node_id="auth-note",
        node_type="concept",
        title="Authentication",
    )

    assert node["id"] == "auth-note"
    assert json.loads(graph.read_text(encoding="utf-8"))["nodes"] == [node]


def test_ingest_markdown_node_rejects_duplicate_id(tmp_path):
    markdown = tmp_path / "note.md"
    markdown.write_text("Details\n", encoding="utf-8")
    graph = tmp_path / "graph.json"
    graph.write_text(
        '{"nodes": [{"id": "auth-note"}], "links": []}', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="node already exists"):
        ingest_markdown_node(
            markdown,
            graph,
            node_id="auth-note",
            node_type="concept",
            title="Authentication",
        )


def test_ingest_markdown_node_creates_parent_child_link(tmp_path):
    markdown = tmp_path / "child.md"
    markdown.write_text("Child details\n", encoding="utf-8")
    graph = tmp_path / "graph.json"
    graph.write_text(
        '{"nodes": [{"id": "root"}], "links": []}', encoding="utf-8"
    )

    ingest_markdown_node(
        markdown,
        graph,
        node_id="child",
        node_type="concept",
        title="Child",
        parent_id="root",
    )

    saved = json.loads(graph.read_text(encoding="utf-8"))
    assert saved["links"] == [
        {"source": "root", "target": "child", "type": "parent"}
    ]


def test_ingest_markdown_node_rejects_missing_parent(tmp_path):
    markdown = tmp_path / "child.md"
    markdown.write_text("Child details\n", encoding="utf-8")
    graph = tmp_path / "graph.json"
    graph.write_text('{"nodes": [], "links": []}', encoding="utf-8")

    with pytest.raises(ValueError, match="parent node not found"):
        ingest_markdown_node(
            markdown,
            graph,
            node_id="child",
            node_type="concept",
            title="Child",
            parent_id="missing",
        )
