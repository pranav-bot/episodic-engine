import json

import pytest

from episodic.cli.main import app
from episodic.drivers.sqlite_episode_store import SQLiteEpisodeStore
from episodic.graph import create_graph
from episodic.ingest.save_pipeline import SavePipeline
from episodic.init_service import run_init
from typer.testing import CliRunner


def test_create_graph_writes_empty_graph(tmp_path):
    path = create_graph(tmp_path / "knowledge")

    assert path.name == "graph.json"
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "nodes": [],
        "links": [],
    }


def test_create_graph_does_not_overwrite_existing_graph(tmp_path):
    path = create_graph(tmp_path)

    with pytest.raises(FileExistsError):
        create_graph(tmp_path)

    assert json.loads(path.read_text(encoding="utf-8"))["nodes"] == []


def test_create_graph_command_creates_file_without_registration(monkeypatch, tmp_path):
    data_dir = tmp_path / "episodic"
    config_path = data_dir / "config.yaml"
    data_dir.mkdir()
    config_path.write_text(
        f"""
storage:
  episode_log:
    path: {data_dir / "episodes.db"}
init:
  marker_file: {data_dir / ".initialized"}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (data_dir / ".initialized").write_text("initialized\n", encoding="utf-8")
    monkeypatch.setenv("EPISODIC_CONFIG", str(config_path))

    result = CliRunner().invoke(
        app, ["create-graph", "--directory", str(tmp_path / "notes")]
    )

    assert result.exit_code == 0
    assert "not registered" in result.stdout
    assert (tmp_path / "notes" / "graph.json").is_file()


def test_delete_subgraph_removes_registration_and_episodes(
    temp_config, tmp_path, monkeypatch
):
    run_init(temp_config)
    monkeypatch.setenv("EPISODIC_CONFIG", str(temp_config.data_dir / "config.yaml"))
    (temp_config.data_dir / "config.yaml").write_text(
        f"""
storage:
  episode_log:
    path: {temp_config.episode_db_path}
init:
  marker_file: {temp_config.marker_path}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    SQLiteEpisodeStore(temp_config.episode_db_path)
    graph = tmp_path / "graph.json"
    graph.write_text('{"nodes": [], "links": []}', encoding="utf-8")
    pipeline = SavePipeline(temp_config)
    pipeline.save(
        "notes",
        source=tmp_path,
        skip_graphify=True,
        graph_json_path=graph,
    )

    result = CliRunner().invoke(app, ["delete-subgraph", "--id", "notes", "--yes"])

    assert result.exit_code == 0
    assert "deleted: subgraph=notes" in result.stdout
    assert pipeline.store.get_subgraph("notes") is None
    assert pipeline.store.episode_count("notes") == 0


def test_reset_deletes_engine_state_with_confirmation(monkeypatch, tmp_path):
    data_dir = tmp_path / "episodic"
    config_path = data_dir / "config.yaml"
    data_dir.mkdir()
    config_path.write_text(
        f"""
storage:
  episode_log:
    path: {data_dir / "episodes.db"}
init:
  marker_file: {data_dir / ".initialized"}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (data_dir / "episodes.db").write_bytes(b"database")
    (data_dir / ".initialized").write_text("initialized\n", encoding="utf-8")
    monkeypatch.setenv("EPISODIC_CONFIG", str(config_path))

    result = CliRunner().invoke(app, ["reset"], input="n\n")
    assert result.exit_code != 0
    assert data_dir.exists()
    assert "WARNING" in result.stdout

    result = CliRunner().invoke(app, ["reset"], input="y\n")
    assert result.exit_code == 0
    assert not data_dir.exists()
