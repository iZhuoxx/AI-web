# api/services/openai_client.py
import httpx
from typing import AsyncIterator, Dict, Any, Optional
from contextlib import asynccontextmanager
import json
from datetime import datetime
from pathlib import Path
from api.services.utils import get_headers, get_proxy
from api.settings import settings

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_COMP_URL = "https://api.openai.com/v1/completions"
# OPENAI_CHAT_COMP_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_AUDIO_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_REALTIME_TRANSCRIBE_URL = "wss://api.openai.com/v1/realtime?intent=transcription"
# OPENAI_REALTIME_TRANSCRIBE_URL = "wss://api.openai.com/v1/realtime?model=gpt-realtime"
OPENAI_FILES_URL = "https://api.openai.com/v1/files"
OPENAI_VECTOR_STORES_URL = "https://api.openai.com/v1/vector_stores"




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
    raw_chunks = []
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

            # try:
            async for line in r.aiter_lines():
                if line:
                    raw_chunks.append(line)
                    yield line
            # finally:
            #     if raw_chunks:
            #         aggregated = "\n".join(raw_chunks)
            #         try:
            #             print("[OpenAI stream aggregated]", aggregated)
            #         except Exception:
            #             pass
            #         try:
            #             log_dir = Path(__file__).resolve().parent / "logs"
            #             log_dir.mkdir(parents=True, exist_ok=True)
            #             log_file = log_dir / "openai_responses.log"
            #             with log_file.open("a", encoding="utf-8") as f:
            #                 timestamp = datetime.now().isoformat() + "Z"
            #                 f.write(f"\n[{timestamp}] -----\n")
            #                 f.write(aggregated)
            #                 f.write("\n")
            #         except Exception as e:
            #             try:
            #                 print("[OpenAI stream log write error]", e)
            #             except Exception:
            #                 pass


async def responses_complete(payload: Dict[str, Any], *, timeout: float = 60.0) -> Dict[str, Any]:
    """
    Call the OpenAI Responses API once and return the parsed JSON body.
    Forces non-streaming mode so callers get the full reply in one shot.
    """
    data = {**(payload or {})}
    data.pop("stream", None)
    data.setdefault("stream", False)

    async with create_client(timeout=timeout) as client:
        try:
            response = await client.post(
                OPENAI_RESPONSES_URL,
                json=data,
                headers=get_headers(),
            )
            body_bytes = await response.aread()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"OpenAI responses request failed: {exc}") from exc

    if response.status_code >= 400:
        detail = body_bytes.decode(errors="ignore").strip()
        raise RuntimeError(
            f"OpenAI responses request failed (HTTP {response.status_code}): {detail[:500]}"
        )

    try:
        return json.loads(body_bytes.decode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise RuntimeError("Failed to parse OpenAI responses payload") from exc


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
        # Log detailed error for troubleshooting
        try:
            print(
                "[OpenAI audio transcription error]",
                response.status_code,
                body_text[:2000],
            )
        except Exception:
            pass
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


def _create_sync_client(timeout: float = 60.0) -> httpx.Client:
    proxy = get_proxy()
    try:
        return httpx.Client(proxy=proxy, timeout=timeout) if proxy else httpx.Client(timeout=timeout)
    except TypeError:
        proxies = {"http://": proxy, "https://": proxy} if proxy else None
        return httpx.Client(proxies=proxies, timeout=timeout)


def delete_file(file_id: str, *, timeout: float = 30.0) -> None:
    """Delete a file from OpenAI Files API. Treats 404 as already deleted."""

    headers = get_headers()
    client = _create_sync_client(timeout=timeout)
    try:
        response = client.delete(f"{OPENAI_FILES_URL}/{file_id}", headers=headers)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Failed to delete OpenAI file '{file_id}': {exc}") from exc
    finally:
        client.close()

    if response.status_code == 404:
        return
    if response.status_code >= 400:
        detail = response.text or response.reason_phrase
        raise RuntimeError(f"Failed to delete OpenAI file '{file_id}': HTTP {response.status_code} {detail}")


def _assistants_headers(include_content_type: bool = True) -> Dict[str, str]:
    headers = get_headers()
    headers["OpenAI-Beta"] = "assistants=v2"
    if not include_content_type:
        headers.pop("Content-Type", None)
    return headers


def create_vector_store(*, name: Optional[str] = None, timeout: float = 30.0) -> str:
    """Create a vector store and return its id."""

    client = _create_sync_client(timeout=timeout)
    payload: Dict[str, Any] = {}
    if name:
        payload["name"] = name
    try:
        response = client.post(
            OPENAI_VECTOR_STORES_URL,
            headers=_assistants_headers(),
            json=payload or {},
        )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Failed to create vector store: {exc}") from exc
    finally:
        client.close()

    if response.status_code >= 400:
        detail = response.text or response.reason_phrase
        raise RuntimeError(f"Failed to create vector store: HTTP {response.status_code} {detail}")

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("Failed to parse vector store creation response") from exc

    vs_id = data.get("id")
    if not vs_id:
        raise RuntimeError("Vector store creation response missing id")
    return vs_id


def add_file_to_vector_store(vector_store_id: str, file_id: str, *, timeout: float = 30.0) -> None:
    """Attach a file to a vector store. 409 (already exists) is treated as success."""

    client = _create_sync_client(timeout=timeout)
    try:
        response = client.post(
            f"{OPENAI_VECTOR_STORES_URL}/{vector_store_id}/files",
            headers=_assistants_headers(),
            json={"file_id": file_id},
        )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Failed to attach file to vector store '{vector_store_id}': {exc}") from exc
    finally:
        client.close()

    if response.status_code in (200, 201, 202):
        return
    if response.status_code == 409:
        return
    detail = response.text or response.reason_phrase
    raise RuntimeError(
        f"Failed to attach file '{file_id}' to vector store '{vector_store_id}': HTTP {response.status_code} {detail}"
    )


def delete_file_from_vector_store(vector_store_id: str, file_id: str, *, timeout: float = 30.0) -> None:
    """Detach a file from a vector store. 404 treated as already removed."""

    client = _create_sync_client(timeout=timeout)
    try:
        response = client.delete(
            f"{OPENAI_VECTOR_STORES_URL}/{vector_store_id}/files/{file_id}",
            headers=_assistants_headers(),
        )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Failed to delete vector store file '{file_id}' from '{vector_store_id}': {exc}") from exc
    finally:
        client.close()

    if response.status_code in (200, 202):
        return
    if response.status_code == 404:
        return
    detail = response.text or response.reason_phrase
    raise RuntimeError(
        f"Failed to delete vector store file '{file_id}' from '{vector_store_id}': HTTP {response.status_code} {detail}"
    )
