import json

from typer.testing import CliRunner

from episodic.cli.main import app
from episodic.model.identity import node_id


def test_help_explains_graph_workflow():
    output = CliRunner().invoke(app, ["--help"]).stdout

    assert "Typical workflow" in output
    assert "create-graph" in output
    assert "ingest-node" in output
    assert "neighbors" in output
    assert "merge-graphs" in output
    assert ".episodic" in output


def test_ingest_help_explains_the_graph_model():
    output = CliRunner().invoke(app, ["ingest-node", "--help"]).stdout

    assert "fingerprint" in output
    assert "--type" in output
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
    source.write_text("# Authentication\n\nDetails\n", encoding="utf-8")
    CliRunner().invoke(
        app,
        ["create-graph", "--name", "Project knowledge", "--directory", str(graph_dir)],
    )

    result = CliRunner().invoke(
        app,
        ["ingest-node", "--source", str(source), "--name", "Project knowledge"],
    )

    saved = json.loads((graph_dir / "graph.json").read_text(encoding="utf-8"))
    document_id = node_id("document", str(source.resolve()), "note.md")
    assert result.exit_code == 0
    assert saved["nodes"][0]["id"] == document_id
    assert "content" not in saved["nodes"][0]
    assert saved["payloads"][document_id]["text"].startswith("# Authentication")


def test_link_neighbors_and_merge(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    code = tmp_path / "code"
    docs = tmp_path / "docs"
    note = tmp_path / "note.md"
    other = tmp_path / "other.md"
    note.write_text("# Login\n\nsecret\n\n# Check\n\npassword\n", encoding="utf-8")
    other.write_text("# Extra\n\nmore\n", encoding="utf-8")
    runner = CliRunner()
    assert runner.invoke(app, ["create-graph", "--name", "Code", "--directory", str(code)]).exit_code == 0
    assert runner.invoke(app, ["create-graph", "--name", "Docs", "--directory", str(docs)]).exit_code == 0
    assert runner.invoke(app, ["ingest-node", "--source", str(note), "--name", "Code"]).exit_code == 0
    saved = json.loads((code / "graph.json").read_text(encoding="utf-8"))
    login = next(node for node in saved["nodes"] if node["label"] == "Login" and node["type"] == "chunk")
    check = next(node for node in saved["nodes"] if node["label"] == "Check")
    assert runner.invoke(
        app,
        ["link", "--name", "Code", "--source", login["id"], "--target", check["id"], "--type", "calls"],
    ).exit_code == 0

    neighbors = runner.invoke(
        app,
        ["neighbors", "--name", "Code", "--node", login["id"], "--edge-type", "calls"],
    )
    assert neighbors.exit_code == 0
    assert f"{check['id']}\tCheck" in neighbors.stdout

    assert runner.invoke(app, ["ingest-node", "--source", str(other), "--name", "Docs"]).exit_code == 0
    merged = runner.invoke(app, ["merge-graphs", "--into", "Code", "--from", "Docs"])

    assert merged.exit_code == 0
    assert "conflicts=0" in merged.stdout
    code_saved = json.loads((code / "graph.json").read_text(encoding="utf-8"))
    extra_id = node_id("document", str(other.resolve()), "other.md")
    assert any(node["id"] == extra_id for node in code_saved["nodes"])
    docs_saved = json.loads((docs / "graph.json").read_text(encoding="utf-8"))
    assert any(node["id"] == extra_id for node in docs_saved["nodes"])
    assert not any(node["label"] == "Login" for node in docs_saved["nodes"])
