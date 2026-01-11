/**
 * Auth API - 认证相关接口
 */

import { apiFetch, clearCsrfToken } from './client'
import type { SessionResponse } from './types'

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
