// src/composables/useChat.ts
import { ref, nextTick } from 'vue'
import useSetting from '@/composables/setting'
import useMessages, { type MessagesStore } from '@/composables/messages'
import { useResponsesStream } from '@/composables/useResponsesStream'
import type { TFileInMessage } from '@/types' 

type ToolConfig = Record<string, any>

export interface UseChatOptions {
  messagesStore?: MessagesStore
  storageKey?: string
  tools?: ToolConfig[] | null | (() => ToolConfig[] | null | undefined)
}

export function useChat(options?: MessagesStore | UseChatOptions) {
  const setting = useSetting()
  const resolvedStore: MessagesStore = (() => {
    if (!options) return useMessages()
    if ('addMessage' in (options as MessagesStore)) {
      return options as MessagesStore
    }
    const opts = options as UseChatOptions
    if (opts.messagesStore) return opts.messagesStore
    if (opts.storageKey) return useMessages(opts.storageKey)
    return useMessages()
  })()
  const messagesStore = resolvedStore
  const loadding = ref(false)
  let controller: AbortController | null = null
  let stoppedFlag = false

  const initializePreferredTools = () => {
    if (!options || 'addMessage' in (options as MessagesStore)) return
    const candidate = (options as UseChatOptions).tools
    if (candidate === undefined) return
    const resolved =
      typeof candidate === 'function'
        ? candidate()
        : candidate ?? null
    messagesStore.setPreferredTools?.(resolved ?? null)
  }

  initializePreferredTools()

  const parseEvent = (line: string) => { try { return JSON.parse(line) } catch { return null } }

  async function send({
    text,
    imagesDataUrls,
    files,
    onDelta,
    tools,
  }: {
    text: string
    imagesDataUrls: string[]
    files: TFileInMessage[]           
    onDelta?: (delta: string) => void
    tools?: ToolConfig[] | null
  }) {
    const content = text.trim()
    if (!content && !imagesDataUrls.length && !files.length) return

    loadding.value = true
    stoppedFlag = false

    // 入列用户消息
    messagesStore.addUserMessage({
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
    messagesStore.addAssistantPlaceholder()
    await nextTick()

    // 开新控制器
    controller?.abort()
    controller = new AbortController()
    const signal = controller.signal

    // 仅在“上一轮已完成”时带 previous_response_id
    const normalizedModel = String(selectedModel)
    const body: Record<string, any> = { model: normalizedModel, input }
    if (normalizedModel !== 'gpt-5') {
      body.temperature = Number(temperature)
    }
    if (typeof maxOutputTokens === 'number') body.max_output_tokens = maxOutputTokens
    const providedTools = Array.isArray(tools) ? tools : null
    if (providedTools) {
      messagesStore.setPreferredTools?.(providedTools)
    }
    const storedTools = Array.isArray(messagesStore.preferredTools?.value)
      ? messagesStore.preferredTools.value
      : null
    const configuredTools = Array.isArray((s as any).tools) ? (s as any).tools : null
    const effectiveTools =
      (providedTools && providedTools.length
        ? providedTools
        : storedTools && storedTools.length
        ? storedTools
        : configuredTools && configuredTools.length
        ? configuredTools
        : null) ?? [{ type: 'image_generation' }]
    body.tools = Array.isArray(effectiveTools)
      ? JSON.parse(JSON.stringify(effectiveTools))
      : effectiveTools
    const lastCompletedResponseId = messagesStore.lastCompletedResponseId?.value ?? null
    if (lastCompletedResponseId) body.previous_response_id = lastCompletedResponseId

    const seenImagePayloads = new Set<string>()

    const extractImagePayloads = (output: any): { base64: string; mimeType?: string }[] => {
      const results: { base64: string; mimeType?: string }[] = []
      const visited = new WeakSet<object>()

      const visit = (value: any): void => {
        if (value == null) return
        if (typeof value === 'string') return
        if (Array.isArray(value)) {
          for (const item of value) visit(item)
          return
        }
        if (typeof value !== 'object') return

        const obj = value as Record<string, any>
        if (visited.has(obj)) return
        visited.add(obj)

        const maybeBase64 =
          typeof obj.image_base64 === 'string'
            ? obj.image_base64
            : typeof obj.b64_json === 'string'
            ? obj.b64_json
            : typeof obj.base64 === 'string'
            ? obj.base64
            : null

        if (obj.type === 'image_generation_call') {
          if (typeof obj.result === 'string') {
            results.push({ base64: obj.result, mimeType: obj.mime_type })
          } else if (obj.result) {
            visit({ ...obj.result, mime_type: obj.result?.mime_type ?? obj.mime_type })
          }
        }

        if (maybeBase64) {
          results.push({ base64: maybeBase64, mimeType: obj.mime_type ?? obj.mimeType })
        }

        const nestedKeys = ['result', 'content', 'data', 'image', 'images', 'output', 'outputs', 'parts', 'items', 'value']
        for (const key of nestedKeys) {
          if (key in obj) visit(obj[key])
        }
      }

      visit(output)
      return results
    }

    const pushImagesFromOutput = (output: any) => {
      const payloads = extractImagePayloads(output)
      for (const { base64, mimeType } of payloads) {
        if (typeof base64 !== 'string') continue
        const clean = base64.replace(/\s+/g, '')
        if (!clean) continue
        if (seenImagePayloads.has(clean)) continue
        seenImagePayloads.add(clean)
        const prepared = clean.startsWith('data:')
          ? clean
          : `data:${mimeType || 'image/png'};base64,${clean}`
        messagesStore.appendImageToLastAssistant(prepared)
      }
    }

    try {
      for await (const line of useResponsesStream(body, { signal })) {
        const evt = parseEvent(line); if (!evt) continue

        if (evt.type === 'response.completed' && evt.response?.id) {
          messagesStore.setLastCompletedResponseId?.(evt.response.id)
          messagesStore.setLastAssistantMeta({ responseId: evt.response.id, completed: true, loading: false })
          pushImagesFromOutput(evt.response?.output)
        }

        if (evt.type === 'response.output_text.delta' && typeof evt.delta === 'string') {
          messagesStore.appendToLastAssistant(evt.delta)
          onDelta?.(evt.delta)
        }

        if (evt.type === 'response.error' && evt.error) {
          messagesStore.setLastAssistantText('获取回复失败，请重试')
          messagesStore.setLastAssistantMeta({ error: true })
        }

      }
    } catch (err: any) {
      if (err?.name !== 'AbortError') {
        messagesStore.setLastAssistantText('获取回复失败，请重试')
        messagesStore.setLastAssistantMeta({ error: true })
      }
    } finally {
      controller = null
      loadding.value = false
      messagesStore.setLastAssistantMeta({ loading: false })
    }
  }

  function stop() {
    stoppedFlag = true
    controller?.abort()
    controller = null
    loadding.value = false
    messagesStore.setLastAssistantMeta({ loading: false })
  }

  return { loadding, send, stop, messagesStore }
}
