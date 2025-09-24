<script setup lang="ts">
import { message as messageTip } from 'ant-design-vue'
import useMessages from '@/composables/messages'
import { CopyOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { useClipboard } from '@vueuse/core'
import { TMessage } from '@/types'

const messages = useMessages()
const { copy } = useClipboard({})

defineProps<{
  message: TMessage;
}>()

const copyIt = (msg: string) => {
  copy(msg)
  messageTip.success('Copied')
}

const deleteIt = (meseage: TMessage) => {
  messages.messages.value = messages.messages.value.filter((item) => item !== meseage)
  messageTip.success('Deleted')
}
</script>

<template>
  <!-- type=1 代表用户消息，蓝色右对齐 -->
  <div class="my-2 self-end flex items-center flex-row" v-if="message.type === 1">
    <DeleteOutlined class="pr-1 cursor-pointer self-end !text-gray-400" @click="deleteIt(message)" />
    <div class="p-1 rounded-t-lg rounded-l-lg bg-blue-300 shadow text-sm min-w-10 max-w-500">
      <pre class="max-w-120 m-2 whitespace-pre-wrap">{{ message.msg }}</pre>
    </div>
  </div>

  <!-- type=0 代表 AI 消息，灰色左对齐 -->
  <div class="my-2 self-start flex items-center" v-else>
    <div class="p-1 rounded-t-lg rounded-r-lg bg-gray-100 text-black shadow text-sm min-w-10">
      <pre class="max-w-120 m-2 whitespace-pre-wrap">{{ message.msg }}</pre>
    </div>
    <CopyOutlined class="pl-2 cursor-pointer self-end !text-gray-400" @click="copyIt(message.msg)" />
    <DeleteOutlined class="pl-1 cursor-pointer self-end !text-gray-400" @click="deleteIt(message)" />
  </div>
</template>

<style scoped>
pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
