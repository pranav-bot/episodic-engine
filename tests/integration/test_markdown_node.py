from episodic.ingest.markdown_node import ingest_markdown_node, parse_markdown_node
from episodic.ingest.save_pipeline import SavePipeline
from episodic.drivers.sqlite_episode_store import SQLiteEpisodeStore
from episodic.init_service import run_init


def test_parse_markdown_node_reads_frontmatter_and_body(tmp_path):
    path = tmp_path / "note.md"
    path.write_text(
        """---
id: auth-note
type: concept
title: Authentication
tags:
  - security
---
JWT validation happens here.
""",
        encoding="utf-8",
    )

    node = parse_markdown_node(path)

    assert node["id"] == "auth-note"
    assert node["type"] == "concept"
    assert node["label"] == "Authentication"
    assert node["tags"] == ["security"]
    assert node["content"] == "JWT validation happens here."


def test_ingest_markdown_node_creates_one_node_snapshot(temp_config, stores, tmp_path):
    run_init(temp_config)
    SQLiteEpisodeStore(temp_config.episode_db_path)
    markdown = tmp_path / "note.md"
    markdown.write_text(
        "---\nid: auth-note\ntype: concept\ntitle: Authentication\n---\nDetails\n",
        encoding="utf-8",
    )

    result = ingest_markdown_node(
        SavePipeline(temp_config), "notes", markdown
    )

    assert result.status == "saved"
    assert result.node_count == 1
    assert result.edge_count == 0


def test_ingest_markdown_node_appends_to_existing_graph(
    temp_config, stores, tmp_path
):
    run_init(temp_config)
    SQLiteEpisodeStore(temp_config.episode_db_path)
    markdown = tmp_path / "note.md"
    markdown.write_text(
        "---\nid: auth-note\ntype: concept\ntitle: Authentication\n---\nDetails\n",
        encoding="utf-8",
    )
    graph = tmp_path / "graph.json"
    graph.write_text('{"nodes": [], "links": []}', encoding="utf-8")

    result = ingest_markdown_node(
        SavePipeline(temp_config), "notes", markdown, graph_json_path=graph
    )

    assert result.node_count == 1
