"""Routes for quiz question and folder management."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Sequence

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
    QuizAttemptCreate,
    QuizAttemptOut,
)
from api.services import openai_client
from api.services.ai_registry import resolve_model_key
from api .settings import settings 
from api.services.openai_utils import build_responses_payload, extract_text_from_response


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


# ---------------------------------------------------------------------------
# Quiz Attempts
# ---------------------------------------------------------------------------


def _attempt_to_schema(attempt: models.QuizAttempt) -> QuizAttemptOut:
    return QuizAttemptOut(
        id=attempt.id,
        folder_id=attempt.folder_id,
        results=attempt.results,
        total_questions=attempt.total_questions,
        correct_count=attempt.correct_count,
        summary=attempt.summary,
        created_at=attempt.created_at,
        updated_at=attempt.updated_at,
    )




@router.get(
    "/folders/{folder_id}/attempt",
    response_model=QuizAttemptOut,
)
def get_quiz_attempt(
    folder_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizAttemptOut:
    """Get the latest quiz attempt for a folder."""
    folder = _get_folder(folder_id, user, db)
    attempt = db.execute(
        select(models.QuizAttempt).where(
            models.QuizAttempt.folder_id == folder.id,
            models.QuizAttempt.user_id == user.id,
        )
    ).scalars().first()

    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No attempt found for this quiz")

    return _attempt_to_schema(attempt)


@router.post(
    "/folders/{folder_id}/attempt",
    response_model=QuizAttemptOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def submit_quiz_attempt(
    folder_id: uuid.UUID,
    payload: QuizAttemptCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizAttemptOut:
    """Submit quiz attempt results and generate AI feedback summary."""
    folder = _get_folder(folder_id, user, db)
    model_info = resolve_model_key(payload.model_key, default_key=settings.AI_MODEL_DEFAULTS.get("quizSummary"))
    model_name = model_info.model

    # Calculate stats
    total_questions = len(payload.results)
    correct_count = sum(1 for r in payload.results if r.is_correct)
    accuracy = correct_count / total_questions if total_questions > 0 else 0


    # Build results list for storage
    results_data = [
        {
            "question_id": str(r.question_id),
            "selected_answer": r.selected_answer,
            "is_correct": r.is_correct,
        }
        for r in payload.results
    ]

    # Get wrong questions for AI feedback
    wrong_question_ids = [r.question_id for r in payload.results if not r.is_correct]
    wrong_questions: List[models.QuizQuestion] = []
    if wrong_question_ids:
        wrong_questions = list(
            db.execute(
                select(models.QuizQuestion).where(
                    models.QuizQuestion.id.in_(wrong_question_ids),
                    models.QuizQuestion.user_id == user.id,
                )
            ).scalars().all()
        )

    # Generate AI summary
    summary = None
    if total_questions > 0:
        try:
            summary = await _generate_attempt_summary(
                folder_name=folder.name,
                total_questions=total_questions,
                correct_count=correct_count,
                accuracy=accuracy,
                wrong_questions=wrong_questions,
                model_name = model_name,
                supports_temperature = model_info.supports_temperature,
            )
        except Exception as exc:
            # Log error but don't fail the request
            import logging
            logging.warning(f"Failed to generate quiz summary: {exc}")

    # Upsert the attempt (replace existing if any)
    existing_attempt = db.execute(
        select(models.QuizAttempt).where(
            models.QuizAttempt.folder_id == folder.id,
        )
    ).scalars().first()

    if existing_attempt:
        existing_attempt.results = results_data
        existing_attempt.total_questions = total_questions
        existing_attempt.correct_count = correct_count
        existing_attempt.summary = summary
        attempt = existing_attempt
    else:
        attempt = models.QuizAttempt(
            user_id=user.id,
            folder_id=folder.id,
            results=results_data,
            total_questions=total_questions,
            correct_count=correct_count,
            summary=summary,
        )
        db.add(attempt)

    db.commit()
    db.refresh(attempt)

    return _attempt_to_schema(attempt)


async def _generate_attempt_summary(
    folder_name: str,
    total_questions: int,
    correct_count: int,
    accuracy: float,
    wrong_questions: List[models.QuizQuestion],
    model_name: str,
    supports_temperature: bool,
) -> str:
    """Generate personalized AI feedback for quiz attempt."""
    accuracy_pct = round(accuracy * 100)
    model_name = model_name

    # Build context about wrong answers
    wrong_context = ""
    if wrong_questions:
        wrong_items = []
        for q in wrong_questions[:5]:  # Limit to 5 questions for context
            correct_answer = q.options[q.correct_index] if q.correct_index < len(q.options) else "N/A"
            wrong_items.append(f"- 题目: {q.question}\n  正确答案: {correct_answer}")
        wrong_context = "\n".join(wrong_items)

    system_prompt = (
        "你是一位专业的学习顾问。根据用户的测验结果，提供简短、鼓励性的个性化反馈。"
        "反馈应该包含：1) 对本次表现的评价 2) 针对错题的学习建议 3) 下一步学习建议。"
        "请使用 Markdown 输出（不要代码块），用小标题和项目符号组织内容。"
        "保持积极的语气。"
    )

    user_prompt = f"""测验名称: {folder_name}
    答题情况: {correct_count}/{total_questions} ({accuracy_pct}%)

    {"错误的题目:" if wrong_context else "恭喜你全部答对！"}
    {wrong_context if wrong_context else ""}

    请根据以上信息提供个性化反馈"""

    openai_payload: Dict[str, Any] = build_responses_payload({
        "model": model_name,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
        ],
    })

    if supports_temperature:
        openai_payload ["temperature"]=float (0.3 )

    data = await openai_client.responses_complete(openai_payload, timeout=30.0)
    return extract_text_from_response(data) or "测验完成！继续加油！"
