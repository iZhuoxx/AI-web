/**
 * API Client - 核心请求逻辑和 CSRF 处理
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || '/api'
const CSRF_HEADER = 'X-CSRF-Token'

export const INTERNAL_TOKEN = import.meta.env.VITE_INTERNAL_TOKEN as string | undefined

let csrfToken: string | null = null
let csrfPromise: Promise<string | null> | null = null

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'

export interface ApiOptions {
  method?: HttpMethod
  body?: unknown
  headers?: Record<string, string>
  skipCsrf?: boolean
}

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

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
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
