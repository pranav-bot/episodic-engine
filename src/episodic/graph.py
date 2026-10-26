"""Graph file creation helpers."""

from __future__ import annotations

import json
from pathlib import Path


GRAPH_STRUCTURE = """Graph files use this JSON structure:

{
  "nodes": [
    {
      "id": "auth-note",
      "label": "Authentication",
      "description": "What this node represents",
      "file": "/path/to/note.md",
      "content": "Markdown body",
    }
  ],
  "links": [
    {
      "source": "auth-note",
      "target": "other-node",
      "type": "parent"
    }
  ]
}

Add a Markdown node with:
  episodic ingest-node --source <node.md> --graph-json <graph.json>
"""


def create_graph(directory: Path) -> Path:
    """Create an empty graph.json in a directory without overwriting it."""
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    graph_path = directory / "graph.json"
    if graph_path.exists():
        raise FileExistsError(f"graph already exists: {graph_path}")
    graph_path.write_text(
        json.dumps({"nodes": [], "links": []}, indent=2) + "\n",
        encoding="utf-8",
    )
    return graph_path


def list_graphs(directory: Path) -> list[tuple[Path, int, int]]:
    """Find valid graph.json files below a directory."""
    root = directory.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"directory not found: {root}")

    graphs: list[tuple[Path, int, int]] = []
    for path in sorted(root.rglob("graph.json")):
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            nodes = data["nodes"]
            links = data.get("links", data.get("edges", []))
            if not isinstance(nodes, list) or not isinstance(links, list):
                raise ValueError
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
        graphs.append((path, len(nodes), len(links)))
    return graphs
