"""CLI for file-based graph creation and Markdown node ingestion."""

from __future__ import annotations

import json
from pathlib import Path

import typer
import yaml

from episodic.graph import GRAPH_STRUCTURE, create_graph
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


@app.command("ingest-node")
def ingest_node_cmd(
    source: Path = typer.Option(..., "--source", help="Markdown node file"),
    graph_json: Path = typer.Option(..., "--graph-json", help="Graph file to update"),
) -> None:
    """Append one Markdown node to an existing graph.json."""
    try:
        node = ingest_markdown_node(source, graph_json)
    except (FileNotFoundError, ValueError, OSError, yaml.YAMLError, json.JSONDecodeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"added: node={node['id']} graph={graph_json.resolve()}")


if __name__ == "__main__":
    app()
