import json
from pathlib import Path

from episodic.ingest.save_pipeline import SavePipeline
from episodic.init_service import is_initialized, run_init


def test_save_first_snapshot_creates_episode(temp_config, stores):
    run_init(temp_config)
    assert is_initialized(temp_config)

    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "graph_v1.json"
    pipeline = SavePipeline(temp_config)
    result = pipeline.save(
        "test-repo",
        source=fixture.parent,
        skip_graphify=True,
        graph_json_path=fixture,
    )
    assert result.status == "saved"
    assert result.episode_id == "test-repo__ep_000001"
    assert result.ops_total == 4

    sqlite_store, blob_store = stores
    reg = sqlite_store.get_subgraph("test-repo")
    assert reg is not None
    assert reg.latest_snapshot_hash == result.snapshot_hash
    assert blob_store.exists(result.snapshot_hash)


def test_resave_unchanged_is_noop(temp_config, stores):
    run_init(temp_config)
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "graph_v1.json"
    pipeline = SavePipeline(temp_config)
    pipeline.save(
        "test-repo",
        source=fixture.parent,
        skip_graphify=True,
        graph_json_path=fixture,
    )
    result = pipeline.save(
        "test-repo",
        source=fixture.parent,
        skip_graphify=True,
        graph_json_path=fixture,
    )
    assert result.status == "unchanged"

    sqlite_store, _ = stores
    assert sqlite_store.episode_count("test-repo") == 1


def test_resave_changed_appends_diff_episode(temp_config, stores):
    run_init(temp_config)
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    pipeline = SavePipeline(temp_config)
    pipeline.save(
        "test-repo",
        source=fixtures,
        skip_graphify=True,
        graph_json_path=fixtures / "graph_v1.json",
    )
    result = pipeline.save(
        "test-repo",
        source=fixtures,
        skip_graphify=True,
        graph_json_path=fixtures / "graph_v2.json",
    )
    assert result.status == "saved"
    assert result.episode_id == "test-repo__ep_000002"
    assert result.ops_total > 0

    sqlite_store, _ = stores
    episode = sqlite_store.get_episode("test-repo__ep_000002")
    assert episode is not None
    op_types = {op.op.value for op in episode.operations}
    assert "RETRACT_NODE" in op_types


def test_blob_dedup_across_subgraphs(temp_config, stores):
    run_init(temp_config)
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "graph_v1.json"
    content = fixture.read_bytes()
    pipeline = SavePipeline(temp_config)

    r1 = pipeline.save(
        "repo-a",
        source=fixture.parent,
        skip_graphify=True,
        graph_json_path=fixture,
    )
    r2 = pipeline.save(
        "repo-b",
        source=fixture.parent,
        skip_graphify=True,
        graph_json_path=fixture,
    )
    assert r1.snapshot_hash == r2.snapshot_hash

    _, blob_store = stores
    shard = r1.snapshot_hash.replace("sha256:", "")[:2]
    blob_path = temp_config.snapshots_dir / shard
    matching = list(blob_path.glob("*.json"))
    assert len(matching) == 1

    sqlite_store, _ = stores
    assert sqlite_store.get_subgraph("repo-a") is not None
    assert sqlite_store.get_subgraph("repo-b") is not None
