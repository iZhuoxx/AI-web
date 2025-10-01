// src/composables/useResponsesStream.ts
/**
 * 可靠的流式读取器：
 * - 把 AbortSignal 传给 fetch，并在读取循环里响应中断（controller.abort）
 * - 同时兼容两种格式：
 *    1) 每行一个事件：  {"type":"..."}\n
 *    2) SSE 事件块：   event: xyz\ndata: {...}\n\n
 * - 默认端点：/api/responses/stream（可用 opts.endpoint 覆盖）
 */

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

  // 1) 请求：一定要把 signal 传给 fetch
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'X-API-KEY': token } : {}),
      ...(opts.headers || {}),
    },
    body: JSON.stringify(body ?? {}),
    signal: opts.signal,         // ← 关键：允许外部中断
    cache: 'no-store',
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text || 'stream request failed'}`)
  }
  if (!res.body) throw new Error('No stream body')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()

  let buf = ''
  let aborted = false
  const onAbort = () => { aborted = true }

  opts.signal?.addEventListener('abort', onAbort, { once: true })

  // 两种解析模式：
  // A) 行模式：以 \n 分隔，每行一条（可能带 "data:" 前缀）
  // B) SSE 块：以 \n\n 分隔，块内若存在 "data:" 行则汇总拼接
  const flushLineMode = (emit: (s: string) => void) => {
    let idx: number
    while ((idx = buf.indexOf('\n')) >= 0) {
      const raw = buf.slice(0, idx)
      buf = buf.slice(idx + 1)
      const line = raw.trim()
      if (!line) continue

      let payload = line
      if (line.startsWith('data:')) payload = line.slice(5).trim()
      if (payload) emit(payload)
    }
  }

  const flushSSEBlocks = (emit: (s: string) => void) => {
    let idx: number
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const block = buf.slice(0, idx)
      buf = buf.slice(idx + 2)

      // 解析一个 SSE 块
      // 可能包含多行 data:，需要按顺序拼接
      const lines = block.split(/\r?\n/)
      const datas: string[] = []
      for (const l of lines) {
        if (l.startsWith('data:')) datas.push(l.slice(5).trim())
      }
      // 如果没有 data:，退回行模式处理（兼容退化情况）
      if (datas.length === 0) {
        const tmp = block.split(/\r?\n/)
        for (const raw of tmp) {
          const s = raw.trim()
          if (!s) continue
          let payload = s
          if (s.startsWith('data:')) payload = s.slice(5).trim()
          if (payload) emit(payload)
        }
      } else {
        // 有 data: 的标准 SSE：把所有 data 逐条吐出（符合大多数后端：每条 data 即一事件）
        for (const d of datas) if (d) emit(d)
      }
    }
  }

  try {
    while (true) {
      if (aborted) {
        try { await reader.cancel() } catch {}
        // 抛出 AbortError，供上层用 name === 'AbortError' 区分
        throw new DOMException('Aborted', 'AbortError')
      }

      const { value, done } = await reader.read()
      if (done) break

      buf += decoder.decode(value || new Uint8Array(), { stream: true })

      // 先尝试按 SSE 块解析（\n\n），解析剩余再按行解析（\n）
      const emit = (s: string) => { /* 占位 */ }
      flushSSEBlocks((s) => { if (s) (emit as any)(s) })

      // 因为 emit 需要把值 yield 出去，这里用闭包技巧：
      const emits: string[] = []
      const collect = (s: string) => emits.push(s)

      flushSSEBlocks(collect) // 再跑一次以覆盖本批次新增的块
      flushLineMode(collect)

      // 统一把本批次解析出的 payload 按新增顺序 yield
      for (const payload of emits) {
        yield payload
      }
    }

    // flush 最后一段：优先 SSE 块，其次行
    const tailEmits: string[] = []
    flushSSEBlocks((s) => tailEmits.push(s))
    // 把剩余用行模式再扫一遍
    let idx: number
    while ((idx = buf.indexOf('\n')) >= 0) {
      const raw = buf.slice(0, idx)
      buf = buf.slice(idx + 1)
      const line = raw.trim()
      if (!line) continue
      tailEmits.push(line.startsWith('data:') ? line.slice(5).trim() : line)
    }
    const last = buf.trim()
    if (last) tailEmits.push(last.startsWith('data:') ? last.slice(5).trim() : last)

    for (const s of tailEmits) yield s
  } finally {
    opts.signal?.removeEventListener('abort', onAbort)
    try { await reader.cancel() } catch {}
  }
}
