import { useStorage } from '@vueuse/core'
import { TMessage } from '@/types'
import dayjs from 'dayjs'

const messages = useStorage<TMessage[]>('messages', [
  {
    username: "chatGPT",
    msg: "Hello, I'm chatGPT",
    time: dayjs().format('HH:mm'),
    type: 0,
  },
])

export default function useMessages() {
  const addMessage = (message: TMessage) => {
    messages.value.push({
      username: message.username,
      msg: message.msg,
      time: message.time || dayjs().format('HH:mm'),
      type: message.type,
    })
  }

  const updateLastMessage = (delta: string) => {
    if (messages.value.length === 0) return
    // 直接修改数组里对象的字段（响应式）
    messages.value[messages.value.length - 1].msg += delta
  }

  const clearMessages = () => {
    messages.value = []
  }

  const getLastMessages = (num: number = 10) => {
    return messages.value.slice(-num)
  }

  return {
    messages,
    addMessage,
    updateLastMessage,
    clearMessages,
    getLastMessages
  }
}
