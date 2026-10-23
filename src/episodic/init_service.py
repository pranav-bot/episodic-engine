"""Initialization service for Episodic Engine.

Handles bootstrapping the local environment: creating directories,
writing config, initializing SQLite schema, installing graphify if needed,
and creating the initialization marker file.
"""

from __future__ import annotations

from pathlib import Path

from episodic.config import EpisodicConfig, write_default_config
from episodic.drivers.sqlite_episode_store import SQLiteEpisodeStore
from episodic.ingest.save_pipeline import ensure_graphify_installed


def run_init(config: EpisodicConfig) -> Path:
    """Initialize Episodic Engine.

    Creates data directories, writes default config if missing,
    initializes SQLite database schema, ensures graphify is installed,
    and creates initialization marker file.

    Args:
        config: Configuration to use

    Returns:
        Path to initialization marker file

    Raises:
        GraphifyRunError: If graphify cannot be installed
    """
    # Create directories
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.snapshots_dir.mkdir(parents=True, exist_ok=True)

    # Write default config if it doesn't exist
    config_path = config.data_dir / "config.yaml"
    write_default_config(config_path)

    # Initialize SQLite database (creates schema)
    SQLiteEpisodeStore(config.episode_db_path)

    # Ensure graphify binary is installed
    ensure_graphify_installed(config)

    # Create marker file
    config.marker_path.write_text("initialized\n", encoding="utf-8")
    return config.marker_path


def is_initialized(config: EpisodicConfig) -> bool:
    """Check if Episodic Engine is initialized.

    Requires both marker file and episode database to exist.

    Args:
        config: Configuration to check

    Returns:
        True if initialized, False otherwise
    """
    return config.marker_path.is_file() and config.episode_db_path.is_file()
