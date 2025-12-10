import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Any, Dict, List
from api.services import openai_client
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


def _coerce_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
        return out
    return []


def _has_file_search(tools: Any) -> bool:
    if isinstance(tools, dict):
        return tools.get("type") == "file_search"
    if isinstance(tools, list):
        for tool in tools:
            if isinstance(tool, dict) and tool.get("type") == "file_search":
                return True
    return False


def _build_responses_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accept either a full Responses API payload (with `input`) or a simplified payload
    containing text/images/files/tools, and normalize to the Responses schema.
    """
    if "input" in raw:
        return raw

    model = str(raw.get("model") or "")
    system_prompt = str(raw.get("system_prompt") or raw.get("systemPrompt") or "").strip()
    text = str(raw.get("text") or raw.get("message") or "").strip()
    images = _coerce_str_list(raw.get("images"))
    files = raw.get("files") if isinstance(raw.get("files"), list) else []
    tools = raw.get("tools")
    includes = _coerce_str_list(raw.get("includes") or raw.get("include"))
    prev_id = raw.get("previous_response_id") or raw.get("previousResponseId")
    temperature = raw.get("temperature")
    max_output_tokens = raw.get("max_output_tokens") or raw.get("maxTokens")
    reasoning = raw.get("reasoning")

    input_blocks: List[Dict[str, Any]] = []
    if system_prompt:
        input_blocks.append({"role": "system", "content": [{"type": "input_text", "text": system_prompt}]})

    user_content: List[Dict[str, Any]] = []
    if text:
        user_content.append({"type": "input_text", "text": text})
    for url in images:
        user_content.append({"type": "input_image", "image_url": url})
    for f in files:
        if not isinstance(f, dict):
            continue
        file_id = f.get("file_id") or f.get("fileId")
        if isinstance(file_id, str) and file_id.strip():
            user_content.append({"type": "input_file", "file_id": file_id.strip()})
        file_text = f.get("text")
        if isinstance(file_text, str) and file_text.strip():
            name = f.get("name") or "file"
            label = f"[截断] {name}" if f.get("truncated") else str(name)
            user_content.append({"type": "input_text", "text": f"【文件：{label}】\n{file_text}"})

    if not user_content and not input_blocks:
        raise HTTPException(status_code=400, detail="请求体缺少内容")

    input_blocks.append({"role": "user", "content": user_content})

    include_set = set(includes)
    if _has_file_search(tools):
        include_set.add("file_search_call.results")

    payload: Dict[str, Any] = {
        "model": model,
        "input": input_blocks,
    }
    if tools is not None:
        payload["tools"] = tools
    if include_set:
        payload["include"] = list(include_set)
    if isinstance(prev_id, str) and prev_id.strip():
        payload["previous_response_id"] = prev_id.strip()
    if not model.lower().startswith("gpt-5") and isinstance(temperature, (int, float)):
        payload["temperature"] = float(temperature)
    if isinstance(max_output_tokens, (int, float)):
        payload["max_output_tokens"] = int(max_output_tokens)
    if reasoning is not None:
        payload["reasoning"] = reasoning

    return payload


@router.post("/responses")
async def responses_complete_route(request: Request):
    _check_auth(request)
    payload: Dict[str, Any] = await request.json()
    try:
        normalized = _build_responses_payload(payload or {})
        data = await openai_client.responses_complete(normalized)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except HTTPException:
        raise
    return JSONResponse(content=data)


@router.post("/responses/stream")
async def responses_stream_route(request: Request):
    _check_auth(request)
    payload: Dict[str, Any] = await request.json()
    # logger = _responses_logger()
    # request_id = uuid4().hex[:8]

    try:
        normalized = _build_responses_payload(payload or {})
    except HTTPException:
        raise

    async def event_gen():
        try:
            async for chunk in openai_client.responses_stream(normalized):
                # logger.info("[%s] %s", request_id, chunk)
                yield chunk + "\n"  # newline delimited
        except Exception as exc:
            # logger.exception("responses_stream_route error [%s]: %s", request_id, exc)
            raise

    return StreamingResponse(event_gen(), media_type="text/event-stream")
