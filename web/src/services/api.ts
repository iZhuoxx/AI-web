import type { NotebookDetail, NotebookSummary, NotebookNote, NoteAttachment } from '@/types/notes'

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || '/api'
const CSRF_HEADER = 'X-CSRF-Token'

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
  kind: string
  object_key: string
  mime: string | null
  bytes: number | null
  sha256: string | null
  summary: string | null
  meta: Record<string, unknown> | null
  created_at: string
}

interface ApiNotebook {
  id: string
  title: string | null
  summary: string | null
  created_at: string
  updated_at: string
  is_archived: boolean
  tags: string[]
  notes: ApiNotebookNote[]
  attachments: ApiNoteAttachment[]
}

const mapNotebookNote = (note: ApiNotebookNote): NotebookNote => ({
  id: note.id,
  title: note.title,
  content: note.content,
  seq: note.seq,
})

const mapAttachment = (attachment: ApiNoteAttachment): NoteAttachment => ({
  id: attachment.id,
  kind: attachment.kind,
  objectKey: attachment.object_key,
  mime: attachment.mime,
  bytes: attachment.bytes ?? undefined,
  sha256: attachment.sha256 ?? undefined,
  summary: attachment.summary ?? null,
  meta: attachment.meta ?? null,
  createdAt: attachment.created_at,
})

const mapNotebookDetail = (notebook: ApiNotebook): NotebookDetail => ({
  id: notebook.id,
  title: notebook.title ?? '未命名笔记',
  summary: notebook.summary,
  createdAt: notebook.created_at,
  updatedAt: notebook.updated_at,
  isArchived: notebook.is_archived,
  tags: notebook.tags ?? [],
  notes: (notebook.notes ?? []).map(mapNotebookNote).sort((a, b) => a.seq - b.seq),
  attachments: (notebook.attachments ?? []).map(mapAttachment),
})

const mapNotebookSummary = (notebook: ApiNotebook): NotebookSummary => ({
  id: notebook.id,
  title: notebook.title ?? '未命名笔记',
  summary: notebook.summary,
  createdAt: notebook.created_at,
  updatedAt: notebook.updated_at,
  isArchived: notebook.is_archived,
  tags: notebook.tags ?? [],
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
  title?: string | null
  content?: string | null
  seq: number
}

export interface NotebookPayload {
  title?: string | null
  summary?: string | null
  is_archived?: boolean
  tags?: string[]
  notes?: NotebookNotePayload[]
}

export const listNotebooks = async (): Promise<NotebookSummary[]> => {
  const data = await apiFetch<ApiNotebook[]>('/notes', { method: 'GET', skipCsrf: true })
  return data.map(mapNotebookSummary)
}

export const getNotebook = async (id: string): Promise<NotebookDetail> => {
  const data = await apiFetch<ApiNotebook>(`/notes/${id}`, { method: 'GET', skipCsrf: true })
  return mapNotebookDetail(data)
}

export const createNotebook = async (payload: NotebookPayload): Promise<NotebookDetail> => {
  const data = await apiFetch<ApiNotebook>('/notes', { method: 'POST', body: payload })
  return mapNotebookDetail(data)
}

export const updateNotebook = async (id: string, payload: NotebookPayload): Promise<NotebookDetail> => {
  const data = await apiFetch<ApiNotebook>(`/notes/${id}`, { method: 'PUT', body: payload })
  return mapNotebookDetail(data)
}

export const deleteNotebook = async (id: string): Promise<void> => {
  await apiFetch<void>(`/notes/${id}`, { method: 'DELETE' })
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
  kind?: string
  bytes?: number
}): Promise<{ attachmentId: string; objectKey: string; upload: { url: string; fields: Record<string, string> } }> => {
  const body = {
    notebook_id: payload.notebookId,
    filename: payload.filename,
    content_type: payload.contentType,
    kind: payload.kind,
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
