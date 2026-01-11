/**
 * Flashcards API - 闪卡相关接口
 */

import type { Flashcard, FlashcardFolder } from '@/types/flashcards'
import { apiFetch } from './client'
import type { ApiFlashcard, ApiFlashcardFolder } from './types'
import { mapFlashcard, mapFlashcardFolder } from './types'

export const listFlashcardFolders = async (options?: { notebookId?: string }): Promise<FlashcardFolder[]> => {
  const query = options?.notebookId ? `?notebook_id=${encodeURIComponent(options.notebookId)}` : ''
  const data = await apiFetch<ApiFlashcardFolder[]>(`/flashcards/folders${query}`, {
    method: 'GET',
    skipCsrf: true,
  })
  return data.map(mapFlashcardFolder)
}

export const updateFlashcardFolder = async (
  folderId: string,
  payload: { name?: string; description?: string | null; flashcardIds?: string[] },
): Promise<FlashcardFolder> => {
  const body: Record<string, unknown> = {}
  if (payload.name !== undefined) body.name = payload.name
  if (payload.description !== undefined) body.description = payload.description
  if (payload.flashcardIds !== undefined) body.flashcard_ids = payload.flashcardIds

  const data = await apiFetch<ApiFlashcardFolder>(`/flashcards/folders/${folderId}`, { method: 'PUT', body })
  return mapFlashcardFolder(data)
}

export const deleteFlashcardFolder = async (folderId: string): Promise<void> => {
  await apiFetch<void>(`/flashcards/folders/${folderId}`, { method: 'DELETE' })
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
    modelKey?: string
    folderId?: string
  },
): Promise<{ folder: FlashcardFolder; flashcards: Flashcard[] }> => {
  const body: Record<string, unknown> = {}
  if (payload?.attachmentIds) body.attachment_ids = payload.attachmentIds
  if (payload?.count) body.count = payload.count
  if (payload?.focus) body.focus = payload.focus
  if (payload?.folderName) body.folder_name = payload.folderName
  if (payload?.folderId) body.folder_id = payload.folderId
  if (payload?.modelKey) body.model_key = payload.modelKey

  const data = await apiFetch<{ folder: ApiFlashcardFolder; flashcards: ApiFlashcard[] }>(
    `/notebooks/${notebookId}/flashcards/generate`,
    { method: 'POST', body },
  )

  return {
    folder: mapFlashcardFolder(data.folder),
    flashcards: (data.flashcards ?? []).map(mapFlashcard),
  }
}
