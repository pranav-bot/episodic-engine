"""CLI for file-based knowledge graphs."""

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
    resolve_registered_graph,
)
from episodic.ingest.markdown_node import ingest_markdown_node
from episodic.model.document import load_graph, save_graph
from episodic.model.identity import edge_id
from episodic.model.types import EDGE_TYPES, Edge

app = typer.Typer(
    name="episodic",
    help=(
        "Create and manage file-based knowledge graphs.\n\n"
        "Typical workflow:\n"
        "  1. episodic create-graph --name \"My graph\" "
        "--directory ./my-graph\n"
        "  2. episodic ingest-node --source note.md "
        "--name \"My graph\"\n"
        "  3. episodic link --name \"My graph\" --source a --target b --type calls\n"
        "  4. episodic neighbors --name \"My graph\" --node a\n"
        "  5. episodic graphs"
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

    headers = ("GRAPH NAME", "LAST UPDATED", "NODES")
    rows = [
        (name, updated or "missing or invalid", "-" if node_count is None else str(node_count))
        for name, _, node_count, updated in graphs
    ]
    widths = [max(len(header), *(len(row[index]) for row in rows)) for index, header in enumerate(headers)]
    separator = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    typer.echo(separator)
    typer.echo("| " + " | ".join(header.ljust(width) for header, width in zip(headers, widths)) + " |")
    typer.echo(separator)
    for row in rows:
        typer.echo("| " + " | ".join(value.ljust(width) for value, width in zip(row, widths)) + " |")
    typer.echo(separator)


@app.command("delete-graph")
def delete_graph_cmd(
    name: str = typer.Option(..., "--name", help="Name of the registered graph to delete"),
) -> None:
    """Delete a registered graph and its registry entry.

    The graph folder is removed only when graph.json is the only file in it.
    """
    typer.confirm(
        f"Delete the registered graph named {name}?",
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
    name: str = typer.Option(..., "--name", help="Registered graph name to update"),
    edge_type: str = typer.Option(
        "contains",
        "--type",
        help="Link from the document to each heading. A heading can override it with {calls}.",
    ),
) -> None:
    """Append a Markdown file as a document node.

    The node id is a fingerprint of the file. Each heading becomes a chunk.
    The link type defaults to contains. Pass --type, or write the type on a
    heading, to use another one: imports, calls, references, or describes.

    Example:
        episodic ingest-node --source note.md --name "My graph" --type describes
    """
    try:
        graph_path = resolve_registered_graph(name)
        node = ingest_markdown_node(source, graph_path, edge_type=edge_type)
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"{'added' if node['created'] else 'updated'}: node={node['id']} graph={name}")


@app.command("link")
def link_cmd(
    name: str = typer.Option(..., "--name", help="Registered graph name"),
    source: str = typer.Option(..., "--source", help="Source node id"),
    target: str = typer.Option(..., "--target", help="Target node id"),
    edge_type: str = typer.Option(..., "--type", help="contains, imports, calls, references, or describes"),
) -> None:
    """Add one typed edge between two nodes that are already in the graph."""
    try:
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"unknown edge type: {edge_type}")
        graph_path = resolve_registered_graph(name)
        graph_name, graph = load_graph(graph_path)
        graph.add_edge(Edge(edge_id(source, target, edge_type), edge_type, source, target))
        save_graph(graph_path, graph_name, graph)
    except (FileNotFoundError, KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"linked: {source} -{edge_type}-> {target}")


@app.command("neighbors")
def neighbors_cmd(
    name: str = typer.Option(..., "--name", help="Registered graph name"),
    node: str = typer.Option(..., "--node", help="Start node id"),
    edge_type: str | None = typer.Option(None, "--edge-type", help="Limit to one edge type"),
    direction: str = typer.Option("out", "--direction", help="out or in"),
) -> None:
    """Print the nodes one step from a node. File bytes are not read."""
    try:
        _graph_name, graph = load_graph(resolve_registered_graph(name))
        neighbor_ids = graph.neighbors(node, edge_type=edge_type, direction=direction)
    except (FileNotFoundError, KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    if not neighbor_ids:
        typer.echo("(none)")
        return
    for neighbor_id in neighbor_ids:
        label = graph.nodes[neighbor_id].label
        typer.echo(f"{neighbor_id}\t{label}")


@app.command("merge-graphs")
def merge_graphs_cmd(
    into: str = typer.Option(..., "--into", help="Graph that receives the merge"),
    source_name: str = typer.Option(..., "--from", help="Graph that is copied in and left unchanged"),
) -> None:
    """Copy nodes, edges, and missing payloads from one graph into another.

    A label or type clash keeps the destination value and is saved on the
    destination graph.
    """
    try:
        into_path = resolve_registered_graph(into)
        source_path = resolve_registered_graph(source_name)
        into_name, destination = load_graph(into_path)
        _source_name, source = load_graph(source_path)
        destination.merge(source)
        save_graph(into_path, into_name, destination)
    except (FileNotFoundError, KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"merged: into={into} from={source_name} conflicts={len(destination.conflicts)}")
    for conflict in destination.conflicts:
        typer.echo(
            f"conflict: {conflict.node_id} {conflict.field} "
            f"kept={conflict.destination} source={conflict.source}"
        )


if __name__ == "__main__":
    app()
