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

    # Notebook 分组文件夹
    notebook_folders: Mapped[List["NotebookFolder"]] = relationship(
        "NotebookFolder", back_populates="user", cascade="all, delete-orphan"
    )

    # 闪卡相关
    flashcard_folders: Mapped[List["FlashcardFolder"]] = relationship(
        "FlashcardFolder", back_populates="user", cascade="all, delete-orphan"
    )
    flashcards: Mapped[List["Flashcard"]] = relationship(
        "Flashcard", back_populates="user", cascade="all, delete-orphan"
    )

    # Quiz 相关
    quiz_questions: Mapped[List["QuizQuestion"]] = relationship(
        "QuizQuestion", back_populates="user", cascade="all, delete-orphan"
    )

    # MindMap
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

    # Notebook 显示颜色（例如 "#FFFFFF" 或 Tailwind 之类）
    color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # OpenAI / 向量库的 vector store id（例如 file search 的索引 id）
    openai_vector_store_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    vector_store_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # TODO
    # Add a column that is related to the AI chat Message.

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

    # Notebook 分组（多对多）
    folders: Mapped[List["NotebookFolder"]] = relationship(
        "NotebookFolder",
        secondary="notebook_folder_items",
        back_populates="notebooks",
    )

    # Flashcard / Quiz / MindMap 归属
    flashcard_folders: Mapped[List["FlashcardFolder"]] = relationship(
        "FlashcardFolder", back_populates="notebook", cascade="all, delete-orphan"
    )
    flashcards: Mapped[List["Flashcard"]] = relationship(
        "Flashcard", back_populates="notebook", cascade="all, delete-orphan"
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
    NONE = "none"          # 不需要转录 / 尚未申请
    PENDING = "pending"    # 已提交转录任务
    COMPLETED = "completed"
    FAILED = "failed"


class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    notebook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 基本信息
    filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mime: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # S3 存储信息（本地 / 自己的对象存储）
    s3_object_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # bucket 内部 key
    s3_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # 预签名或公开访问 URL

    # 外部链接（例如 Youtube / Bilibili 视频）
    external_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # OpenAI 侧信息：用于 File / Vector Store / File Search
    openai_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # 有些场景你可能还想区分 purpose（assistants / user_data 等）
    openai_file_purpose: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # 是否参与 File Search（有些附件可以只做存档，不进检索）
    enable_file_search: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    # 文本摘要（用于列表展示 / 快速预览）
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 通用扩展信息（例如 OCR 结果、解析元数据等）
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # --------------------------
    # 转录相关的轻量信息
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

    # 最近一次转录的语言 / 时长（方便前端展示）
    transcription_lang: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    transcription_duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 关系
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
# Notebook 文件夹（多对多）
# ---------------------------------------------------------------------------


class NotebookFolder(Base, TimestampMixin):
    """Notebook 的分组文件夹（多对多）。"""

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
    """NotebookFolder - Notebook 多对多中间表。"""

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
# 闪卡 & 闪卡文件夹
# ---------------------------------------------------------------------------


class FlashcardFolder(Base, TimestampMixin):
    """闪卡文件夹 / 卡组，强制属于某个 Notebook。"""

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
    """闪卡：只存问题和答案，强制属于 Notebook。"""

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
    """闪卡文件夹 - 闪卡 多对多关系 + 排序。"""

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
# Quiz 题目 + 收藏（选择题，options 用 JSONB）
# ---------------------------------------------------------------------------


class QuizQuestion(Base, TimestampMixin):
    """测验题目：选择题，保存问题、选项、正确答案索引和提示。"""

    __tablename__ = "quiz_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False
    )

    # 题干
    question: Mapped[str] = mapped_column(Text, nullable=False)

    # 选项：例如 ["A 内容", "B 内容", "C 内容", "D 内容"]
    options: Mapped[List[str]] = mapped_column(JSONB, nullable=False)

    # 正确选项在 options 中的下标（0~3）
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # 提示
    hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 预留元数据（难度、来源等）
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="quiz_questions")
    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="quiz_questions")

    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("idx_quiz_questions_user_nb", "user_id", "notebook_id"),
    )


# ---------------------------------------------------------------------------
# 思维导图（保存整张导图的 JSON）
# ---------------------------------------------------------------------------


class MindMap(Base, TimestampMixin):
    """思维导图：保存整张导图的 JSON 数据。"""

    __tablename__ = "mindmaps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
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
    "QuizQuestion",
    "MindMap",
]




# Legsacy model. Will be deleted

# class User(Base, TimestampMixin):
#     __tablename__ = "users"

#     id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     email: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False, index=True)
#     password_hash: Mapped[str] = mapped_column(Text, nullable=False)
#     name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
#     is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
#     member_plan: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
#     member_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

#     memberships: Mapped[List[Membership]] = relationship(
#         "Membership", back_populates="user", cascade="all, delete-orphan"
#     )
#     notebooks: Mapped[List["Notebook"]] = relationship(
#         "Notebook", back_populates="user", cascade="all, delete-orphan"
#     )
#     attachments: Mapped[List[Attachment]] = relationship(
#         "Attachment", back_populates="user", cascade="all, delete-orphan"
#     )
#     transcription_sessions: Mapped[List[TranscriptionSession]] = relationship(
#         "TranscriptionSession", back_populates="user", cascade="all, delete-orphan"
#     )
#     tags: Mapped[List[Tag]] = relationship("Tag", back_populates="user", cascade="all, delete-orphan")


# class MembershipStatus(str, enum.Enum):
#     ACTIVE = "active"
#     CANCELED = "canceled"
#     EXPIRED = "expired"
#     PAST_DUE = "past_due"


# class Membership(Base):
#     __tablename__ = "memberships"

#     id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
#     plan: Mapped[str] = mapped_column(String(50), nullable=False)
#     status: Mapped[MembershipStatus] = mapped_column(Enum(MembershipStatus, name="membership_status"), nullable=False)
#     started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
#     ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
#     meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
#     created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

#     user: Mapped[User] = relationship("User", back_populates="memberships")

#     __table_args__ = (Index("idx_memberships_user", "user_id"),)


# class Notebook(Base, TimestampMixin):
#     __tablename__ = "notebooks"

#     id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
#     title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
#     summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
#     is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
#     # TODO
#     # Add a column for Color
#     # Add a column for vector_store_id, this is for OpenAI file search function
#     # Add a column that is related to the AI chat Message.the chat message informtion can reference to the meesage.ts

#     user: Mapped[User] = relationship("User", back_populates="notebooks")
#     notes: Mapped[List["Note"]] = relationship(
#         "Note", back_populates="notebook", cascade="all, delete-orphan", order_by="Note.seq"
#     )
#     attachments: Mapped[List[Attachment]] = relationship(
#         "Attachment", back_populates="notebook", cascade="all, delete-orphan"
#     )
#     transcription_sessions: Mapped[List[TranscriptionSession]] = relationship(
#         "TranscriptionSession", back_populates="notebook"
#     )
#     tags: Mapped[List[Tag]] = relationship(
#         "Tag", secondary="note_tags", back_populates="notebooks"
#     )

#     __table_args__ = (
#         Index("idx_notebooks_user_updated", "user_id", "updated_at"),
#     )


# class Note(Base):
#     __tablename__ = "notes"

#     id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     notebook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"))
#     title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
#     content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
#     seq: Mapped[int] = mapped_column(Integer, nullable=False)

#     notebook: Mapped[Notebook] = relationship("Notebook", back_populates="notes")

#     __table_args__ = (
#         UniqueConstraint("notebook_id", "seq", name="uq_notes_seq"),
#         Index("idx_notes_notebook", "notebook_id"),
#     )



# class TranscriptionSource(str, enum.Enum):
#     REALTIME = "realtime"
#     BATCH = "batch"


# class TranscriptionSession(Base, TimestampMixin):
#     __tablename__ = "transcription_sessions"

#     id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
#     notebook_id: Mapped[uuid.UUID] = mapped_column(
#         UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="SET NULL"), nullable=True
#     )
#     attachment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
#         UUID(as_uuid=True), ForeignKey("attachments.id", ondelete="SET NULL"), nullable=True
#     )
#     source: Mapped[TranscriptionSource] = mapped_column(
#         Enum(TranscriptionSource, name="transcription_source"), nullable=False
#     )
#     session_uid: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
#     model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
#     engine: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
#     lang: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
#     sample_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
#     duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
#     full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
#     confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

#     user: Mapped[User] = relationship("User", back_populates="transcription_sessions")
#     notebook: Mapped[Notebook] = relationship("Notebook", back_populates="transcription_sessions")
#     attachment: Mapped[Optional[Attachment]] = relationship("Attachment")
#     segments: Mapped[List[TranscriptionSegment]] = relationship(
#         "TranscriptionSegment", back_populates="session", cascade="all, delete-orphan", order_by="TranscriptionSegment.seq"
#     )

#     __table_args__ = (
#         Index("idx_ts_user_created", "user_id", "created_at"),
#         Index("idx_ts_notebook_created", "notebook_id", "created_at"),
#         Index("idx_ts_attachment_created", "attachment_id", "created_at"),
#     )


# class TranscriptionSegment(Base):
#     __tablename__ = "transcription_segments"

#     id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("transcription_sessions.id", ondelete="CASCADE"))
#     seq: Mapped[int] = mapped_column(Integer, nullable=False)
#     item_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
#     content_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
#     ts_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
#     timestamp: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
#     text: Mapped[str] = mapped_column(Text, nullable=False)
#     confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 3), nullable=True)
#     created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

#     session: Mapped[TranscriptionSession] = relationship("TranscriptionSession", back_populates="segments")

#     __table_args__ = (
#         UniqueConstraint("session_id", "seq", name="uq_ts_segments_seq"),
#         Index("idx_ts_segments_session", "session_id", "seq"),
#     )


# class Tag(Base):
#     __tablename__ = "tags"

#     id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
#     name: Mapped[str] = mapped_column(String(64), nullable=False)

#     user: Mapped[User] = relationship("User", back_populates="tags")
#     notebooks: Mapped[List[Notebook]] = relationship("Notebook", secondary="note_tags", back_populates="tags")

#     __table_args__ = (
#         UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
#     )


# class NoteTag(Base):
#     __tablename__ = "note_tags"

#     notebook_id: Mapped[uuid.UUID] = mapped_column(
#         UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), primary_key=True
#     )
#     tag_id: Mapped[uuid.UUID] = mapped_column(
#         UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
#     )


# __all__ = [
#     "User",
#     "Membership",
#     "MembershipStatus",
#     "Notebook",
#     "Note",
#     "Attachment",
#     "TranscriptionSession",
#     "TranscriptionSegment",
#     "TranscriptionSource",
#     "Tag",
#     "NoteTag",
# ]
