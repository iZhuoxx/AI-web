/**
 * AI API - AI 配置和音频转写
 */

import { TRANSCRIBE_ENDPOINT } from '@/constants/audio'
import { getModelFor } from '@/composables/setting'
import { apiFetch, INTERNAL_TOKEN } from './client'
import type { AiConfigResponse, AudioTranscriptionResponse } from './types'

export const fetchAiConfig = async (): Promise<AiConfigResponse> => {
  return apiFetch<AiConfigResponse>('/ai/config', { method: 'GET', skipCsrf: true })
}

export const transcribeAudio = async (
  file: File,
  options?: {
    modelKey?: string
    responseFormat?: string
    language?: string
    temperature?: number
    prompt?: string
    minConfidence?: number
  },
): Promise<AudioTranscriptionResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('model_key', options?.modelKey ?? getModelFor('audioTranscribe'))
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
