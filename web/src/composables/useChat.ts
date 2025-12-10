// src/composables/useChat.ts
import { ref, nextTick } from 'vue'
import useSetting from '@/composables/setting'
import useMessages, { type MessagesStore } from '@/composables/messages'
import { useResponsesStream } from '@/composables/useResponsesStream'
import type { TFileInMessage, ResponseUIState } from '@/types'

// ==================== 类型定义（保持原有导出） ====================

type ToolConfig = Record<string, any>

export interface UseChatOptions {
  messagesStore?: MessagesStore
  storageKey?: string
  tools?: ToolConfig[] | null | (() => ToolConfig[] | null | undefined)
  includes?: string | string[] | (() => string[] | null | undefined)
}

// 保持原有类型导出，供外部使用
export type Citation = {
  fileId: string
  filename?: string | null
  index?: number
  startIndex?: number
  endIndex?: number
  quote?: string | null
  label?: number
}

export type FileSearchMetaResult = {
  fileId: string
  filename?: string
  score?: number
}

export type FileSearchMeta = {
  queries: string[]
  results: FileSearchMetaResult[]
  totalResults?: number
}

export type ImagePayload = {
  base64: string
  mimeType?: string
}

export type ReasoningStep = {
  type: 'part' | 'delta' | 'summary'
  content: string
  timestamp: number
}

export type ReasoningState = {
  phase: 'thinking' | 'streaming' | 'completed'
  steps: ReasoningStep[]
  isVisible: boolean
}

type WaitingStatus = { key: string; text: string }

const WAITING_STATUS_BY_EVENT: Record<string, WaitingStatus> = {
  'response.output_item.added': { key: 'preparing_message', text: '正在思考' },
  'response.content_part.added': { key: 'structuring_content', text: '正在组织回答内容' },

  'response.created': { key: 'thinking', text: '正在思考' },
  'response.in_progress': { key: 'thinking', text: '正在思考' },

  'response.file_search_call.in_progress': {
    key: 'file_search_start',
    text: '正在准备搜索文件',
  },
  'response.file_search_call.searching': {
    key: 'file_searching',
    text: '正在搜索内部文件和知识库',
  },
  'response.file_search_call.completed': {
    key: 'file_search_done',
    text: '正在整理思路',
  },

  'response.web_search_call.in_progress': {
    key: 'web_search_start',
    text: '正在准备联网搜索',
  },
  'response.web_search_call.searching': {
    key: 'web_searching',
    text: '正在搜索网页资料',
  },
  'response.web_search_call.completed': {
    key: 'web_search_done',
    text: '正在整理回答',
  },

  'response.function_call_arguments.delta': {
    key: 'tool_args_building',
    text: '正在构造工具调用参数',
  },
  'response.function_call_arguments.done': {
    key: 'tool_args_done',
    text: '已生成工具调用参数，等待工具结果',
  },
  'response.custom_tool_call_input.delta': {
    key: 'custom_tool_inputing',
    text: '正在向外部工具发送输入',
  },
  'response.custom_tool_call_input.done': {
    key: 'custom_tool_input_done',
    text: '已发送输入给外部工具，等待响应',
  },

  'response.mcp_call.in_progress': {
    key: 'mcp_call',
    text: '正在通过外部工具获取数据',
  },
  'response.mcp_call.completed': {
    key: 'mcp_call_done',
    text: '已从外部工具获取数据，正在整理',
  },

  'response.code_interpreter_call.in_progress': {
    key: 'code_running',
    text: '正在生成并运行代码',
  },
  'response.code_interpreter_call.interpreting': {
    key: 'code_running',
    text: '正在执行代码并分析结果',
  },

  'response.image_generation_call.in_progress': {
    key: 'img_gen_start',
    text: '正在准备生成图片…',
  },
  'response.image_generation_call.generating': {
    key: 'img_generating',
    text: '正在生成图片',
  },
  'response.image_generation_call.partial_image': {
    key: 'img_partial',
    text: '正在细化图片细节',
  },
  'response.image_generation_call.completed': {
    key: 'img_done',
    text: '图片生成完成，正在准备展示',
  },
}

const createInitialResponseUIState = (): ResponseUIState => ({
  phase: 'waiting',
  statusKey: null,
  statusText: null,
  hasTextStarted: false,
})

const createInitialReasoningState = (): ReasoningState => ({
  phase: 'thinking',
  steps: [],
  isVisible: false,
})

// ==================== 通用工具函数 ====================

const NESTED_KEYS = ['content', 'data', 'result', 'output', 'items', 'value', 'parts', 'outputs'] as const

/**
 * 深度遍历对象，收集所有符合条件的结果
 */
function traverseDeep<T>(
  value: any,
  visitor: (node: Record<string, any>) => T | T[] | undefined
): T[] {
  const collected: T[] = []
  const visited = new WeakSet<object>()

  const walk = (val: any): void => {
    if (!val) return

    if (Array.isArray(val)) {
      for (const item of val) walk(item)
      return
    }

    if (typeof val !== 'object') return
    if (visited.has(val)) return
    visited.add(val)

    const result = visitor(val)
    if (result !== undefined) {
      if (Array.isArray(result)) {
        collected.push(...result)
      } else {
        collected.push(result)
      }
    }

    for (const key of NESTED_KEYS) {
      if (key in val) walk(val[key])
    }
  }

  walk(value)
  return collected
}

/**
 * 通用去重
 */
function dedupeBy<T>(items: T[], keyFn: (item: T) => string): T[] {
  const seen = new Set<string>()
  return items.filter(item => {
    const key = keyFn(item)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

// ==================== Citation 处理 ====================

const toNumber = (val: any): number | null => {
  if (typeof val === 'number' && Number.isFinite(val)) return val
  if (typeof val === 'string' && val.trim() !== '' && !Number.isNaN(Number(val))) {
    return Number(val)
  }
  return null
}

function normalizeAnnotation(annotation: any): Citation | null {
  if (!annotation || typeof annotation !== 'object') return null
  if (annotation.type !== 'file_citation') return null

  const fileId =
    (typeof annotation.file_id === 'string' && annotation.file_id) ||
    (typeof (annotation as any).fileId === 'string' && (annotation as any).fileId) ||
    null

  if (!fileId) return null

  const citation: Citation = { fileId }
  if (typeof annotation.filename === 'string') citation.filename = annotation.filename
  const start = toNumber(annotation.start_index ?? annotation.startIndex)
  const end = toNumber(annotation.end_index ?? annotation.endIndex)
  const idx = toNumber(annotation.index)
  if (start !== null) citation.startIndex = start
  if (end !== null) citation.endIndex = end
  if (idx !== null) citation.index = idx
  const quote =
    (typeof annotation.quote === 'string' && annotation.quote.trim()) ||
    (typeof annotation.text === 'string' && annotation.text.trim()) ||
    null
  if (quote) citation.quote = quote
  const label = toNumber(annotation.label)
  if (label !== null) citation.label = label

  return citation
}

// ==================== FileSearch 处理 ====================

function normalizeFileSearchResult(entry: any): FileSearchMetaResult | null {
  if (!entry || typeof entry !== 'object') return null

  const fileId =
    (typeof entry.file_id === 'string' && entry.file_id) ||
    (typeof entry.fileId === 'string' && entry.fileId) ||
    (typeof entry.document_id === 'string' && entry.document_id) ||
    (typeof entry.id === 'string' && entry.id) ||
    null

  if (!fileId) return null

  return {
    fileId,
    filename:
      (typeof entry.filename === 'string' && entry.filename) ||
      (typeof entry.file?.name === 'string' && entry.file.name) ||
      undefined,
    score: typeof entry.score === 'number' ? entry.score : undefined,
  }
}

function compactFileSearchMeta(payload: any): FileSearchMeta | null {
  if (!payload || typeof payload !== 'object') return null

  const queries = new Set<string>()
  if (Array.isArray(payload.queries)) {
    for (const q of payload.queries) {
      if (typeof q === 'string' && q.trim()) queries.add(q.trim())
    }
  }

  const results: FileSearchMetaResult[] = []
  const rawResults = Array.isArray(payload.results) ? payload.results : []

  for (const raw of rawResults) {
    const normalized = normalizeFileSearchResult(raw)
    if (normalized) results.push(normalized)
  }

  if (!queries.size && !results.length) return null

  const meta: FileSearchMeta = { queries: Array.from(queries), results }
  const totalResults =
    typeof payload.totalResults === 'number' && payload.totalResults > rawResults.length
      ? payload.totalResults
      : undefined

  if (totalResults) meta.totalResults = totalResults
  return meta
}

function extractFileSearchMeta(output: any): FileSearchMeta | null {
  const queries = new Set<string>()
  const results: FileSearchMetaResult[] = []
  let totalResults = 0

  traverseDeep(output, node => {
    if (node.type !== 'file_search_call') return undefined

    if (Array.isArray(node.queries)) {
      for (const q of node.queries) {
        if (typeof q === 'string' && q.trim()) queries.add(q.trim())
      }
    }

    if (Array.isArray(node.search_results)) {
      totalResults += node.search_results.length
      for (const raw of node.search_results) {
        const normalized = normalizeFileSearchResult(raw)
        if (normalized) results.push(normalized)
      }
    }

    return undefined
  })

  if (!queries.size && !results.length) return null

  const meta: FileSearchMeta = {
    queries: Array.from(queries),
    results: dedupeBy(results, r => r.fileId),
  }

  if (totalResults > results.length) meta.totalResults = totalResults
  return meta
}

// ==================== 图片处理 ====================

function extractImages(output: any): ImagePayload[] {
  const seen = new Set<string>()

  return traverseDeep<ImagePayload>(output, node => {
    // image_generation_call 类型
    if (node.type === 'image_generation_call' && typeof node.result === 'string') {
      const clean = node.result.replace(/\s+/g, '')
      if (clean && !seen.has(clean)) {
        seen.add(clean)
        return { base64: clean, mimeType: node.mime_type }
      }
    }

    // 各种 base64 字段
    const base64 =
      (typeof node.image_base64 === 'string' && node.image_base64) ||
      (typeof node.b64_json === 'string' && node.b64_json) ||
      (typeof node.base64 === 'string' && node.base64) ||
      null

    if (base64) {
      const clean = base64.replace(/\s+/g, '')
      if (clean && !seen.has(clean)) {
        seen.add(clean)
        return { base64: clean, mimeType: node.mime_type ?? node.mimeType }
      }
    }

    return undefined
  })
}

function toDataUrl(payload: ImagePayload): string {
  const { base64, mimeType = 'image/png' } = payload
  return base64.startsWith('data:') ? base64 : `data:${mimeType};base64,${base64}`
}

// ==================== Reasoning 提取 ====================

function extractReasoningText(payload: any): string | null {
  if (payload === null || payload === undefined) return null
  if (typeof payload === 'string') return payload
  if (typeof payload.text === 'string') return payload.text
  if (typeof payload.summary === 'string') return payload.summary
  if (typeof payload.content === 'string') return payload.content
  if (typeof payload.value === 'string') return payload.value

  if (payload && typeof payload === 'object') {
    const nested = ['content', 'parts', 'values', 'items']
    for (const key of nested) {
      const val = (payload as any)[key]
      if (Array.isArray(val)) {
        for (const item of val) {
          const found = extractReasoningText(item)
          if (found !== null) return found
        }
      }
    }
  }

  return null
}

// ==================== 主函数 ====================

export function useChat(options?: MessagesStore | UseChatOptions) {
  const setting = useSetting()

  // 解析 messagesStore
  const messagesStore: MessagesStore = (() => {
    if (!options) return useMessages()
    if ('addMessage' in (options as MessagesStore)) return options as MessagesStore
    const opts = options as UseChatOptions
    if (opts.messagesStore) return opts.messagesStore
    if (opts.storageKey) return useMessages(opts.storageKey)
    return useMessages()
  })()

  // 保持原有变量名 loadding（兼容性）
  const loadding = ref(false)
  let controller: AbortController | null = null
  let stoppedFlag = false

  // ========== 初始化 ==========

  const initializePreferredTools = () => {
    if (!options || 'addMessage' in (options as MessagesStore)) return
    const candidate = (options as UseChatOptions).tools
    if (candidate === undefined) return
    const resolved = typeof candidate === 'function' ? candidate() : candidate ?? null
    messagesStore.setPreferredTools?.(resolved ?? null)
  }

  const pruneStoredFileSearchMeta = () => {
    const list = messagesStore.messages?.value
    if (!Array.isArray(list) || !list.length) return

    let mutated = false
    for (const msg of list) {
      if (!msg?.meta) continue
      const raw = (msg.meta as any).fileSearch
      if (raw === undefined) continue

      const cleaned = compactFileSearchMeta(raw)
      if (!cleaned) {
        delete (msg.meta as any).fileSearch
        mutated = true
      } else {
        msg.meta = { ...msg.meta, fileSearch: cleaned }
        mutated = true
      }
    }

    if (mutated) {
      messagesStore.messages.value = [...list]
    }
  }

  initializePreferredTools()
  pruneStoredFileSearchMeta()

  // ========== 辅助函数 ==========

  const parseEvent = (line: string) => {
    try {
      return JSON.parse(line)
    } catch {
      return null
    }
  }

  const resolveEffectiveTools = (tools?: ToolConfig[] | null) => {
    const s = setting.value as any
    const providedTools = Array.isArray(tools) ? tools : null

    if (providedTools) {
      messagesStore.setPreferredTools?.(providedTools)
    }

    const candidates = [
      providedTools,
      messagesStore.preferredTools?.value,
      s.tools,
    ]

    for (const candidate of candidates) {
      if (Array.isArray(candidate) && candidate.length) {
        return JSON.parse(JSON.stringify(candidate))
      }
    }

    return null
  }

  const resolveIncludes = (): string[] => {
    if (!options || 'addMessage' in (options as MessagesStore)) return []
    const includes = (options as UseChatOptions).includes
    const resolved = typeof includes === 'function' ? includes() : includes
    const list: string[] = []

    if (Array.isArray(resolved)) {
      list.push(...resolved)
    } else if (typeof resolved === 'string') {
      list.push(resolved)
    }

    return list.map(item => (typeof item === 'string' ? item.trim() : '')).filter(Boolean)
  }

  const buildRequestBody = (
    content: string,
    imagesDataUrls: string[],
    files: TFileInMessage[],
    tools?: ToolConfig[] | null
  ): Record<string, any> => {
    const s = setting.value as any
    const selectedModel = String(s.model)
    const systemPrompt = s.systemPrompt || ''
    const temperature = typeof s.temperature === 'number' ? s.temperature : 0.7
    const maxOutputTokens = typeof s.maxTokens === 'number' ? s.maxTokens : undefined
    const effectiveTools = resolveEffectiveTools(tools)
    const includeSet = new Set<string>(resolveIncludes())

    if (effectiveTools) {
      const hasFileSearch = Array.isArray(effectiveTools)
        ? effectiveTools.some((t: any) => t?.type === 'file_search')
        : effectiveTools?.type === 'file_search'

      if (hasFileSearch) {
        includeSet.add('file_search_call.results')
      }
    }

    const lastCompletedResponseId = messagesStore.lastCompletedResponseId?.value ?? null

    const body: Record<string, any> = {
      model: selectedModel,
      text: content,
      images: imagesDataUrls.slice(),
      files,
      system_prompt: systemPrompt || undefined,
      tools: effectiveTools ?? undefined,
      includes: includeSet.size ? Array.from(includeSet) : undefined,
      previous_response_id: lastCompletedResponseId || undefined,
      reasoning: { summary: 'auto', effort: "high"},
    }

    if (!selectedModel.includes('gpt-5')) {
      body.temperature = Number(temperature)
    }

    if (typeof maxOutputTokens === 'number') {
      body.max_output_tokens = maxOutputTokens
    }

    return body
  }

  // ========== 核心方法 ==========

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
    let uiState = createInitialResponseUIState()
    let reasoningState = createInitialReasoningState()

    const syncUiState = (
      patch?: Partial<ResponseUIState>,
      extraMeta?: Record<string, any>
    ) => {
      uiState = { ...uiState, ...(patch || {}) }
      messagesStore.setLastAssistantMeta({ ...(extraMeta || {}), uiState })
    }

    const syncReasoningState = (patch: Partial<ReasoningState>) => {
      reasoningState = { ...reasoningState, ...patch }
      messagesStore.setLastAssistantMeta({ reasoning: reasoningState })
    }

    const appendReasoningStep = (
      type: ReasoningStep['type'],
      content: string,
      options: { targetIndex?: number | null; forceNew?: boolean } = {}
    ): number | null => {
      const text = String(content)
      if (text.length === 0) return options.targetIndex ?? null

      const steps = reasoningState.steps
      const targetIndex =
        typeof options.targetIndex === 'number' && steps[options.targetIndex]?.type === type
          ? options.targetIndex
          : options.forceNew
            ? null
            : steps.length && steps[steps.length - 1].type === type
            ? steps.length - 1
            : null

      if (targetIndex !== null) {
        const existing = steps[targetIndex]
        const merged = existing.content + text
        if (merged !== existing.content) {
          steps[targetIndex] = { ...existing, content: merged }
          syncReasoningState({ steps: [...steps], isVisible: true })
        }
        return targetIndex
      }

      const newStep: ReasoningStep = {
        type,
        content: text,
        timestamp: Date.now(),
      }
      steps.push(newStep)
      syncReasoningState({
        steps: [...steps],
        isVisible: true,
      })
      return steps.length - 1
    }

    let currentDeltaIndex: number | null = null

    const applyWaitingStatus = (type: string) => {
      if (uiState.hasTextStarted || uiState.phase !== 'waiting') return
      const status = WAITING_STATUS_BY_EVENT[type]
      if (!status) return
      syncUiState({ statusKey: status.key, statusText: status.text })
    }

    const markTextStarted = () => {
      if (uiState.hasTextStarted) return
      
      // 文本开始时，如果有 reasoning steps，标记为已完成
      if (reasoningState.steps.length > 0 && reasoningState.phase !== 'completed') {
        syncReasoningState({ phase: 'completed' })
      }
      
      syncUiState(
        { hasTextStarted: true, phase: 'streaming', statusKey: null, statusText: null },
        { loading: false },
      )
    }

    const finishUiPhase = (
      statusPatch?: Partial<Pick<ResponseUIState, 'statusKey' | 'statusText'>>,
      extraMeta?: Record<string, any>
    ) => {
      const patch: Partial<ResponseUIState> = { phase: 'finished' }
      if (statusPatch?.statusKey !== undefined) patch.statusKey = statusPatch.statusKey
      if (statusPatch?.statusText !== undefined) patch.statusText = statusPatch.statusText
      syncUiState(patch, { loading: false, ...(extraMeta || {}) })
    }

    // 添加用户消息
    messagesStore.addUserMessage({
      text: content,
      images: imagesDataUrls.slice(),
      files,
    })

    // 构建请求
    const body = buildRequestBody(content, imagesDataUrls, files, tools)

    // 占位 assistant
    messagesStore.addAssistantPlaceholder()
    syncUiState()
    await nextTick()

    // 新建 controller
    controller?.abort()
    controller = new AbortController()
    const signal = controller.signal

    // 状态追踪
    const seenImageHashes = new Set<string>()
    const collectedCitations: Citation[] = []

    const collectAnnotation = (annotation: any) => {
      const normalized = normalizeAnnotation(annotation)
      if (normalized) collectedCitations.push(normalized)
    }

    const deduplicateCitations = (): Citation[] => {
      return dedupeBy(collectedCitations, c => {
        const keyParts = [c.fileId, c.filename ?? '']
        return keyParts.join('-')
      })
    }

    const pushImages = (output: any) => {
      for (const img of extractImages(output)) {
        const hash = img.base64
        if (!seenImageHashes.has(hash)) {
          seenImageHashes.add(hash)
          messagesStore.appendImageToLastAssistant(toDataUrl(img))
        }
      }
    }

    try {
      for await (const line of useResponsesStream(body, { signal })) {
        const evt = parseEvent(line)
        if (!evt?.type) continue

        applyWaitingStatus(evt.type)

        switch (evt.type) {
          // ========== Reasoning 事件处理 ==========
          case 'response.reasoning_summary_part.added': {
            syncReasoningState({ phase: 'thinking' })
            break
          }

          case 'response.reasoning_summary_part.done': {
            syncReasoningState({ phase: 'thinking' })
            currentDeltaIndex = appendReasoningStep('part', "\n", { forceNew: true })
            break
          }

          case 'response.reasoning_summary_text.delta': {
            const delta = extractReasoningText(evt.delta ?? evt.text ?? evt.reasoning_summary_text)
            if (delta) {
              syncReasoningState({ phase: 'streaming' })
              currentDeltaIndex = appendReasoningStep('delta', delta, { targetIndex: currentDeltaIndex })
            }
            break
          }

          // ========== 文本输出 ==========
          case 'response.output_text.delta':
            if (typeof evt.delta === 'string') {
              markTextStarted()
              messagesStore.appendToLastAssistant(evt.delta)
              onDelta?.(evt.delta)
            }
            break

          case 'response.output_text.annotation.added':
            collectAnnotation(evt.annotation)
            break

          case 'response.completed':
            if (evt.response?.id) {
              messagesStore.setLastCompletedResponseId?.(evt.response.id)
              const output = evt.response.output
              pushImages(output)
              finishUiPhase(undefined, {
                responseId: evt.response.id,
                completed: true,
                citations: deduplicateCitations(),
              })
            } else {
              finishUiPhase()
            }
            break

          case 'response.failed':
            finishUiPhase(
              { statusKey: 'failed', statusText: '本次回答失败：服务器错误' },
              { error: true },
            )
            break

          case 'response.incomplete':
            finishUiPhase({
              statusKey: 'incomplete',
              statusText: '回答被截断（原因：max_tokens 等）',
            })
            break

          case 'response.error':
            if (evt.error) {
              finishUiPhase(
                {
                  statusKey: 'stream_error',
                  statusText:
                    typeof evt.error?.message === 'string'
                      ? `请求异常：${evt.error.message}`
                      : '本次回答失败：服务器错误',
                },
                { error: true },
              )
              messagesStore.setLastAssistantText('获取回复失败，请重试')
            }
            break

          case 'error': {
            const message =
              (typeof evt.message === 'string' && evt.message) ||
              (typeof evt.error === 'string' && evt.error) ||
              '请求异常'
            finishUiPhase(
              { statusKey: 'stream_error', statusText: `请求异常：${message}` },
              { error: true },
            )
            break
          }
        }
      }
    } catch (err: any) {
      if (err?.name !== 'AbortError') {
        finishUiPhase(
          { statusKey: 'stream_error', statusText: '请求异常：获取回复失败，请重试' },
          { error: true },
        )
        messagesStore.setLastAssistantText('获取回复失败，请重试')
      }
    } finally {
      controller = null
      loadding.value = false
      if (stoppedFlag) {
        return
      }
      messagesStore.setLastAssistantMeta({ 
        loading: false, 
        uiState,
        reasoning: reasoningState 
      })
    }
  }

  function stop() {
    stoppedFlag = true
    controller?.abort()
    controller = null
    loadding.value = false
    const list = messagesStore.messages?.value
    const last = Array.isArray(list) && list.length ? list[list.length - 1] : null
    const prev = (last?.meta?.uiState as Partial<ResponseUIState> | undefined) ?? undefined
    const prevReasoning = (last?.meta?.reasoning as Partial<ReasoningState> | undefined) ?? undefined
    const stopStatusText = '回复已停止'
    
    messagesStore.setLastAssistantMeta({
      loading: false,
      uiState: {
        phase: 'finished',
        statusKey: 'terminated',
        statusText: stopStatusText,
        hasTextStarted: Boolean(prev?.hasTextStarted),
      },
      reasoning: prevReasoning ? {
        phase: 'completed',
        steps: Array.isArray(prevReasoning.steps) ? prevReasoning.steps : [],
        isVisible: Boolean(prevReasoning.isVisible),
      } : undefined,
    })
  }

  return { loadding, send, stop, messagesStore }
}
