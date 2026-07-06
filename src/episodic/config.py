from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class EpisodeLogConfig(BaseModel):
    driver: str = "sqlite"
    path: str = "~/.episodic-engine/episodes.db"


class SnapshotsConfig(BaseModel):
    driver: str = "local"
    path: str = "~/.episodic-engine/snapshots/"


class StorageConfig(BaseModel):
    episode_log: EpisodeLogConfig = Field(default_factory=EpisodeLogConfig)
    snapshots: SnapshotsConfig = Field(default_factory=SnapshotsConfig)


class GraphifyConfig(BaseModel):
    binary: str = "graphify"
    install_via: str = "uv tool install graphifyy"


class InitConfig(BaseModel):
    marker_file: str = "~/.episodic-engine/.initialized"


class EpisodicConfig(BaseModel):
    deployment: str = "hybrid-local"
    storage: StorageConfig = Field(default_factory=StorageConfig)
    graphify: GraphifyConfig = Field(default_factory=GraphifyConfig)
    init: InitConfig = Field(default_factory=InitConfig)

    def expand_paths(self) -> EpisodicConfig:
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
        return Path(self.storage.episode_log.path).expanduser().parent

    @property
    def episode_db_path(self) -> Path:
        return Path(self.storage.episode_log.path).expanduser()

    @property
    def snapshots_dir(self) -> Path:
        return Path(self.storage.snapshots.path).expanduser()

    @property
    def marker_path(self) -> Path:
        return Path(self.init.marker_file).expanduser()


def default_config_dict() -> dict:
    example = Path(__file__).resolve().parents[2] / "config.example.yaml"
    if example.exists():
        with example.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    return EpisodicConfig().model_dump()


def config_search_paths() -> list[Path]:
    paths: list[Path] = []
    if env := os.environ.get("EPISODIC_CONFIG"):
        paths.append(Path(env).expanduser())
    paths.append(Path("~/.episodic-engine/config.yaml").expanduser())
    return paths


def load_config() -> EpisodicConfig:
    for path in config_search_paths():
        if path.is_file():
            with path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            return EpisodicConfig.model_validate(data).expand_paths()
    return EpisodicConfig.model_validate(default_config_dict()).expand_paths()


def write_default_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(default_config_dict(), fh, sort_keys=False)


SUBGRAPH_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def validate_subgraph_id(subgraph_id: str) -> str:
    if not SUBGRAPH_ID_PATTERN.match(subgraph_id):
        raise ValueError(
            "subgraph_id must match [a-z0-9][a-z0-9_-]* "
            f"(got {subgraph_id!r})"
        )
    return subgraph_id
