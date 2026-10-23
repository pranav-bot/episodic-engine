"""Build and ingest graph nodes from Markdown files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

def parse_markdown_node(
    path: Path,
    *,
    node_id: str,
    node_type: str,
    title: str,
) -> dict[str, Any]:
    """Build a graph node from plain Markdown and interactive details."""
    if not path.is_file():
        raise FileNotFoundError(f"Markdown file not found: {path}")
    if path.suffix.lower() != ".md":
        raise ValueError(f"Markdown source must have a .md extension: {path}")

    return {
        "id": node_id,
        "type": node_type,
        "label": title,
        "file": str(path.resolve()),
        "content": path.read_text(encoding="utf-8"),
    }


def ingest_markdown_node(
    markdown_path: Path,
    graph_json_path: Path,
    *,
    node_id: str,
    node_type: str,
    title: str,
    parent_id: str | None = None,
) -> dict[str, Any]:
    """Append one Markdown node, optionally as a child of an existing node."""
    node = parse_markdown_node(
        markdown_path.resolve(),
        node_id=node_id,
        node_type=node_type,
        title=title,
    )
    graph_path = graph_json_path.resolve()
    if not graph_path.is_file():
        raise FileNotFoundError(f"graph.json not found: {graph_path}")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
        raise ValueError(f"invalid graph.json: {graph_path}")
    if any(existing.get("id") == node["id"] for existing in graph["nodes"]):
        raise ValueError(f"node already exists: {node['id']}")
    graph.setdefault("links", graph.get("edges") or [])
    if parent_id is not None and not any(
        existing.get("id") == parent_id for existing in graph["nodes"]
    ):
        raise ValueError(f"parent node not found: {parent_id}")
    graph["nodes"].append(node)
    if parent_id is not None:
        graph["links"].append(
            {"source": parent_id, "target": node["id"], "type": "parent"}
        )
    graph_path.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return node
