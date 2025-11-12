# api/services/openai_client.py
import httpx
from typing import AsyncIterator, Dict, Any, Optional
from contextlib import asynccontextmanager
import json
from api.services.utils import get_headers, get_proxy
from api.settings import settings

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_COMP_URL = "https://api.openai.com/v1/completions"
OPENAI_CHAT_COMP_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_AUDIO_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_REALTIME_TRANSCRIBE_URL = "wss://api.openai.com/v1/realtime?intent=transcription"
# OPENAI_REALTIME_TRANSCRIBE_URL = "wss://api.openai.com/v1/realtime?model=gpt-realtime"




@asynccontextmanager
async def create_client(timeout: float = 60.0):
    proxy = get_proxy()
    kwargs: Dict[str, Any] = {"timeout": timeout}
    try:
        client = httpx.AsyncClient(proxy=proxy, **kwargs) if proxy else httpx.AsyncClient(**kwargs)
    except TypeError:
        proxies = {"http://": proxy, "https://": proxy} if proxy else None
        client = httpx.AsyncClient(proxies=proxies, **kwargs)
    try:
        yield client
    finally:
        await client.aclose()


# --- Responses API ---

async def responses_stream(payload: Dict[str, Any]) -> AsyncIterator[str]:
    # data = normalize_responses_payload(payload)
    data = payload
    print("DEBUG final payload (stream):", data)  
    async with create_client() as client:
        async with client.stream(
            "POST",
            OPENAI_RESPONSES_URL,
            json={**data, "stream": True},
            headers=get_headers(),
        ) as r:
            if r.status_code >= 400:
                body = await r.aread()
                print("[OpenAI error stream]", r.status_code, body.decode(errors="ignore"))
                r.raise_for_status()

            async for line in r.aiter_lines():
                if line:
                    yield line


async def transcribe_audio(
    *,
    filename: str,
    content: bytes,
    content_type: Optional[str],
    model: str,
    response_format: str = "text",
    include: Optional[list[str]] = None,
    timestamp_granularities: Optional[list[str]] = None,
    language: Optional[str] = None,
    temperature: Optional[float] = None,
    prompt: Optional[str] = None,
    timeout: float = 120.0,
) -> Dict[str, Any]:
    headers = get_headers()
    headers.pop("Content-Type", None)
    files = {
        "file": (
            filename,
            content,
            content_type or "application/octet-stream",
        )
    }
    data: Dict[str, Any] = {"model": model}
    if response_format:
        data["response_format"] = response_format
    if language:
        data["language"] = language
    if temperature is not None:
        data["temperature"] = temperature
    if prompt:
        data["prompt"] = prompt
    if include:
        filtered_include = [item for item in include if item]
        if filtered_include:
            data["include[]"] = filtered_include
    if timestamp_granularities:
        filtered_granularity = [item for item in timestamp_granularities if item]
        if filtered_granularity:
            data["timestamp_granularities[]"] = filtered_granularity

    async with create_client(timeout=timeout) as client:
        response = await client.post(
            OPENAI_AUDIO_TRANSCRIPTIONS_URL,
            data=data,
            files=files,
            headers=headers,
        )
        body_bytes = await response.aread()
    if response.status_code >= 400:
        body_text = body_bytes.decode(errors="ignore")
        raise RuntimeError(
            f"OpenAI audio transcription failed (HTTP {response.status_code}): {body_text}"
        )
    content_type_header = response.headers.get("content-type", "")
    parsed_json: Optional[Dict[str, Any]] = None
    text_result: Optional[str] = None
    if "application/json" in content_type_header:
        try:
            parsed_json = json.loads(body_bytes.decode("utf-8"))
            text_candidate = parsed_json.get("text")
            if isinstance(text_candidate, str):
                text_result = text_candidate
        except (ValueError, TypeError):
            parsed_json = None
    if text_result is None:
        text_result = body_bytes.decode("utf-8", errors="ignore").strip()
    return {
        "text": text_result,
        "model": model,
        "response_format": response_format,
        "language": language,
        "temperature": temperature,
        "prompt": prompt,
        "raw": parsed_json,
    }


async def stream_audio_transcription(
    *,
    filename: str,
    content: bytes,
    content_type: Optional[str],
    model: str,
    response_format: str = "text",
    include: Optional[list[str]] = None,
    timestamp_granularities: Optional[list[str]] = None,
    language: Optional[str] = None,
    temperature: Optional[float] = None,
    prompt: Optional[str] = None,
    timeout: float = 120.0,
) -> AsyncIterator[str]:
    headers = get_headers()
    headers.pop("Content-Type", None)
    files = {
        "file": (
            filename,
            content,
            content_type or "application/octet-stream",
        )
    }
    data: Dict[str, Any] = {"model": model, "stream": "true"}
    if response_format:
        data["response_format"] = response_format
    if language:
        data["language"] = language
    if temperature is not None:
        data["temperature"] = temperature
    if prompt:
        data["prompt"] = prompt
    if include:
        filtered_include = [item for item in include if item]
        if filtered_include:
            data["include[]"] = filtered_include
    if timestamp_granularities:
        filtered_granularity = [item for item in timestamp_granularities if item]
        if filtered_granularity:
            data["timestamp_granularities[]"] = filtered_granularity

    async with create_client(timeout=timeout) as client:
        async with client.stream(
            "POST",
            OPENAI_AUDIO_TRANSCRIPTIONS_URL,
            data=data,
            files=files,
            headers=headers,
        ) as response:
            if response.status_code >= 400:
                body = await response.aread()
                body_text = body.decode(errors="ignore")
                raise RuntimeError(
                    f"OpenAI audio transcription stream failed (HTTP {response.status_code}): {body_text}"
                )
            async for chunk in response.aiter_lines():
                if chunk:
                    yield chunk
