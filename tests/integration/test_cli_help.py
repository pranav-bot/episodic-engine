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


def test_create_graph_registers_graph_outside_default_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    graph_dir = tmp_path / "project" / "knowledge"

    result = CliRunner().invoke(
        app, ["create-graph", "--directory", str(graph_dir)]
    )
    listed = CliRunner().invoke(app, ["graphs"])

    assert result.exit_code == 0
    assert listed.exit_code == 0
    assert str(graph_dir / "graph.json") in listed.stdout
