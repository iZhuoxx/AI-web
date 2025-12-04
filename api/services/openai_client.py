from __future__ import annotations

import inspect
import json
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator, Dict, Iterator, Optional

import httpx
from openai import APIStatusError, AsyncOpenAI, OpenAI

from api.services.utils import get_proxy
from api.settings import settings

OPENAI_REALTIME_TRANSCRIBE_URL = "wss://api.openai.com/v1/realtime?intent=transcription"


def _ensure_api_key() -> str:
    if not settings.API_KEY:
        raise RuntimeError("Missing API_KEY. Set it in api/.env (API_KEY=sk-...)")
    return settings.API_KEY


def _async_http_client(timeout: float) -> httpx.AsyncClient:
    proxy = get_proxy()
    kwargs: Dict[str, Any] = {"timeout": timeout}
    try:
        return httpx.AsyncClient(proxies=proxy, **kwargs) if proxy else httpx.AsyncClient(**kwargs)
    except TypeError:
        proxies = {"http://": proxy, "https://": proxy} if proxy else None
        return httpx.AsyncClient(proxies=proxies, **kwargs)


def _sync_http_client(timeout: float) -> httpx.Client:
    proxy = get_proxy()
    kwargs: Dict[str, Any] = {"timeout": timeout}
    try:
        return httpx.Client(proxies=proxy, **kwargs) if proxy else httpx.Client(**kwargs)
    except TypeError:
        proxies = {"http://": proxy, "https://": proxy} if proxy else None
        return httpx.Client(proxies=proxies, **kwargs)


@asynccontextmanager
async def _async_client(timeout: float = 120.0) -> AsyncIterator[AsyncOpenAI]:
    api_key = _ensure_api_key()
    http_client = _async_http_client(timeout)
    client = AsyncOpenAI(api_key=api_key, http_client=http_client)
    try:
        yield client
    finally:
        await http_client.aclose()


@contextmanager
def _sync_client(timeout: float = 60.0) -> Iterator[OpenAI]:
    api_key = _ensure_api_key()
    http_client = _sync_http_client(timeout)
    client = OpenAI(api_key=api_key, http_client=http_client)
    try:
        yield client
    finally:
        http_client.close()


def _event_to_json(data: Any) -> str:
    if hasattr(data, "model_dump_json"):
        try:
            return data.model_dump_json(exclude_none=True)
        except Exception:
            pass
    if hasattr(data, "model_dump"):
        try:
            return json.dumps(data.model_dump())
        except Exception:
            pass
    try:
        return json.dumps(data)
    except TypeError:
        return json.dumps(str(data))


# --- Responses API ---

async def responses_stream(payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> AsyncIterator[str]:
    data = {**(payload or {}), **kwargs}
    data.pop("stream", None)

    async with _async_client() as client:
        try:
            stream = await client.responses.create(stream=True, **data)
        except Exception as exc:
            raise RuntimeError(f"OpenAI responses stream failed: {exc}") from exc

        closer = getattr(stream, "aclose", None) or getattr(stream, "close", None)
        try:
            async for event in stream:  # type: ignore[async-iterator]
                yield _event_to_json(event)
        finally:
            if callable(closer):
                result = closer()
                if inspect.isawaitable(result):
                    await result


async def responses_complete(payload: Optional[Dict[str, Any]] = None, *, timeout: float = 60.0, **kwargs: Any) -> Dict[str, Any]:
    """
    Call the OpenAI Responses API once and return the parsed JSON body.
    Forces non-streaming mode so callers get the full reply in one shot.
    """
    data = {**(payload or {}), **kwargs}
    data.pop("stream", None)
    data.setdefault("stream", False)

    async with _async_client(timeout=timeout) as client:
        try:
            response = await client.responses.create(**data)
        except Exception as exc:
            raise RuntimeError(f"OpenAI responses request failed: {exc}") from exc

    try:
        return response.model_dump()
    except Exception as exc:
        raise RuntimeError("Failed to parse OpenAI responses payload") from exc


def _audio_extra_body(
    include: Optional[list[str]],
    timestamp_granularities: Optional[list[str]],
    *,
    stream: bool = False,
) -> Dict[str, Any]:
    extra: Dict[str, Any] = {}
    if stream:
        extra["stream"] = True

    if include:
        filtered = [item for item in include if item]
        if filtered:
            extra["include[]"] = filtered

    if timestamp_granularities:
        filtered = [item for item in timestamp_granularities if item]
        if filtered:
            extra["timestamp_granularities[]"] = filtered
    return extra


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
    extra_body = _audio_extra_body(include, timestamp_granularities, stream=False) or None

    async with _async_client(timeout=timeout) as client:
        try:
            result = await client.audio.transcriptions.create(
                model=model,
                file=(filename, content, content_type or "application/octet-stream"),
                response_format=response_format,
                language=language,
                temperature=temperature,
                prompt=prompt,
                extra_body=extra_body,
            )
        except Exception as exc:
            raise RuntimeError(f"OpenAI audio transcription failed: {exc}") from exc

    raw: Dict[str, Any] | None = None
    text_result: Optional[str] = None
    try:
        raw = result.model_dump()
        text_candidate = raw.get("text")
        if isinstance(text_candidate, str):
            text_result = text_candidate
    except Exception:
        pass

    return {
        "text": text_result or "",
        "model": model,
        "response_format": response_format,
        "language": language,
        "temperature": temperature,
        "prompt": prompt,
        "raw": raw,
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
    extra_body = _audio_extra_body(include, timestamp_granularities, stream=True) or None
    http_client = _async_http_client(timeout)
    client = AsyncOpenAI(api_key=_ensure_api_key(), http_client=http_client)

    try:
        response = await client.audio.transcriptions.with_streaming_response.create(
            model=model,
            file=(filename, content, content_type or "application/octet-stream"),
            response_format=response_format,
            language=language,
            temperature=temperature,
            prompt=prompt,
            extra_body=extra_body,
        )
    except Exception as exc:
        await http_client.aclose()
        raise RuntimeError(f"OpenAI audio transcription stream failed: {exc}") from exc

    async def _iterate() -> AsyncIterator[str]:
        try:
            line_iter = getattr(response, "aiter_lines", None) or getattr(response, "iter_lines", None)
            if callable(line_iter):
                async for line in line_iter():  # type: ignore[misc]
                    if line:
                        yield line.decode() if isinstance(line, (bytes, bytearray)) else line
                return

            byte_iter = getattr(response, "aiter_bytes", None) or getattr(response, "iter_bytes", None)
            if not callable(byte_iter):
                body = await response.aread() if hasattr(response, "aread") else response.read()
                decoded = body.decode("utf-8", errors="ignore") if isinstance(body, (bytes, bytearray)) else str(body)
                if decoded:
                    yield decoded
                return

            buffer = ""
            async for chunk in byte_iter():  # type: ignore[misc]
                decoded = chunk.decode("utf-8", errors="ignore") if isinstance(chunk, (bytes, bytearray)) else str(chunk)
                buffer += decoded
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line:
                        yield line
            if buffer.strip():
                yield buffer.strip()
        finally:
            closer = getattr(response, "aclose", None) or getattr(response, "close", None)
            if callable(closer):
                res = closer()
                if inspect.isawaitable(res):
                    await res
            await http_client.aclose()

    async for chunk in _iterate():
        yield chunk


def delete_file(file_id: str, *, timeout: float = 30.0) -> None:
    """Delete a file from OpenAI Files API. Treats 404 as already deleted."""
    with _sync_client(timeout=timeout) as client:
        try:
            client.files.delete(file_id)
        except APIStatusError as exc:
            if exc.status_code == 404:
                return
            raise RuntimeError(f"Failed to delete OpenAI file '{file_id}': {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Failed to delete OpenAI file '{file_id}': {exc}") from exc


def create_vector_store(*, name: Optional[str] = None, timeout: float = 30.0) -> str:
    """Create a vector store and return its id."""
    with _sync_client(timeout=timeout) as client:
        try:
            store = client.vector_stores.create(name=name) if name else client.vector_stores.create()
        except Exception as exc:
            raise RuntimeError(f"Failed to create vector store: {exc}") from exc

    vs_id = getattr(store, "id", None)
    if not vs_id:
        try:
            vs_id = store.model_dump().get("id")  # type: ignore[arg-type]
        except Exception:
            pass
    if not vs_id:
        raise RuntimeError("Vector store creation response missing id")
    return vs_id


def add_file_to_vector_store(vector_store_id: str, file_id: str, *, timeout: float = 30.0) -> None:
    """Attach a file to a vector store. 409 (already exists) is treated as success."""
    with _sync_client(timeout=timeout) as client:
        try:
            client.vector_stores.files.create(vector_store_id=vector_store_id, file_id=file_id)
        except APIStatusError as exc:
            if exc.status_code == 409:
                return
            raise RuntimeError(
                f"Failed to attach file '{file_id}' to vector store '{vector_store_id}': {exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Failed to attach file '{file_id}' to vector store '{vector_store_id}': {exc}"
            ) from exc


def delete_file_from_vector_store(vector_store_id: str, file_id: str, *, timeout: float = 30.0) -> None:
    """Detach a file from a vector store. 404 treated as already removed."""
    with _sync_client(timeout=timeout) as client:
        try:
            client.vector_stores.files.delete(vector_store_id=vector_store_id, file_id=file_id)
        except APIStatusError as exc:
            if exc.status_code == 404:
                return
            raise RuntimeError(
                f"Failed to delete vector store file '{file_id}' from '{vector_store_id}': {exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Failed to delete vector store file '{file_id}' from '{vector_store_id}': {exc}"
            ) from exc


# --- Files API helpers for async routes ---

async def upload_file_to_openai(
    *,
    filename: str,
    content: bytes,
    mime: str,
    purpose: str,
    extra_form: Dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    async with _async_client(timeout=timeout) as client:
        try:
            file_obj = await client.files.create(
                file=(filename, content, mime),
                purpose=purpose,
                extra_body=extra_form or None,
            )
        except Exception as exc:
            raise RuntimeError(f"Upload to Files API failed: {exc}") from exc

    try:
        return file_obj.model_dump()
    except Exception as exc:
        raise RuntimeError("Failed to parse Files API response") from exc


async def list_files(
    *,
    after: str | None = None,
    limit: int | None = None,
    order: str | None = None,
    purpose: str | None = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    async with _async_client(timeout=timeout) as client:
        try:
            resp = await client.files.list(after=after, limit=limit, order=order, purpose=purpose)
        except Exception as exc:
            raise RuntimeError(f"OpenAI file listing failed: {exc}") from exc
    return resp.model_dump()


async def retrieve_file(file_id: str, *, timeout: float = 60.0) -> Dict[str, Any]:
    async with _async_client(timeout=timeout) as client:
        try:
            resp = await client.files.retrieve(file_id)
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch file '{file_id}': {exc}") from exc
    return resp.model_dump()


async def delete_file_async(file_id: str, *, timeout: float = 30.0) -> Dict[str, Any]:
    async with _async_client(timeout=timeout) as client:
        try:
            resp = await client.files.delete(file_id)
        except Exception as exc:
            raise RuntimeError(f"Failed to delete OpenAI file '{file_id}': {exc}") from exc
    return resp.model_dump()


async def stream_file_content(
    file_id: str,
    *,
    timeout: float = 120.0,
) -> tuple[AsyncIterator[bytes], str]:
    http_client = _async_http_client(timeout)
    client = AsyncOpenAI(api_key=_ensure_api_key(), http_client=http_client)
    try:
        response = await client.files.content(file_id)
    except Exception as exc:
        await http_client.aclose()
        raise RuntimeError(f"Failed to fetch file content for '{file_id}': {exc}") from exc

    content_type = "application/octet-stream"
    try:
        headers = getattr(response, "headers", None) or getattr(response, "response_headers", None)
        if headers and isinstance(headers, dict):
            content_type = headers.get("content-type", content_type)
        else:
            raw_resp = getattr(response, "response", None)
            if raw_resp and hasattr(raw_resp, "headers"):
                content_type = raw_resp.headers.get("content-type", content_type)
    except Exception:
        pass

    async def iterator() -> AsyncIterator[bytes]:
        try:
            byte_iter = getattr(response, "aiter_bytes", None) or getattr(response, "iter_bytes", None)
            if callable(byte_iter):
                async for chunk in byte_iter():  # type: ignore[misc]
                    yield chunk
            else:
                data = await response.aread() if hasattr(response, "aread") else response.read()
                if isinstance(data, (bytes, bytearray)):
                    yield bytes(data)
                elif data:
                    yield str(data).encode("utf-8")
        finally:
            closer = getattr(response, "aclose", None) or getattr(response, "close", None)
            if callable(closer):
                res = closer()
                if inspect.isawaitable(res):
                    await res
            await http_client.aclose()

    return iterator(), content_type
