from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.app.schemas import Attachment
from backend.app.tools.image import to_data_url, validate_image
from backend.app.tools.url_fetch import fetch_url_as_text

router = APIRouter(prefix="/api/attachments", tags=["attachments"])


class UrlRequest(BaseModel):
    url: str


@router.post("/image")
async def upload_image(file: Annotated[UploadFile, File(...)]) -> Attachment:
    data = await file.read()
    try:
        mime, _ = validate_image(data, file.filename or "image")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Attachment(kind="image", payload=to_data_url(data, mime), source=file.filename)


@router.post("/url")
async def attach_url(req: UrlRequest) -> Attachment:
    try:
        text = await fetch_url_as_text(req.url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Attachment(kind="url", payload=text, source=req.url)
