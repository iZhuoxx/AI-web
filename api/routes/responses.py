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

@router.get("/responses/credit_summary")
async def credit_summary(request: Request):
    api_key = get_headers()
    return await openai_client.credit_summary(api_key=api_key)

@router.post("/responses/stream")
async def responses_stream_route(request: Request):
    _check_auth(request)
    payload: Dict[str, Any] = await request.json()

    async def event_gen():
        async for chunk in openai_client.responses_stream(payload):
            yield chunk + "\n"  # newline delimited

    return StreamingResponse(event_gen(), media_type="text/event-stream")

@router.post("/responses")
async def responses_once_route(request: Request):
    _check_auth(request)
    payload: Dict[str, Any] = await request.json()
    data = await openai_client.responses_once(payload)
    return JSONResponse(data)
