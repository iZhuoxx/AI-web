<script setup lang="ts">
import { message as messageTip } from 'ant-design-vue'
import useMessages from '@/composables/messages'
import { CopyOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { useClipboard } from '@vueuse/core'
import { TMessage } from '@/types'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

const messages = useMessages()
const { copy } = useClipboard({})

const props = defineProps<{ message: TMessage }>()

</script>

<template>
  <!-- 一条消息 -->
  <div class="message-row" :class="props.message.type === 1 ? 'send' : 'replay'">
    <!-- 用户消息（小气泡） -->
    <template v-if="props.message.type === 1">
      <div class="bubble user">
        <pre class="text">{{ props.message.msg }}</pre>
      </div>
    </template>

    <!-- AI 消息（大气泡，支持 Markdown） -->
    <template v-else>
      <div class="bubble ai">
        <div class="md-wrap">
          <MarkdownRenderer :source="props.message.msg" />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.message-row {
  display: flex;
  align-items: flex-start;
  width: 100%;
  gap: 8px;
  margin: 8px 0;
}
.message-row.send   { justify-content: flex-end; }
.message-row.replay { justify-content: flex-start; }

/* === 气泡 === */
.bubble {
  width: fit-content;
  border-radius: 12px;
  border: 1px solid var(--border-muted, #e5e7eb);
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
  padding: 10px 12px;
  font-size: 14px;
  line-height: 1.6;
}

.bubble.user { 
  background: #e7f3ff; 
  border-color: #d6e8ff; 
  max-width: 60%;         
}

.bubble.ai   { 
  background: #fff; 
  border-color: #e5e7eb; 
  max-width: 90%;        
}

/* 文本/Markdown */
.text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.md-wrap :deep(.prose) { max-width: none; }

/* 操作图标 */
.op {
  align-self: flex-end;
  cursor: pointer;
  color: #9ca3af;
  transition: color .15s ease, transform .15s ease;
}
.op:hover { color: #111827; transform: translateY(-1px); }
.op + .op { margin-left: 6px; }
</style>
