"""Routes for mind map CRUD operations."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, require_csrf
from api.db import models
from api.db.database import get_db
from api.schemas import MindMapCreate, MindMapOut, MindMapUpdate


router = APIRouter(prefix="/mindmaps", tags=["mindmaps"])


def _ensure_notebook_owned(db: Session, user: models.User, notebook_id: uuid.UUID) -> models.Notebook:
    notebook = db.get(models.Notebook, notebook_id)
    if not notebook or notebook.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    return notebook


def _mindmap_to_schema(mindmap: models.MindMap) -> MindMapOut:
    return MindMapOut(
        id=mindmap.id,
        notebook_id=mindmap.notebook_id,
        title=mindmap.title,
        data=mindmap.data,
        created_at=mindmap.created_at,
        updated_at=mindmap.updated_at,
    )


def _get_mindmap(mindmap_id: uuid.UUID, user: models.User, db: Session) -> models.MindMap:
    mindmap = db.get(models.MindMap, mindmap_id)
    if not mindmap or mindmap.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mind map not found")
    return mindmap


@router.get("", response_model=List[MindMapOut])
def list_mindmaps(
    notebook_id: uuid.UUID | None = Query(default=None),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MindMapOut]:
    """List mind maps for the user; optionally filter by notebook id."""
    query = (
        select(models.MindMap)
        .where(models.MindMap.user_id == user.id)
        .order_by(models.MindMap.updated_at.desc())
    )
    if notebook_id is not None:
        query = query.where(models.MindMap.notebook_id == notebook_id)

    items = db.execute(query).scalars().all()
    return [_mindmap_to_schema(item) for item in items]


@router.get("/{mindmap_id}", response_model=MindMapOut)
def get_mindmap(
    mindmap_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MindMapOut:
    """Fetch a single mind map by id."""
    mindmap = _get_mindmap(mindmap_id, user, db)
    return _mindmap_to_schema(mindmap)


@router.post(
    "",
    response_model=MindMapOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_mindmap(
    payload: MindMapCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MindMapOut:
    """Create a mind map under a notebook."""
    _ensure_notebook_owned(db, user, payload.notebook_id)
    mindmap = models.MindMap(
        user_id=user.id,
        notebook_id=payload.notebook_id,
        title=payload.title,
        data=payload.data,
    )
    db.add(mindmap)
    db.commit()
    db.refresh(mindmap)
    return _mindmap_to_schema(mindmap)


@router.put(
    "/{mindmap_id}",
    response_model=MindMapOut,
    dependencies=[Depends(require_csrf)],
)
def update_mindmap(
    mindmap_id: uuid.UUID,
    payload: MindMapUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MindMapOut:
    """Update a mind map’s notebook, title, or data payload."""
    mindmap = _get_mindmap(mindmap_id, user, db)

    if payload.notebook_id is not None and payload.notebook_id != mindmap.notebook_id:
        _ensure_notebook_owned(db, user, payload.notebook_id)
        mindmap.notebook_id = payload.notebook_id
    if payload.title is not None:
        mindmap.title = payload.title
    if payload.data is not None:
        mindmap.data = payload.data

    db.add(mindmap)
    db.commit()
    db.refresh(mindmap)
    return _mindmap_to_schema(mindmap)


@router.delete(
    "/{mindmap_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_mindmap(
    mindmap_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Delete a mind map owned by the user."""
    mindmap = _get_mindmap(mindmap_id, user, db)
    db.delete(mindmap)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
