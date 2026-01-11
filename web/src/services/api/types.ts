/**
 * API Types - 共享类型定义和映射函数
 */

import type { NotebookDetail, NotebookSummary, NotebookNote, NoteAttachment } from '@/types/notes'
import type { Flashcard, FlashcardFolder } from '@/types/flashcards'
import type { MindMap } from '@/types/mindmaps'
import type { QuizQuestion, QuizFolder } from '@/types/quizzes'
import type { MindElixirData } from 'mind-elixir'

// ============================================================================
// Session Types
// ============================================================================

export interface SessionUser {
  id: string
  email: string
  name: string | null
  is_active: boolean
  member_plan: string | null
  member_until: string | null
}

export interface SessionMembership {
  id: string
  plan: string
  status: string
  started_at: string
  ends_at: string | null
}

export interface SessionResponse {
  user: SessionUser
  memberships: SessionMembership[]
}

// ============================================================================
// AI Config Types
// ============================================================================

export interface AiConfigOption {
  key: string
  label: string
  type?: string
}

export interface AiConfigResponse {
  model_options: AiConfigOption[]
  model_defaults: Record<string, string>
  tool_options: AiConfigOption[]
  tool_defaults: Record<string, string[]>
}

// ============================================================================
// Audio Transcription Types
// ============================================================================

export interface AudioTranscriptionResponse {
  text?: string
  confidence?: number
  duration?: number
  language?: string
  model?: string
  model_key?: string
  response_format?: string
}

// ============================================================================
// Notebook Types
// ============================================================================

export interface NotebookNotePayload {
  id?: string | null
  title?: string | null
  content?: string | null
  seq: number
}

export interface NotebookPayload {
  title?: string | null
  summary?: string | null
  is_archived?: boolean
  color?: string | null
  openai_vector_store_id?: string | null
  vector_store_expires_at?: string | null
  folder_ids?: string[]
  notes?: NotebookNotePayload[]
}

// ============================================================================
// Quiz Attempt Types
// ============================================================================

export interface QuizAttemptResultItem {
  questionId: string
  selectedAnswer: number
  isCorrect: boolean
}

export interface QuizAttempt {
  id: string
  folderId: string
  results: Array<{
    question_id: string
    selected_answer: number
    is_correct: boolean
  }>
  totalQuestions: number
  correctCount: number
  summary: string | null
  createdAt: string
  updatedAt: string
}

// ============================================================================
// Internal API Response Types
// ============================================================================

export interface ApiNotebookNote {
  id: string
  title: string | null
  content: string | null
  seq: number
}

export interface ApiNoteAttachment {
  id: string
  filename: string | null
  mime: string | null
  bytes: number | null
  sha256: string | null
  s3_object_key: string | null
  s3_url: string | null
  external_url: string | null
  openai_file_id: string | null
  openai_file_purpose: string | null
  enable_file_search: boolean
  summary: string | null
  meta: Record<string, unknown> | null
  transcription_status: string
  transcription_lang: string | null
  transcription_duration_sec: number | null
  created_at: string
  updated_at: string
}

export interface ApiNotebookFolderRef {
  id: string
  name: string
  description: string | null
  color: string | null
}

export interface ApiNotebook {
  id: string
  title: string | null
  summary: string | null
  color: string | null
  openai_vector_store_id: string | null
  vector_store_expires_at: string | null
  created_at: string
  updated_at: string
  is_archived: boolean
  notes: ApiNotebookNote[]
  attachments: ApiNoteAttachment[]
  folders: ApiNotebookFolderRef[]
}

export interface ApiFlashcardFolder {
  id: string
  notebook_id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
  flashcard_ids: string[]
}

export interface ApiFlashcard {
  id: string
  notebook_id: string
  question: string
  answer: string
  meta: Record<string, unknown> | null
  folder_ids: string[]
}

export interface ApiMindMap {
  id: string
  notebook_id: string
  title: string
  data: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface ApiQuizQuestion {
  id: string
  notebook_id: string
  question: string
  options: string[]
  correct_index: number
  hint: string | null
  explaination: string | null
  meta: Record<string, unknown> | null
  is_favorite: boolean
  folder_ids: string[]
  created_at: string
  updated_at: string
}

export interface ApiQuizFolder {
  id: string
  notebook_id: string
  name: string
  description: string | null
  question_ids: string[]
  created_at: string
  updated_at: string
}

export interface ApiQuizGenerateResponse {
  folder: ApiQuizFolder
  questions: ApiQuizQuestion[]
}

export interface ApiQuizAttempt {
  id: string
  folder_id: string
  results: Array<{
    question_id: string
    selected_answer: number
    is_correct: boolean
  }>
  total_questions: number
  correct_count: number
  summary: string | null
  created_at: string
  updated_at: string
}

// ============================================================================
// Mapper Functions
// ============================================================================

export const mapNotebookNote = (note: ApiNotebookNote): NotebookNote => ({
  id: note.id,
  title: note.title,
  content: note.content,
  seq: note.seq,
})

export const mapAttachment = (attachment: ApiNoteAttachment): NoteAttachment => ({
  id: attachment.id,
  filename: attachment.filename,
  mime: attachment.mime,
  bytes: attachment.bytes,
  sha256: attachment.sha256,
  s3ObjectKey: attachment.s3_object_key,
  s3Url: attachment.s3_url,
  externalUrl: attachment.external_url,
  openaiFileId: attachment.openai_file_id,
  openaiFilePurpose: attachment.openai_file_purpose,
  enableFileSearch: attachment.enable_file_search,
  summary: attachment.summary,
  meta: attachment.meta ?? null,
  transcriptionStatus: attachment.transcription_status,
  transcriptionLang: attachment.transcription_lang,
  transcriptionDurationSec: attachment.transcription_duration_sec,
  createdAt: attachment.created_at,
  updatedAt: attachment.updated_at,
})

export const mapNotebookDetail = (notebook: ApiNotebook): NotebookDetail => ({
  id: notebook.id,
  title: notebook.title,
  summary: notebook.summary,
  color: notebook.color,
  openaiVectorStoreId: notebook.openai_vector_store_id,
  vectorStoreExpiresAt: notebook.vector_store_expires_at,
  createdAt: notebook.created_at,
  updatedAt: notebook.updated_at,
  isArchived: notebook.is_archived,
  notes: (notebook.notes ?? []).map(mapNotebookNote).sort((a, b) => a.seq - b.seq),
  attachments: (notebook.attachments ?? []).map(mapAttachment),
  folders: notebook.folders ?? [],
})

export const mapNotebookSummary = (notebook: ApiNotebook): NotebookSummary => ({
  id: notebook.id,
  title: notebook.title,
  summary: notebook.summary,
  color: notebook.color,
  openaiVectorStoreId: notebook.openai_vector_store_id,
  vectorStoreExpiresAt: notebook.vector_store_expires_at,
  createdAt: notebook.created_at,
  updatedAt: notebook.updated_at,
  isArchived: notebook.is_archived,
})

export const mapFlashcardFolder = (folder: ApiFlashcardFolder): FlashcardFolder => ({
  id: folder.id,
  notebookId: folder.notebook_id,
  name: folder.name,
  description: folder.description,
  flashcardIds: folder.flashcard_ids ?? [],
  createdAt: folder.created_at,
  updatedAt: folder.updated_at,
})

export const mapFlashcard = (card: ApiFlashcard): Flashcard => ({
  id: card.id,
  notebookId: card.notebook_id,
  question: card.question,
  answer: card.answer,
  meta: card.meta ?? null,
  folderIds: card.folder_ids ?? [],
})

const isValidMindElixirData = (data: any): data is MindElixirData =>
  !!data &&
  typeof data === 'object' &&
  data.nodeData &&
  typeof data.nodeData === 'object'

export const mapMindMap = (item: ApiMindMap): MindMap => {
  const baseData = (item.data as any) ?? {}
  const normalizedData: MindElixirData = isValidMindElixirData(baseData)
    ? baseData
    : {
        nodeData: {
          id: item.id,
          topic: item.title || '思维导图',
          root: true,
          children: [],
        },
        linkData: {},
      }

  return {
    id: item.id,
    notebookId: item.notebook_id,
    title: item.title,
    data: normalizedData,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  }
}

export const mapQuizQuestion = (item: ApiQuizQuestion): QuizQuestion => ({
  id: item.id,
  notebookId: item.notebook_id,
  question: item.question,
  options: item.options,
  correctIndex: item.correct_index,
  hint: item.hint,
  explaination: item.explaination,
  meta: item.meta,
  isFavorite: item.is_favorite,
  folderIds: item.folder_ids ?? [],
  createdAt: item.created_at,
  updatedAt: item.updated_at,
})

export const mapQuizFolder = (item: ApiQuizFolder): QuizFolder => ({
  id: item.id,
  notebookId: item.notebook_id,
  name: item.name,
  description: item.description,
  questionIds: item.question_ids ?? [],
  createdAt: item.created_at,
  updatedAt: item.updated_at,
})

export const mapQuizAttempt = (item: ApiQuizAttempt): QuizAttempt => ({
  id: item.id,
  folderId: item.folder_id,
  results: item.results,
  totalQuestions: item.total_questions,
  correctCount: item.correct_count,
  summary: item.summary,
  createdAt: item.created_at,
  updatedAt: item.updated_at,
})
