"""Routes for quiz question and folder management."""

from __future__ import annotations

import uuid
from typing import List, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.dependencies import get_current_user, require_csrf
from api.db import models
from api.db.database import get_db
from api.schemas import (
    QuizQuestionCreate,
    QuizQuestionOut,
    QuizQuestionUpdate,
    QuizFolderCreate,
    QuizFolderOut,
    QuizFolderUpdate,
)


router = APIRouter(prefix="/quizzes", tags=["quiz"])


def _ensure_notebook_owned(db: Session, user: models.User, notebook_id: uuid.UUID) -> models.Notebook:
    notebook = db.get(models.Notebook, notebook_id)
    if not notebook or notebook.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    return notebook


def _question_to_schema(question: models.QuizQuestion) -> QuizQuestionOut:
    return QuizQuestionOut(
        id=question.id,
        notebook_id=question.notebook_id,
        question=question.question,
        options=question.options,
        correct_index=question.correct_index,
        hint=question.hint,
        explaination=question.explaination,
        meta=question.meta,
        is_favorite=question.is_favorite,
        created_at=question.created_at,
        updated_at=question.updated_at,
        folder_ids=[folder.id for folder in question.folders],
    )


def _folder_to_schema(folder: models.QuizFolder) -> QuizFolderOut:
    return QuizFolderOut(
        id=folder.id,
        notebook_id=folder.notebook_id,
        name=folder.name,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        question_ids=[q.id for q in folder.questions],
    )


def _get_question(question_id: uuid.UUID, user: models.User, db: Session) -> models.QuizQuestion:
    question = db.get(models.QuizQuestion, question_id)
    if not question or question.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz question not found")
    return question


def _get_folder(folder_id: uuid.UUID, user: models.User, db: Session) -> models.QuizFolder:
    folder = (
        db.execute(
            select(models.QuizFolder)
            .where(models.QuizFolder.id == folder_id, models.QuizFolder.user_id == user.id)
            .options(selectinload(models.QuizFolder.questions))
        )
        .scalars()
        .first()
    )
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz folder not found")
    return folder


def _validate_index(options: Sequence[str], correct_index: int) -> None:
    if correct_index < 0 or correct_index >= len(options):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="correct_index is out of range")


# ---------------------------------------------------------------------------
# Quiz Folders
# ---------------------------------------------------------------------------


@router.get("/folders", response_model=List[QuizFolderOut])
def list_quiz_folders(
    notebook_id: uuid.UUID | None = Query(default=None),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[QuizFolderOut]:
    """List quiz folders for the user; optionally filter by notebook id."""
    query = (
        select(models.QuizFolder)
        .where(models.QuizFolder.user_id == user.id)
        .options(selectinload(models.QuizFolder.questions))
        .order_by(models.QuizFolder.created_at.desc())
    )
    if notebook_id is not None:
        query = query.where(models.QuizFolder.notebook_id == notebook_id)

    folders = db.execute(query).scalars().all()
    return [_folder_to_schema(folder) for folder in folders]


@router.post(
    "/folders",
    response_model=QuizFolderOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_quiz_folder(
    payload: QuizFolderCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizFolderOut:
    """Create a quiz folder under a notebook."""
    _ensure_notebook_owned(db, user, payload.notebook_id)

    folder = models.QuizFolder(
        user_id=user.id,
        notebook_id=payload.notebook_id,
        name=payload.name,
    )

    if payload.question_ids:
        questions = (
            db.execute(
                select(models.QuizQuestion).where(
                    models.QuizQuestion.id.in_(payload.question_ids),
                    models.QuizQuestion.user_id == user.id,
                )
            )
            .scalars()
            .all()
        )
        folder.questions = list(questions)

    db.add(folder)
    db.commit()
    db.refresh(folder)
    return _folder_to_schema(folder)


@router.put(
    "/folders/{folder_id}",
    response_model=QuizFolderOut,
    dependencies=[Depends(require_csrf)],
)
def update_quiz_folder(
    folder_id: uuid.UUID,
    payload: QuizFolderUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizFolderOut:
    """Update quiz folder name or question membership."""
    folder = _get_folder(folder_id, user, db)

    if payload.name is not None:
        folder.name = payload.name
    if payload.question_ids is not None:
        questions = (
            db.execute(
                select(models.QuizQuestion).where(
                    models.QuizQuestion.id.in_(payload.question_ids),
                    models.QuizQuestion.user_id == user.id,
                )
            )
            .scalars()
            .all()
        )
        folder.questions = list(questions)

    db.add(folder)
    db.commit()
    db.refresh(folder)
    return _folder_to_schema(folder)


@router.delete(
    "/folders/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_quiz_folder(
    folder_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Delete a quiz folder owned by the user."""
    folder = _get_folder(folder_id, user, db)
    db.delete(folder)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Quiz Questions
# ---------------------------------------------------------------------------


@router.get("", response_model=List[QuizQuestionOut])
def list_quiz_questions(
    notebook_id: uuid.UUID | None = Query(default=None),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[QuizQuestionOut]:
    """List quiz questions for the user; optionally filter by notebook id."""
    query = (
        select(models.QuizQuestion)
        .where(models.QuizQuestion.user_id == user.id)
        .options(selectinload(models.QuizQuestion.folders))
        .order_by(models.QuizQuestion.created_at.desc())
    )
    if notebook_id is not None:
        query = query.where(models.QuizQuestion.notebook_id == notebook_id)

    questions = db.execute(query).scalars().all()
    return [_question_to_schema(question) for question in questions]


@router.post(
    "",
    response_model=QuizQuestionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_quiz_question(
    payload: QuizQuestionCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizQuestionOut:
    """Create a multiple-choice quiz question under a notebook."""
    _ensure_notebook_owned(db, user, payload.notebook_id)
    _validate_index(payload.options, payload.correct_index)
    question = models.QuizQuestion(
        user_id=user.id,
        notebook_id=payload.notebook_id,
        question=payload.question,
        options=payload.options,
        correct_index=payload.correct_index,
        hint=payload.hint,
        meta=payload.meta,
        is_favorite=payload.is_favorite,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return _question_to_schema(question)


@router.put(
    "/{question_id}",
    response_model=QuizQuestionOut,
    dependencies=[Depends(require_csrf)],
)
def update_quiz_question(
    question_id: uuid.UUID,
    payload: QuizQuestionUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizQuestionOut:
    """Update quiz question text/options/correct index and favorite flag."""
    question = _get_question(question_id, user, db)

    options = payload.options or question.options
    correct_index = payload.correct_index if payload.correct_index is not None else question.correct_index
    _validate_index(options, correct_index)

    if payload.notebook_id is not None and payload.notebook_id != question.notebook_id:
        _ensure_notebook_owned(db, user, payload.notebook_id)
        question.notebook_id = payload.notebook_id
    if payload.question is not None:
        question.question = payload.question
    if payload.options is not None:
        question.options = payload.options
    question.correct_index = correct_index
    if payload.hint is not None:
        question.hint = payload.hint
    if payload.meta is not None:
        question.meta = payload.meta
    if payload.is_favorite is not None:
        question.is_favorite = payload.is_favorite

    db.add(question)
    db.commit()
    db.refresh(question)
    return _question_to_schema(question)


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_quiz_question(
    question_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Delete a quiz question owned by the user."""
    question = _get_question(question_id, user, db)
    db.delete(question)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
