from typing import Optional, Dict, Any, AsyncIterator
import asyncio
import json
import math
import mimetypes
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from api.settings import settings
from api.services import openai_client
import websockets
from starlette.websockets import WebSocketState

router = APIRouter(prefix="/audio", tags=["audio"])

# --- Default Settings ---
DEFAULT_AUDIO_MODEL = "gpt-4o-transcribe"
DEFAULT_RESPONSE_FORMAT = "json"
MAX_AUDIO_MB = 250


# --- Auth Helpers ---
def _sanitize_response_format(model: str, requested: Optional[str]) -> str:
    desired = (requested or "").strip() or DEFAULT_RESPONSE_FORMAT
    lowered = model.lower()
    if desired == "verbose_json" and "-api-" in lowered:
        return "json"
    return desired


def _check_auth(request: Request) -> None:
    if settings.INTERNAL_TOKEN and request.headers.get("X-API-KEY") != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _ensure_ws_auth(websocket: WebSocket) -> None:
    if not settings.INTERNAL_TOKEN:
        return
    token = websocket.headers.get("x-api-key") or websocket.query_params.get("token")
    if token != settings.INTERNAL_TOKEN:
        await websocket.close(code=1008, reason="Unauthorized")
        raise WebSocketDisconnect(code=1008)


# --- Confidence Computation ---
def _normalize_confidence(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric):
        return None
    return max(0.0, min(1.0, numeric))


def _compute_segment_confidence(segment: Dict[str, Any]) -> Optional[float]:
    """计算单个分段置信度"""
    primary = _normalize_confidence(segment.get("confidence"))
    if primary is not None:
        return primary

    words = segment.get("words")
    if isinstance(words, list) and words:
        word_confidences: list[float] = []
        for word in words:
            if not isinstance(word, dict):
                continue
            candidate = (
                _normalize_confidence(word.get("confidence"))
                or _normalize_confidence(word.get("probability"))
            )
            if candidate is not None:
                word_confidences.append(candidate)
        if word_confidences:
            return max(0.0, min(1.0, sum(word_confidences) / len(word_confidences)))

    avg_logprob = segment.get("avg_logprob")
    if isinstance(avg_logprob, (int, float)):
        try:
            return _normalize_confidence(math.exp(float(avg_logprob)))
        except OverflowError:
            return None
    no_speech_prob = segment.get("no_speech_prob")
    if isinstance(no_speech_prob, (int, float)):
        return _normalize_confidence(1.0 - float(no_speech_prob))
    return None


def _filter_confident_segments(
    raw: Optional[Dict[str, Any]],
    threshold: Optional[float],
    missing_default: float = 0.5,
) -> Optional[Dict[str, Any]]:
    """过滤低置信度文本段"""
    if not isinstance(raw, dict):
        return None
    segments = raw.get("segments")
    if not isinstance(segments, list):
        return None

    accepted: list[str] = []
    confidences: list[float] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        text = segment.get("text")
        if not isinstance(text, str):
            continue
        cleaned_text = text.strip()
        if not cleaned_text:
            continue
        confidence = _compute_segment_confidence(segment)
        effective_conf = confidence if confidence is not None else missing_default
        if threshold is not None and effective_conf < threshold:
            continue
        accepted.append(cleaned_text)
        confidences.append(effective_conf)

    if not accepted:
        return None

    combined_text = " ".join(accepted).strip()
    avg_conf = sum(confidences) / len(confidences) if confidences else None
    return {"text": combined_text, "confidence": avg_conf}


# --- Utility Converters ---
def _maybe_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _maybe_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


# --- Audio Handling ---
async def _prepare_audio_upload(file: UploadFile) -> tuple[str, bytes, str]:
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

    guessed_type, _ = mimetypes.guess_type(filename)
    content_type = file.content_type or guessed_type or "application/octet-stream"
    return filename, contents, content_type


# --- Core Endpoint: Audio Transcription ---
@router.post("/transcriptions")
async def create_transcription(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form(DEFAULT_AUDIO_MODEL),
    response_format: str = Form(DEFAULT_RESPONSE_FORMAT),
    language: Optional[str] = Form(None),
    temperature: Optional[float] = Form(None),
    prompt: Optional[str] = Form(None),
    min_confidence: Optional[float] = Form(None),
):
    """上传音频并按置信度过滤文字"""
    _check_auth(request)
    filename, contents, content_type = await _prepare_audio_upload(file)

    clean_model = (model or "").strip() or DEFAULT_AUDIO_MODEL
    clean_response_format = _sanitize_response_format(clean_model, response_format)

    try:
        result = await openai_client.transcribe_audio(
            filename=filename,
            content=contents,
            content_type=content_type,
            model=clean_model,
            response_format=clean_response_format,
            include=["logprobs"],
            timestamp_granularities=["word", "segment"],
            language=language.strip() if language else None,
            temperature=temperature,
            prompt=prompt.strip() if prompt else None,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # --- 置信度过滤 ---
    confidence_threshold = None
    if isinstance(min_confidence, (int, float)):
        confidence_threshold = max(0.0, min(1.0, float(min_confidence)))

    payload = {
        "text": result.get("text", ""),
        "model": result.get("model", clean_model),
        "response_format": result.get("response_format", clean_response_format),
    }

    raw = result.get("raw")
    filtered = _filter_confident_segments(raw, confidence_threshold)
    if filtered and filtered.get("text"):
        payload["text"] = filtered["text"]
        payload["confidence"] = filtered.get("confidence")

    # 附带额外信息
    if isinstance(raw, dict):
        if isinstance(raw.get("duration"), (int, float)):
            payload["duration"] = raw["duration"]
        if isinstance(raw.get("language"), str):
            payload.setdefault("language", raw["language"])
        if "segments" in raw and "confidence" not in payload:
            stats = _filter_confident_segments(raw, None)
            if stats and stats.get("confidence") is not None:
                payload["confidence"] = stats["confidence"]

    if language:
        payload.setdefault("language", language)

    if confidence_threshold is not None and not payload.get("text"):
        raise HTTPException(status_code=422, detail="Transcription confidence below threshold")

    return JSONResponse(payload)


# --- Streaming (SSE) Transcription ---
@router.post("/transcriptions/stream")
async def stream_transcriptions(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form(DEFAULT_AUDIO_MODEL),
    response_format: str = Form(DEFAULT_RESPONSE_FORMAT),
    language: Optional[str] = Form(None),
    temperature: Optional[float] = Form(None),
    prompt: Optional[str] = Form(None),
):
    _check_auth(request)
    filename, contents, content_type = await _prepare_audio_upload(file)

    clean_model = (model or "").strip() or DEFAULT_AUDIO_MODEL
    clean_response_format = _sanitize_response_format(clean_model, response_format)

    async def event_gen() -> AsyncIterator[str]:
        try:
            async for chunk in openai_client.stream_audio_transcription(
                filename=filename,
                content=contents,
                content_type=content_type,
                model=clean_model,
                response_format=clean_response_format,
                include=["logprobs"],
                timestamp_granularities=["word", "segment"],
                language=language,
                temperature=temperature,
                prompt=prompt,
            ):
                yield f"{chunk}\n"
            yield "data: [DONE]\n\n"
        except RuntimeError as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# --- Realtime WebSocket Transcription ---
async def _relay_realtime_transcription(client_ws: WebSocket, openai_ws: Any) -> None:
    async def forward_client_to_openai() -> None:
        try:
            while True:
                message = await client_ws.receive()
                if message.get("type") == "websocket.disconnect":
                    await openai_ws.close()
                    break
                if message.get("text") is not None:
                    print("[CLIENT→OPENAI] TEXT:", message["text"][:300])
                    await openai_ws.send(message["text"])
                elif message.get("bytes") is not None:
                    print("[CLIENT→OPENAI] BYTES:", len(message["bytes"]))
                    await openai_ws.send(message["bytes"])
        except WebSocketDisconnect:
            await openai_ws.close()
        except Exception:
            await openai_ws.close()

    async def forward_openai_to_client() -> None:
        try:
            async for message in openai_ws:
                if client_ws.application_state != WebSocketState.CONNECTED:
                    break
                if isinstance(message, bytes):
                    try:
                        print("[OPENAI→CLIENT] BYTES:", len(message))
                        await client_ws.send_bytes(message)
                    except RuntimeError:
                        break
                else:
                    try:
                        print("[OPENAI→CLIENT] TEXT:", str(message)[:])
                        await client_ws.send_text(message)
                    except RuntimeError:
                        break
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if client_ws.application_state == WebSocketState.CONNECTED:
                try:
                    await client_ws.close()
                except RuntimeError:
                    # Ignore race where Starlette has already issued websocket.close
                    pass

    await asyncio.wait(
        [
            asyncio.create_task(forward_client_to_openai()),
            asyncio.create_task(forward_openai_to_client()),
        ],
        return_when=asyncio.FIRST_COMPLETED,
    )


@router.websocket("/transcriptions/live")
async def realtime_transcriptions(websocket: WebSocket):
    await websocket.accept()
    try:
        await _ensure_ws_auth(websocket)
    except WebSocketDisconnect:
        return

    if not settings.API_KEY:
        await websocket.send_text(json.dumps({"event": "error", "message": "Missing API key on server"}))
        await websocket.close(code=1011)
        return

    query = websocket.query_params
    model = (query.get("model") or DEFAULT_AUDIO_MODEL).strip()
    language = (query.get("language") or "").strip()
    include_logprobs = (query.get("include_logprobs") or "").lower() in {"1", "true", "yes"}
    vad_threshold = _maybe_float(query.get("vad_threshold")) or 0.5
    silence_ms = _maybe_int(query.get("silence_duration_ms")) or 500
    prefix_ms = _maybe_int(query.get("prefix_padding_ms")) or 300
    noise_reduction = (query.get("noise_reduction") or "near_field").strip()
    sample_rate = _maybe_int(query.get("sample_rate")) or 24000
    confidence_threshold = _maybe_float(query.get("min_confidence"))
    if confidence_threshold is None:
        confidence_threshold = 0.0
    confidence_threshold = max(0.0, min(1.0, confidence_threshold))

    transcription_config: Dict[str, Any] = {"model": model}
    if language:
        transcription_config["language"] = language

    include_fields: list[str] = []
    if include_logprobs:
        include_fields.append("item.input_audio_transcription.logprobs")

    noise_reduction_config: Optional[Dict[str, Any]] = None
    if noise_reduction:
        normalized_noise = noise_reduction.lower()
        if normalized_noise not in {"none", "null", "off"}:
            noise_reduction_config = {"type": normalized_noise}

    session_update: Dict[str, Any] = {
        "type": "session.update",
        "session": {
            "input_audio_format": "pcm16",
            "input_audio_transcription": transcription_config,
        },
    }
    turn_detection_config: Dict[str, Any] = {
        "type": "server_vad",
        "threshold": max(0.0, min(1.0, vad_threshold)),
        "silence_duration_ms": max(100, silence_ms),
        "prefix_padding_ms": max(0, prefix_ms),
    }
    session_update["session"]["turn_detection"] = turn_detection_config
    if noise_reduction_config is not None:
        session_update["session"]["input_audio_noise_reduction"] = noise_reduction_config
    if include_fields:
        session_update["session"]["include"] = include_fields

    
    headers = [
        ("Authorization", f"Bearer {settings.API_KEY}"),
        ("OpenAI-Beta", "realtime=v1"),
    ]


    try:
        async with websockets.connect(
            openai_client.OPENAI_REALTIME_TRANSCRIBE_URL,
            extra_headers=headers,
            max_size=None,
        ) as openai_ws:
            await openai_ws.send(json.dumps(session_update))
            await websocket.send_text(
                json.dumps(
                    {
                        "event": "session_started",
                        "model": model,
                        "sample_rate": sample_rate,
                        "min_confidence": confidence_threshold,
                    }
                )
            )
            await _relay_realtime_transcription(websocket, openai_ws)
    except websockets.exceptions.InvalidStatusCode as exc:
        await websocket.send_text(json.dumps({"event": "error", "message": f"HTTP {exc.status_code}"}))
        await websocket.close(code=1011)
    except Exception as exc:
        await websocket.send_text(json.dumps({"event": "error", "message": str(exc)}))
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close(code=1011)
