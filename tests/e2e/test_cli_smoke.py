from typer.testing import CliRunner

from episodic.cli.main import app


def test_save_without_init_fails(monkeypatch, tmp_path):
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
    monkeypatch.setenv("EPISODIC_CONFIG", str(config_path))

    runner = CliRunner()
    result = runner.invoke(app, ["save", "--id", "myrepo", "--source", str(tmp_path)])
    assert result.exit_code == 1
    combined = (result.stdout + result.stderr).lower()
    assert "not initialized" in combined
