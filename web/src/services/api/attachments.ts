/**
 * Attachments API - 附件管理
 */

import { apiFetch, INTERNAL_TOKEN } from './client'

interface AttachmentUploadResponse {
  attachment_id: string
  object_key: string
  upload: {
    url: string
    fields: Record<string, string>
  }
}

interface AttachmentDownloadResponse {
  url: string
  expires_in: number
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
