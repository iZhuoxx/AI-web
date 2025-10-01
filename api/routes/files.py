# api/routers/files.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any
from api.settings import settings
from api.services import openai_client
from api.services.utils import get_headers
import mimetypes

router = APIRouter(prefix="/files", tags=["files"])

TEXTUAL_MIME_PREFIXES = (
    "text/",
)

TEXTUAL_MIME_TYPES = {
    "application/json",
    "application/xml",
    "application/x-yaml",
    "application/yaml",
    "application/javascript",
    "application/x-javascript",
    "application/typescript",
    "application/x-python",
    "application/x-python-code",
    "application/rtf",
}

PREFERRED_ENCODINGS = (
    "utf-8",
    "utf-16",
    "utf-16le",
    "utf-16be",
    "utf-32",
    "gb18030",
    "big5",
    "shift_jis",
    "iso-8859-1",
    "latin-1",
)

MAX_FILE_MB = 25
MAX_TEXT_CHARS = 120_000

def _check_auth(request: Request):
    if settings.INTERNAL_TOKEN and request.headers.get("X-API-KEY") != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

def is_textual_mime(mime: str) -> bool:
    return mime.startswith(TEXTUAL_MIME_PREFIXES) or mime in TEXTUAL_MIME_TYPES

def _decode_bytes(data: bytes) -> str:
    for enc in PREFERRED_ENCODINGS:
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    # 最后兜底使用 "utf-8" 忽略错误
    return data.decode("utf-8", errors="ignore")

def extract_text(content: bytes, mime: str, filename: str) -> str:
    if not is_textual_mime(mime):
        # 对于未知类型尝试根据扩展名判断
        ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
        text_like_exts = {"txt", "md", "markdown", "csv", "tsv", "json", "yaml", "yml", "xml", "html", "htm", "py", "js", "ts"}
        if ext in text_like_exts:
            return _decode_bytes(content)
        raise HTTPException(status_code=415, detail=f"Unsupported text format: {mime}")

    return _decode_bytes(content)

def _validate_file_id(file_id: str) -> None:
    if not isinstance(file_id, str) or not file_id.strip():
        raise HTTPException(status_code=500, detail="Upload ok but missing file id")


async def _upload_pdf(filename: str, content: bytes, mime: str) -> Dict[str, Any]:
    files = {"file": (filename, content, mime)}
    data = {"purpose": "assistants"}
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

        resp = r.json()
        file_id = resp.get("id")
        _validate_file_id(file_id)
        return {
            "file_id": file_id,
            "name": filename,
            "mime": mime,
            "purpose": "assistants",
            "size": len(content),
        }


@router.post("/")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
):
    _check_auth(request)

    # 1) 类型与体积校验
    filename = file.filename or "unnamed.txt"
    ctype = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(status_code=413, detail=f"File too large: {size_mb:.2f}MB > {MAX_FILE_MB}MB")
    if ctype == "application/pdf":
        payload = await _upload_pdf(filename, content, ctype)
        return JSONResponse(payload)

    try:
        text = extract_text(content, ctype, filename)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=415, detail=f"Failed to read file: {exc}")

    if not text.strip():
        raise HTTPException(status_code=422, detail="File contains no readable text")

    trimmed = text if len(text) <= MAX_TEXT_CHARS else text[:MAX_TEXT_CHARS]

    return JSONResponse({
        "name": filename,
        "mime": ctype,
        "size": len(content),
        "text": trimmed,
        "truncated": len(trimmed) < len(text),
    })
