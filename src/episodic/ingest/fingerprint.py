"""Fingerprinting for stable node and edge identity.

Graphify may assign arbitrary local IDs that change between runs.
Fingerprints provide stable identity based on semantic properties
(type, file, qualified name, label) so we can diff across snapshots.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any


def normalize_label(label: str) -> str:
    """Normalize a label for fingerprinting.

    - NFKC normalization
    - Lowercase
    - Remove punctuation (replace with spaces)
    - Collapse whitespace
    - Strip

    Args:
        label: Raw label to normalize

    Returns:
        Normalized label
    """
    text = unicodedata.normalize("NFKC", label or "")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_fingerprint(node: dict[str, Any]) -> str:
    """Compute stable fingerprint for a node.

    Strategy depends on node type:
    - function/method/class with qualified_name: type:file:qualified_name
    - module/file: type:file:name/label
    - concept/doc/section: type:file:normalized_heading
    - fallback: type:file:normalized_label

    Args:
        node: Node dict from graphify (may have type, file/path, qualified_name, name, label)

    Returns:
        Fingerprint string
    """
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
    """Compute stable key for an edge.

    Args:
        source_fp: Fingerprint of source node
        target_fp: Fingerprint of target node
        edge_type: Type of edge/relationship

    Returns:
        Edge key in format "src_fp|edge_type|tgt_fp"
    """
    return f"{source_fp}|{edge_type}|{target_fp}"


@dataclass
class GraphNode:
    """Normalized graph node for diffing."""

    local_id: str                      # ID from graphify in this snapshot
    fingerprint: str                   # Stable fingerprint
    properties: dict[str, Any] = field(default_factory=dict)  # Node properties


@dataclass
class GraphEdge:
    """Normalized graph edge for diffing."""

    local_id: str                      # ID from graphify in this snapshot
    source_local_id: str               # Local ID of source node
    target_local_id: str               # Local ID of target node
    source_fingerprint: str            # Fingerprint of source node
    target_fingerprint: str            # Fingerprint of target node
    edge_type: str                     # Type of relationship
    properties: dict[str, Any] = field(default_factory=dict)  # Edge properties
    edge_key: str = ""                 # Computed from fingerprints and edge_type

    def __post_init__(self) -> None:
        """Compute edge_key if not provided."""
        if not self.edge_key:
            self.edge_key = edge_key(
                self.source_fingerprint, self.target_fingerprint, self.edge_type
            )
