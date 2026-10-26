"""CLI for file-based graph creation and Markdown node ingestion."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from episodic.graph import GRAPH_STRUCTURE, create_graph, list_graphs
from episodic.ingest.markdown_node import ingest_markdown_node

app = typer.Typer(
    name="episodic",
    help="File-based graph creation and Markdown node ingestion.",
    no_args_is_help=True,
)


@app.command("create-graph")
def create_graph_cmd(
    directory: Path = typer.Option(..., "--directory", help="Directory for graph.json"),
) -> None:
    """Create an empty graph.json and explain how to add nodes."""
    try:
        graph_path = create_graph(directory)
    except (FileExistsError, OSError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"created: {graph_path}")
    typer.echo(GRAPH_STRUCTURE)


@app.command("graphs")
def graphs_cmd(
    directory: Path = typer.Option(
        Path("."),
        "--directory",
        help="Directory to search recursively for graph.json files",
    ),
) -> None:
    """List graph.json files and their node/link counts."""
    try:
        graphs = list_graphs(directory)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if not graphs:
        typer.echo(f"No graphs found under {directory.resolve()}")
        return

    typer.echo(f"{'graph':<60} {'nodes':>5} {'links':>5}")
    for path, node_count, link_count in graphs:
        typer.echo(f"{str(path):<60} {node_count:>5} {link_count:>5}")


@app.command("ingest-node")
def ingest_node_cmd(
    source: Path = typer.Option(..., "--source", help="Markdown node file"),
    graph_json: Path = typer.Option(..., "--graph-json", help="Graph file to update"),
) -> None:
    """Interactively append a node to an existing graph.json."""
    graph_path = graph_json.resolve()
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
            raise ValueError(f"invalid graph.json: {graph_path}")
        existing_ids = [str(node.get("id")) for node in graph["nodes"]]
        typer.echo(
            "Existing node IDs: "
            + (", ".join(existing_ids) if existing_ids else "(none; node will be top-level)")
        )
        node_id = typer.prompt("Node ID")
        title = typer.prompt("Node title")
        description = typer.prompt("Node description")
        parent_id = typer.prompt(
            "Parent node ID (leave blank for a top-level node)",
            default="",
            show_default=False,
        ) or None
        node = ingest_markdown_node(
            source,
            graph_path,
            node_id=node_id,
            title=title,
            description=description,
            parent_id=parent_id,
        )
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"added: node={node['id']} graph={graph_json.resolve()}")


if __name__ == "__main__":
    app()
