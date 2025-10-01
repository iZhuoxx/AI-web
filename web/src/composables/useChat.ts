// src/composables/useChat.ts
import { ref, nextTick } from 'vue'
import useSetting from '@/composables/setting'
import useMessages from '@/composables/messages'
import { useResponsesStream } from '@/composables/useResponsesStream'
import type { TFileInMessage } from '@/types' 

export function useChat() {
  const setting = useSetting()
  const messages = useMessages()
  const loadding = ref(false)
  let controller: AbortController | null = null
  let stoppedFlag = false

  let lastCompletedResponseId: string | null = null

  const parseEvent = (line: string) => { try { return JSON.parse(line) } catch { return null } }

  async function send({
    text,
    imagesDataUrls,
    files,
    onDelta,
  }: {
    text: string
    imagesDataUrls: string[]
    files: TFileInMessage[]           
    onDelta?: (delta: string) => void
  }) {
    const content = text.trim()
    if (!content && !imagesDataUrls.length && !files.length) return

    loadding.value = true
    stoppedFlag = false

    // 入列用户消息
    messages.addUserMessage({
      text: content,
      images: imagesDataUrls.slice(),
      files,
    })

    // 组装当前轮 input
    const s = setting.value
    const selectedModel   = s.model
    const systemPrompt    = (s as any).systemPrompt || ''
    const temperature     = typeof (s as any).temperature === 'number' ? (s as any).temperature : 0.7
    const maxOutputTokens = typeof (s as any).maxTokens === 'number' ? (s as any).maxTokens : undefined

    const input: any[] = []
    if (systemPrompt) input.push({ role: 'system', content: [{ type: 'input_text', text: systemPrompt }] })

    const userContent: any[] = []
    if (content) userContent.push({ type: 'input_text', text: content })
    for (const url of imagesDataUrls) userContent.push({ type: 'input_image', image_url: url })
    for (const f of files) {
      if (f.fileId) {
        userContent.push({ type: 'input_file', file_id: f.fileId })
      }
      if (f.text) {
        const label = f.truncated ? `[截断] ${f.name}` : f.name
        const payload = `【文件：${label}】\n${f.text}`
        userContent.push({ type: 'input_text', text: payload })
      }
    }
    input.push({ role: 'user', content: userContent })

    // 占位 assistant
    messages.addAssistantPlaceholder()
    await nextTick()

    // 开新控制器
    controller?.abort()
    controller = new AbortController()
    const signal = controller.signal

    // 仅在“上一轮已完成”时带 previous_response_id
    const body: Record<string, any> = { model: String(selectedModel), input, temperature: Number(temperature) }
    if (typeof maxOutputTokens === 'number') body.max_output_tokens = maxOutputTokens
    if (lastCompletedResponseId) body.previous_response_id = lastCompletedResponseId

    try {
      for await (const line of useResponsesStream(body, { signal })) {
        const evt = parseEvent(line); if (!evt) continue

        if (evt.type === 'response.completed' && evt.response?.id) {
          lastCompletedResponseId = evt.response.id
          messages.setLastAssistantMeta({ responseId: evt.response.id, completed: true })
        }

        if (evt.type === 'response.output_text.delta' && typeof evt.delta === 'string') {
          messages.appendToLastAssistant(evt.delta)
          onDelta?.(evt.delta)
        }

        if (evt.type === 'response.error' && evt.error) {
          messages.appendToLastAssistant(`\n[error] ${evt.error?.message || 'unknown error'}`)
        }
      }
    } catch (err: any) {
      if (err?.name !== 'AbortError') {
        messages.appendToLastAssistant(`\n[error] ${err?.message ?? String(err)}`)
      }
    } finally {
      controller = null
      loadding.value = false
    }
  }

  function stop() {
    stoppedFlag = true
    controller?.abort()
    controller = null
    loadding.value = false
    lastCompletedResponseId = null
  }

  return { loadding, send, stop }
}
