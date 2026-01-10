"""Pydantic models for notebook, note, attachment, and related payloads."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    id: Optional[UUID] = None
    title: Optional[str] = None
    content: Optional[str] = None
    seq: int = Field(ge=0)


class NoteOut(NoteCreate):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class AttachmentOut(BaseModel):
    id: UUID
    filename: Optional[str]
    mime: Optional[str]
    bytes: Optional[int]
    sha256: Optional[str]
    s3_object_key: Optional[str]
    s3_url: Optional[str]
    external_url: Optional[str]
    openai_file_id: Optional[str]
    openai_file_purpose: Optional[str]
    enable_file_search: bool
    summary: Optional[str]
    meta: Optional[dict]
    transcription_status: str
    transcription_lang: Optional[str]
    transcription_duration_sec: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttachmentUpdate(BaseModel):
    filename: Optional[str] = Field(default=None, max_length=255)


class NotebookFolderRef(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    color: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class NotebookBase(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    is_archived: Optional[bool] = False
    color: Optional[str] = None
    openai_vector_store_id: Optional[str] = None
    vector_store_expires_at: Optional[datetime] = None


class NotebookCreate(NotebookBase):
    notes: List[NoteCreate] = Field(default_factory=list)
    folder_ids: List[UUID] = Field(default_factory=list)


class NotebookUpdate(NotebookBase):
    notes: Optional[List[NoteCreate]] = None
    folder_ids: Optional[List[UUID]] = None


class NotebookOut(NotebookBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    notes: List[NoteOut] = Field(default_factory=list)
    attachments: List[AttachmentOut] = Field(default_factory=list)
    folders: List[NotebookFolderRef] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class NotebookFolderBase(BaseModel):
    name: str = Field(max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(default=None, max_length=32)


class NotebookFolderCreate(NotebookFolderBase):
    notebook_ids: List[UUID] = Field(default_factory=list)


class NotebookFolderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(default=None, max_length=32)
    notebook_ids: Optional[List[UUID]] = None


class NotebookFolderOut(NotebookFolderBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    notebook_ids: List[UUID] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class FlashcardFolderBase(BaseModel):
    notebook_id: UUID
    name: str = Field(max_length=255)
    description: Optional[str] = None


class FlashcardFolderCreate(FlashcardFolderBase):
    flashcard_ids: List[UUID] = Field(default_factory=list)


class FlashcardFolderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    flashcard_ids: Optional[List[UUID]] = None


class FlashcardFolderOut(FlashcardFolderBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    flashcard_ids: List[UUID] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class FlashcardBase(BaseModel):
    question: str
    answer: str
    meta: Optional[dict] = None


class FlashcardCreate(FlashcardBase):
    notebook_id: UUID
    folder_ids: List[UUID] = Field(default_factory=list)


class FlashcardUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    meta: Optional[dict] = None
    folder_ids: Optional[List[UUID]] = None


class FlashcardOut(FlashcardBase):
    id: UUID
    notebook_id: UUID
    folder_ids: List[UUID] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class FlashcardGenerateRequest(BaseModel):
    attachment_ids: List[UUID] = Field(default_factory=list)
    count: Optional[int] = Field(default=None, ge=1, le=60)
    focus: Optional[str] = Field(default=None, max_length=600)
    folder_name: Optional[str] = Field(default=None, max_length=255)
    folder_id: Optional[UUID] = None
    model: Optional[str] = Field(default=None, max_length=100)


class FlashcardGenerateResponse(BaseModel):
    folder: FlashcardFolderOut
    flashcards: List[FlashcardOut]


class MindMapGenerateRequest(BaseModel):
    attachment_ids: List[UUID] = Field(default_factory=list)
    focus: Optional[str] = Field(default=None, max_length=600)
    title: Optional[str] = Field(default=None, max_length=255)
    model: Optional[str] = Field(default=None, max_length=100)


class QuizGenerateRequest(BaseModel):
    attachment_ids: List[UUID] = Field(default_factory=list)
    count: Optional[int] = Field(default=None, ge=1, le=30)
    focus: Optional[str] = Field(default=None, max_length=600)
    model: Optional[str] = Field(default=None, max_length=100)
    folder_name: Optional[str] = Field(default=None, max_length=255)


class TitleGenerateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=12000)


class TitleGenerateResponse(BaseModel):
    title: str


class StructuredFlashcard(BaseModel):
    question: str = Field(..., description="清晰的提问或提示，用于闪卡正面")
    answer: str = Field(..., description="简洁的答案，用于闪卡背面，50-120字以内")
    sources: List[str] = Field(default_factory=list, description="引用的文件名或 file_id")


class StructuredFlashcardSet(BaseModel):
    folder_name: str = Field(..., description="闪卡合集的名称")
    flashcards: List[StructuredFlashcard]


class StructuredQuizOption(BaseModel):
    text: str = Field(..., description="选项文本")
    is_correct: bool = Field(..., description="是否为正确答案")


class StructuredQuizQuestion(BaseModel):
    question: str = Field(..., description="题目内容")
    options: List[StructuredQuizOption] = Field(..., description="选项列表，通常4个选项")
    hint: Optional[str] = Field(default=None, description="提示")
    explaination: Optional[str] = Field(default=None, description="解释为什么正确答案是对的，为什么错误答案是错的")
    sources: List[str] = Field(default_factory=list, description="引用的文件名或 file_id")


class StructuredQuizSet(BaseModel):
    folder_name: str = Field(..., description="测试合集的名称")
    questions: List[StructuredQuizQuestion]


class StructuredMindMapNode(BaseModel):
    title: str = Field(..., description="节点标题")
    summary: Optional[str] = Field(default=None, description="节点的简短备注")
    children: List["StructuredMindMapNode"] = Field(default_factory=list, description="子节点")


class StructuredMindMap(BaseModel):
    title: str = Field(..., description="思维导图名称")
    root: StructuredMindMapNode


StructuredMindMapNode.model_rebuild()
StructuredMindMap.model_rebuild()


class NotebookQuizBase(BaseModel):
    notebook_id: UUID
    question: str
    options: List[str] = Field(min_length=2)
    correct_index: int = Field(ge=0)
    hint: Optional[str] = None
    explaination: Optional[str] = None
    meta: Optional[dict] = None
    is_favorite: bool = False


class QuizQuestionCreate(NotebookQuizBase):
    pass


class QuizQuestionUpdate(BaseModel):
    notebook_id: Optional[UUID] = None
    question: Optional[str] = None
    options: Optional[List[str]] = None
    correct_index: Optional[int] = Field(default=None, ge=0)
    hint: Optional[str] = None
    meta: Optional[dict] = None
    is_favorite: Optional[bool] = None


class QuizQuestionOut(NotebookQuizBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    folder_ids: List[UUID] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class QuizFolderBase(BaseModel):
    notebook_id: UUID
    name: str = Field(max_length=255)


class QuizFolderCreate(QuizFolderBase):
    question_ids: List[UUID] = Field(default_factory=list)


class QuizFolderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    question_ids: Optional[List[UUID]] = None


class QuizFolderOut(QuizFolderBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    question_ids: List[UUID] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class QuizGenerateResponse(BaseModel):
    folder: QuizFolderOut
    questions: List[QuizQuestionOut]


class MindMapBase(BaseModel):
    notebook_id: UUID
    title: str = Field(max_length=255)
    data: dict


class MindMapCreate(MindMapBase):
    pass


class MindMapUpdate(BaseModel):
    notebook_id: Optional[UUID] = None
    title: Optional[str] = Field(default=None, max_length=255)
    data: Optional[dict] = None


class MindMapOut(MindMapBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotebooksListOut(BaseModel):
    notebooks: List[NotebookOut]


class PresignUploadRequest(BaseModel):
    notebook_id: str
    filename: str
    content_type: Optional[str] = None
    bytes: Optional[int] = None


class PresignUploadResponse(BaseModel):
    attachment_id: UUID
    s3_object_key: str
    upload: dict


class PresignDownloadResponse(BaseModel):
    url: str
    expires_in: int


class AttachmentLinkOpenAI(BaseModel):
    openai_file_id: str = Field(min_length=1, max_length=255)
