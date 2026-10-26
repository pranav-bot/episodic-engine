"""Graph file creation helpers."""

from __future__ import annotations

import json
import os
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

def write_text_atomic(path: Path, text: str) -> None:
    """Replace path in one step so a reader never sees a half-written file."""
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


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
    write_text_atomic(
        graph_path,
        json.dumps({"name": name, "nodes": [], "links": []}, indent=2) + "\n",
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
    write_text_atomic(registry, json.dumps(sorted(entries), indent=2) + "\n")


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
    """Delete a named registered graph. Remove its folder only when it holds nothing else."""
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
        names = {item.name for item in graph_directory.iterdir()}
        if names <= {"graph.json"}:
            shutil.rmtree(graph_directory)
        elif graph_path.is_file():
            graph_path.unlink()
    data.remove(resolved)
    write_text_atomic(registry, json.dumps(sorted(data), indent=2) + "\n")


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
            graphs.append((graph.parent.name, graph, None, None))
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
            graphs.append((graph.parent.name, graph, None, None))
            continue
        updated = datetime.fromtimestamp(graph.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        graphs.append((name, graph, len(nodes), updated))
    return graphs
