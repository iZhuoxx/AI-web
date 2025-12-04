from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, Any
from api.services import openai_client
from api.settings import settings
from api.model import Message, MessageTurbo
from api.services.utils import get_headers, get_proxy

router = APIRouter(tags=["responses"]) 

def _check_auth(request: Request):
    if settings.INTERNAL_TOKEN and request.headers.get("X-API-KEY") != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/responses")
async def responses_complete_route(request: Request):
    _check_auth(request)
    payload: Dict[str, Any] = await request.json()
    try:
        data = await openai_client.responses_complete(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return JSONResponse(content=data)


@router.post("/responses/stream")
async def responses_stream_route(request: Request):
    _check_auth(request)
    payload: Dict[str, Any] = await request.json()

    async def event_gen():
        async for chunk in openai_client.responses_stream(payload):
            yield chunk + "\n"  # newline delimited

    return StreamingResponse(event_gen(), media_type="text/event-stream")
