"""Routes for generating S3 presigned URLs and managing attachment metadata."""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, require_csrf
from api.db import models
from api.db.database import get_db
from api.schemas import PresignDownloadResponse, PresignUploadRequest, PresignUploadResponse
from api.services.s3_client import create_presigned_download, create_presigned_upload


router = APIRouter(prefix="/attachments", tags=["attachments"])


def _sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    return cleaned or "upload.bin"


def _get_notebook_owned(notebook_id: uuid.UUID, user: models.User, db: Session) -> models.Notebook:
    notebook = db.get(models.Notebook, notebook_id)
    if not notebook or notebook.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    return notebook


@router.post("/presign-upload", response_model=PresignUploadResponse, dependencies=[Depends(require_csrf)])
def presign_upload(
    payload: PresignUploadRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresignUploadResponse:
    try:
        notebook_id = uuid.UUID(payload.notebook_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notebook id") from exc

    notebook = _get_notebook_owned(notebook_id, user, db)

    try:
        kind = models.AttachmentKind(payload.kind or "file")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid attachment kind") from exc

    filename = _sanitize_filename(payload.filename)
    object_key = f"users/{user.id}/notebooks/{notebook.id}/{uuid.uuid4()}-{filename}"

    extra_fields = {}
    if payload.content_type:
        extra_fields["Content-Type"] = payload.content_type

    try:
        upload = create_presigned_upload(object_key, extra=extra_fields)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    attachment = models.Attachment(
        notebook_id=notebook.id,
        user_id=user.id,
        kind=kind,
        object_key=object_key,
        mime=payload.content_type,
        bytes=payload.bytes,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return PresignUploadResponse(
        attachment_id=str(attachment.id),
        object_key=object_key,
        upload=upload,
    )


@router.get("/{attachment_id}/download-url", response_model=PresignDownloadResponse)
def attachment_download_url(
    attachment_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresignDownloadResponse:
    attachment = db.get(models.Attachment, attachment_id)
    if not attachment or attachment.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    try:
        url = create_presigned_download(attachment.object_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return PresignDownloadResponse(url=url, expires_in=900)
