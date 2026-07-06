from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any


def normalize_label(label: str) -> str:
    text = unicodedata.normalize("NFKC", label or "")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_fingerprint(node: dict[str, Any]) -> str:
    node_type = str(node.get("type") or "unknown")
    file_path = str(node.get("file") or node.get("path") or "unknown")
    qualified = node.get("qualified_name") or node.get("name") or node.get("label")
    label = normalize_label(str(node.get("label") or node.get("name") or node.get("id")))

    if node_type in {"function", "method", "class"} and qualified:
        return f"{node_type}:{file_path}:{qualified}"
    if node_type in {"module", "file"}:
        name = node.get("name") or node.get("label") or file_path
        return f"{node_type}:{file_path}:{name}"
    if node_type in {"concept", "doc", "section"}:
        heading = node.get("heading") or label
        return f"{node_type}:{file_path}:{normalize_label(str(heading))}"
    return f"{node_type}:{file_path}:{label}"


def edge_key(source_fp: str, target_fp: str, edge_type: str) -> str:
    return f"{source_fp}|{edge_type}|{target_fp}"


@dataclass
class GraphNode:
    local_id: str
    fingerprint: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    local_id: str
    source_local_id: str
    target_local_id: str
    source_fingerprint: str
    target_fingerprint: str
    edge_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    edge_key: str = ""

    def __post_init__(self) -> None:
        if not self.edge_key:
            self.edge_key = edge_key(
                self.source_fingerprint, self.target_fingerprint, self.edge_type
            )
