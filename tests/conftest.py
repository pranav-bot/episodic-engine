import json
from pathlib import Path

import pytest

from episodic.config import EpisodicConfig, EpisodeLogConfig, InitConfig, StorageConfig
from episodic.drivers.sqlite_episode_store import SQLiteEpisodeStore
from episodic.ingest.graphify_adapter import parse_graph_json


FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def temp_config(tmp_path: Path) -> EpisodicConfig:
    data_dir = tmp_path / "episodic"
    return EpisodicConfig(
        storage=StorageConfig(
            episode_log=EpisodeLogConfig(path=str(data_dir / "episodes.db")),
        ),
        init=InitConfig(marker_file=str(data_dir / ".initialized")),
    ).expand_paths()


@pytest.fixture
def stores(temp_config: EpisodicConfig) -> SQLiteEpisodeStore:
    return SQLiteEpisodeStore(temp_config.episode_db_path)


def load_fixture(name: str) -> tuple[list, list]:
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return parse_graph_json(data)
