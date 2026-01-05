from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Form, Query
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, Any
from api.settings import settings
from api.services import openai_client
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


@router.post("/")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    purpose: str = Form("assistants"),
    expires_after_anchor: str | None = Form(default=None, alias="expires_after[anchor]"),
    expires_after_seconds: int | None = Form(default=None, alias="expires_after[seconds]"),
):
    """Upload a file to OpenAI Files API for the given purpose (assistants, user_data, etc.)."""
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

    # 1) Validate content type and payload size.
    filename = file.filename or "unnamed.txt"
    ctype = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(status_code=413, detail=f"File too large: {size_mb:.2f}MB > {MAX_FILE_MB}MB")
    if not content:
        raise HTTPException(status_code=422, detail="File contains no data")

    try:
        payload = await openai_client.upload_file_to_openai(
            filename=filename,
            content=content,
            mime=ctype,
            purpose=normalized_purpose,
            extra_form=extra_form or None,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    _validate_file_id(payload.get("id"))
    return JSONResponse(payload)


@router.get("")
async def list_files(
    request: Request,
    after: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=10_000),
    order: str | None = Query(default=None),
    purpose: str | None = Query(default=None),
):
    """List files in the authenticated OpenAI account with optional paging/filters."""
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
    try:
        content = await openai_client.list_files(**params)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content=content)


@router.get("/{file_id}")
async def get_file_metadata(request: Request, file_id: str):
    """Fetch metadata for a specific OpenAI file id."""
    _check_auth(request)
    try:
        data = await openai_client.retrieve_file(file_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content=data)


@router.delete("/{file_id}")
async def delete_file(request: Request, file_id: str):
    """Delete an OpenAI file by id."""
    _check_auth(request)
    try:
        data = await openai_client.delete_file_async(file_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content=data)


@router.get("/{file_id}/content")
async def get_file_content(request: Request, file_id: str):
    """Stream the raw bytes of an OpenAI file."""
    _check_auth(request)
    try:
        iterator, media_type = await openai_client.stream_file_content(file_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StreamingResponse(
        iterator,
        media_type=media_type,
    )
