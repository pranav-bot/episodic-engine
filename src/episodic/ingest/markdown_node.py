"""Build and ingest graph nodes from Markdown files."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import yaml

from episodic.config import validate_subgraph_id
from episodic.ingest.save_pipeline import SavePipeline, SaveResult


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
    pipeline: SavePipeline,
    subgraph_id: str,
    markdown_path: Path,
    graph_json_path: Path | None = None,
) -> SaveResult:
    """Ingest a Markdown node as a new or appended graph snapshot."""
    subgraph_id = validate_subgraph_id(subgraph_id)
    node = parse_markdown_node(markdown_path.resolve())

    if graph_json_path is None:
        graph = {"nodes": [node], "links": []}
    else:
        graph_path = graph_json_path.resolve()
        if not graph_path.is_file():
            raise FileNotFoundError(f"graph.json not found: {graph_path}")
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
            raise ValueError(f"invalid graph.json: {graph_path}")
        graph.setdefault("links", graph.get("edges") or [])
        graph["nodes"].append(node)

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".json", delete=False
    ) as handle:
        json.dump(graph, handle, ensure_ascii=False, sort_keys=True)
        temp_path = Path(handle.name)
    try:
        return pipeline.save(
            subgraph_id,
            source=markdown_path.resolve().parent,
            skip_graphify=True,
            graph_json_path=temp_path,
        )
    finally:
        temp_path.unlink(missing_ok=True)
