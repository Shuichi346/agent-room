import json
import logging
import os
import re
from pathlib import Path
from uuid import uuid4

from backend.app.paths import get_presets_dir
from backend.app.schemas import Preset, utc_now

logger = logging.getLogger(__name__)


def _safe_name(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name).strip("._")
    if not safe:
        safe = "preset"
    return safe


def _preset_files() -> list[Path]:
    return sorted(get_presets_dir().glob("*.json"))


def _load(path: Path) -> Preset | None:
    try:
        return Preset.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Skipping unreadable preset %s: %s", path, exc)
        return None


def list_presets() -> list[Preset]:
    presets = [preset for path in _preset_files() if (preset := _load(path)) is not None]
    return sorted(presets, key=lambda preset: preset.updated_at, reverse=True)


def get_preset(preset_id: str) -> Preset | None:
    return next((preset for preset in list_presets() if preset.id == preset_id), None)


def _path_for(preset: Preset) -> Path:
    base = _safe_name(preset.name)
    candidate = get_presets_dir() / f"{base}.json"
    if candidate.exists():
        existing = _load(candidate)
        if existing and existing.id != preset.id:
            candidate = get_presets_dir() / f"{base}_{preset.id[:8]}.json"
    return candidate


def save_preset(preset: Preset) -> Preset:
    if not preset.id:
        preset.id = uuid4().hex
    now = utc_now()
    if not preset.created_at:
        preset.created_at = now
    preset.updated_at = now
    path = _path_for(preset)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(preset.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp_path, path)
    return preset


def delete_preset(preset_id: str) -> bool:
    for path in _preset_files():
        preset = _load(path)
        if preset and preset.id == preset_id:
            path.unlink()
            return True
    return False


def get_preset_file(preset_id: str) -> Path | None:
    for path in _preset_files():
        preset = _load(path)
        if preset and preset.id == preset_id:
            return path
    return None
