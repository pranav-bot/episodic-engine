import json

from episodic.mcp_server import build_server, create_context_graph_tool


def test_create_context_graph_tool_returns_the_hot_map(tmp_path):
    folder = tmp_path / "repo"
    folder.mkdir()
    (folder / "a.py").write_text("def start():\n    return 1\n", encoding="utf-8")
    registry_home = tmp_path / "home"
    registry_home.mkdir()

    import episodic.graph as graph_module
    import episodic.ingest.folder as folder_module

    original = graph_module.registry_path
    graph_module.registry_path = lambda: registry_home / "graphs.json"
    folder_module.registry_path = graph_module.registry_path
    try:
        payload = json.loads(create_context_graph_tool(str(folder), "Repo"))
    finally:
        graph_module.registry_path = original
        folder_module.registry_path = original

    assert payload["name"] == "Repo"
    assert any(node["label"] == "start" for node in payload["nodes"])
    assert "def start" not in json.dumps(payload)
