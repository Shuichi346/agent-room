import logging

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api import attachments, auto_agents, chat, conversations, health, models, presets
from backend.app.paths import get_project_root
from backend.app.settings import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="agent-room", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(models.router)
    app.include_router(presets.router)
    app.include_router(conversations.router)
    app.include_router(attachments.router)
    app.include_router(chat.router)
    app.include_router(auto_agents.router)

    dist = get_project_root() / "frontend" / "dist"
    if dist.exists():
        assets = dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="not found")
            target = dist / full_path
            if target.is_file():
                return FileResponse(target)
            return FileResponse(dist / "index.html")

    return app


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    uvicorn.run(
        "backend.app.main:create_app",
        host=settings.app_host,
        port=settings.app_port,
        factory=True,
        reload=False,
    )


if __name__ == "__main__":
    main()
