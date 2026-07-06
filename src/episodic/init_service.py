from __future__ import annotations

from pathlib import Path

from episodic.config import EpisodicConfig, write_default_config
from episodic.drivers.sqlite_episode_store import SQLiteEpisodeStore
from episodic.ingest.save_pipeline import ensure_graphify_installed


def run_init(config: EpisodicConfig) -> Path:
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.snapshots_dir.mkdir(parents=True, exist_ok=True)

    config_path = config.data_dir / "config.yaml"
    write_default_config(config_path)

    SQLiteEpisodeStore(config.episode_db_path)
    ensure_graphify_installed(config)

    config.marker_path.write_text("initialized\n", encoding="utf-8")
    return config.marker_path


def is_initialized(config: EpisodicConfig) -> bool:
    return config.marker_path.is_file() and config.episode_db_path.is_file()
