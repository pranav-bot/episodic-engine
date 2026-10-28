"""Build a context graph for one code folder."""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any

from episodic.graph import create_graph, register_graph, registry_path, resolve_registered_graph
from episodic.ingest.markdown_node import ingest_markdown_node, parse_markdown_node
from episodic.model.document import load_graph, memory_graph_class, save_graph
from episodic.model.identity import edge_id, node_id
from episodic.model.types import Edge, HotNode, Provenance

_SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}


def create_context_graph(folder: Path, name: str, *, registry: Path | None = None) -> dict[str, Any]:
    """Register ``name`` and write a hot graph of ``folder``. The caller chooses the name."""
    folder = folder.resolve()
    if not folder.is_dir():
        raise FileNotFoundError(f"folder not found: {folder}")
    name = name.strip()
    if not name:
        raise ValueError("graph name cannot be empty")
    registry = registry or registry_path()
    graph_path = _graph_path(name, registry)
    graph = memory_graph_class()()
    markdown_files = _fill_tree(graph, folder)
    save_graph(graph_path, name, graph)
    for path in markdown_files:
        ingest_markdown_node(path, graph_path)
        document_id = parse_markdown_node(path).id
        parent_id = _directory_id(path.parent)
        _link_saved(graph_path, parent_id, document_id)
    _name, saved = load_graph(graph_path)
    return {
        "name": name,
        "path": str(graph_path),
        "nodes": [{"id": node.id, "type": node.type, "label": node.label} for node in saved.nodes.values()],
        "edges": [
            {"type": edge.type, "source": edge.source, "target": edge.target}
            for edge in saved.edges.values()
        ],
    }


def _graph_path(name: str, registry: Path) -> Path:
    try:
        return resolve_registered_graph(name, registry)
    except ValueError:
        path = create_graph(registry.parent / "graphs" / name, name)
        register_graph(path, registry)
        return path


def _fill_tree(graph: Any, folder: Path) -> list[Path]:
    markdown: list[Path] = []
    python: list[tuple[Path, ast.AST]] = []
    for directory, dirnames, filenames in os.walk(folder):
        dirnames[:] = sorted(name for name in dirnames if name not in _SKIP)
        current = Path(directory)
        graph.add_node(_directory_node(current))
        if current != folder:
            _contains(graph, _directory_id(current.parent), _directory_id(current))
        for filename in sorted(filenames):
            path = current / filename
            if path.suffix == ".py":
                python.append((path, _parsed(path)))
            elif path.suffix.lower() == ".md":
                markdown.append(path)
    symbols: dict[Path, dict[str, str]] = {}
    file_ids: dict[Path, str] = {}
    for path, tree in python:
        file_node = _file_node(path)
        graph.add_node(file_node)
        file_ids[path.resolve()] = file_node.id
        _contains(graph, _directory_id(path.parent), file_node.id)
        symbols[path.resolve()] = _add_symbols(graph, file_node.id, path, tree)
    for path, tree in python:
        _add_imports_and_calls(graph, folder, path, tree, file_ids, symbols)
    return markdown


def _add_symbols(graph: Any, file_id: str, path: Path, tree: ast.AST) -> dict[str, str]:
    found: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        symbol = HotNode(
            node_id("symbol", str(path.resolve()), node.name),
            "symbol",
            node.name,
            Provenance(str(path.resolve()), str(node.lineno)),
        )
        graph.add_node(symbol)
        _contains(graph, file_id, symbol.id)
        found[node.name] = symbol.id
    return found


def _add_imports_and_calls(
    graph: Any,
    folder: Path,
    path: Path,
    tree: ast.AST,
    file_ids: dict[Path, str],
    symbols: dict[Path, dict[str, str]],
) -> None:
    file_id = file_ids[path.resolve()]
    local = symbols[path.resolve()]
    bindings: dict[str, str] = {}
    modules: dict[str, Path] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = _module_file(folder, path, alias.name, 0)
                if target is None or target.resolve() not in file_ids:
                    continue
                _imports(graph, file_id, file_ids[target.resolve()])
                bound = alias.asname or alias.name.split(".")[0]
                modules[bound] = target.resolve()
        elif isinstance(node, ast.ImportFrom):
            target = _module_file(folder, path, node.module, node.level)
            if target is None or target.resolve() not in file_ids:
                continue
            _imports(graph, file_id, file_ids[target.resolve()])
            for alias in node.names:
                exported = symbols[target.resolve()].get(alias.name)
                if exported is not None:
                    bindings[alias.asname or alias.name] = exported
    _calls(graph, tree, file_id, local, bindings, modules, symbols)


def _calls(
    graph: Any,
    tree: ast.AST,
    file_id: str,
    local: dict[str, str],
    bindings: dict[str, str],
    modules: dict[str, Path],
    symbols: dict[Path, dict[str, str]],
) -> None:
    class Scan(ast.NodeVisitor):
        def __init__(self) -> None:
            self.caller = file_id

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._enter(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._enter(node)

        def _enter(self, node: ast.AST) -> None:
            previous = self.caller
            self.caller = local.get(getattr(node, "name", ""), previous)
            for child in getattr(node, "body", []):
                self.visit(child)
            self.caller = previous

        def visit_Call(self, node: ast.Call) -> None:
            target = _call_target(node.func, local, bindings, modules, symbols)
            if target is not None and target != self.caller:
                graph.add_edge(Edge(edge_id(self.caller, target, "calls"), "calls", self.caller, target))
            self.generic_visit(node)

    Scan().visit(tree)


def _call_target(
    func: ast.expr,
    local: dict[str, str],
    bindings: dict[str, str],
    modules: dict[str, Path],
    symbols: dict[Path, dict[str, str]],
) -> str | None:
    if isinstance(func, ast.Name):
        return bindings.get(func.id) or local.get(func.id)
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        module = modules.get(func.value.id)
        if module is None:
            return None
        return symbols[module].get(func.attr)
    # shortcut: calls through a variable or an unresolved attribute are skipped, fill them in when a real repo needs them
    return None


def _module_file(folder: Path, current: Path, module: str | None, level: int) -> Path | None:
    parts = [part for part in (module or "").split(".") if part]
    if level:
        root = current.parent
        for _ in range(level - 1):
            root = root.parent
        return _lookup(root, parts)
    for root in (current.parent, folder):
        found = _lookup(root, parts)
        if found is not None:
            return found
    return None


def _lookup(root: Path, parts: list[str]) -> Path | None:
    if not parts:
        init = root / "__init__.py"
        return init.resolve() if init.is_file() else None
    candidate = root.joinpath(*parts)
    script = Path(str(candidate) + ".py")
    if script.is_file():
        return script.resolve()
    init = candidate / "__init__.py"
    if init.is_file():
        return init.resolve()
    return None


def _link_saved(graph_path: Path, source: str, target: str) -> None:
    name, graph = load_graph(graph_path)
    if target not in graph.nodes or source not in graph.nodes:
        return
    graph.add_edge(Edge(edge_id(source, target, "contains"), "contains", source, target))
    save_graph(graph_path, name, graph)


def _directory_node(path: Path) -> HotNode:
    resolved = str(path.resolve())
    return HotNode(_directory_id(path), "directory", path.name, Provenance(resolved, None))


def _directory_id(path: Path) -> str:
    return node_id("directory", str(path.resolve()), path.name)


def _file_node(path: Path) -> HotNode:
    resolved = str(path.resolve())
    return HotNode(node_id("file", resolved, path.name), "file", path.name, Provenance(resolved, None))


def _contains(graph: Any, source: str, target: str) -> None:
    graph.add_edge(Edge(edge_id(source, target, "contains"), "contains", source, target))


def _imports(graph: Any, source: str, target: str) -> None:
    graph.add_edge(Edge(edge_id(source, target, "imports"), "imports", source, target))


def _parsed(path: Path) -> ast.AST:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        raise ValueError(f"cannot parse {path}: {exc.msg}") from exc
