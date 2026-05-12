import json
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.app.schemas import Preset, utc_now
from backend.app.storage import preset_repo

router = APIRouter(prefix="/api/presets", tags=["presets"])


@router.get("/")
async def list_presets() -> list[Preset]:
    return preset_repo.list_presets()


@router.get("/{preset_id}")
async def get_preset(preset_id: str) -> Preset:
    preset = preset_repo.get_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="preset not found")
    return preset


@router.post("/")
async def create_preset(preset: Preset) -> Preset:
    if not preset.id:
        preset.id = uuid4().hex
    now = utc_now()
    preset.created_at = preset.created_at or now
    preset.updated_at = now
    return preset_repo.save_preset(preset)


@router.put("/{preset_id}")
async def update_preset(preset_id: str, preset: Preset) -> Preset:
    preset.id = preset_id
    return preset_repo.save_preset(preset)


@router.delete("/{preset_id}")
async def delete_preset(preset_id: str) -> dict[str, bool]:
    deleted = preset_repo.delete_preset(preset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="preset not found")
    return {"deleted": True}


@router.post("/import")
async def import_preset(file: Annotated[UploadFile, File(...)]) -> Preset:
    try:
        data = json.loads((await file.read()).decode("utf-8"))
        preset = Preset.model_validate(data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid preset JSON: {exc}") from exc
    return preset_repo.save_preset(preset)


@router.get("/{preset_id}/export")
async def export_preset(preset_id: str) -> FileResponse:
    preset = preset_repo.get_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="preset not found")
    path = preset_repo.get_preset_file(preset_id)
    if path:
        return FileResponse(path, filename=f"{preset.name}.json", media_type="application/json")
    raise HTTPException(status_code=404, detail="preset file not found")
