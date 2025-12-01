"""Routes for generating S3 presigned URLs and managing attachment metadata."""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, require_csrf
from api.db import models
from api.db.database import get_db
from api.schemas import (
    AttachmentLinkOpenAI,
    AttachmentUpdate,
    PresignDownloadResponse,
    PresignUploadRequest,
    PresignUploadResponse,
)
from api.services import openai_client
from api.services.s3_client import create_presigned_download, create_presigned_upload, delete_object


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

    filename = _sanitize_filename(payload.filename)
    s3_object_key = f"users/{user.id}/notebooks/{notebook.id}/{uuid.uuid4()}-{filename}"

    extra_fields = {}
    if payload.content_type:
        extra_fields["Content-Type"] = payload.content_type

    try:
        upload = create_presigned_upload(s3_object_key, extra=extra_fields)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    attachment = models.Attachment(
        notebook_id=notebook.id,
        user_id=user.id,
        filename=filename,
        mime=payload.content_type,
        bytes=payload.bytes,
        s3_object_key=s3_object_key,
        enable_file_search = True
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return PresignUploadResponse(
        attachment_id=str(attachment.id),
        s3_object_key=s3_object_key,
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

    if not attachment.s3_object_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attachment does not have an S3 object key",
        )

    try:
        url = create_presigned_download(attachment.s3_object_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return PresignDownloadResponse(url=url, expires_in=900)


@router.put(
    "/{attachment_id}",
    dependencies=[Depends(require_csrf)],
)
def update_attachment_metadata(
    attachment_id: uuid.UUID,
    payload: AttachmentUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str | None]:
    attachment = db.get(models.Attachment, attachment_id)
    if not attachment or attachment.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    if payload.filename is not None:
        attachment.filename = _sanitize_filename(payload.filename)

    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {"id": str(attachment.id), "filename": attachment.filename}


@router.post(
    "/{attachment_id}/link-openai",
    dependencies=[Depends(require_csrf)],
)
def attach_openai_file(
    attachment_id: uuid.UUID,
    payload: AttachmentLinkOpenAI,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    attachment = db.get(models.Attachment, attachment_id)
    if not attachment or attachment.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    try:
        notebook = attachment.notebook
        vector_store_id = notebook.openai_vector_store_id if notebook else None
        if not vector_store_id:
            name = f"Notebook-{notebook.id}" if notebook else None
            vector_store_id = openai_client.create_vector_store(name=name)
            if notebook:
                notebook.openai_vector_store_id = vector_store_id
                db.add(notebook)

        openai_client.add_file_to_vector_store(vector_store_id, payload.openai_file_id)

        attachment.openai_file_id = payload.openai_file_id
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
    except Exception:
        db.rollback()
        raise

    return {
        "id": str(attachment.id),
        "openai_file_id": attachment.openai_file_id,
        "openai_vector_store_id": attachment.notebook.openai_vector_store_id if attachment.notebook else None,
    }


@router.delete(
    "/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_attachment(
    attachment_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    attachment = db.get(models.Attachment, attachment_id)
    if not attachment or attachment.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    s3_key = attachment.s3_object_key
    openai_file_id = attachment.openai_file_id
    vector_store_id = attachment.notebook.openai_vector_store_id if attachment.notebook else None

    try:
        if s3_key:
            try:
                delete_object(s3_key)
            except RuntimeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete attachment object: {exc}",
                ) from exc

        if vector_store_id and openai_file_id:
            try:
                openai_client.delete_file_from_vector_store(vector_store_id, openai_file_id)
            except RuntimeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete vector store file: {exc}",
                ) from exc

        if openai_file_id:
            try:
                openai_client.delete_file(openai_file_id)
            except RuntimeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete OpenAI file: {exc}",
                ) from exc

        db.delete(attachment)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)
