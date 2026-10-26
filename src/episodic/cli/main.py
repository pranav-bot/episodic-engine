"""CLI for file-based graph creation and Markdown node ingestion."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from episodic.graph import (
    GRAPH_STRUCTURE,
    create_graph,
    delete_graph,
    list_registered_graphs,
    register_graph,
)
from episodic.ingest.markdown_node import ingest_markdown_node

app = typer.Typer(
    name="episodic",
    help=(
        "Create and manage file-based knowledge graphs.\n\n"
        "Typical workflow:\n"
        "  1. episodic create-graph --name \"My graph\" "
        "--directory ./my-graph\n"
        "  2. episodic ingest-node --source note.md "
        "--graph-json ./my-graph/graph.json\n"
        "  3. episodic graphs"
    ),
    no_args_is_help=True,
)


@app.command("create-graph")
def create_graph_cmd(
    name: str = typer.Option(..., "--name", help="Name for the graph"),
    directory: Path = typer.Option(
        Path(".episodic"),
        "--directory",
        help="Directory for graph.json (default: .episodic/)",
    ),
) -> None:
    """Create an empty graph.json.

    The command creates the directory when needed and never overwrites an
    existing graph.json.

    Example:
        episodic create-graph --name "My graph" --directory ./my-graph
    """
    try:
        graph_path = create_graph(directory, name)
        register_graph(graph_path)
    except (FileExistsError, OSError, ValueError, json.JSONDecodeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"created: {graph_path}")
    typer.echo(GRAPH_STRUCTURE)


@app.command("graphs")
def graphs_cmd(
) -> None:
    """List every graph recorded in ~/.episodic/graphs.json."""
    try:
        graphs = list_registered_graphs()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if not graphs:
        typer.echo("No graphs registered.")
        return

    typer.echo(f"{'name':<30} {'graph':<60} {'nodes':>5} {'links':>5} status")
    for name, path, node_count, link_count in graphs:
        if node_count is None:
            typer.echo(
                f"{name:<30} {str(path):<60} {'-':>5} {'-':>5} missing or invalid"
            )
        else:
            typer.echo(
                f"{name:<30} {str(path):<60} {node_count:>5} {link_count:>5} ok"
            )


@app.command("delete-graph")
def delete_graph_cmd(
    name: str = typer.Option(..., "--name", help="Name of the registered graph to delete"),
) -> None:
    """Delete a registered graph, its folder, and its registry entry."""
    typer.confirm(
        f"Delete the registered graph named {name} and its folder?",
        abort=True,
    )
    try:
        delete_graph(name)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"deleted: {name}")


@app.command("ingest-node")
def ingest_node_cmd(
    source: Path = typer.Option(..., "--source", help="Markdown node file"),
    graph_json: Path = typer.Option(..., "--graph-json", help="Graph file to update"),
) -> None:
    """Interactively append a Markdown node to a graph.

    The Markdown file is stored as the node content. The command asks for the
    node ID, title, description, and optional parent ID.

    Leave the parent ID blank to create a top-level node. Use an existing node
    ID to create a parent link and build a chain.

    Example:
        episodic ingest-node --source note.md --graph-json ./my-graph/graph.json
    """
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
