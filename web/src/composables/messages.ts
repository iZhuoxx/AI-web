import { useStorage } from '@vueuse/core'
import dayjs from 'dayjs'
import type { TMessage, TFileInMessage, ResponseUIState } from '@/types'

const createInitialUiState = (): ResponseUIState => ({
  phase: 'waiting',
  statusKey: null,
  statusText: null,
  hasTextStarted: false,
})

type ToolConfig = Record<string, any>

function normalizeMessage(payload: Partial<TMessage>): TMessage {
  return {
    username: String(payload.username ?? ''),
    msg: String(payload.msg ?? ''),
    type: (payload.type ?? 0) as 0 | 1,
    time: payload.time ?? dayjs().format('HH:mm'),
    images: Array.isArray(payload.images) ? payload.images : [],
    files: Array.isArray(payload.files) ? (payload.files as TFileInMessage[]) : [],
    meta: typeof payload.meta === 'object' && payload.meta ? payload.meta : {},
  }
}

function createMessagesStore(storageKey: string) {
  const messages = useStorage<TMessage[]>(storageKey, [])
  const lastCompletedResponseId = useStorage<string | null>(
    `${storageKey}::last-response-id`,
    null,
  )
  const preferredTools = useStorage<ToolConfig[] | null>(
    `${storageKey}::preferred-tools`,
    null,
  )

  const cloneTools = (tools: ToolConfig[] | null | undefined) => {
    if (!Array.isArray(tools)) return null
    try {
      return JSON.parse(JSON.stringify(tools)) as ToolConfig[]
    } catch {
      return tools.slice()
    }
  }

  const addMessage = (message: TMessage) => {
    messages.value.push(normalizeMessage(message))
  }

  const addUserMessage = (payload: {
    text: string
    images?: string[]
    files?: TFileInMessage[]
  }) => {
    addMessage({
      username: 'user',
      msg: payload.text,
      type: 1,
      time: dayjs().format('HH:mm'),
      images: payload.images ?? [],
      files: payload.files ?? [],
      meta: {},
    })
  }

  const addAssistantPlaceholder = () => {
    addMessage({
      username: 'chatGPT',
      msg: '',
      type: 0,
      time: dayjs().format('HH:mm'),
      images: [],
      files: [],
      meta: { loading: true, uiState: createInitialUiState() },
    })
  }

  const mergeDeltaNaturally = (prev: string, delta: string): string => {
    if (typeof delta !== 'string' || delta.length === 0) return prev

    let next = delta

    // ① 先处理「空格+标点」这种常见 delta，比如 " ,"
    //    如果 prev 结尾是非空字符，next 是空格+标点，就把 prev 末尾空格 / next 头部空格都去掉
    if (/\S$/.test(prev) && /^\s+[.,!?;:]/.test(next)) {
      // 去掉 prev 末尾可能存在的空格（防御性处理）
      prev = prev.replace(/\s+$/, '')
      // 去掉 next 开头空格，只保留标点
      next = next.replace(/^\s+/, '')
      return prev + next
    }

    const punct = /^[.,!?;:]/

    // ② 标点本身就在开头的情况（比如模型正好切成 "." 这种）
    if (punct.test(next)) {
      return prev.replace(/\s+$/, '') + next
    }

    // ③ 前后都是空格 → 删掉后面的
    if (prev.endsWith(' ') && next.startsWith(' ')) {
      next = next.trimStart()
    }

    // ④ 单词被拆开，如 "Confirm" / "ing"
    if (!next.startsWith(' ') && /[a-zA-Z]/.test(next[0])) {
      return prev + next
    }

    return prev + next
  }


  const appendToLastAssistant = (delta: string) => {
    const list = messages.value
    if (!list.length) return
    const last = list[list.length - 1]
    if (last.type !== 0) return
    const wasLoading = Boolean(last.meta?.loading)
    const currentUiState =
      (last.meta?.uiState as Partial<ResponseUIState> | undefined) ?? createInitialUiState()
    last.meta = {
      ...(last.meta || {}),
      loading: false,
      uiState: {
        ...currentUiState,
        phase: 'streaming',
        statusKey: null,
        statusText: null,
        hasTextStarted: true,
      },
    }
    const currentText = wasLoading
      ? ''
      : typeof last.msg === 'string'
        ? last.msg
        : ''
    last.msg = mergeDeltaNaturally(currentText, delta)
  }

  const appendImageToLastAssistant = (src: string) => {
    const list = messages.value
    if (!list.length) return
    const last = list[list.length - 1]
    if (last.type !== 0) return
    if (!Array.isArray(last.images)) {
      last.images = []
    }
    last.images.push(src)
    if (last.meta?.loading) {
      last.meta = { ...(last.meta || {}), loading: false }
    }
  }

  const setLastAssistantMeta = (patch: Record<string, any>) => {
    const list = messages.value
    if (!list.length) return
    const last = list[list.length - 1]
    if (last.type !== 0) return
    last.meta = { ...(last.meta || {}), ...patch }
  }

  const setLastAssistantText = (text: string) => {
    const list = messages.value
    if (!list.length) return
    const last = list[list.length - 1]
    if (last.type !== 0) return
    last.meta = { ...(last.meta || {}), loading: false }
    last.msg = text
  }

  const clearMessages = () => {
    messages.value = []
    lastCompletedResponseId.value = null
  }

  const getLastMessages = (num = 10) => messages.value.slice(-num)

  const setLastCompletedResponseId = (responseId: string | null) => {
    lastCompletedResponseId.value = responseId
  }

  const resetLastCompletedResponseId = () => {
    lastCompletedResponseId.value = null
  }

  const setPreferredTools = (tools: ToolConfig[] | null | undefined) => {
    if (tools === undefined) return
    preferredTools.value = tools === null ? null : cloneTools(tools)
  }

  const clearPreferredTools = () => {
    preferredTools.value = null
  }

  return {
    messages,
    lastCompletedResponseId,
    preferredTools,
    addMessage,
    clearMessages,
    getLastMessages,
    addUserMessage,
    addAssistantPlaceholder,
    appendToLastAssistant,
    appendImageToLastAssistant,
    setLastAssistantMeta,
    setLastAssistantText,
    setLastCompletedResponseId,
    resetLastCompletedResponseId,
    setPreferredTools,
    clearPreferredTools,
  }
}

type MessagesStore = ReturnType<typeof createMessagesStore>

const STORE_CACHE = new Map<string, MessagesStore>()
const DEFAULT_KEY = 'messages'

export type { MessagesStore }

export default function useMessages(storageKey?: string): MessagesStore {
  const key = storageKey || DEFAULT_KEY
  if (!STORE_CACHE.has(key)) {
    STORE_CACHE.set(key, createMessagesStore(key))
  }
  return STORE_CACHE.get(key)!
}
