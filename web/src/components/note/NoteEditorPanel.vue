<template>
  <div class="note-editor-panel">
    <!-- 标题区：独占一行 -->
    <div class="title-row">
      <div class="title-input">
        <span class="field-label">笔记标题</span>
        <a-input v-model:value="titleValue" placeholder="输入笔记标题" />
      </div>
    </div>

    <!-- 工具栏：按钮全部靠左排列 -->
    <div class="editor-toolbar">
      <a-badge v-if="isGenerating" status="processing" text="AI 正在生成..." />

      <a-button
        type="default"
        size="small"
        @click="showAISuggestions = !showAISuggestions"
      >
        <SparklesIcon class="icon" />
        {{ showAISuggestions ? '隐藏建议' : 'AI 建议' }}
      </a-button>

      <a-divider type="vertical" class="divider" />

      <a-button
        v-if="showSyncButton"
        size="small"
        type="link"
        @click="emit('request-sync')"
      >
        <RefreshCcwIcon class="icon" />
        同步实时转写
      </a-button>

      <a-button size="small" @click="handleShare">
        <Share2Icon class="icon" />
        分享
      </a-button>

      <a-button size="small" @click="handleExport">
        <DownloadIcon class="icon" />
        导出
      </a-button>

      <a-button type="primary" size="small" @click="handleSave">
        <SaveIcon class="icon" />
        保存
      </a-button>

      <a-button
        v-if="showFullscreenToggle"
        size="small"
        @click="$emit('toggle-fullscreen')"
      >
        <component
          :is="isFullscreenComputed ? Minimize2Icon : Maximize2Icon"
          class="icon"
        />
        {{ isFullscreenComputed ? '退出全屏' : '全屏编辑' }}
      </a-button>
    </div>

    <!-- 编辑器区域 -->
    <a-card class="editor-card" :bordered="false">
      <template #title>
        <div class="card-title">AI笔记</div>
      </template>

      <RichTextEditor
        v-model="noteContent"
        placeholder="AI 生成的内容会出现在这里，也可以直接记录课堂笔记..."
        @update:modelValue="handleModelChange"
      />
    </a-card>

    <!-- AI 建议折叠区 -->
    <a-collapse v-model:activeKey="aiPanelKeys" ghost>
      <a-collapse-panel key="ai" header="AI 建议">
        <div class="ai-panel">
          <a-textarea
            v-model:value="suggestions"
            placeholder="例如：『帮我整理成提纲』、『补充一个示例』、『用 bullet list 展示重点』"
            :auto-size="{ minRows: 3, maxRows: 5 }"
          />
          <a-button
            type="primary"
            block
            :loading="isApplyingSuggestions"
            :disabled="!suggestions.trim()"
            @click="handleApplySuggestions"
          >
            <SparklesIcon class="icon" /> 应用建议
          </a-button>
        </div>
      </a-collapse-panel>
    </a-collapse>
  </div>
</template>

<script setup lang="ts">
import { message } from 'ant-design-vue'
import { computed, ref, watch } from 'vue'
import {
  DownloadIcon,
  Maximize2Icon,
  Minimize2Icon,
  RefreshCcwIcon,
  SaveIcon,
  Share2Icon,
  SparklesIcon,
} from 'lucide-vue-next'
import RichTextEditor from './RichTextEditor.vue'
import type { NoteItem } from '@/types/notes'

const props = defineProps<{
  notes: NoteItem[]
  isGenerating: boolean
  isFullscreen?: boolean
  showSyncButton?: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle-fullscreen'): void
  (e: 'user-edit'): void
  (e: 'request-sync'): void
  (e: 'change', payload: { title: string; content: string }): void
  (e: 'save', payload: { title: string; content: string }): void
}>()

const noteTitle = ref('未命名笔记')
const noteContent = ref('')
const suggestions = ref('')
const isApplyingSuggestions = ref(false)
const userEdited = ref(false)
const aiPanelKeys = ref<string[]>([])
const currentNoteId = ref<string | null>(null)

const showAISuggestions = computed({
  get: () => aiPanelKeys.value.includes('ai'),
  set: (v: boolean) => (aiPanelKeys.value = v ? ['ai'] : []),
})

const showFullscreenToggle = computed(() => typeof props.isFullscreen === 'boolean')
const isFullscreenComputed = computed(() => props.isFullscreen === true)

const emitChange = () => emit('change', { title: noteTitle.value, content: noteContent.value })

watch(
  () => props.notes,
  (newNotes) => {
    const first = newNotes[0]
    if (!first) {
      noteTitle.value = '未命名笔记'
      noteContent.value = ''
      currentNoteId.value = null
      userEdited.value = false
      emitChange()
      return
    }

    if (currentNoteId.value !== first.id || !userEdited.value) {
      currentNoteId.value = first.id
      noteTitle.value = first.title || '未命名笔记'
      noteContent.value = first.content || ''
      userEdited.value = false
      emitChange()
    }
  },
  { immediate: true, deep: true },
)

const handleModelChange = () => {
  userEdited.value = true
  emit('user-edit')
  emitChange()
}

const titleValue = computed({
  get: () => noteTitle.value,
  set: (v: string) => {
    userEdited.value = true
    emit('user-edit')
    noteTitle.value = v
    emitChange()
  },
})

const handleApplySuggestions = () => {
  if (!suggestions.value.trim()) return message.error('请先输入想要调整的方向')
  isApplyingSuggestions.value = true
  setTimeout(() => {
    const addition = `<p><em>✨ AI 已根据建议调整：${suggestions.value}</em></p>`
    noteContent.value = `${noteContent.value}<br>${addition}`
    userEdited.value = true
    suggestions.value = ''
    isApplyingSuggestions.value = false
    message.success('AI 已应用你的建议')
    emit('user-edit')
    emitChange()
  }, 1000)
}

const handleSave = () => {
  emit('save', { title: noteTitle.value, content: noteContent.value })
  userEdited.value = false
}
const handleExport = () => {
  const blob = new Blob([noteContent.value], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${noteTitle.value || 'notes'}.html`
  a.click()
  URL.revokeObjectURL(url)
  message.success('已导出 HTML 文件')
}
const handleShare = () => message.info('分享功能可以接入团队工作区或外链分享')
</script>

<style scoped>
.note-editor-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

/* 标题区 */
.title-row {
  display: flex;
  align-items: flex-end;
  padding: 8px 0;
}

.title-input {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.45);
}

/* 工具栏样式 */
.editor-toolbar {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(5, 5, 5, 0.06);
  flex-wrap: wrap;
}

.icon {
  width: 14px;
  height: 14px;
  margin-right: 4px;
}

.divider {
  height: 18px;
}

/* 卡片 */
.editor-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-radius: 22px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
  overflow: hidden;
  background: #fff;
}

.editor-card :deep(.ant-card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.card-title {
  font-weight: 600;
}

.card-subtitle {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.45);
}

/* AI 折叠区 */
.ai-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
