import json
from pathlib import Path

import pytest

from episodic.drivers.sqlite_episode_store import SQLiteEpisodeStore
from episodic.ingest.save_pipeline import SavePipeline
from episodic.init_service import is_initialized, run_init


def test_save_first_snapshot_creates_episode(temp_config, stores):
    run_init(temp_config)
    SQLiteEpisodeStore(temp_config.episode_db_path)
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

    reg = stores.get_subgraph("test-repo")
    assert reg is not None
    assert reg.latest_snapshot_hash == result.snapshot_hash


def test_init_defers_storage_creation(temp_config):
    run_init(temp_config)

    assert is_initialized(temp_config)
    assert not temp_config.episode_db_path.exists()


def test_resave_unchanged_is_noop(temp_config, stores):
    run_init(temp_config)
    SQLiteEpisodeStore(temp_config.episode_db_path)
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

    assert stores.episode_count("test-repo") == 1


def test_resave_changed_requires_snapshot_storage(temp_config, stores):
    run_init(temp_config)
    SQLiteEpisodeStore(temp_config.episode_db_path)
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    pipeline = SavePipeline(temp_config)
    pipeline.save(
        "test-repo",
        source=fixtures,
        skip_graphify=True,
        graph_json_path=fixtures / "graph_v1.json",
    )
    with pytest.raises(RuntimeError, match="snapshot storage"):
        pipeline.save(
            "test-repo",
            source=fixtures,
            skip_graphify=True,
            graph_json_path=fixtures / "graph_v2.json",
        )
