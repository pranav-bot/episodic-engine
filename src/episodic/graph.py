"""Graph file creation helpers."""

from __future__ import annotations

import json
from pathlib import Path


GRAPH_STRUCTURE = """Graph files use this JSON structure:

{
  "nodes": [
    {
      "id": "auth-note",
      "type": "concept",
      "label": "Authentication",
      "file": "/path/to/note.md",
      "content": "Markdown body",
      "...": "additional properties"
    }
  ],
  "links": [
    {
      "source": "auth-note",
      "target": "other-node",
      "type": "related"
    }
  ]
}

Add a Markdown node with:
  episodic ingest-node --id <subgraph-id> --source <node.md> --graph-json <graph.json>
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
