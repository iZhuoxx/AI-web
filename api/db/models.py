"""SQLAlchemy ORM models for the AI Web API backend."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.db.database import Base


def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Return the enum values as strings for SQLAlchemy Enum columns."""
    return [member.value for member in enum_cls]


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    member_plan: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    member_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    memberships: Mapped[List["Membership"]] = relationship(
        "Membership", back_populates="user", cascade="all, delete-orphan"
    )
    notebooks: Mapped[List["Notebook"]] = relationship(
        "Notebook", back_populates="user", cascade="all, delete-orphan"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment", back_populates="user", cascade="all, delete-orphan"
    )
    transcription_sessions: Mapped[List["TranscriptionSession"]] = relationship(
        "TranscriptionSession", back_populates="user", cascade="all, delete-orphan"
    )

    # Notebook folder relationships.
    notebook_folders: Mapped[List["NotebookFolder"]] = relationship(
        "NotebookFolder", back_populates="user", cascade="all, delete-orphan"
    )

    # Flashcard relationships.
    flashcard_folders: Mapped[List["FlashcardFolder"]] = relationship(
        "FlashcardFolder", back_populates="user", cascade="all, delete-orphan"
    )
    flashcards: Mapped[List["Flashcard"]] = relationship(
        "Flashcard", back_populates="user", cascade="all, delete-orphan"
    )

    # Quiz relationships.
    quiz_folders: Mapped[List["QuizFolder"]] = relationship(
        "QuizFolder", back_populates="user", cascade="all, delete-orphan"
    )
    quiz_questions: Mapped[List["QuizQuestion"]] = relationship(
        "QuizQuestion", back_populates="user", cascade="all, delete-orphan"
    )

    # Mind maps.
    mindmaps: Mapped[List["MindMap"]] = relationship(
        "MindMap", back_populates="user", cascade="all, delete-orphan"
    )


class MembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"


class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    plan: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(
            MembershipStatus,
            name="membership_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="memberships")

    __table_args__ = (Index("idx_memberships_user", "user_id"),)


class Notebook(Base, TimestampMixin):
    __tablename__ = "notebooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Notebook color for UI (e.g. "#FFFFFF" or a Tailwind class).
    color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # OpenAI vector store id (e.g., for file search index).
    openai_vector_store_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    vector_store_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # TODO: add relation to AI chat messages.

    user: Mapped["User"] = relationship("User", back_populates="notebooks")
    notes: Mapped[List["Note"]] = relationship(
        "Note", back_populates="notebook", cascade="all, delete-orphan", order_by="Note.seq"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment", back_populates="notebook", cascade="all, delete-orphan"
    )
    transcription_sessions: Mapped[List["TranscriptionSession"]] = relationship(
        "TranscriptionSession", back_populates="notebook"
    )

    # Notebook folders (many-to-many).
    folders: Mapped[List["NotebookFolder"]] = relationship(
        "NotebookFolder",
        secondary="notebook_folder_items",
        back_populates="notebooks",
    )

    # Flashcard / Quiz / MindMap ownership.
    flashcard_folders: Mapped[List["FlashcardFolder"]] = relationship(
        "FlashcardFolder", back_populates="notebook", cascade="all, delete-orphan"
    )
    flashcards: Mapped[List["Flashcard"]] = relationship(
        "Flashcard", back_populates="notebook", cascade="all, delete-orphan"
    )
    quiz_folders: Mapped[List["QuizFolder"]] = relationship(
        "QuizFolder", back_populates="notebook", cascade="all, delete-orphan"
    )
    quiz_questions: Mapped[List["QuizQuestion"]] = relationship(
        "QuizQuestion", back_populates="notebook", cascade="all, delete-orphan"
    )
    mindmaps: Mapped[List["MindMap"]] = relationship(
        "MindMap", back_populates="notebook", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_notebooks_user_updated", "user_id", "updated_at"),
    )


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE")
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)

    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="notes")

    __table_args__ = (
        UniqueConstraint("notebook_id", "seq", name="uq_notes_seq"),
        Index("idx_notes_notebook", "notebook_id"),
    )


class AttachmentTranscriptionStatus(str, enum.Enum):
    NONE = "none"          # No transcription requested yet.
    PENDING = "pending"    # Transcription task submitted.
    COMPLETED = "completed"
    FAILED = "failed"


class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    notebook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Basic metadata.
    filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mime: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # S3/object storage info.
    s3_object_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # Key within the bucket.
    s3_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # Presigned or public URL.

    # External link (e.g., YouTube / Bilibili video).
    external_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # OpenAI metadata for Files / Vector Store / File Search.
    openai_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Some flows may also track a purpose (assistants / user_data etc.).
    openai_file_purpose: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Whether the attachment participates in File Search (some are archive-only).
    enable_file_search: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    # Text summary used for list display / quick preview.
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # General extension info (e.g., OCR results or parsed metadata).
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # --------------------------
    # Lightweight transcription details
    # --------------------------
    transcription_status: Mapped[AttachmentTranscriptionStatus] = mapped_column(
        Enum(
            AttachmentTranscriptionStatus,
            name="attachment_transcription_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        server_default=AttachmentTranscriptionStatus.NONE.value,
    )

    # Last transcription language / duration (for UI display).
    transcription_lang: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    transcription_duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="attachments")
    user: Mapped["User"] = relationship("User", back_populates="attachments")
    transcription_session: Mapped[Optional["TranscriptionSession"]] = relationship(
        "TranscriptionSession",
        back_populates="attachment",
        foreign_keys="TranscriptionSession.attachment_id",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
    )

    __table_args__ = (
        Index("idx_attachments_notebook", "notebook_id"),
        Index("idx_attachments_user", "user_id"),
        Index("idx_attachments_sha", "sha256"),
        Index("idx_attachments_openai_file_id", "openai_file_id"),
    )


class TranscriptionSource(str, enum.Enum):
    REALTIME = "realtime"
    BATCH = "batch"


class TranscriptionSession(Base, TimestampMixin):
    __tablename__ = "transcription_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    notebook_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="SET NULL"),
        nullable=True,
    )
    attachment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attachments.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[TranscriptionSource] = mapped_column(
        Enum(
            TranscriptionSource,
            name="transcription_source",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    
    lang: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    sample_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="transcription_sessions")
    notebook: Mapped[Optional["Notebook"]] = relationship("Notebook", back_populates="transcription_sessions")
    attachment: Mapped["Attachment"] = relationship(
        "Attachment",
        back_populates="transcription_session",
        foreign_keys=[attachment_id],
    )

    segments: Mapped[List["TranscriptionSegment"]] = relationship(
        "TranscriptionSegment",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="TranscriptionSegment.seq",
    )

    __table_args__ = (
        Index("idx_ts_user_created", "user_id", "created_at"),
        Index("idx_ts_notebook_created", "notebook_id", "created_at"),
        Index("idx_ts_attachment_created", "attachment_id", "created_at"),
        UniqueConstraint("attachment_id", name="uq_transcription_sessions_attachment_id"),
    )


class TranscriptionSegment(Base):
    __tablename__ = "transcription_segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transcription_sessions.id", ondelete="CASCADE")
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    item_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ts_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped["TranscriptionSession"] = relationship("TranscriptionSession", back_populates="segments")

    __table_args__ = (
        UniqueConstraint("session_id", "seq", name="uq_ts_segments_seq"),
        Index("idx_ts_segments_session", "session_id", "seq"),
    )


# ---------------------------------------------------------------------------
# Notebook folders (many-to-many)
# ---------------------------------------------------------------------------


class NotebookFolder(Base, TimestampMixin):
    """Notebook grouping folder (many-to-many)."""

    __tablename__ = "notebook_folders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="notebook_folders")
    notebooks: Mapped[List["Notebook"]] = relationship(
        "Notebook",
        secondary="notebook_folder_items",
        back_populates="folders",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_notebook_folders_user_name"),
        Index("idx_notebook_folders_user", "user_id"),
    )


class NotebookFolderItem(Base):
    """Join table between NotebookFolder and Notebook."""

    __tablename__ = "notebook_folder_items"

    folder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebook_folders.id", ondelete="CASCADE"), primary_key=True
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), primary_key=True
    )

    seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_notebook_folder_items_folder", "folder_id"),
        Index("idx_notebook_folder_items_notebook", "notebook_id"),
    )


# ---------------------------------------------------------------------------
# Flashcards & flashcard folders
# ---------------------------------------------------------------------------


class FlashcardFolder(Base, TimestampMixin):
    """Flashcard folder/collection scoped to a Notebook."""

    __tablename__ = "flashcard_folders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="flashcard_folders")
    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="flashcard_folders")
    flashcards: Mapped[List["Flashcard"]] = relationship(
        "Flashcard",
        secondary="flashcard_folder_items",
        back_populates="folders",
        order_by="FlashcardFolderItem.seq",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "notebook_id", "name", name="uq_flashcard_folders_user_nb_name"
        ),
        Index("idx_flashcard_folders_user_nb", "user_id", "notebook_id"),
    )


class Flashcard(Base):
    """Flashcard storing only question and answer, scoped to a Notebook."""

    __tablename__ = "flashcards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False
    )

    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="flashcards")
    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="flashcards")
    folders: Mapped[List["FlashcardFolder"]] = relationship(
        "FlashcardFolder",
        secondary="flashcard_folder_items",
        back_populates="flashcards",
    )

    __table_args__ = (
        Index("idx_flashcards_user_nb", "user_id", "notebook_id"),
    )


class FlashcardFolderItem(Base):
    """Join table mapping flashcards to folders (with optional ordering)."""

    __tablename__ = "flashcard_folder_items"

    folder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("flashcard_folders.id", ondelete="CASCADE"), primary_key=True
    )
    flashcard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("flashcards.id", ondelete="CASCADE"), primary_key=True
    )

    seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_flashcard_folder_items_folder", "folder_id"),
        Index("idx_flashcard_folder_items_flashcard", "flashcard_id"),
    )


# ---------------------------------------------------------------------------
# Quiz questions + favorites (multiple choice, options stored as JSONB)
# ---------------------------------------------------------------------------


class QuizFolder(Base, TimestampMixin):
    """Quiz folder/collection scoped to a Notebook."""

    __tablename__ = "quiz_folders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="quiz_folders")
    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="quiz_folders")
    questions: Mapped[List["QuizQuestion"]] = relationship(
        "QuizQuestion",
        secondary="quiz_folder_items",
        back_populates="folders",
        order_by="QuizFolderItem.seq",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "notebook_id", "name", name="uq_quiz_folders_user_nb_name"
        ),
        Index("idx_quiz_folders_user_nb", "user_id", "notebook_id"),
    )


class QuizQuestion(Base, TimestampMixin):
    """Multiple-choice quiz question with options, correct index."""

    __tablename__ = "quiz_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False
    )

    # Question stem.
    question: Mapped[str] = mapped_column(Text, nullable=False)

    # Options, e.g., ["A ...", "B ...", "C ...", "D ..."].
    options: Mapped[List[str]] = mapped_column(JSONB, nullable=False)

    # Index of the correct option in options (0-3).
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # hint.
    hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # explaination.
    explaination: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional metadata (difficulty, source, etc.).
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="quiz_questions")
    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="quiz_questions")
    folders: Mapped[List["QuizFolder"]] = relationship(
        "QuizFolder",
        secondary="quiz_folder_items",
        back_populates="questions",
    )

    __table_args__ = (
        Index("idx_quiz_questions_user_nb", "user_id", "notebook_id"),
    )


class QuizFolderItem(Base):
    """Join table mapping quiz questions to folders (with optional ordering)."""

    __tablename__ = "quiz_folder_items"

    folder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quiz_folders.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quiz_questions.id", ondelete="CASCADE"), primary_key=True
    )

    seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_quiz_folder_items_folder", "folder_id"),
        Index("idx_quiz_folder_items_question", "question_id"),
    )


# ---------------------------------------------------------------------------
# Mind maps (store the full diagram JSON)
# ---------------------------------------------------------------------------


class MindMap(Base, TimestampMixin):
    """Mind map that stores the full diagram JSON."""

    __tablename__ = "mindmaps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="mindmaps")
    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="mindmaps")

    __table_args__ = (
        Index("idx_mindmaps_user_nb", "user_id", "notebook_id"),
    )


__all__ = [
    "User",
    "Membership",
    "MembershipStatus",
    "Notebook",
    "Note",
    "Attachment",
    "TranscriptionSession",
    "TranscriptionSegment",
    "TranscriptionSource",
    "NotebookFolder",
    "NotebookFolderItem",
    "FlashcardFolder",
    "Flashcard",
    "FlashcardFolderItem",
    "QuizFolder",
    "QuizQuestion",
    "QuizFolderItem",
    "MindMap",
]
