"""Graph file creation helpers."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path


GRAPH_STRUCTURE = """Graph files use this JSON structure:

{
  "name": "My knowledge graph",
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
  episodic ingest-node --source <node.md> --name "<graph name>"
"""

def registry_path() -> Path:
    """Return the central graph registry path."""
    return Path.home() / ".episodic" / "graphs.json"


def create_graph(directory: Path, name: str) -> Path:
    """Create an empty graph.json in a directory without overwriting it."""
    name = name.strip()
    if not name:
        raise ValueError("graph name cannot be empty")
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    graph_path = directory / "graph.json"
    if graph_path.exists():
        raise FileExistsError(f"graph already exists: {graph_path}")
    graph_path.write_text(
        json.dumps({"name": name, "nodes": [], "links": []}, indent=2) + "\n",
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


def resolve_registered_graph(name: str, path: Path | None = None) -> Path:
    """Resolve a unique graph path by its registered graph name."""
    registry = path or registry_path()
    if not registry.is_file():
        raise ValueError(f"graph is not registered: {name}")

    data = json.loads(registry.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError(f"invalid graph registry: {registry}")

    matches: list[Path] = []
    for item in data:
        graph_path = Path(item)
        graph_name = graph_path.parent.name
        if graph_path.is_file():
            try:
                content = json.loads(graph_path.read_text(encoding="utf-8"))
                graph_name = content.get("name", graph_name)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                pass
        if graph_name == name:
            matches.append(graph_path)
    if not matches:
        raise ValueError(f"graph is not registered: {name}")
    if len(matches) > 1:
        raise ValueError(f"multiple registered graphs have the name: {name}")
    return matches[0]


def delete_graph(name: str, path: Path | None = None) -> None:
    """Delete a named registered graph and its containing directory."""
    registry = path or registry_path()
    if not registry.is_file():
        raise ValueError(f"graph is not registered: {name}")

    data = json.loads(registry.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError(f"invalid graph registry: {registry}")

    graph_path = resolve_registered_graph(name, registry)
    resolved = str(graph_path.resolve())

    graph_directory = graph_path.resolve().parent
    if graph_directory in {Path("/"), Path.home(), Path.cwd()}:
        raise ValueError(f"refusing to delete unsafe graph directory: {graph_directory}")

    if graph_directory.is_dir():
        shutil.rmtree(graph_directory)
    data.remove(resolved)
    registry.write_text(json.dumps(sorted(data), indent=2) + "\n", encoding="utf-8")


def list_registered_graphs(
    path: Path | None = None,
) -> list[tuple[str, Path, int | None, str | None]]:
    """Read registered graphs and return names, node counts, and update times."""
    registry = path or registry_path()
    if not registry.is_file():
        return []
    data = json.loads(registry.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError(f"invalid graph registry: {registry}")

    graphs: list[tuple[str, Path, int | None, str | None]] = []
    for item in data:
        graph = Path(item)
        if not graph.is_file():
            graphs.append((graph.stem, graph, None, None))
            continue
        try:
            content = json.loads(graph.read_text(encoding="utf-8"))
            name = content.get("name", graph.parent.name)
            nodes = content["nodes"]
            if not isinstance(name, str) or not name.strip():
                raise ValueError
            if not isinstance(nodes, list):
                raise ValueError
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            graphs.append((graph.stem, graph, None, None))
            continue
        updated = datetime.fromtimestamp(graph.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        graphs.append((name, graph, len(nodes), updated))
    return graphs
