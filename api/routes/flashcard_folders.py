"""Routes for flashcard folder management."""

from __future__ import annotations

import uuid
from typing import Iterable, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.dependencies import get_current_user, require_csrf
from api.db import models
from api.db.database import get_db
from api.schemas import FlashcardFolderCreate, FlashcardFolderOut, FlashcardFolderUpdate


router = APIRouter(prefix="/flashcard-folders", tags=["flashcards"])


def _folder_to_schema(folder: models.FlashcardFolder) -> FlashcardFolderOut:
    return FlashcardFolderOut(
        id=folder.id,
        notebook_id=folder.notebook_id,
        name=folder.name,
        description=folder.description,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        flashcard_ids=[card.id for card in folder.flashcards],
    )


def _get_folder(folder_id: uuid.UUID, user: models.User, db: Session) -> models.FlashcardFolder:
    folder = (
        db.execute(
            select(models.FlashcardFolder)
            .where(models.FlashcardFolder.id == folder_id)
            .options(selectinload(models.FlashcardFolder.flashcards))
        )
        .scalars()
        .first()
    )
    if not folder or folder.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard folder not found")
    return folder


def _ensure_notebook_owned(db: Session, user: models.User, notebook_id: uuid.UUID) -> models.Notebook:
    notebook = db.get(models.Notebook, notebook_id)
    if not notebook or notebook.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    return notebook


def _get_flashcards(
    db: Session,
    user: models.User,
    notebook_id: uuid.UUID,
    flashcard_ids: Iterable[uuid.UUID],
) -> List[models.Flashcard]:
    ids = list(dict.fromkeys(flashcard_ids))
    if not ids:
        return []
    cards = (
        db.execute(
            select(models.Flashcard).where(
                models.Flashcard.user_id == user.id,
                models.Flashcard.id.in_(ids),
            )
        )
        .scalars()
        .all()
    )
    found = {card.id for card in cards}
    missing = [str(card_id) for card_id in ids if card_id not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Flashcards not found: {', '.join(missing)}",
        )
    invalid_notebook = [str(card.id) for card in cards if card.notebook_id != notebook_id]
    if invalid_notebook:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Flashcards belong to a different notebook: {', '.join(invalid_notebook)}",
        )
    return cards


@router.get("", response_model=List[FlashcardFolderOut])
def list_flashcard_folders(
    notebook_id: uuid.UUID | None = Query(default=None),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[FlashcardFolderOut]:
    """List flashcard folders for the user; optionally filter by notebook id."""
    query = (
        select(models.FlashcardFolder)
        .where(models.FlashcardFolder.user_id == user.id)
        .options(selectinload(models.FlashcardFolder.flashcards))
        .order_by(models.FlashcardFolder.created_at.desc())
    )
    if notebook_id is not None:
        query = query.where(models.FlashcardFolder.notebook_id == notebook_id)

    folders = db.execute(query).scalars().unique().all()
    return [_folder_to_schema(folder) for folder in folders]


@router.post(
    "",
    response_model=FlashcardFolderOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_flashcard_folder(
    payload: FlashcardFolderCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlashcardFolderOut:
    """Create a flashcard folder under a notebook and optionally link existing cards."""
    _ensure_notebook_owned(db, user, payload.notebook_id)
    folder = models.FlashcardFolder(
        user_id=user.id,
        notebook_id=payload.notebook_id,
        name=payload.name,
        description=payload.description,
    )
    folder.flashcards = _get_flashcards(db, user, folder.notebook_id, payload.flashcard_ids)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return _folder_to_schema(folder)


@router.put(
    "/{folder_id}",
    response_model=FlashcardFolderOut,
    dependencies=[Depends(require_csrf)],
)
def update_flashcard_folder(
    folder_id: uuid.UUID,
    payload: FlashcardFolderUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlashcardFolderOut:
    """Rename/update a flashcard folder and reset its card membership."""
    folder = _get_folder(folder_id, user, db)
    if payload.name is not None:
        folder.name = payload.name
    if payload.description is not None:
        folder.description = payload.description
    if payload.flashcard_ids is not None:
        folder.flashcards = _get_flashcards(db, user, folder.notebook_id, payload.flashcard_ids)

    db.add(folder)
    db.commit()
    db.refresh(folder)
    return _folder_to_schema(folder)


@router.delete(
    "/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_flashcard_folder(
    folder_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Delete a flashcard folder (cards remain)."""
    folder = _get_folder(folder_id, user, db)
    db.delete(folder)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
