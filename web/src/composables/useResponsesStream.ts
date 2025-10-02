export type StreamOptions = {
  signal?: AbortSignal
  endpoint?: string
  headers?: Record<string, string>
}

const DEFAULT_ENDPOINT =
  import.meta.env.VITE_RESPONSES_ENDPOINT?.trim() || '/api/responses/stream'

export async function* useResponsesStream(
  body: unknown,
  opts: StreamOptions = {}
): AsyncGenerator<string, void, void> {
  const endpoint = (opts.endpoint || DEFAULT_ENDPOINT).replace(/\/+$/, '')
  const token = (import.meta as any).env?.VITE_INTERNAL_TOKEN

  const res = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'X-API-KEY': token } : {}),
      ...(opts.headers || {}),
    },
    body: JSON.stringify(body ?? {}),
    signal: opts.signal,        
    cache: 'no-store',
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text || 'stream request failed'}`)
  }
  if (!res.body) throw new Error('No stream body')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()

  let buffer = ''
  let aborted = false
  const onAbort = () => { aborted = true }

  opts.signal?.addEventListener('abort', onAbort, { once: true })

  const queued: string[] = []

  const push = (value: string) => {
    const trimmed = value.trim()
    if (trimmed) queued.push(trimmed)
  }

  const emitSSEBlock = (block: string) => {
    const lines = block.split(/\r?\n/)
    const dataLines: string[] = []
    for (const raw of lines) {
      if (!raw || raw.startsWith(':')) continue
      if (raw.startsWith('data:')) {
        dataLines.push(raw.slice(5).trim())
      }
    }

    if (dataLines.length) {
      for (const payload of dataLines) push(payload)
      return
    }

    for (const raw of lines) {
      if (!raw) continue
      const trimmed = raw.trim()
      if (!trimmed) continue
      if (trimmed.startsWith(':')) continue
      if (trimmed.startsWith('data:')) {
        push(trimmed.slice(5).trim())
      } else {
        push(trimmed)
      }
    }
  }

  type SSEBoundary = { index: number; length: number }

  const findSSEBoundary = (source: string): SSEBoundary | null => {
    const nn = source.indexOf('\n\n')
    const rr = source.indexOf('\r\n\r\n')
    if (nn === -1 && rr === -1) return null
    if (nn === -1) return { index: rr, length: 4 }
    if (rr === -1) return { index: nn, length: 2 }
    return rr < nn ? { index: rr, length: 4 } : { index: nn, length: 2 }
  }

  const processBuffer = (final = false) => {
    let boundary = findSSEBoundary(buffer)
    while (boundary) {
      const block = buffer.slice(0, boundary.index)
      buffer = buffer.slice(boundary.index + boundary.length)
      emitSSEBlock(block)
      boundary = findSSEBoundary(buffer)
    }

    let newlineIdx: number
    while ((newlineIdx = buffer.indexOf('\n')) >= 0) {
      const rawLine = buffer.slice(0, newlineIdx)
      buffer = buffer.slice(newlineIdx + 1)
      const trimmed = rawLine.trim()
      if (!trimmed) continue
      if (trimmed.startsWith(':')) continue
      if (trimmed.startsWith('data:')) push(trimmed.slice(5).trim())
      else push(trimmed)
    }

    if (final && buffer.length) {
      const trimmed = buffer.trim()
      if (trimmed) {
        if (trimmed.startsWith('data:')) push(trimmed.slice(5).trim())
        else push(trimmed)
      }
      buffer = ''
    }
  }

  try {
    while (true) {
      if (aborted) {
        try {
          await reader.cancel()
        } catch {}
        throw new DOMException('Aborted', 'AbortError')
      }

      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      processBuffer()

      if (queued.length) {
        for (const item of queued) {
          if (item) yield item
        }
        queued.length = 0
      }
    }

    buffer += decoder.decode()
    processBuffer(true)

    if (queued.length) {
      for (const item of queued) {
        if (item) yield item
      }
      queued.length = 0
    }
  } finally {
    opts.signal?.removeEventListener('abort', onAbort)
    try {
      await reader.cancel()
    } catch {}
  }
}
