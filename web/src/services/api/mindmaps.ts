/**
 * MindMaps API - 思维导图相关接口
 */

import type { MindMap } from '@/types/mindmaps'
import { apiFetch } from './client'
import type { ApiMindMap } from './types'
import { mapMindMap } from './types'

export const listMindMaps = async (options?: { notebookId?: string }): Promise<MindMap[]> => {
  const query = options?.notebookId ? `?notebook_id=${encodeURIComponent(options.notebookId)}` : ''
  const data = await apiFetch<ApiMindMap[]>(`/mindmaps${query}`, { method: 'GET', skipCsrf: true })
  return (data ?? []).map(mapMindMap)
}

export const createMindMap = async (payload: {
  notebookId: string
  title: string
  data: Record<string, unknown>
}): Promise<MindMap> => {
  const body: Record<string, unknown> = {
    notebook_id: payload.notebookId,
    title: payload.title,
    data: payload.data,
  }
  const data = await apiFetch<ApiMindMap>('/mindmaps', { method: 'POST', body })
  return mapMindMap(data)
}

export const updateMindMap = async (
  mindmapId: string,
  payload: { notebookId?: string; title?: string; data?: Record<string, unknown> },
): Promise<MindMap> => {
  const body: Record<string, unknown> = {}
  if (payload.notebookId !== undefined) body.notebook_id = payload.notebookId
  if (payload.title !== undefined) body.title = payload.title
  if (payload.data !== undefined) body.data = payload.data

  const data = await apiFetch<ApiMindMap>(`/mindmaps/${mindmapId}`, { method: 'PUT', body })
  return mapMindMap(data)
}

export const deleteMindMap = async (mindmapId: string): Promise<void> => {
  await apiFetch<void>(`/mindmaps/${mindmapId}`, { method: 'DELETE' })
}

export const generateMindMapForNotebook = async (
  notebookId: string,
  payload?: { attachmentIds?: string[]; focus?: string; title?: string; modelKey?: string },
): Promise<MindMap> => {
  const body: Record<string, unknown> = {}
  if (payload?.attachmentIds) body.attachment_ids = payload.attachmentIds
  if (payload?.focus) body.focus = payload.focus
  if (payload?.title) body.title = payload.title
  if (payload?.modelKey) body.model_key = payload.modelKey

  const data = await apiFetch<ApiMindMap>(`/notebooks/${notebookId}/mindmaps/generate`, { method: 'POST', body })
  return mapMindMap(data)
}
