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

export type NotebookNote = {
  id: string
  title: string | null
  content: string | null
  seq: number
}

export type NoteAttachment = {
  id: string
  kind: string
  objectKey: string
  mime: string | null
  bytes?: number | null
  sha256?: string | null
  summary: string | null
  meta?: Record<string, unknown> | null
  createdAt: string
}

export type NotebookSummary = {
  id: string
  title: string
  summary: string | null
  createdAt: string
  updatedAt: string
  tags: string[]
  isArchived: boolean
}

export type NotebookDetail = NotebookSummary & {
  notes: NotebookNote[]
  attachments: NoteAttachment[]
}

export type KeywordItem = {
  id: string
  text: string
  relevance: number
}

export type LearningMaterial = {
  id: string
  title: string
  description: string
  type: 'article' | 'video' | 'document'
  url: string
  relevance: number
  keywords: string[]
}
