import type { NotebookDetail, NotebookSummary, NotebookNote, NoteAttachment } from '@/types/notes'
import type { Flashcard, FlashcardFolder } from '@/types/flashcards'
import { DEFAULT_AUDIO_MODEL, TRANSCRIBE_ENDPOINT } from '@/constants/audio'
import { getModelFor } from '@/composables/setting'

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || '/api'
const CSRF_HEADER = 'X-CSRF-Token'
const INTERNAL_TOKEN = import.meta.env.VITE_INTERNAL_TOKEN as string | undefined

let csrfToken: string | null = null
let csrfPromise: Promise<string | null> | null = null

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'

interface ApiOptions {
  method?: HttpMethod
  body?: unknown
  headers?: Record<string, string>
  skipCsrf?: boolean
}

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

interface ApiNotebookNote {
  id: string
  title: string | null
  content: string | null
  seq: number
}

interface ApiNoteAttachment {
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

interface ApiNotebookFolderRef {
  id: string
  name: string
  description: string | null
  color: string | null
}

interface ApiNotebook {
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

interface ApiFlashcardFolder {
  id: string
  notebook_id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
  flashcard_ids: string[]
}

interface ApiFlashcard {
  id: string
  notebook_id: string
  question: string
  answer: string
  meta: Record<string, unknown> | null
  folder_ids: string[]
}

const mapNotebookNote = (note: ApiNotebookNote): NotebookNote => ({
  id: note.id,
  title: note.title,
  content: note.content,
  seq: note.seq,
})

const mapAttachment = (attachment: ApiNoteAttachment): NoteAttachment => ({
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

const mapNotebookDetail = (notebook: ApiNotebook): NotebookDetail => ({
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

const mapNotebookSummary = (notebook: ApiNotebook): NotebookSummary => ({
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

const mapFlashcardFolder = (folder: ApiFlashcardFolder): FlashcardFolder => ({
  id: folder.id,
  notebookId: folder.notebook_id,
  name: folder.name,
  description: folder.description,
  flashcardIds: folder.flashcard_ids ?? [],
  createdAt: folder.created_at,
  updatedAt: folder.updated_at,
})

const mapFlashcard = (card: ApiFlashcard): Flashcard => ({
  id: card.id,
  notebookId: card.notebook_id,
  question: card.question,
  answer: card.answer,
  meta: card.meta ?? null,
  folderIds: card.folder_ids ?? [],
})

export const ensureCsrfToken = async (force = false): Promise<string | null> => {
  if (!force && csrfToken) return csrfToken
  if (csrfPromise) return csrfPromise

  csrfPromise = (async () => {
    const response = await fetch(`${API_BASE}/auth/csrf`, {
      method: 'GET',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    })
    if (!response.ok) {
      csrfToken = null
      return null
    }
    const data = await response.json().catch(() => ({}))
    csrfToken = typeof data?.csrf_token === 'string' ? data.csrf_token : null
    return csrfToken
  })()

  try {
    return await csrfPromise
  } finally {
    csrfPromise = null
  }
}

export const clearCsrfToken = () => {
  csrfToken = null
}

async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers ?? {}),
  }

  const needsCsrf = !options.skipCsrf && method !== 'GET'
  if (needsCsrf) {
    const token = await ensureCsrfToken()
    if (token) headers[CSRF_HEADER] = token
  }

  let body: BodyInit | undefined
  if (options.body instanceof FormData) {
    body = options.body
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }

  const response = await fetch(path.startsWith('http') ? path : `${API_BASE}${path}`, {
    method,
    headers,
    body,
    credentials: 'include',
  })

  if (response.status === 204) {
    return undefined as T
  }

  const data = await response.json().catch(() => undefined)

  if (!response.ok) {
    const message =
      (data as any)?.detail || (data as any)?.error?.message || response.statusText || '请求失败'
    throw new Error(message)
  }

  return data as T
}

export const fetchSession = async (): Promise<SessionResponse> => {
  return apiFetch<SessionResponse>('/auth/me', { method: 'GET', skipCsrf: true })
}

export const loginUser = async (payload: { email: string; password: string }): Promise<SessionResponse> => {
  return apiFetch<SessionResponse>('/auth/login', { method: 'POST', body: payload })
}

export const registerUser = async (payload: {
  email: string
  password: string
  name?: string | null
}): Promise<SessionResponse> => {
  return apiFetch<SessionResponse>('/auth/register', { method: 'POST', body: payload })
}

export const logoutUser = async (): Promise<void> => {
  await apiFetch<void>('/auth/logout', { method: 'POST' })
  clearCsrfToken()
}

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

export const listNotebooks = async (): Promise<NotebookSummary[]> => {
  const data = await apiFetch<ApiNotebook[]>('/notebooks', { method: 'GET', skipCsrf: true })
  return data.map(mapNotebookSummary)
}

export const getNotebook = async (id: string): Promise<NotebookDetail> => {
  const data = await apiFetch<ApiNotebook>(`/notebooks/${id}`, { method: 'GET', skipCsrf: true })
  return mapNotebookDetail(data)
}

export const generateNoteTitle = async (content: string, options?: { model?: string }): Promise<string> => {
  const body: Record<string, unknown> = { content }
  if (options?.model) body.model = options.model

  const data = await apiFetch<{ title?: string }>(`/notebooks/title`, {
    method: 'POST',
    body,
  })
  if (typeof data?.title === 'string' && data.title.trim()) return data.title.trim()
  return ''
}

export const createNotebook = async (payload: NotebookPayload): Promise<NotebookDetail> => {
  const data = await apiFetch<ApiNotebook>('/notebooks', { method: 'POST', body: payload })
  return mapNotebookDetail(data)
}

export const updateNotebook = async (id: string, payload: NotebookPayload): Promise<NotebookDetail> => {
  const data = await apiFetch<ApiNotebook>(`/notebooks/${id}`, { method: 'PUT', body: payload })
  return mapNotebookDetail(data)
}

export const deleteNotebook = async (id: string): Promise<void> => {
  await apiFetch<void>(`/notebooks/${id}`, { method: 'DELETE' })
}

interface AttachmentUploadResponse {
  attachment_id: string
  object_key: string
  upload: {
    url: string
    fields: Record<string, string>
  }
}

export const presignAttachmentUpload = async (payload: {
  notebookId: string
  filename: string
  contentType?: string
  bytes?: number
}): Promise<{ attachmentId: string; objectKey: string; upload: { url: string; fields: Record<string, string> } }> => {
  const body = {
    notebook_id: payload.notebookId,
    filename: payload.filename,
    content_type: payload.contentType,
    bytes: payload.bytes,
  }
  const data = await apiFetch<AttachmentUploadResponse>('/attachments/presign-upload', { method: 'POST', body })
  return {
    attachmentId: data.attachment_id,
    objectKey: data.object_key,
    upload: data.upload,
  }
}

interface AttachmentDownloadResponse {
  url: string
  expires_in: number
}

export const getAttachmentDownloadUrl = async (
  attachmentId: string,
): Promise<{ url: string; expiresIn: number }> => {
  const data = await apiFetch<AttachmentDownloadResponse>(`/attachments/${attachmentId}/download-url`, {
    method: 'GET',
    skipCsrf: true,
  })
  return { url: data.url, expiresIn: data.expires_in }
}

export const updateAttachment = async (
  attachmentId: string,
  payload: { filename?: string | null },
): Promise<void> => {
  await apiFetch<void>(`/attachments/${attachmentId}`, {
    method: 'PUT',
    body: payload,
  })
}

export const deleteAttachment = async (attachmentId: string): Promise<void> => {
  await apiFetch<void>(`/attachments/${attachmentId}`, { method: 'DELETE' })
}

export const listFlashcardFolders = async (options?: { notebookId?: string }): Promise<FlashcardFolder[]> => {
  const query = options?.notebookId ? `?notebook_id=${encodeURIComponent(options.notebookId)}` : ''
  const data = await apiFetch<ApiFlashcardFolder[]>(`/flashcard-folders${query}`, {
    method: 'GET',
    skipCsrf: true,
  })
  return data.map(mapFlashcardFolder)
}

export const deleteFlashcardFolder = async (folderId: string): Promise<void> => {
  await apiFetch<void>(`/flashcard-folders/${folderId}`, { method: 'DELETE' })
}

export const listFlashcards = async (options?: { notebookId?: string }): Promise<Flashcard[]> => {
  const query = options?.notebookId ? `?notebook_id=${encodeURIComponent(options.notebookId)}` : ''
  const data = await apiFetch<ApiFlashcard[]>(`/flashcards${query}`, { method: 'GET', skipCsrf: true })
  return data.map(mapFlashcard)
}

export const deleteFlashcard = async (cardId: string): Promise<void> => {
  await apiFetch<void>(`/flashcards/${cardId}`, { method: 'DELETE' })
}

export const updateFlashcard = async (
  cardId: string,
  payload: { question?: string; answer?: string; meta?: Record<string, unknown> | null; folderIds?: string[] },
): Promise<Flashcard> => {
  const body: Record<string, unknown> = {}
  if (payload.question !== undefined) body.question = payload.question
  if (payload.answer !== undefined) body.answer = payload.answer
  if (payload.meta !== undefined) body.meta = payload.meta
  if (payload.folderIds !== undefined) body.folder_ids = payload.folderIds

  const data = await apiFetch<ApiFlashcard>(`/flashcards/${cardId}`, { method: 'PUT', body })
  return mapFlashcard(data)
}

export const createFlashcard = async (payload: {
  notebookId: string
  question: string
  answer: string
  meta?: Record<string, unknown> | null
  folderIds?: string[]
}): Promise<Flashcard> => {
  const body: Record<string, unknown> = {
    notebook_id: payload.notebookId,
    question: payload.question,
    answer: payload.answer,
  }
  if (payload.meta !== undefined) body.meta = payload.meta
  if (payload.folderIds !== undefined) body.folder_ids = payload.folderIds

  const data = await apiFetch<ApiFlashcard>('/flashcards', { method: 'POST', body })
  return mapFlashcard(data)
}

export const generateFlashcardsForNotebook = async (
  notebookId: string,
  payload?: {
    attachmentIds?: string[]
    count?: number
    focus?: string
    folderName?: string
    model?: string
    folderId?: string
  },
): Promise<{ folder: FlashcardFolder; flashcards: Flashcard[] }> => {
  const body: Record<string, unknown> = {}
  if (payload?.attachmentIds) body.attachment_ids = payload.attachmentIds
  if (payload?.count) body.count = payload.count
  if (payload?.focus) body.focus = payload.focus
  if (payload?.folderName) body.folder_name = payload.folderName
  if (payload?.folderId) body.folder_id = payload.folderId
  if (payload?.model) body.model = payload.model

  const data = await apiFetch<{ folder: ApiFlashcardFolder; flashcards: ApiFlashcard[] }>(
    `/notebooks/${notebookId}/flashcards/generate`,
    { method: 'POST', body },
  )

  return {
    folder: mapFlashcardFolder(data.folder),
    flashcards: (data.flashcards ?? []).map(mapFlashcard),
  }
}

interface OpenAIFileResponse {
  id: string
  object: string
  bytes: number
  created_at: number
  expires_at?: number
  filename: string
  purpose: string
}

export const uploadOpenAIFile = async (
  file: File,
  options?: { purpose?: string; expiresAfterAnchor?: string; expiresAfterSeconds?: number },
): Promise<OpenAIFileResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('purpose', options?.purpose ?? 'user_data')
  if (options?.expiresAfterAnchor) {
    formData.append('expires_after[anchor]', options.expiresAfterAnchor)
  }
  if (typeof options?.expiresAfterSeconds === 'number') {
    formData.append('expires_after[seconds]', String(options.expiresAfterSeconds))
  }
  const headers = INTERNAL_TOKEN ? { 'X-API-KEY': INTERNAL_TOKEN } : undefined
  return apiFetch<OpenAIFileResponse>('/files/', {
    method: 'POST',
    body: formData,
    ...(headers ? { headers } : {}),
  })
}

export const linkAttachmentToOpenAI = async (
  attachmentId: string,
  openaiFileId: string,
): Promise<{ id: string; openai_file_id: string }> => {
  return apiFetch<{ id: string; openai_file_id: string }>(`/attachments/${attachmentId}/link-openai`, {
    method: 'POST',
    body: { openai_file_id: openaiFileId },
  })
}

export interface AudioTranscriptionResponse {
  text?: string
  confidence?: number
  duration?: number
  language?: string
  model?: string
  response_format?: string
}

export const transcribeAudio = async (
  file: File,
  options?: {
    model?: string
    responseFormat?: string
    language?: string
    temperature?: number
    prompt?: string
    minConfidence?: number
  },
): Promise<AudioTranscriptionResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('model', options?.model ?? getModelFor('audioTranscribe') ?? DEFAULT_AUDIO_MODEL)
  formData.append('response_format', options?.responseFormat ?? 'json')
  if (options?.language) formData.append('language', options.language)
  if (typeof options?.temperature === 'number') {
    formData.append('temperature', String(options.temperature))
  }
  if (options?.prompt) formData.append('prompt', options.prompt)
  if (typeof options?.minConfidence === 'number') {
    formData.append('min_confidence', String(options.minConfidence))
  }

  const headers = INTERNAL_TOKEN ? { 'X-API-KEY': INTERNAL_TOKEN } : undefined

  return apiFetch<AudioTranscriptionResponse>(TRANSCRIBE_ENDPOINT, {
    method: 'POST',
    body: formData,
    skipCsrf: true,
    ...(headers ? { headers } : {}),
  })
}
