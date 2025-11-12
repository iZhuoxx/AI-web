"""Pydantic models for notebook, note, and attachment payloads."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    seq: int = Field(ge=0)


class NoteOut(NoteCreate):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class AttachmentOut(BaseModel):
    id: UUID
    kind: str
    object_key: str
    mime: Optional[str]
    bytes: Optional[int]
    sha256: Optional[str]
    summary: Optional[str]
    meta: Optional[dict]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotebookBase(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    is_archived: Optional[bool] = False
    tags: List[str] = Field(default_factory=list)


class NotebookCreate(NotebookBase):
    notes: List[NoteCreate] = Field(default_factory=list)


class NotebookUpdate(NotebookBase):
    notes: List[NoteCreate] = Field(default_factory=list)


class NotebookOut(NotebookBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    notes: List[NoteOut] = Field(default_factory=list)
    attachments: List[AttachmentOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class NotebooksListOut(BaseModel):
    notebooks: List[NotebookOut]


class PresignUploadRequest(BaseModel):
    notebook_id: str
    filename: str
    content_type: Optional[str] = None
    kind: Optional[str] = Field(default="file")
    bytes: Optional[int] = None


class PresignUploadResponse(BaseModel):
    attachment_id: UUID
    object_key: str
    upload: dict


class PresignDownloadResponse(BaseModel):
    url: str
    expires_in: int
