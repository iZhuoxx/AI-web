"""Routes for working with notebooks, notes, and folders."""

from __future__ import annotations

import uuid
from typing import List, Sequence

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from api.dependencies import get_current_user, require_csrf
from api.db.database import get_db
from api.db import models
from api.services import openai_client
from api.schemas import (
    AttachmentOut,
    NotebookCreate,
    NotebookFolderRef,
    NotebookOut,
    NotebookUpdate,
    NoteOut,
)


router = APIRouter(prefix="/notebooks", tags=["notebooks"])


class TitleGenerateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=12000)


class TitleGenerateResponse(BaseModel):
    title: str


def _notebook_query(user_id: uuid.UUID) -> Select[tuple[models.Notebook]]:
    return (
        select(models.Notebook)
        .where(models.Notebook.user_id == user_id)
        .options(
            selectinload(models.Notebook.notes),
            selectinload(models.Notebook.attachments),
            selectinload(models.Notebook.folders),
        )
        .order_by(models.Notebook.updated_at.desc())
    )


def _note_to_schema(note: models.Note) -> NoteOut:
    return NoteOut(id=note.id, title=note.title, content=note.content, seq=note.seq)


def _attachment_to_schema(attachment: models.Attachment) -> AttachmentOut:
    return AttachmentOut(
        id=attachment.id,
        filename=attachment.filename,
        mime=attachment.mime,
        bytes=attachment.bytes,
        sha256=attachment.sha256,
        s3_object_key=attachment.s3_object_key,
        s3_url=attachment.s3_url,
        external_url=attachment.external_url,
        openai_file_id=attachment.openai_file_id,
        openai_file_purpose=attachment.openai_file_purpose,
        enable_file_search=attachment.enable_file_search,
        summary=attachment.summary,
        meta=attachment.meta,
        transcription_status=attachment.transcription_status.value,
        transcription_lang=attachment.transcription_lang,
        transcription_duration_sec=attachment.transcription_duration_sec,
        created_at=attachment.created_at,
        updated_at=attachment.updated_at,
    )


def _folder_to_schema(folder: models.NotebookFolder) -> NotebookFolderRef:
    return NotebookFolderRef(
        id=folder.id,
        name=folder.name,
        description=folder.description,
        color=folder.color,
    )


def _notebook_to_schema(notebook: models.Notebook) -> NotebookOut:
    return NotebookOut(
        id=notebook.id,
        title=notebook.title,
        summary=notebook.summary,
        is_archived=notebook.is_archived,
        color=notebook.color,
        openai_vector_store_id=notebook.openai_vector_store_id,
        vector_store_expires_at=notebook.vector_store_expires_at,
        notes=[_note_to_schema(n) for n in sorted(notebook.notes, key=lambda n: n.seq)],
        attachments=[_attachment_to_schema(a) for a in notebook.attachments],
        folders=[_folder_to_schema(folder) for folder in notebook.folders],
        created_at=notebook.created_at,
        updated_at=notebook.updated_at,
    )


def _load_folders(db: Session, user: models.User, folder_ids: Sequence[uuid.UUID]) -> List[models.NotebookFolder]:
    if not folder_ids:
        return []

    unique_ids = list(dict.fromkeys(folder_ids))
    folders = (
        db.execute(
            select(models.NotebookFolder).where(
                models.NotebookFolder.user_id == user.id,
                models.NotebookFolder.id.in_(unique_ids),
            )
        )
        .scalars()
        .all()
    )
    found_ids = {folder.id for folder in folders}
    missing = [str(folder_id) for folder_id in unique_ids if folder_id not in found_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Notebook folder not found for ids: {', '.join(missing)}",
        )
    return folders


@router.get("", response_model=List[NotebookOut])
def list_notebooks(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> List[NotebookOut]:
    notebooks = db.execute(_notebook_query(user.id)).scalars().unique().all()
    return [_notebook_to_schema(notebook) for notebook in notebooks]


@router.post("", response_model=NotebookOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
def create_notebook(payload: NotebookCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> NotebookOut:
    notebook = models.Notebook(
        user_id=user.id,
        title=payload.title,
        summary=payload.summary,
        is_archived=payload.is_archived or False,
        color=payload.color,
        openai_vector_store_id=payload.openai_vector_store_id,
        vector_store_expires_at=payload.vector_store_expires_at,
    )

    for note_payload in payload.notes:
        notebook.notes.append(
            models.Note(
                id=note_payload.id,
                title=note_payload.title,
                content=note_payload.content,
                seq=note_payload.seq,
            )
        )

    notebook.folders = _load_folders(db, user, payload.folder_ids)

    db.add(notebook)
    db.commit()
    db.refresh(notebook)

    return _notebook_to_schema(notebook)


def _get_notebook_for_user(notebook_id: uuid.UUID, user: models.User, db: Session) -> models.Notebook:
    notebook = (
        db.execute(_notebook_query(user.id).where(models.Notebook.id == notebook_id))
        .scalars()
        .unique()
        .one_or_none()
    )
    if notebook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    return notebook


@router.get("/{notebook_id}", response_model=NotebookOut)
def get_notebook(
    notebook_id: uuid.UUID, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
) -> NotebookOut:
    notebook = _get_notebook_for_user(notebook_id, user, db)
    return _notebook_to_schema(notebook)


@router.put("/{notebook_id}", response_model=NotebookOut, dependencies=[Depends(require_csrf)])
def update_notebook(
    notebook_id: uuid.UUID, payload: NotebookUpdate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
) -> NotebookOut:
    notebook = _get_notebook_for_user(notebook_id, user, db)

    notebook.title = payload.title
    notebook.summary = payload.summary
    if payload.is_archived is not None:
        notebook.is_archived = payload.is_archived
    notebook.color = payload.color
    notebook.openai_vector_store_id = payload.openai_vector_store_id
    notebook.vector_store_expires_at = payload.vector_store_expires_at

    if payload.notes is not None:
        existing_notes = {str(note.id): note for note in notebook.notes}
        updated_notes: list[models.Note] = []
        incoming_ids: set[str] = set()

        for idx, note_payload in enumerate(payload.notes):
            payload_id = str(note_payload.id) if note_payload.id is not None else None
            if payload_id:
                incoming_ids.add(payload_id)
            if payload_id and payload_id in existing_notes:
                note = existing_notes[payload_id]
                note.title = note_payload.title
                note.content = note_payload.content
            else:
                note = models.Note(
                    id=note_payload.id,
                    title=note_payload.title,
                    content=note_payload.content,
                    seq=idx,
                )
            updated_notes.append(note)

        # 两阶段重排，先把现存的所有笔记（包括将被删除的）移到临时 seq，再写入最终 seq
        temp_offset = 1_000_000
        for i, note in enumerate(notebook.notes):
            note.seq = temp_offset + i
        db.flush()

        for i, note in enumerate(updated_notes):
            note.seq = i

        notebook.notes[:] = sorted(updated_notes, key=lambda n: n.seq)

    if payload.folder_ids is not None:
        notebook.folders = _load_folders(db, user, payload.folder_ids)

    db.add(notebook)
    db.commit()
    db.refresh(notebook)

    return _notebook_to_schema(notebook)


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
def delete_notebook(
    notebook_id: uuid.UUID, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    notebook = _get_notebook_for_user(notebook_id, user, db)
    db.delete(notebook)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/title",
    response_model=TitleGenerateResponse,
    dependencies=[Depends(require_csrf)],
)
async def generate_note_title(
    payload: TitleGenerateRequest,
    user: models.User = Depends(get_current_user),
) -> TitleGenerateResponse:
    # 用户鉴权由依赖处理，这里只需确认内容有效
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="内容不能为空")

    system_prompt = (
        "你是一名笔记标题助手。请为给定内容生成一个简短且清晰的标题，"
        "总长度不超过15个字符（中英文均按单字符计数），能够准确概括核心含义。"
        "标题不要使用引号、句号或多余的标点，并保持与内容语言一致。"
    )

    # Responses API 需要使用 input_text 而不是 text
    messages = [
        {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
        {"role": "user", "content": [{"type": "input_text", "text": content}]},
    ]

    try:
        data = await openai_client.responses_complete(
            model="gpt-4.1-nano",
            input=messages,
            max_output_tokens=80,
            temperature=0.3,
            timeout=20.0,
        )
    except Exception as exc:  # pragma: no cover - 网络异常兜底
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"请求标题生成失败：{exc}")

    def _extract_text(payload: dict) -> str:
        """Try to pull the first text reply from Responses or ChatCompletions style payloads."""
        if not isinstance(payload, dict):
            return ""

        output = payload.get("output") or []
        if isinstance(output, list) and output:
            first = output[0]
            if isinstance(first, dict):
                content_list = first.get("content") or []
                for item in content_list:
                    if isinstance(item, dict):
                        text_val = item.get("text")
                        if isinstance(text_val, str):
                            return text_val

        choices = payload.get("choices") or []
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message") or {}
            if isinstance(message, dict):
                content_text = message.get("content")
                if isinstance(content_text, str):
                    return content_text
        return ""

    raw_title = _extract_text(data)

    title = (raw_title or "").strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="生成标题失败：模型未返回结果")

    # 确保长度限制，避免过长标题
    if len(title) > 15:
        title = title[:15]

    return TitleGenerateResponse(title=title)
