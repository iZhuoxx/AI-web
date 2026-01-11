/**
 * Notebooks API - 笔记本 CRUD 操作
 */

import type { NotebookDetail, NotebookSummary } from '@/types/notes'
import { apiFetch } from './client'
import type { ApiNotebook, NotebookPayload } from './types'
import { mapNotebookDetail, mapNotebookSummary } from './types'

export const listNotebooks = async (): Promise<NotebookSummary[]> => {
  const data = await apiFetch<ApiNotebook[]>('/notebooks', { method: 'GET', skipCsrf: true })
  return data.map(mapNotebookSummary)
}

export const getNotebook = async (id: string): Promise<NotebookDetail> => {
  const data = await apiFetch<ApiNotebook>(`/notebooks/${id}`, { method: 'GET', skipCsrf: true })
  return mapNotebookDetail(data)
}

export const generateNoteTitle = async (content: string, options?: { modelKey?: string }): Promise<string> => {
  const body: Record<string, unknown> = { content }
  if (options?.modelKey) body.model_key = options.modelKey

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
