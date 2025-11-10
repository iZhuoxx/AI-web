import { useStorage } from '@vueuse/core'
import dayjs from 'dayjs'
import type { TMessage, TFileInMessage } from '@/types'

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
      meta: { loading: true },
    })
  }

  const appendToLastAssistant = (delta: string) => {
    const list = messages.value
    if (!list.length) return
    const last = list[list.length - 1]
    if (last.type !== 0) return
    if (last.meta?.loading) {
      last.meta = { ...(last.meta || {}), loading: false }
      last.msg = ''
    }
    last.msg += delta
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
