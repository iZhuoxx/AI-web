export type TranscriptSegment = {
  id: string
  timestamp: string
  text: string
  speaker?: string
  confidence?: number
}

export type NoteItem = {
  id: string
  title: string
  content: string
}

export interface ActiveNoteForEditor {
  id: string
  title: string
  content: string
}

export type NotebookNote = {
  id: string
  title: string | null
  content: string | null
  seq: number
}

export type NoteAttachment = {
  id: string
  filename: string | null
  mime: string | null
  bytes: number | null
  sha256: string | null
  s3ObjectKey: string | null
  s3Url: string | null
  externalUrl: string | null
  openaiFileId: string | null
  openaiFilePurpose: string | null
  enableFileSearch: boolean
  summary: string | null
  meta: Record<string, unknown> | null
  transcriptionStatus: string
  transcriptionLang: string | null
  transcriptionDurationSec: number | null
  createdAt: string
  updatedAt: string
}

export type NotebookSummary = {
  id: string
  title: string | null
  summary: string | null
  createdAt: string
  updatedAt: string
  color: string | null
  openaiVectorStoreId: string | null
  vectorStoreExpiresAt: string | null
  isArchived: boolean
}

export type NotebookDetail = NotebookSummary & {
  notes: NotebookNote[]
  attachments: NoteAttachment[]
  folders: NotebookFolderRef[]
}

export type NotebookFolderRef = {
  id: string
  name: string
  description: string | null
  color: string | null
}

export type KeywordItem = {
  id: string
  text: string
  relevance: number
}
