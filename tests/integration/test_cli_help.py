import json

from typer.testing import CliRunner

from episodic.cli.main import app


def test_help_explains_graph_workflow():
    output = CliRunner().invoke(app, ["--help"]).stdout

    assert "Typical workflow" in output
    assert "create-graph" in output
    assert "ingest-node" in output
    assert ".episodic" in output


def test_ingest_help_explains_parent_nodes():
    output = CliRunner().invoke(app, ["ingest-node", "--help"]).stdout

    assert "parent ID" in output
    assert "top-level node" in output
    assert "--name" in output


def test_delete_graph_requires_confirmation_and_removes_graph(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    graph_dir = tmp_path / "project" / "knowledge"
    CliRunner().invoke(
        app, ["create-graph", "--name", "Knowledge", "--directory", str(graph_dir)]
    )

    result = CliRunner().invoke(
        app,
        ["delete-graph", "--name", "Knowledge"],
        input="y\n",
    )

    assert result.exit_code == 0
    assert not graph_dir.exists()
    assert "deleted:" in result.stdout
    assert CliRunner().invoke(app, ["graphs"]).stdout == "No graphs registered.\n"


def test_delete_graph_can_be_cancelled(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    graph_dir = tmp_path / "project" / "knowledge"
    CliRunner().invoke(
        app, ["create-graph", "--name", "Knowledge", "--directory", str(graph_dir)]
    )

    result = CliRunner().invoke(
        app,
        ["delete-graph", "--name", "Knowledge"],
        input="n\n",
    )

    assert result.exit_code != 0
    assert graph_dir.exists()


def test_create_graph_registers_graph_outside_default_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    graph_dir = tmp_path / "project" / "knowledge"

    result = CliRunner().invoke(
        app,
        ["create-graph", "--name", "Project knowledge", "--directory", str(graph_dir)],
    )
    listed = CliRunner().invoke(app, ["graphs"])

    assert result.exit_code == 0
    assert listed.exit_code == 0
    assert "Project knowledge" in listed.stdout
    assert "LAST UPDATED" in listed.stdout
    assert "NODES" in listed.stdout
    assert "0" in listed.stdout


def test_ingest_node_resolves_graph_by_name(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    graph_dir = tmp_path / "project" / "knowledge"
    source = tmp_path / "note.md"
    source.write_text("Details\n", encoding="utf-8")
    CliRunner().invoke(
        app,
        ["create-graph", "--name", "Project knowledge", "--directory", str(graph_dir)],
    )

    result = CliRunner().invoke(
        app,
        ["ingest-node", "--source", str(source), "--name", "Project knowledge"],
        input="auth-note\nAuthentication\nAuth details\n\n",
    )

    assert result.exit_code == 0
    assert json.loads((graph_dir / "graph.json").read_text(encoding="utf-8"))["nodes"][0][
        "id"
    ] == "auth-note"
