<script setup lang="ts">
import { message as messageTip } from 'ant-design-vue'
import useMessages from '@/composables/messages'
import { CopyOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { useClipboard } from '@vueuse/core'
import { TMessage } from '@/types'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

const messages = useMessages()
const { copy } = useClipboard({})

defineProps<{ message: TMessage }>()

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
  <!-- 用户消息：右对齐、蓝色气泡，仍用纯文本 -->
  <div class="my-2 self-end flex items-center flex-row" v-if="message.type === 1">
    <DeleteOutlined class="pr-1 cursor-pointer self-end !text-gray-400" @click="deleteIt(message)" />
    <div class="p-1 rounded-t-lg rounded-l-lg bg-blue-300 shadow text-sm min-w-10 max-w-500">
      <pre class="max-w-120 m-2 whitespace-pre-wrap">{{ message.msg }}</pre>
    </div>
  </div>

  <!-- AI 消息：左对齐、灰色气泡，使用 Markdown 渲染（代码/粗体/列表/表格...） -->
  <div class="my-2 self-start flex items-center" v-else>
    <div class="p-1 rounded-t-lg rounded-r-lg bg-gray-100 text-black shadow text-sm min-w-10">
      <div class="max-w-120 m-2">
        <MarkdownRenderer :source="message.msg" />
      </div>
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
