// src/composables/useResponsesStream.ts
export async function* useResponsesStream(
  body: any,
  opts?: { signal?: AbortSignal }
) {
  const token = import.meta.env.VITE_INTERNAL_TOKEN
  const res = await fetch('/api/responses/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-KEY': token ?? '',
    },
    body: JSON.stringify(body),
    signal: opts?.signal,
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

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value || new Uint8Array(), { stream: true })

    const lines = buffer.split(/\r?\n/)
    buffer = lines.pop() || ''

    for (const rawLine of lines) {
      const line = rawLine.trim()
      if (!line) continue

      // 处理 SSE 格式：以 data: 开头
      let payload = line
      if (line.startsWith('data:')) {
        payload = line.slice(5).trim()
      }
      yield payload
    }
  }

  if (buffer) {
    const tail = buffer.trim()
    if (tail) yield tail
  }
}
