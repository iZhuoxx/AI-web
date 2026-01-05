"""Routes for flashcard CRUD operations."""

from __future__ import annotations

import uuid
from typing import Iterable, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.dependencies import get_current_user, require_csrf
from api.db import models
from api.db.database import get_db
from api.schemas import FlashcardCreate, FlashcardOut, FlashcardUpdate


router = APIRouter(prefix="/flashcards", tags=["flashcards"])


def _ensure_notebook_owned(db: Session, user: models.User, notebook_id: uuid.UUID) -> models.Notebook:
    notebook = db.get(models.Notebook, notebook_id)
    if not notebook or notebook.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    return notebook


def _card_to_schema(card: models.Flashcard) -> FlashcardOut:
    return FlashcardOut(
        id=card.id,
        notebook_id=card.notebook_id,
        question=card.question,
        answer=card.answer,
        meta=card.meta,
        folder_ids=[folder.id for folder in card.folders],
    )


def _get_card(card_id: uuid.UUID, user: models.User, db: Session) -> models.Flashcard:
    card = (
        db.execute(
            select(models.Flashcard)
            .where(models.Flashcard.id == card_id)
            .options(selectinload(models.Flashcard.folders))
        )
        .scalars()
        .first()
    )
    if not card or card.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found")
    return card


def _get_folders(
    db: Session,
    user: models.User,
    notebook_id: uuid.UUID,
    folder_ids: Iterable[uuid.UUID],
) -> List[models.FlashcardFolder]:
    ids = list(dict.fromkeys(folder_ids))
    if not ids:
        return []
    folders = (
        db.execute(
            select(models.FlashcardFolder).where(
                models.FlashcardFolder.user_id == user.id,
                models.FlashcardFolder.id.in_(ids),
            )
        )
        .scalars()
        .all()
    )
    found = {folder.id for folder in folders}
    missing = [str(folder_id) for folder_id in ids if folder_id not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Flashcard folders not found: {', '.join(missing)}",
        )
    invalid = [str(folder.id) for folder in folders if folder.notebook_id != notebook_id]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Folders belong to a different notebook: {', '.join(invalid)}",
        )
    return folders


@router.get("", response_model=List[FlashcardOut])
def list_flashcards(
    notebook_id: uuid.UUID | None = Query(default=None),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[FlashcardOut]:
    """List flashcards for the user; optionally filter by notebook id."""
    query = (
        select(models.Flashcard)
        .where(models.Flashcard.user_id == user.id)
        .options(selectinload(models.Flashcard.folders))
        .order_by(models.Flashcard.id)
    )
    if notebook_id is not None:
        query = query.where(models.Flashcard.notebook_id == notebook_id)

    cards = db.execute(query).scalars().unique().all()
    return [_card_to_schema(card) for card in cards]


@router.post(
    "",
    response_model=FlashcardOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_flashcard(
    payload: FlashcardCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlashcardOut:
    """Create a flashcard under a notebook and optionally attach it to folders."""
    _ensure_notebook_owned(db, user, payload.notebook_id)
    card = models.Flashcard(
        user_id=user.id,
        notebook_id=payload.notebook_id,
        question=payload.question,
        answer=payload.answer,
        meta=payload.meta,
    )
    card.folders = _get_folders(db, user, card.notebook_id, payload.folder_ids)
    db.add(card)
    db.commit()
    db.refresh(card)
    return _card_to_schema(card)


@router.put(
    "/{card_id}",
    response_model=FlashcardOut,
    dependencies=[Depends(require_csrf)],
)
def update_flashcard(
    card_id: uuid.UUID,
    payload: FlashcardUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlashcardOut:
    """Update flashcard text/metadata and its folder membership."""
    card = _get_card(card_id, user, db)

    if payload.question is not None:
        card.question = payload.question
    if payload.answer is not None:
        card.answer = payload.answer
    if payload.meta is not None:
        card.meta = payload.meta
    if payload.folder_ids is not None:
        card.folders = _get_folders(db, user, card.notebook_id, payload.folder_ids)

    db.add(card)
    db.commit()
    db.refresh(card)
    return _card_to_schema(card)


@router.delete(
    "/{card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_flashcard(
    card_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Delete a flashcard owned by the user."""
    card = _get_card(card_id, user, db)
    db.delete(card)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
