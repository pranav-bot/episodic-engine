"""Build and ingest graph nodes from Markdown files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

def parse_markdown_node(path: Path) -> dict[str, Any]:
    """Parse a Markdown file with YAML frontmatter into a graph node."""
    if not path.is_file():
        raise FileNotFoundError(f"Markdown file not found: {path}")
    if path.suffix.lower() != ".md":
        raise ValueError(f"Markdown source must have a .md extension: {path}")

    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("Markdown node must start with YAML frontmatter")

    lines = text.splitlines()
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line == "---")
    except StopIteration as exc:
        raise ValueError("Markdown node frontmatter is not closed") from exc

    metadata = yaml.safe_load("\n".join(lines[1:end])) or {}
    if not isinstance(metadata, dict):
        raise ValueError("Markdown node frontmatter must be a YAML mapping")
    missing = [key for key in ("id", "type", "title") if not metadata.get(key)]
    if missing:
        raise ValueError(f"Markdown node frontmatter missing: {', '.join(missing)}")

    properties = {
        key: value
        for key, value in metadata.items()
        if key not in {"id", "type", "title"} and value is not None
    }
    properties["content"] = "\n".join(lines[end + 1 :]).lstrip("\n")
    return {
        "id": str(metadata["id"]),
        "type": str(metadata["type"]),
        "label": str(metadata["title"]),
        "file": str(path.resolve()),
        **properties,
    }


def ingest_markdown_node(
    markdown_path: Path,
    graph_json_path: Path,
) -> dict[str, Any]:
    """Append one Markdown node to an existing graph.json."""
    node = parse_markdown_node(markdown_path.resolve())
    graph_path = graph_json_path.resolve()
    if not graph_path.is_file():
        raise FileNotFoundError(f"graph.json not found: {graph_path}")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
        raise ValueError(f"invalid graph.json: {graph_path}")
    if any(existing.get("id") == node["id"] for existing in graph["nodes"]):
        raise ValueError(f"node already exists: {node['id']}")
    graph.setdefault("links", graph.get("edges") or [])
    graph["nodes"].append(node)
    graph_path.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return node
