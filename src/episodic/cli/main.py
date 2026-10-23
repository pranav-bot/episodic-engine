"""CLI for Episodic Engine.

Provides commands for initializing the engine, saving snapshots,
and checking status of tracked subgraphs.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer
import yaml

from episodic.config import load_config
from episodic.graph import GRAPH_STRUCTURE, create_graph
from episodic.init_service import is_initialized, run_init
from episodic.ingest.markdown_node import ingest_markdown_node
from episodic.ingest.save_pipeline import GraphifyRunError, SavePipeline

app = typer.Typer(
    name="episodic",
    help="Episodic memory layer for graphify knowledge graphs.",
    no_args_is_help=True,
)


@app.command("create-graph")
def create_graph_cmd(
    directory: Path = typer.Option(..., "--directory", help="Directory for graph.json"),
) -> None:
    """Create an empty graph file and explain how to add nodes later."""
    _require_init()
    graph_dir = directory.resolve()

    try:
        graph_path = create_graph(graph_dir)
    except (FileExistsError, FileNotFoundError, ValueError, OSError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"created: {graph_path}")
    typer.echo("not registered: storage-backed graph saving is disabled")
    typer.echo(GRAPH_STRUCTURE)


def _require_init() -> None:
    """Check if engine is initialized, exit if not.

    Raises:
        typer.Exit: If not initialized
    """
    config = load_config()
    if not is_initialized(config):
        typer.secho(
            "Episodic Engine is not initialized. Run: episodic init",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)


@app.command("init")
def init_cmd() -> None:
    """Create local data dir, SQLite schema, config, and install graphify."""
    config = load_config()
    try:
        marker = run_init(config)
    except GraphifyRunError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo("Episodic Engine initialized.")
    typer.echo(f"  data dir:  {config.data_dir}")
    typer.echo(f"  config:    {config.data_dir / 'config.yaml'}")
    typer.echo(f"  marker:    {marker}")


@app.command("save")
def save_cmd(
    id: str = typer.Option(..., "--id", help="Subgraph slug (e.g. myrepo-code)"),
    source: Path = typer.Option(..., "--source", help="Corpus path for graphify"),
    graphify_out: Path | None = typer.Option(
        None, "--graphify-out", help="Override graphify-out directory"
    ),
    graph_json: Path | None = typer.Option(
        None, "--graph-json", help="Use existing graph.json instead of running graphify"
    ),
) -> None:
    """Run graphify on source and persist the subgraph snapshot + episode."""
    _require_init()
    config = load_config()
    pipeline = SavePipeline(config)
    try:
        result = pipeline.save(
            id,
            source,
            graphify_out,
            skip_graphify=graph_json is not None,
            graph_json_path=graph_json,
        )
    except (GraphifyRunError, FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if result.status == "unchanged":
        typer.echo(
            f"unchanged: subgraph={result.subgraph_id} hash={result.snapshot_hash} "
            f"nodes={result.node_count} edges={result.edge_count}"
        )
        return

    typer.echo(
        f"saved: subgraph={result.subgraph_id} episode={result.episode_id} "
        f"ops={result.ops_total} hash={result.snapshot_hash} "
        f"nodes={result.node_count} edges={result.edge_count}"
    )


@app.command("ingest-node")
def ingest_node_cmd(
    id: str = typer.Option(..., "--id", help="Subgraph slug (e.g. myrepo-code)"),
    source: Path = typer.Option(..., "--source", help="Markdown node file"),
    graph_json: Path | None = typer.Option(
        None,
        "--graph-json",
        help="Existing graph.json to append this node to; omit for a one-node graph",
    ),
) -> None:
    """Ingest one Markdown node as a graph snapshot."""
    _require_init()
    config = load_config()
    try:
        result = ingest_markdown_node(
            SavePipeline(config), id, source, graph_json_path=graph_json
        )
    except (FileNotFoundError, ValueError, OSError, yaml.YAMLError, json.JSONDecodeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"{result.status}: subgraph={result.subgraph_id} "
        f"episode={result.episode_id or '-'} nodes={result.node_count} "
        f"edges={result.edge_count}"
    )


@app.command("delete-subgraph")
def delete_subgraph_cmd(
    id: str = typer.Option(..., "--id", help="Subgraph slug to delete"),
    yes: bool = typer.Option(
        False, "--yes", help="Confirm deletion without an interactive prompt"
    ),
) -> None:
    """Delete a registered subgraph and its episode history."""
    _require_init()
    if not yes:
        typer.confirm(
            f"Delete subgraph {id!r}, its episodes, and registry entry?",
            abort=True,
        )

    config = load_config()
    if not config.episode_db_path.is_file():
        typer.secho(f"unknown subgraph: {id}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    store = SavePipeline(config).store
    if not store.delete_subgraph(id):
        typer.secho(f"unknown subgraph: {id}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.echo(f"deleted: subgraph={id}")


@app.command("reset")
def reset_cmd(
    yes: bool = typer.Option(
        False, "--yes", help="Confirm deletion without an interactive prompt"
    ),
) -> None:
    """Delete all Episodic-managed graphs, storage, database, and init state."""
    config = load_config()
    data_dir = config.data_dir.resolve()
    typer.echo(
        f"WARNING: this will permanently delete all Episodic graphs, snapshots, "
        f"the SQLite database, config, and initialization state at {data_dir}."
    )
    if not yes:
        typer.confirm("Continue and start afresh?", abort=True)
    if data_dir.exists():
        shutil.rmtree(data_dir)
    typer.echo(f"reset: deleted {data_dir}")


def _show_graphs() -> None:
    _require_init()
    config = load_config()
    if not config.episode_db_path.is_file():
        typer.echo("No graphs registered.")
        return
    store = SavePipeline(config).store
    rows = store.list_status()
    if not rows:
        typer.echo("No subgraphs registered.")
        return

    typer.echo(
        f"{'subgraph_id':<20} {'hash':<14} {'episodes':>8}  {'last_seen_at':<22} source"
    )
    for row in rows:
        short_hash = "-"
        if row.latest_snapshot_hash:
            short_hash = row.latest_snapshot_hash.replace("sha256:", "")[:12] + "…"
        typer.echo(
            f"{row.subgraph_id:<20} {short_hash:<14} {row.episode_count:>8}  "
            f"{row.last_seen_at or '-':<22} {row.source_path}"
        )


@app.command("graphs")
def graphs_cmd() -> None:
    """List all graphs registered with Episodic Engine."""
    _show_graphs()


@app.command("status")
def status_cmd() -> None:
    """List registered subgraphs and episode counts."""
    _show_graphs()


if __name__ == "__main__":
    app()
