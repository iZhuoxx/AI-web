"""SQLAlchemy ORM models for the AI Web API backend."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.db.database import Base


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

    memberships: Mapped[List[Membership]] = relationship(
        "Membership", back_populates="user", cascade="all, delete-orphan"
    )
    notebooks: Mapped[List["Notebook"]] = relationship(
        "Notebook", back_populates="user", cascade="all, delete-orphan"
    )
    attachments: Mapped[List[Attachment]] = relationship(
        "Attachment", back_populates="user", cascade="all, delete-orphan"
    )
    transcription_sessions: Mapped[List[TranscriptionSession]] = relationship(
        "TranscriptionSession", back_populates="user", cascade="all, delete-orphan"
    )
    tags: Mapped[List[Tag]] = relationship("Tag", back_populates="user", cascade="all, delete-orphan")


class MembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"


class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    plan: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(Enum(MembershipStatus, name="membership_status"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship("User", back_populates="memberships")

    __table_args__ = (Index("idx_memberships_user", "user_id"),)


class Notebook(Base, TimestampMixin):
    __tablename__ = "notebooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped[User] = relationship("User", back_populates="notebooks")
    notes: Mapped[List["Note"]] = relationship(
        "Note", back_populates="notebook", cascade="all, delete-orphan", order_by="Note.seq"
    )
    attachments: Mapped[List[Attachment]] = relationship(
        "Attachment", back_populates="notebook", cascade="all, delete-orphan"
    )
    transcription_sessions: Mapped[List[TranscriptionSession]] = relationship(
        "TranscriptionSession", back_populates="notebook"
    )
    tags: Mapped[List[Tag]] = relationship(
        "Tag", secondary="note_tags", back_populates="notebooks"
    )

    __table_args__ = (
        Index("idx_notebooks_user_updated", "user_id", "updated_at"),
    )


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notebook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"))
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)

    notebook: Mapped[Notebook] = relationship("Notebook", back_populates="notes")

    __table_args__ = (
        UniqueConstraint("notebook_id", "seq", name="uq_notes_seq"),
        Index("idx_notes_notebook", "notebook_id"),
    )


class AttachmentKind(str, enum.Enum):
    PDF = "pdf"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    OTHER = "other"


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notebook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[AttachmentKind] = mapped_column(Enum(AttachmentKind, name="attachment_kind"), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    notebook: Mapped[Notebook] = relationship("Notebook", back_populates="attachments")
    user: Mapped[User] = relationship("User", back_populates="attachments")

    __table_args__ = (
        Index("idx_attachments_notebook", "notebook_id"),
        Index("idx_attachments_user", "user_id"),
        Index("idx_attachments_sha", "sha256"),
    )


class TranscriptionSource(str, enum.Enum):
    REALTIME = "realtime"
    BATCH = "batch"


class TranscriptionSession(Base, TimestampMixin):
    __tablename__ = "transcription_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    notebook_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="SET NULL"), nullable=True
    )
    attachment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attachments.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[TranscriptionSource] = mapped_column(
        Enum(TranscriptionSource, name="transcription_source"), nullable=False
    )
    session_uid: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    engine: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lang: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    sample_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="transcription_sessions")
    notebook: Mapped[Optional[Notebook]] = relationship("Notebook", back_populates="transcription_sessions")
    attachment: Mapped[Optional[Attachment]] = relationship("Attachment")
    segments: Mapped[List[TranscriptionSegment]] = relationship(
        "TranscriptionSegment", back_populates="session", cascade="all, delete-orphan", order_by="TranscriptionSegment.seq"
    )

    __table_args__ = (
        Index("idx_ts_user_created", "user_id", "created_at"),
        Index("idx_ts_notebook_created", "notebook_id", "created_at"),
        Index("idx_ts_attachment_created", "attachment_id", "created_at"),
    )


class TranscriptionSegment(Base):
    __tablename__ = "transcription_segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("transcription_sessions.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    item_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ts_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session: Mapped[TranscriptionSession] = relationship("TranscriptionSession", back_populates="segments")

    __table_args__ = (
        UniqueConstraint("session_id", "seq", name="uq_ts_segments_seq"),
        Index("idx_ts_segments_session", "session_id", "seq"),
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64), nullable=False)

    user: Mapped[User] = relationship("User", back_populates="tags")
    notebooks: Mapped[List[Notebook]] = relationship("Notebook", secondary="note_tags", back_populates="tags")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
    )


class NoteTag(Base):
    __tablename__ = "note_tags"

    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )


__all__ = [
    "User",
    "Membership",
    "MembershipStatus",
    "Notebook",
    "Note",
    "Attachment",
    "AttachmentKind",
    "TranscriptionSession",
    "TranscriptionSegment",
    "TranscriptionSource",
    "Tag",
    "NoteTag",
]
