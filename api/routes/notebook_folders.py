"""Routes for notebook folder management."""

from __future__ import annotations

import uuid
from typing import Iterable, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.dependencies import get_current_user, require_csrf
from api.db import models
from api.db.database import get_db
from api.schemas import NotebookFolderCreate, NotebookFolderOut, NotebookFolderUpdate


router = APIRouter(prefix="/notebook-folders", tags=["notebook-folders"])


def _folder_to_schema(folder: models.NotebookFolder) -> NotebookFolderOut:
    return NotebookFolderOut(
        id=folder.id,
        name=folder.name,
        description=folder.description,
        color=folder.color,
        notebook_ids=[notebook.id for notebook in folder.notebooks],
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


def _get_folder(folder_id: uuid.UUID, user: models.User, db: Session) -> models.NotebookFolder:
    folder = db.get(models.NotebookFolder, folder_id)
    if not folder or folder.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook folder not found")
    return folder


def _get_notebooks(db: Session, user: models.User, notebook_ids: Iterable[uuid.UUID]) -> List[models.Notebook]:
    ids = list(dict.fromkeys(notebook_ids))
    if not ids:
        return []
    notebooks = (
        db.execute(
            select(models.Notebook).where(
                models.Notebook.user_id == user.id,
                models.Notebook.id.in_(ids),
            )
        )
        .scalars()
        .all()
    )
    found = {notebook.id for notebook in notebooks}
    missing = [str(notebook_id) for notebook_id in ids if notebook_id not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Notebooks not found or not owned: {', '.join(missing)}",
        )
    return notebooks


@router.get("", response_model=List[NotebookFolderOut])
def list_notebook_folders(
    notebook_id: uuid.UUID | None = Query(default=None),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[NotebookFolderOut]:
    """List notebook folders; optionally filter to those containing a specific notebook."""
    query = (
        select(models.NotebookFolder)
        .where(models.NotebookFolder.user_id == user.id)
        .options(selectinload(models.NotebookFolder.notebooks))
        .order_by(models.NotebookFolder.created_at.desc())
    )
    if notebook_id is not None:
        query = query.join(models.NotebookFolder.notebooks).where(models.Notebook.id == notebook_id)

    folders = db.execute(query).scalars().unique().all()
    return [_folder_to_schema(folder) for folder in folders]


@router.post(
    "",
    response_model=NotebookFolderOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_notebook_folder(
    payload: NotebookFolderCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotebookFolderOut:
    """Create a notebook folder and attach notebooks to it."""
    folder = models.NotebookFolder(
        user_id=user.id,
        name=payload.name,
        description=payload.description,
        color=payload.color,
    )
    folder.notebooks = _get_notebooks(db, user, payload.notebook_ids)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return _folder_to_schema(folder)


@router.put(
    "/{folder_id}",
    response_model=NotebookFolderOut,
    dependencies=[Depends(require_csrf)],
)
def update_notebook_folder(
    folder_id: uuid.UUID,
    payload: NotebookFolderUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotebookFolderOut:
    """Update folder name/description/color and its notebook membership."""
    folder = _get_folder(folder_id, user, db)

    if payload.name is not None:
        folder.name = payload.name
    if payload.description is not None:
        folder.description = payload.description
    if payload.color is not None:
        folder.color = payload.color
    if payload.notebook_ids is not None:
        folder.notebooks = _get_notebooks(db, user, payload.notebook_ids)

    db.add(folder)
    db.commit()
    db.refresh(folder)
    return _folder_to_schema(folder)


@router.delete(
    "/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_notebook_folder(
    folder_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Delete a notebook folder (notebooks remain)."""
    folder = _get_folder(folder_id, user, db)
    db.delete(folder)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
