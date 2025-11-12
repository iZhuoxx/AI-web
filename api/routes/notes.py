"""Routes for working with notebooks, notes, and tags."""

from __future__ import annotations

import uuid
from typing import Iterable, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from api.dependencies import get_current_user, require_csrf
from api.db.database import get_db
from api.db import models
from api.schemas import NoteCreate, NoteOut, NotebookCreate, NotebookOut, NotebookUpdate


router = APIRouter(prefix="/notes", tags=["notes"])


def _notebook_query(user_id: uuid.UUID) -> Select[tuple[models.Notebook]]:
    return (
        select(models.Notebook)
        .where(models.Notebook.user_id == user_id)
        .options(
            selectinload(models.Notebook.notes),
            selectinload(models.Notebook.attachments),
            selectinload(models.Notebook.tags),
        )
        .order_by(models.Notebook.updated_at.desc())
    )


def _note_to_schema(note: models.Note) -> NoteOut:
    return NoteOut(id=note.id, title=note.title, content=note.content, seq=note.seq)


def _notebook_to_schema(notebook: models.Notebook) -> NotebookOut:
    return NotebookOut(
        id=notebook.id,
        title=notebook.title,
        summary=notebook.summary,
        is_archived=notebook.is_archived,
        tags=[tag.name for tag in notebook.tags],
        notes=[_note_to_schema(n) for n in sorted(notebook.notes, key=lambda n: n.seq)],
        attachments=[
            # Use dict unpack to satisfy schema conversion
            {
                "id": str(a.id),
                "kind": a.kind.value,
                "object_key": a.object_key,
                "mime": a.mime,
                "bytes": a.bytes,
                "sha256": a.sha256,
                "meta": a.meta,
                "created_at": a.created_at,
            }
            for a in notebook.attachments
        ],
        created_at=notebook.created_at,
        updated_at=notebook.updated_at,
    )


def _sync_tags(db: Session, user: models.User, tag_names: Iterable[str]) -> List[models.Tag]:
    names = [name.strip() for name in tag_names if name and name.strip()]
    if not names:
        return []

    existing = (
        db.execute(
            select(models.Tag).where(models.Tag.user_id == user.id, models.Tag.name.in_(names))
        )
        .scalars()
        .all()
    )
    existing_map = {tag.name: tag for tag in existing}

    tags: List[models.Tag] = []
    for name in names:
        tag = existing_map.get(name)
        if tag is None:
            tag = models.Tag(user_id=user.id, name=name)
            db.add(tag)
        tags.append(tag)
    return tags


@router.get("", response_model=List[NotebookOut])
def list_notes(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> List[NotebookOut]:
    notebooks = db.execute(_notebook_query(user.id)).scalars().unique().all()
    return [_notebook_to_schema(notebook) for notebook in notebooks]


@router.post("", response_model=NotebookOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
def create_note(payload: NotebookCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> NotebookOut:
    notebook = models.Notebook(
        user_id=user.id,
        title=payload.title,
        summary=payload.summary,
        is_archived=payload.is_archived or False,
    )

    for note_payload in payload.notes:
        notebook.notes.append(
            models.Note(title=note_payload.title, content=note_payload.content, seq=note_payload.seq)
        )

    notebook.tags = _sync_tags(db, user, payload.tags)

    db.add(notebook)
    db.commit()
    db.refresh(notebook)

    return _notebook_to_schema(notebook)


def _get_notebook_for_user(notebook_id: uuid.UUID, user: models.User, db: Session) -> models.Notebook:
    note = (
        db.execute(_notebook_query(user.id).where(models.Notebook.id == notebook_id))
        .scalars()
        .unique()
        .one_or_none()
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    return note


@router.get("/{note_id}", response_model=NotebookOut)
def get_note(note_id: uuid.UUID, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> NotebookOut:
    notebook = _get_notebook_for_user(note_id, user, db)
    return _notebook_to_schema(notebook)


@router.put("/{note_id}", response_model=NotebookOut, dependencies=[Depends(require_csrf)])
def update_note(note_id: uuid.UUID, payload: NotebookUpdate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> NotebookOut:
    notebook = _get_notebook_for_user(note_id, user, db)

    notebook.title = payload.title
    notebook.summary = payload.summary
    if payload.is_archived is not None:
        notebook.is_archived = payload.is_archived

    # Replace notes to keep sequence consistent
    notebook.notes.clear()
    for note_payload in payload.notes:
        notebook.notes.append(
            models.Note(title=note_payload.title, content=note_payload.content, seq=note_payload.seq)
        )

    notebook.tags = _sync_tags(db, user, payload.tags)

    db.add(notebook)
    db.commit()
    db.refresh(notebook)

    return _notebook_to_schema(notebook)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
def delete_note(note_id: uuid.UUID, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    notebook = _get_notebook_for_user(note_id, user, db)
    db.delete(notebook)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
