from functools import lru_cache
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@lru_cache
def get_data_dir() -> Path:
    data_dir = get_project_root() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "presets").mkdir(parents=True, exist_ok=True)
    (data_dir / "conversations").mkdir(parents=True, exist_ok=True)
    return data_dir


def get_presets_dir() -> Path:
    return get_data_dir() / "presets"


def get_conversations_dir() -> Path:
    return get_data_dir() / "conversations"

