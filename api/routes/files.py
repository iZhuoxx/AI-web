# api/routers/files.py
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Form, Query
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask
from typing import Dict, Any
from api.settings import settings
from api.services import openai_client
from api.services.utils import get_headers
import mimetypes

router = APIRouter(prefix="/files", tags=["files"])

MAX_FILE_MB = 250
ALLOWED_PURPOSES = {"assistants", "batch", "fine-tune", "vision", "user_data", "evals"}

def _check_auth(request: Request):
    if settings.INTERNAL_TOKEN and request.headers.get("X-API-KEY") != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

def _validate_file_id(file_id: str) -> None:
    if not isinstance(file_id, str) or not file_id.strip():
        raise HTTPException(status_code=500, detail="Upload ok but missing file id")


OPENAI_FILES_URL = "https://api.openai.com/v1/files"


async def _upload_to_openai(
    filename: str,
    content: bytes,
    mime: str,
    purpose: str,
    extra_form: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    files = {"file": (filename, content, mime)}
    data: Dict[str, Any] = {"purpose": purpose}
    if extra_form:
        data.update(extra_form)
    headers = get_headers()
    headers.pop("Content-Type", None)
    async with openai_client.create_client(timeout=60.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/files",
            data=data,
            files=files,
            headers=headers,
        )
        if r.status_code >= 400:
            body_bytes = await r.aread()
            body_text = body_bytes.decode(errors="ignore")
            print("[Files API error]", r.status_code, body_text)
            raise HTTPException(
                status_code=500,
                detail=f"Upload to Files API failed: HTTP {r.status_code} - {body_text}",
            )

        try:
            resp = r.json()
        except ValueError as exc:
            raise HTTPException(status_code=500, detail="Failed to parse Files API response") from exc
        file_id = resp.get("id")
        _validate_file_id(file_id)
        return resp


# Supported formats: 
# \"c\", \"cpp\", \"cs\", \"css\", \"csv\", \"doc\", \"docx\", \"gif\", \"go\", \"html\", \"java\", 
# \"jpeg\", \"jpg\", \"js\", \"json\", \"md\", \"pdf\", \"php\", \"pkl\", \"png\", \"pptx\", \"py\", 
# \"rb\", \"tar\", \"tex\", \"ts\", \"txt\", \"webp\", \"xlsx\", \"xml\", \"zip\"",

@router.post("/")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    purpose: str = Form("assistants"),
    expires_after_anchor: str | None = Form(default=None, alias="expires_after[anchor]"),
    expires_after_seconds: int | None = Form(default=None, alias="expires_after[seconds]"),
):
    _check_auth(request)

    normalized_purpose = (purpose or "").strip()
    if not normalized_purpose:
        raise HTTPException(status_code=400, detail="purpose is required")
    if normalized_purpose not in ALLOWED_PURPOSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid purpose '{normalized_purpose}'. Allowed: {', '.join(sorted(ALLOWED_PURPOSES))}",
        )

    extra_form: Dict[str, Any] = {}
    if expires_after_anchor:
        if expires_after_anchor not in {"created_at"}:
            raise HTTPException(status_code=400, detail="expires_after[anchor] must be 'created_at'")
        extra_form["expires_after[anchor]"] = expires_after_anchor
    if expires_after_seconds is not None:
        if expires_after_seconds < 3600 or expires_after_seconds > 2_592_000:
            raise HTTPException(status_code=400, detail="expires_after[seconds] must be between 3600 and 2592000")
        extra_form["expires_after[seconds]"] = str(expires_after_seconds)
        if "expires_after[anchor]" not in extra_form:
            extra_form["expires_after[anchor]"] = "created_at"

    # 1) 类型与体积校验
    filename = file.filename or "unnamed.txt"
    ctype = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(status_code=413, detail=f"File too large: {size_mb:.2f}MB > {MAX_FILE_MB}MB")
    if not content:
        raise HTTPException(status_code=422, detail="File contains no data")

    payload = await _upload_to_openai(filename, content, ctype, normalized_purpose, extra_form or None)
    return JSONResponse(payload)


async def _forward_files_request(
    method: str,
    url: str,
    *,
    params: Dict[str, Any] | None = None,
) -> JSONResponse:
    headers = get_headers()
    async with openai_client.create_client(timeout=60.0) as client:
        request_args: Dict[str, Any] = {"headers": headers}
        if params:
            request_args["params"] = params
        http_response = await client.request(method, url, **request_args)

        if http_response.status_code >= 400:
            body_bytes = await http_response.aread()
            body_text = body_bytes.decode(errors="ignore")
            raise HTTPException(
                status_code=http_response.status_code,
                detail=body_text or "OpenAI request failed",
            )

        return JSONResponse(content=http_response.json())


@router.get("")
async def list_files(
    request: Request,
    after: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=10_000),
    order: str | None = Query(default=None),
    purpose: str | None = Query(default=None),
):
    _check_auth(request)
    params: Dict[str, Any] = {}
    if after:
        params["after"] = after
    if limit is not None:
        params["limit"] = limit
    if order:
        normalized_order = order.lower()
        if normalized_order not in {"asc", "desc"}:
            raise HTTPException(status_code=400, detail="order must be 'asc' or 'desc'")
        params["order"] = normalized_order
    if purpose:
        normalized_purpose = purpose.strip()
        if normalized_purpose not in ALLOWED_PURPOSES:
            raise HTTPException(
                status_code=400,
                detail=f"purpose must be one of: {', '.join(sorted(ALLOWED_PURPOSES))}",
            )
        params["purpose"] = normalized_purpose
    return await _forward_files_request("GET", OPENAI_FILES_URL, params=params or None)


@router.get("/{file_id}")
async def get_file_metadata(request: Request, file_id: str):
    _check_auth(request)
    return await _forward_files_request("GET", f"{OPENAI_FILES_URL}/{file_id}")


@router.delete("/{file_id}")
async def delete_file(request: Request, file_id: str):
    _check_auth(request)
    return await _forward_files_request("DELETE", f"{OPENAI_FILES_URL}/{file_id}")


@router.get("/{file_id}/content")
async def get_file_content(request: Request, file_id: str):
    _check_auth(request)
    headers = get_headers()
    async with openai_client.create_client(timeout=120.0) as client:
        request_obj = client.build_request(
            "GET",
            f"{OPENAI_FILES_URL}/{file_id}/content",
            headers=headers,
        )
        resp = await client.send(request_obj, stream=True)
        if resp.status_code >= 400:
            body_text = (await resp.aread()).decode(errors="ignore")
            await resp.aclose()
            raise HTTPException(
                status_code=resp.status_code,
                detail=body_text or "Failed to fetch file content",
            )

        async def chunk_iter():
            async for chunk in resp.aiter_bytes():
                yield chunk

        media_type = resp.headers.get("content-type", "application/octet-stream")
        return StreamingResponse(
            chunk_iter(),
            media_type=media_type,
            background=BackgroundTask(resp.aclose),
        )
