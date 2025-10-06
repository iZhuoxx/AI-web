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

  const pendingSSE: string[] = []
  const queued: string[] = []

  const push = (value: string) => {
    const trimmed = value.trim()
    if (trimmed) queued.push(trimmed)
  }

  const flushSSE = () => {
    if (!pendingSSE.length) return
    for (const entry of pendingSSE) push(entry)
    pendingSSE.length = 0
  }

  const handleLine = (rawLine: string) => {
    const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine
    if (line.length === 0) {
      flushSSE()
      return
    }
    if (line.startsWith(':')) {
      return
    }

    if (line.startsWith('data:')) {
      const payload = line.slice(5).trim()
      pendingSSE.push(payload)
      return
    }
    flushSSE()
    push(line)
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

      let newlineIdx: number
      while ((newlineIdx = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, newlineIdx)
        buffer = buffer.slice(newlineIdx + 1)
        handleLine(line)
      }

      if (queued.length) {
        for (const item of queued) {
          if (item) yield item
        }
        queued.length = 0
      }
    }

    buffer += decoder.decode()
    if (buffer.length) {
      handleLine(buffer)
      buffer = ''
    }

    flushSSE()

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
