"""Configuration for Episodic Engine.

Handles loading, validation, and path expansion for configuration.
Config is loaded from $EPISODIC_CONFIG or ~/.episodic-engine/config.yaml,
falling back to defaults from config.example.yaml.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class EpisodeLogConfig(BaseModel):
    """Configuration for the episode log (SQLite database)."""

    driver: str = "sqlite"
    path: str = "~/.episodic-engine/episodes.db"


class SnapshotsConfig(BaseModel):
    """Configuration for snapshot storage (blob store)."""

    driver: str = "local"
    path: str = "~/.episodic-engine/snapshots/"


class StorageConfig(BaseModel):
    """Storage configuration for episodes and snapshots."""

    episode_log: EpisodeLogConfig = Field(default_factory=EpisodeLogConfig)
    snapshots: SnapshotsConfig = Field(default_factory=SnapshotsConfig)


class GraphifyConfig(BaseModel):
    """Configuration for graphify binary."""

    binary: str = "graphify"                        # Name/path of graphify binary
    install_via: str = "uv tool install graphifyy"  # Command to install if missing


class InitConfig(BaseModel):
    """Configuration for initialization."""

    marker_file: str = "~/.episodic-engine/.initialized"


class EpisodicConfig(BaseModel):
    """Main configuration for Episodic Engine."""

    deployment: str = "hybrid-local"
    storage: StorageConfig = Field(default_factory=StorageConfig)
    graphify: GraphifyConfig = Field(default_factory=GraphifyConfig)
    init: InitConfig = Field(default_factory=InitConfig)

    def expand_paths(self) -> EpisodicConfig:
        """Expand ~ in all paths to absolute paths.

        Returns:
            New EpisodicConfig instance with expanded paths
        """
        data = self.model_dump()
        data["storage"]["episode_log"]["path"] = str(
            Path(data["storage"]["episode_log"]["path"]).expanduser()
        )
        data["storage"]["snapshots"]["path"] = str(
            Path(data["storage"]["snapshots"]["path"]).expanduser()
        )
        data["init"]["marker_file"] = str(Path(data["init"]["marker_file"]).expanduser())
        return EpisodicConfig.model_validate(data)

    @property
    def data_dir(self) -> Path:
        """Get the data directory (parent of episode db)."""
        return Path(self.storage.episode_log.path).expanduser().parent

    @property
    def episode_db_path(self) -> Path:
        """Get path to episode SQLite database."""
        return Path(self.storage.episode_log.path).expanduser()

    @property
    def snapshots_dir(self) -> Path:
        """Get path to snapshots blob store directory."""
        return Path(self.storage.snapshots.path).expanduser()

    @property
    def marker_path(self) -> Path:
        """Get path to initialization marker file."""
        return Path(self.init.marker_file).expanduser()


def default_config_dict() -> dict:
    """Get default configuration dict.

    Tries to load from config.example.yaml in repo root,
    falls back to EpisodicConfig defaults.

    Returns:
        Configuration dictionary
    """
    example = Path(__file__).resolve().parents[2] / "config.example.yaml"
    if example.exists():
        with example.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    return EpisodicConfig().model_dump()


def config_search_paths() -> list[Path]:
    """Get list of config file search paths in order of priority.

    Returns:
        List of paths to check for config
    """
    paths: list[Path] = []
    if env := os.environ.get("EPISODIC_CONFIG"):
        paths.append(Path(env).expanduser())
    paths.append(Path("~/.episodic-engine/config.yaml").expanduser())
    return paths


def load_config() -> EpisodicConfig:
    """Load configuration from file or use defaults.

    Searches config paths in order, loads first found YAML file,
    validates with Pydantic, expands paths.

    Returns:
        Loaded and validated configuration
    """
    for path in config_search_paths():
        if path.is_file():
            with path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            return EpisodicConfig.model_validate(data).expand_paths()
    return EpisodicConfig.model_validate(default_config_dict()).expand_paths()


def write_default_config(path: Path) -> None:
    """Write default configuration to file if it doesn't exist.

    Args:
        path: Path to write config file
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(default_config_dict(), fh, sort_keys=False)


# Regex for validating subgraph IDs
SUBGRAPH_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def validate_subgraph_id(subgraph_id: str) -> str:
    """Validate subgraph ID format.

    Must match pattern: lowercase letters, numbers, hyphens, underscores
    Must start with alphanumeric character

    Args:
        subgraph_id: ID to validate

    Returns:
        Validated subgraph_id

    Raises:
        ValueError: If ID doesn't match pattern
    """
    if not SUBGRAPH_ID_PATTERN.match(subgraph_id):
        raise ValueError(
            "subgraph_id must match [a-z0-9][a-z0-9_-]* "
            f"(got {subgraph_id!r})"
        )
    return subgraph_id
