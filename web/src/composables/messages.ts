// src/composables/messages.ts
import { useStorage } from '@vueuse/core'
import dayjs from 'dayjs'
import type { TMessage, TFileInMessage } from '@/types'

const WELCOME = (): TMessage => ({
  username: 'chatGPT',
  msg: "您好，我是ChatGPT，请问有什么能帮您的?",
  time: dayjs().format('HH:mm'),
  type: 0,
  images: [],
  files: [],
  meta: {},
})

const messages = useStorage<TMessage[]>('messages', [WELCOME()])

function normalize(m: Partial<TMessage>): TMessage {
  return {
    username: String(m.username ?? ''),
    msg: String(m.msg ?? ''),
    type: (m.type ?? 0) as 0 | 1,
    time: m.time ?? dayjs().format('HH:mm'),
    images: Array.isArray(m.images) ? m.images : [],
    files: Array.isArray(m.files) ? (m.files as TFileInMessage[]) : [],
    meta: typeof m.meta === 'object' && m.meta ? m.meta : {},
  }
}

function addMessage(message: TMessage) {
  messages.value.push(normalize(message))
}

function addUserMessage(payload: {
  text: string
  images?: string[]
  files?: TFileInMessage[]   
}) {
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

function addAssistantPlaceholder() {
  addMessage({
    username: 'chatGPT',
    msg: '',
    type: 0,
    time: dayjs().format('HH:mm'),
    images: [],
    files: [],
    meta: {},
  })
}

function appendToLastAssistant(delta: string) {
  const list = messages.value
  if (!list.length) return
  const last = list[list.length - 1]
  if (last.type !== 0) return
  last.msg += delta
}

function setLastAssistantMeta(patch: Record<string, any>) {
  const list = messages.value
  if (!list.length) return
  const last = list[list.length - 1]
  if (last.type !== 0) return
  last.meta = { ...(last.meta || {}), ...patch }
}

function clearMessages(keepWelcome = true) {
  messages.value = keepWelcome ? [WELCOME()] : []
}

function getLastMessages(num = 10) {
  return messages.value.slice(-num)
}

export default function useMessages() {
  return {
    messages,
    addMessage,
    clearMessages,
    getLastMessages,
    addUserMessage,
    addAssistantPlaceholder,
    appendToLastAssistant,
    setLastAssistantMeta,
  }
}
