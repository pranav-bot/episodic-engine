import json
from pathlib import Path

import pytest

from episodic.config import EpisodicConfig, EpisodeLogConfig, InitConfig, SnapshotsConfig, StorageConfig
from episodic.drivers.local_blob_store import LocalBlobStore
from episodic.drivers.sqlite_episode_store import SQLiteEpisodeStore
from episodic.ingest.graphify_adapter import parse_graph_json


FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def temp_config(tmp_path: Path) -> EpisodicConfig:
    data_dir = tmp_path / "episodic"
    return EpisodicConfig(
        storage=StorageConfig(
            episode_log=EpisodeLogConfig(path=str(data_dir / "episodes.db")),
            snapshots=SnapshotsConfig(path=str(data_dir / "snapshots")),
        ),
        init=InitConfig(marker_file=str(data_dir / ".initialized")),
    ).expand_paths()


@pytest.fixture
def stores(temp_config: EpisodicConfig) -> tuple[SQLiteEpisodeStore, LocalBlobStore]:
    return (
        SQLiteEpisodeStore(temp_config.episode_db_path),
        LocalBlobStore(temp_config.snapshots_dir),
    )


def load_fixture(name: str) -> tuple[list, list]:
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return parse_graph_json(data)
