"""Graph file creation helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


GRAPH_STRUCTURE = """Graph files use this JSON structure:

{
  "nodes": [
    {
      "id": "auth-note",
      "label": "Authentication",
      "description": "What this node represents",
      "file": "/path/to/note.md",
      "content": "Markdown body"
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

def registry_path() -> Path:
    """Return the central graph registry path."""
    return Path.home() / ".episodic" / "graphs.json"


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


def register_graph(graph_path: Path, path: Path | None = None) -> None:
    """Register a graph path in the central JSON registry."""
    registry = path or registry_path()
    registry.parent.mkdir(parents=True, exist_ok=True)
    entries: list[str] = []
    if registry.exists():
        data = json.loads(registry.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
            raise ValueError(f"invalid graph registry: {registry}")
        entries = data
    resolved = str(graph_path.resolve())
    if resolved not in entries:
        entries.append(resolved)
    registry.write_text(json.dumps(sorted(entries), indent=2) + "\n", encoding="utf-8")


def delete_graph(graph_path: Path, path: Path | None = None) -> None:
    """Delete a registered graph and its containing directory."""
    registry = path or registry_path()
    resolved = str(graph_path.resolve())
    if not registry.is_file():
        raise ValueError(f"graph is not registered: {graph_path}")

    data = json.loads(registry.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError(f"invalid graph registry: {registry}")
    if resolved not in data:
        raise ValueError(f"graph is not registered: {graph_path}")

    graph_directory = graph_path.resolve().parent
    if graph_directory in {Path("/"), Path.home(), Path.cwd()}:
        raise ValueError(f"refusing to delete unsafe graph directory: {graph_directory}")

    if graph_directory.is_dir():
        shutil.rmtree(graph_directory)
    data.remove(resolved)
    registry.write_text(json.dumps(sorted(data), indent=2) + "\n", encoding="utf-8")


def list_registered_graphs(
    path: Path | None = None,
) -> list[tuple[Path, int | None, int | None]]:
    """Read registered graphs and return their current node/link counts."""
    registry = path or registry_path()
    if not registry.is_file():
        return []
    data = json.loads(registry.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError(f"invalid graph registry: {registry}")

    graphs: list[tuple[Path, int | None, int | None]] = []
    for item in data:
        graph = Path(item)
        if not graph.is_file():
            graphs.append((graph, None, None))
            continue
        try:
            content = json.loads(graph.read_text(encoding="utf-8"))
            nodes = content["nodes"]
            links = content.get("links", content.get("edges", []))
            if not isinstance(nodes, list) or not isinstance(links, list):
                raise ValueError
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            graphs.append((graph, None, None))
            continue
        graphs.append((graph, len(nodes), len(links)))
    return graphs
