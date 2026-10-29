"""Ingest one Markdown file as a document node and its heading chunks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from episodic.model.document import load_graph, save_graph
from episodic.model.identity import edge_id, node_id
from episodic.model.types import EDGE_TYPES, Edge, HotNode, Provenance

_HEADING = re.compile(r"(?m)^(#{1,6})[ \t]+(.+?)\s*$")
_KIND = re.compile(r"^(?P<title>.+?)\s*\{(?P<kind>[a-z_]+)\}\s*$")


def parse_markdown_node(path: Path) -> HotNode:
    """Build the document node. The id is a fingerprint of type, path, and file name."""
    resolved = _markdown_file(path)
    text = resolved.read_text(encoding="utf-8")
    sections = _sections(text)
    label = _link_type(sections[0][0], "contains")[0] if sections else resolved.stem
    return HotNode(
        node_id("document", str(resolved), resolved.name),
        "document",
        label,
        Provenance(str(resolved), None),
    )


def add_markdown_file(graph: Any, markdown_path: Path, *, edge_type: str = "contains") -> str:
    """Add one Markdown file to an in-memory graph. Does not write the file."""
    if edge_type not in EDGE_TYPES:
        raise ValueError(f"unknown edge type: {edge_type}")
    resolved = _markdown_file(markdown_path)
    text = resolved.read_text(encoding="utf-8")
    source_path = str(resolved)
    sections = _sections(text)
    label = _link_type(sections[0][0], edge_type)[0] if sections else resolved.stem
    document = HotNode(
        node_id("document", source_path, resolved.name),
        "document",
        label,
        Provenance(source_path, None),
    )
    graph.add_node(document)
    graph.put_payload(document.id, text.encode("utf-8"))
    for heading, body in sections:
        title, kind = _link_type(heading, edge_type)
        chunk = HotNode(
            node_id("chunk", source_path, title),
            "chunk",
            title,
            Provenance(source_path, title),
        )
        graph.add_node(chunk)
        if body:
            graph.put_payload(chunk.id, body.encode("utf-8"))
        graph.add_edge(Edge(edge_id(document.id, chunk.id, kind), kind, document.id, chunk.id))
    return document.id


def ingest_markdown_node(
    markdown_path: Path,
    graph_json_path: Path,
    *,
    edge_type: str = "contains",
) -> dict[str, Any]:
    """Add or update one Markdown file. Each heading links to the document.

    ``edge_type`` is the link used when a heading does not name one. A heading
    can name its own link: ``# Tokens {describes}``.
    """
    resolved = _markdown_file(markdown_path)
    graph_path = graph_json_path.resolve()
    if not graph_path.is_file():
        raise FileNotFoundError(f"graph.json not found: {graph_path}")
    name, graph = load_graph(graph_path)
    document = parse_markdown_node(resolved)
    created = document.id not in graph.nodes
    add_markdown_file(graph, resolved, edge_type=edge_type)
    save_graph(graph_path, name, graph)
    return {"id": document.id, "label": graph.nodes[document.id].label, "created": created}


def _markdown_file(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Markdown file not found: {resolved}")
    if resolved.suffix.lower() != ".md":
        raise ValueError(f"Markdown source must have a .md extension: {resolved}")
    return resolved


def _link_type(heading: str, default: str) -> tuple[str, str]:
    match = _KIND.match(heading)
    if match is None:
        return heading, default
    kind = match.group("kind")
    if kind not in EDGE_TYPES:
        raise ValueError(f"unknown edge type: {kind}")
    return match.group("title").strip(), kind


def _sections(text: str) -> list[tuple[str, str]]:
    matches = list(_HEADING.finditer(text))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(2).strip(), text[start:end].strip("\n")))
    return sections
