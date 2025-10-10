"""Audio transcription routes."""
from typing import Optional
import mimetypes
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from api.settings import settings
from api.services import openai_client

router = APIRouter(prefix="/audio", tags=["audio"])

DEFAULT_AUDIO_MODEL = "gpt-4o-transcribe"
DEFAULT_RESPONSE_FORMAT = "text"
MAX_AUDIO_MB = 250


def _check_auth(request: Request) -> None:
    if settings.INTERNAL_TOKEN and request.headers.get("X-API-KEY") != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/transcriptions")
async def create_transcription(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form(DEFAULT_AUDIO_MODEL),
    response_format: str = Form(DEFAULT_RESPONSE_FORMAT),
    language: Optional[str] = Form(None),
    temperature: Optional[float] = Form(None),
    prompt: Optional[str] = Form(None),
):
    _check_auth(request)

    filename = file.filename or "audio.wav"
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Audio file contains no data")

    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_AUDIO_MB:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file too large: {size_mb:.2f}MB > {MAX_AUDIO_MB}MB",
        )

    clean_model = model.strip() or DEFAULT_AUDIO_MODEL
    clean_response_format = response_format.strip() or DEFAULT_RESPONSE_FORMAT
    guessed_type, _ = mimetypes.guess_type(filename)
    content_type = file.content_type or guessed_type or "application/octet-stream"

    try:
        result = await openai_client.transcribe_audio(
            filename=filename,
            content=contents,
            content_type=content_type,
            model=clean_model,
            response_format=clean_response_format,
            language=language.strip() if isinstance(language, str) and language.strip() else None,
            temperature=temperature,
            prompt=prompt.strip() if isinstance(prompt, str) and prompt.strip() else None,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    payload = {
        "text": result.get("text", ""),
        "model": result.get("model", clean_model),
        "response_format": result.get("response_format", clean_response_format),
    }

    raw = result.get("raw")
    if isinstance(raw, dict):
        if isinstance(raw.get("duration"), (int, float)):
            payload["duration"] = raw["duration"]
        if isinstance(raw.get("language"), str) and not payload.get("language"):
            payload["language"] = raw["language"]
    if language:
        payload.setdefault("language", language)

    return JSONResponse(payload)
