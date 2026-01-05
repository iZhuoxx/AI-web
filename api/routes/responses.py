import logging
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Any, Dict, List
from api.services import openai_client
from api.services.openai_utils import build_responses_payload
from api.settings import settings

router = APIRouter(tags=["responses"])

LOG_DIR = Path(__file__).resolve().parent.parent / "services" / "logs"
LOG_FILE = LOG_DIR / "openai_responses.log"


def _responses_logger() -> logging.Logger:
    logger = logging.getLogger("openai_responses")
    if logger.handlers:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))

    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger

def _check_auth(request: Request):
    if settings.INTERNAL_TOKEN and request.headers.get("X-API-KEY") != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/responses")
async def responses_complete_route(request: Request):
    """Proxy a single Responses API request to OpenAI and return the full JSON payload."""
    _check_auth(request)
    payload: Dict[str, Any] = await request.json()
    try:
        normalized = build_responses_payload(payload or {})
        data = await openai_client.responses_complete(normalized)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except HTTPException:
        raise
    return JSONResponse(content=data)


@router.post("/responses/stream")
async def responses_stream_route(request: Request):
    """Proxy a streaming Responses API request to OpenAI and relay SSE chunks."""
    _check_auth(request)
    payload: Dict[str, Any] = await request.json()

    try:
        normalized = build_responses_payload(payload or {})
    except HTTPException:
        raise

    async def event_gen():
        try:
            async for chunk in openai_client.responses_stream(normalized):
                yield chunk + "\n"  # newline delimited
        except Exception as exc:
            raise

    return StreamingResponse(event_gen(), media_type="text/event-stream")
