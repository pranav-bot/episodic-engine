"""Stdio MCP server any harness can launch."""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from episodic.ingest.folder import create_context_graph


def create_context_graph_tool(folder: str, name: str) -> str:
    """Build a context graph for a code folder. The harness chooses name.

    Returns ids, labels, types, and edges. File bytes stay on disk.
    """
    return json.dumps(create_context_graph(Path(folder), name))


def build_server() -> MCPServer:
    server = MCPServer("episodic")
    server.tool(name="create_context_graph")(create_context_graph_tool)
    return server


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
