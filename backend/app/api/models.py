import httpx
from fastapi import APIRouter

from backend.app.settings import get_settings

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/")
async def list_models() -> dict:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                settings.openai_base_url.rstrip("/") + "/models",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            )
            response.raise_for_status()
        data = response.json()
        models = [item["id"] for item in data.get("data", []) if "id" in item]
        return {"models": models, "default": settings.default_model}
    except Exception as exc:
        return {"models": [], "default": settings.default_model, "error": str(exc)}

