/**
 * Quizzes API - 测验相关接口
 */

import type { QuizQuestion, QuizFolder } from '@/types/quizzes'
import { apiFetch } from './client'
import type {
  ApiQuizQuestion,
  ApiQuizFolder,
  ApiQuizGenerateResponse,
  ApiQuizAttempt,
  QuizAttempt,
  QuizAttemptResultItem,
} from './types'
import { mapQuizQuestion, mapQuizFolder, mapQuizAttempt } from './types'

// ============================================================================
// Quiz Folders
// ============================================================================

export const listQuizFolders = async (options?: { notebookId?: string }): Promise<QuizFolder[]> => {
  const query = options?.notebookId ? `?notebook_id=${encodeURIComponent(options.notebookId)}` : ''
  const data = await apiFetch<ApiQuizFolder[]>(`/quizzes/folders${query}`, { method: 'GET', skipCsrf: true })
  return data.map(mapQuizFolder)
}

export const createQuizFolder = async (payload: {
  notebookId: string
  name: string
  description?: string | null
  questionIds?: string[]
}): Promise<QuizFolder> => {
  const body: Record<string, unknown> = {
    notebook_id: payload.notebookId,
    name: payload.name,
  }
  if (payload.description !== undefined) body.description = payload.description
  if (payload.questionIds) body.question_ids = payload.questionIds

  const data = await apiFetch<ApiQuizFolder>('/quizzes/folders', { method: 'POST', body })
  return mapQuizFolder(data)
}

export const updateQuizFolder = async (
  folderId: string,
  payload: {
    name?: string
    description?: string | null
    questionIds?: string[]
  },
): Promise<QuizFolder> => {
  const body: Record<string, unknown> = {}
  if (payload.name !== undefined) body.name = payload.name
  if (payload.description !== undefined) body.description = payload.description
  if (payload.questionIds !== undefined) body.question_ids = payload.questionIds

  const data = await apiFetch<ApiQuizFolder>(`/quizzes/folders/${folderId}`, { method: 'PUT', body })
  return mapQuizFolder(data)
}

export const deleteQuizFolder = async (folderId: string): Promise<void> => {
  await apiFetch<void>(`/quizzes/folders/${folderId}`, { method: 'DELETE' })
}

// ============================================================================
// Quiz Questions
// ============================================================================

export const listQuizQuestions = async (options?: { notebookId?: string }): Promise<QuizQuestion[]> => {
  const query = options?.notebookId ? `?notebook_id=${encodeURIComponent(options.notebookId)}` : ''
  const data = await apiFetch<ApiQuizQuestion[]>(`/quizzes${query}`, { method: 'GET', skipCsrf: true })
  return data.map(mapQuizQuestion)
}

export const createQuizQuestion = async (payload: {
  notebookId: string
  question: string
  options: string[]
  correctIndex: number
  hint?: string | null
  meta?: Record<string, unknown> | null
  isFavorite?: boolean
}): Promise<QuizQuestion> => {
  const body: Record<string, unknown> = {
    notebook_id: payload.notebookId,
    question: payload.question,
    options: payload.options,
    correct_index: payload.correctIndex,
  }
  if (payload.hint !== undefined) body.hint = payload.hint
  if (payload.meta !== undefined) body.meta = payload.meta
  if (payload.isFavorite !== undefined) body.is_favorite = payload.isFavorite

  const data = await apiFetch<ApiQuizQuestion>('/quizzes', { method: 'POST', body })
  return mapQuizQuestion(data)
}

export const updateQuizQuestion = async (
  questionId: string,
  payload: {
    question?: string
    options?: string[]
    correctIndex?: number
    hint?: string | null
    meta?: Record<string, unknown> | null
    isFavorite?: boolean
  },
): Promise<QuizQuestion> => {
  const body: Record<string, unknown> = {}
  if (payload.question !== undefined) body.question = payload.question
  if (payload.options !== undefined) body.options = payload.options
  if (payload.correctIndex !== undefined) body.correct_index = payload.correctIndex
  if (payload.hint !== undefined) body.hint = payload.hint
  if (payload.meta !== undefined) body.meta = payload.meta
  if (payload.isFavorite !== undefined) body.is_favorite = payload.isFavorite

  const data = await apiFetch<ApiQuizQuestion>(`/quizzes/${questionId}`, { method: 'PUT', body })
  return mapQuizQuestion(data)
}

export const deleteQuizQuestion = async (questionId: string): Promise<void> => {
  await apiFetch<void>(`/quizzes/${questionId}`, { method: 'DELETE' })
}

// ============================================================================
// Quiz Generation
// ============================================================================

export const generateQuizForNotebook = async (
  notebookId: string,
  payload?: {
    attachmentIds?: string[]
    count?: number
    focus?: string
    modelKey?: string
    folderName?: string
  },
): Promise<{ folder: QuizFolder; questions: QuizQuestion[] }> => {
  const body: Record<string, unknown> = {}
  if (payload?.attachmentIds) body.attachment_ids = payload.attachmentIds
  if (payload?.count) body.count = payload.count
  if (payload?.focus) body.focus = payload.focus
  if (payload?.modelKey) body.model_key = payload.modelKey
  if (payload?.folderName) body.folder_name = payload.folderName

  const data = await apiFetch<ApiQuizGenerateResponse>(`/notebooks/${notebookId}/quizzes/generate`, { method: 'POST', body })
  return {
    folder: mapQuizFolder(data.folder),
    questions: (data.questions ?? []).map(mapQuizQuestion),
  }
}

// ============================================================================
// Quiz Attempts
// ============================================================================

export const getQuizAttempt = async (folderId: string): Promise<QuizAttempt | null> => {
  try {
    const data = await apiFetch<ApiQuizAttempt>(`/quizzes/folders/${folderId}/attempt`, {
      method: 'GET',
      skipCsrf: true,
    })
    return mapQuizAttempt(data)
  } catch (err) {
    // 404 means no attempt exists yet
    if (err instanceof Error && err.message.includes('No attempt found')) {
      return null
    }
    throw err
  }
}

export const submitQuizAttempt = async (
  folderId: string,
  results: QuizAttemptResultItem[],
  modelKey: string,
): Promise<QuizAttempt> => {
  const body = {
    results: results.map(r => ({
      question_id: r.questionId,
      selected_answer: r.selectedAnswer,
      is_correct: r.isCorrect,
    })),
    model_key: modelKey,
  }
  const data = await apiFetch<ApiQuizAttempt>(`/quizzes/folders/${folderId}/attempt`, {
    method: 'POST',
    body,
  })
  return mapQuizAttempt(data)
}
