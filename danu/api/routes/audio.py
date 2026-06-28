from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from danu.config import get_settings

router = APIRouter(tags=["audio"])


@router.get("/audio/{clip_id}.mp3")
async def serve_audio_clip(clip_id: str) -> FileResponse:
    if not clip_id.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid clip id")

    settings = get_settings()
    path = Path(settings.voice_tts_audio_dir) / f"{clip_id}.mp3"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")

    return FileResponse(path, media_type="audio/mpeg")