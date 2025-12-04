<!-- src/components/message.vue -->
<script setup lang="ts">
import type { TMessage, ResponseUIState } from '@/types'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import { ref, computed } from 'vue'
import { message as antdMessage } from 'ant-design-vue'
import { Copy, ThumbsUp, ThumbsDown, Volume2, FilePlus2, Loader2 } from 'lucide-vue-next'
import { generateNoteTitle } from '@/services/api'
import { useNotebookStore } from '@/composables/useNotes'

type CitationPayload = {
  fileId: string
  filename?: string
  index?: number
  startIndex?: number
  endIndex?: number
  quote?: string
  label?: number
}

const parseNumber = (val: any): number | undefined => {
  if (typeof val === 'number' && Number.isFinite(val)) return val
  if (typeof val === 'string' && val.trim() !== '' && !Number.isNaN(Number(val))) return Number(val)
  return undefined
}

const props = defineProps<{ message: TMessage }>()
const emit = defineEmits<{
  (e: 'open-citation', payload: CitationPayload): void
}>()

const citationsRaw = computed(() =>
  Array.isArray(props.message.meta?.citations) ? props.message.meta.citations : [],
)
const citations = computed(() =>
  citationsRaw.value
    .map((c: any) => ({
      fileId: String(c.fileId || c.file_id || ''),
      filename: typeof c.filename === 'string' ? c.filename : undefined,
      index: parseNumber(c.index ?? c.annotation_index),
      startIndex: parseNumber(c.startIndex ?? c.start_index ?? c.index),
      endIndex: parseNumber(c.endIndex ?? c.end_index),
      quote:
        typeof c.quote === 'string'
          ? c.quote
          : typeof c.text === 'string'
          ? c.text
          : undefined,
      label: parseNumber(c.label),
    }))
    .filter(c => c.fileId),
)

const inlineCitations = computed<CitationPayload[]>(() => {
  const fileOrder = new Map<string, number>()
  let nextLabel = 1

  return citations.value.map((cit, idx) => {
    const label = (() => {
      const provided = typeof cit.label === 'number' && cit.label > 0 ? cit.label : null
      if (provided) {
        if (provided >= nextLabel) nextLabel = provided + 1
        const key = cit.fileId || `__missing-${idx}`
        if (!fileOrder.has(key)) fileOrder.set(key, provided)
        return provided
      }
      const key = cit.fileId || `__missing-${idx}`
      if (!fileOrder.has(key)) {
        fileOrder.set(key, nextLabel++)
      }
      return fileOrder.get(key) ?? idx + 1
    })()
    return { ...cit, label }
  })
})

const uiState = computed<ResponseUIState>(() => {
  const raw = props.message.meta?.uiState as Partial<ResponseUIState> | undefined
  return {
    phase: raw?.phase ?? 'waiting',
    statusKey: typeof raw?.statusKey === 'string' ? raw.statusKey : null,
    statusText: typeof raw?.statusText === 'string' ? raw.statusText : null,
    hasTextStarted: Boolean(raw?.hasTextStarted),
  }
})

const isBeforeFirstText = computed(() => !uiState.value.hasTextStarted && !props.message.msg)
const showWaitingSpinner = computed(
  () => isBeforeFirstText.value && uiState.value.phase === 'waiting' && !uiState.value.statusText,
)
const shouldShowStatusText = computed(
  () => isBeforeFirstText.value && !!uiState.value.statusText,
)

const handleCitationOpen = (payload: CitationPayload) => {
  emit('open-citation', payload)
}

/* 文件类型判断 + 对应的 SVG 图标 */
function isImageType(t?: string) { return typeof t === 'string' && t.startsWith('image/') }
function isPdfType(t?: string)   { return t === 'application/pdf' }
function isDocType(t?: string)   { 
  return t === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
    || t === 'application/msword' 
}
function isExcelType(t?: string) { 
  return t === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
    || t === 'application/vnd.ms-excel' 
}
function isPptType(t?: string)   { 
  return t === 'application/vnd.openxmlformats-officedocument.presentationml.presentation' 
    || t === 'application/vnd.ms-powerpoint' 
}

// 根据文件类型返回 SVG 图标
function getFileIcon(type?: string) {
  if (isImageType(type)) {
    return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
      <circle cx="8.5" cy="8.5" r="1.5"/>
      <polyline points="21 15 16 10 5 21"/>
    </svg>`
  }
  if (isPdfType(type)) {
    return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/>
      <polyline points="10 9 9 9 8 9"/>
    </svg>`
  }
  if (isDocType(type)) {
    return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/>
    </svg>`
  }
  if (isExcelType(type)) {
    return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <rect x="8" y="12" width="8" height="8"/>
      <line x1="12" y1="12" x2="12" y2="20"/>
    </svg>`
  }
  if (isPptType(type)) {
    return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <rect x="8" y="12" width="8" height="6"/>
    </svg>`
  }
  // 默认文件图标
  return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
    <polyline points="13 2 13 9 20 9"/>
  </svg>`
}

// 简洁的文件图标（用于用户上传的文件卡片）- 类似 Gemini 风格
function getSimpleFileIcon(type?: string) {
  const baseColor = '#5f6368' // Google 灰色
  
  if (isPdfType(type)) {
    // PDF 图标 - 红色
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" fill="#EA4335" stroke="#EA4335" stroke-width="2" stroke-linejoin="round"/>
      <path d="M14 2v6h6" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <text x="12" y="17" text-anchor="middle" fill="#fff" font-size="6" font-weight="600">PDF</text>
    </svg>`
  }
  
  if (isDocType(type)) {
    // Word 图标 - 蓝色
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" fill="#4285F4" stroke="#4285F4" stroke-width="2" stroke-linejoin="round"/>
      <path d="M14 2v6h6" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M8 14h8M8 17h5" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`
  }
  
  if (isExcelType(type)) {
    // Excel 图标 - 绿色
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" fill="#0F9D58" stroke="#0F9D58" stroke-width="2" stroke-linejoin="round"/>
      <path d="M14 2v6h6" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <rect x="8" y="13" width="8" height="6" stroke="#fff" stroke-width="1.5" fill="none"/>
      <line x1="12" y1="13" x2="12" y2="19" stroke="#fff" stroke-width="1.5"/>
    </svg>`
  }
  
  if (isPptType(type)) {
    // PPT 图标 - 橙色
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" fill="#F4B400" stroke="#F4B400" stroke-width="2" stroke-linejoin="round"/>
      <path d="M14 2v6h6" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <rect x="9" y="13" width="6" height="5" stroke="#fff" stroke-width="1.5" fill="none"/>
    </svg>`
  }
  
  if (isImageType(type)) {
    // 图片图标 - 紫色
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" fill="#9334E9" stroke="#9334E9" stroke-width="2" stroke-linejoin="round"/>
      <path d="M14 2v6h6" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="10" cy="13" r="1.5" fill="#fff"/>
      <path d="M8 18l3-3 2 2 3-4" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`
  }
  
  if (type?.includes('audio') || type?.includes('mp3')) {
    // 音频图标 - 粉色
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" fill="#EC4899" stroke="#EC4899" stroke-width="2" stroke-linejoin="round"/>
      <path d="M14 2v6h6" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="10" cy="16" r="1.5" stroke="#fff" stroke-width="1.2" fill="none"/>
      <path d="M11.5 16v-4l3-0.5v4" stroke="#fff" stroke-width="1.2" stroke-linecap="round"/>
    </svg>`
  }
  
  // 默认文件图标 - 灰色
  return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" fill="#5f6368" stroke="#5f6368" stroke-width="2" stroke-linejoin="round"/>
    <path d="M14 2v6h6" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`
}


/** 图片 Lightbox*/
const lightboxVisible = ref(false)
const lightboxSrc = ref<string>('')
function openLightbox(src: string) { lightboxSrc.value = src; lightboxVisible.value = true }
function closeLightbox() { lightboxVisible.value = false; lightboxSrc.value = '' }

const notebookStore = useNotebookStore()
const isCopying = ref(false)
const isCreatingNote = ref(false)

const copyMarkdown = async () => {
  if (isCopying.value) return
  const text = (props.message.msg || '').trim()
  if (!text) {
    antdMessage.warning('暂无可复制的文本')
    return
  }
  isCopying.value = true
  try {
    if (navigator.clipboard?.write && typeof ClipboardItem !== 'undefined') {
      const markdownBlob = new Blob([text], { type: 'text/markdown' })
      const plainBlob = new Blob([text], { type: 'text/plain' })
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/markdown': markdownBlob,
          'text/plain': plainBlob,
        }),
      ])
    } else if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      throw new Error('当前环境不支持复制')
    }
    antdMessage.success('已复制 Markdown')
  } catch (err: any) {
    const msg = err?.message || '复制失败，请稍后再试'
    antdMessage.error(msg)
  } finally {
    isCopying.value = false
  }
}

const createNoteFromReply = async () => {
  if (isCreatingNote.value) return
  const text = (props.message.msg || '').trim()
  if (!text) {
    antdMessage.warning('暂无可保存的回复内容')
    return
  }
  const activeNotebookId = notebookStore.activeNotebook.value?.id
  if (!activeNotebookId) {
    antdMessage.warning('请先选择一个笔记本再保存笔记')
    return
  }
  isCreatingNote.value = true
  const pendingId = notebookStore.addPendingNotePlaceholder('AI 笔记生成中…')
  try {
    const title = (await generateNoteTitle(text)) || 'AI 生成笔记'
    if (pendingId) notebookStore.updatePendingNotePlaceholder(pendingId, title)
    const created = await notebookStore.addNoteToActiveNotebook(
      { title, content: text },
      {
        successMessage: `已创建并保存到笔记：《${title}》`,
        suppressErrorToast: true,
      },
    )
    if (!created) {
      antdMessage.error('未能创建笔记，请稍后再试')
    }
  } catch (err: any) {
    const msg = err?.message || '创建笔记失败，请稍后再试'
    antdMessage.error(msg)
  } finally {
    if (pendingId) notebookStore.removePendingNotePlaceholder(pendingId)
    isCreatingNote.value = false
  }
}
</script>

<template>
  <div class="message-row" :class="props.message.type === 1 ? 'send' : 'replay'">
    <!-- 用户消息 -->
    <template v-if="props.message.type === 1">
      <div class="user-message-container">
        <!-- 文件附件 - 显示在文本上方 -->
        <div v-if="props.message.files?.length" class="user-files">
          <div 
            v-for="(f,i) in props.message.files" 
            :key="'file-'+i"
            class="user-file-card" 
            :title="f.name"
          >
            <div class="file-icon-simple" v-html="getSimpleFileIcon(f.type)"></div>
            <span class="file-name-display">{{ f.name }}</span>
          </div>
        </div>

        <!-- 图片附件 - 显示在文本上方 -->
        <div v-if="props.message.images?.length" class="user-imgs">
          <img
            v-for="(src,i) in props.message.images"
            :key="'img-'+i"
            :src="src"
            alt="image"
            @click="openLightbox(src)"
            class="clickable"
          />
        </div>

        <!-- 文本消息气泡 - 显示在最下方 -->
        <div v-if="props.message.msg" class="bubble user">
          <div class="text">{{ props.message.msg }}</div>
        </div>
      </div>
    </template>

    <!-- AI 消息 -->
    <template v-else>
      <div class="bubble ai">
        <div v-if="showWaitingSpinner || shouldShowStatusText" class="ai-status">
          <span v-if="showWaitingSpinner" class="loader-dots"><span></span><span></span><span></span></span>
          <span v-if="shouldShowStatusText" class="ai-status__text">{{ uiState.statusText }}</span>
        </div>
        <div v-else class="md-wrap">
          <MarkdownRenderer :source="props.message.msg" :citations="inlineCitations" @citation-click="handleCitationOpen" />
        </div>

        <!-- 图片（dataURL）+ 点击放大 -->
        <div v-if="props.message.images?.length" class="ai-imgs">
          <img
            v-for="(src,i) in props.message.images"
            :key="'aiimg-'+i"
            :src="src"
            alt="image"
            @click="openLightbox(src)"
            class="clickable"
          />
        </div>

        <!-- 文件（仅展示，不提供下载） -->
        <div v-if="props.message.files?.length" class="ai-files">
          <div 
            v-for="(f,i) in props.message.files" 
            :key="'aifile-'+i"
            class="pill" 
            :title="f.name"
          >
            <span class="file-icon" v-html="getFileIcon(f.type)"></span>
            <span class="file-name">{{ f.name }}</span>
          </div>
        </div>

        <div v-if="!showWaitingSpinner && !shouldShowStatusText" class="ai-actions">
          <button
            class="action-btn"
            type="button"
            :disabled="isCopying"
            title="复制 Markdown 到剪贴板"
            aria-label="复制回复"
            @click="copyMarkdown"
          >
            <Copy class="action-icon" :size="18" />
          </button>
          <button class="action-btn" type="button" disabled title="点赞（即将上线）" aria-label="点赞">
            <ThumbsUp class="action-icon" :size="18" />
          </button>
          <button class="action-btn" type="button" disabled title="点踩（即将上线）" aria-label="点踩">
            <ThumbsDown class="action-icon" :size="18" />
          </button>
          <button class="action-btn" type="button" disabled title="朗读（即将上线）" aria-label="朗读">
            <Volume2 class="action-icon" :size="18" />
          </button>
          <button
            class="action-btn primary"
            type="button"
            :class="{ loading: isCreatingNote }"
            :disabled="isCreatingNote"
            :title="isCreatingNote ? '正在创建笔记…' : '创建并添加至 Note'"
            aria-label="创建并添加至 Note"
            @click="createNoteFromReply"
          >
            <Loader2 v-if="isCreatingNote" class="action-icon spin" :size="18" />
            <FilePlus2 v-else class="action-icon" :size="18" />
          </button>
        </div>
      </div>
    </template>
  </div>

  <!-- Lightbox -->
  <teleport to="body">
    <div v-if="lightboxVisible" class="lightbox" @click.self="closeLightbox">
      <button class="lightbox-close" @click="closeLightbox">✕</button>
      <img :src="lightboxSrc" alt="preview" />
    </div>
  </teleport>
</template>

<style scoped>
/* 消息行布局 - 增加垂直间距 */
.message-row { 
  display: flex; 
  width: 100%; 
  min-width: 0; 
  margin: 0;
}

/* 用户消息 - 右对齐 */
.message-row.send { 
  justify-content: flex-end; 
  padding: 8px 0;
}

/* AI 消息 - 居中全宽 ChatGPT 风格 */
.message-row.replay { 
  justify-content: center;
  background: #fff;
  padding: 16px 0;
  margin: 0 -14px; /* 抵消父容器的 padding */
}

/* 气泡样式 - 参考 ChatGPT/Gemini 设计 */
.bubble {
  width: 100%;
  max-width: 100%;
  padding: 0;
  /* 优化中英文混排字体栈 */
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Source Han Sans SC', 'Noto Sans CJK SC', sans-serif;
  font-size: 18px;
  font-weight: 400;
  line-height: 1.8;
  letter-spacing: 0.02em;
  word-break: break-word;
  overflow-wrap: anywhere;
  box-sizing: border-box;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 用户消息 - 保持原有的气泡样式 */
.bubble.user { 
  font-size: 16px;
  width: fit-content;
  max-width: 70%;
  padding: 15px 18px;
  border-radius: 18px;
  background: linear-gradient(135deg, #e3f2fd 0%, #dbeafe 100%);
  border: 1px solid rgba(59, 130, 246, 0.15);
  color: #1e293b;
  box-shadow: 0 1px 2px rgba(59, 130, 246, 0.08);
  transition: box-shadow 0.2s ease;
}

/* AI 消息 - ChatGPT 风格：无边框、无背景、全宽 */
.bubble.ai { 
  font-size: 18px;
  width: 100%;
  max-width: 48rem; /* 限制最大宽度，类似 ChatGPT 的 max-w-3xl */
  padding: 0 16px;
  background: transparent;
  border: none;
  color: #1f2937;
  box-shadow: none;
}

/* AI 状态指示器 */
.ai-status { 
  color: #64748b; 
  font-size: 14px; 
  display: flex; 
  gap: 8px; 
  align-items: center; 
  padding: 2px 0;
}

.ai-status__text {
  display: inline-flex;
  align-items: center;
  color: #94a3b8;
  background: linear-gradient(
    120deg,
    #94a3b8 25%,
    #e2e8f0 45%,
    #f8fafc 50%,
    #e2e8f0 55%,
    #94a3b8 75%
  );
  background-size: 200% 100%;
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: statusShimmer 1.6s ease-in-out infinite;
}

.ai-status .loader-dots { display: inline-flex; gap: 5px; }
.ai-status .loader-dots span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #64748b;
  animation: loaderDots 1.2s infinite ease-in-out;
}
.ai-status .loader-dots span:nth-child(2) { animation-delay: 0.15s; }
.ai-status .loader-dots span:nth-child(3) { animation-delay: 0.3s; }

@keyframes loaderDots {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

@keyframes statusShimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 用户消息容器 */
.user-message-container {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  width: 100%;
}

/* 文本样式 - 统一用户和AI消息的样式 */
.text { 
  /* font-size: 18px; */
  margin: 0; 
  white-space: pre-wrap; 
  word-break: break-word; 
  font-weight: 400;
  line-height: 1.8;
}

/* Markdown 内容样式 */
.md-wrap { 
  max-width: 100%; 
  min-width: 0; 
  overflow-wrap: anywhere; 
}

.md-wrap :deep(.prose) { 
  max-width: none; 
  word-break: break-word; 
  overflow-wrap: anywhere; 
  font-size: 18px; 
  font-weight: 400;
  line-height: 1.8; 
  color: #1f2937;
  font-family: inherit;
}

/* 段落间距优化 - 更大的段间距 */
.md-wrap :deep(p) {
  margin: 0.85em 0;
}

.md-wrap :deep(p:first-child) {
  margin-top: 0;
}

.md-wrap :deep(p:last-child) {
  margin-bottom: 0;
}

/* 列表间距优化 - 更舒适的列表展示 */
.md-wrap :deep(ul),
.md-wrap :deep(ol) {
  margin: 0.85em 0;
  padding-left: 2em;
  line-height: 1.9;
}

.md-wrap :deep(li) {
  margin: 0.5em 0;
}

/* 代码块样式 */
.md-wrap :deep(code) {
  font-family: 'SF Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
}

.md-wrap :deep(pre) {
  margin: 1em 0;
  border-radius: 8px;
}

/* 强调文本样式 */
.md-wrap :deep(strong),
.md-wrap :deep(b) {
  font-weight: 600;
  color: #111827;
}

.md-wrap :deep(em),
.md-wrap :deep(i) {
  font-style: italic;
}

/* 标题样式 - 更粗更醒目 */
.md-wrap :deep(h1),
.md-wrap :deep(h2),
.md-wrap :deep(h3),
.md-wrap :deep(h4),
.md-wrap :deep(h5),
.md-wrap :deep(h6) {
  margin-top: 1.5em;
  margin-bottom: 0.6em;
  line-height: 1.4;
  font-weight: 600;
  color: #111827;
}

.md-wrap :deep(h1) {
  font-size: 1.75em;
}

.md-wrap :deep(h2) {
  font-size: 1.5em;
}

.md-wrap :deep(h3) {
  font-size: 1.3em;
}

.md-wrap :deep(h1:first-child),
.md-wrap :deep(h2:first-child),
.md-wrap :deep(h3:first-child) {
  margin-top: 0;
}

/* 表格样式 */
.md-wrap :deep(table) { 
  display: block; 
  width: 100%; 
  overflow-x: auto; 
  margin: 1em 0;
  border-radius: 6px;
}

.md-wrap :deep(td), 
.md-wrap :deep(th) { 
  word-break: break-word; 
  padding: 8px 12px;
}

/* 用户上传的图片 */
.user-imgs { 
  display: flex; 
  gap: 10px; 
  flex-wrap: wrap; 
}

.user-imgs img {
  width: 200px;
  max-width: min(280px, 100%);
  height: auto;
  border-radius: 12px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  box-shadow: 0 2px 6px rgba(59, 130, 246, 0.12);
  cursor: zoom-in;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.user-imgs img:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.18);
}

/* 用户上传的文件 - 简洁的 Gemini 风格 */
.user-files {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.user-file-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
  max-width: 320px;
  transition: all 0.2s ease;
  cursor: default;
}

.user-file-card:hover {
  background: #eeeeee;
  border-color: #d0d0d0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.12);
}

.file-icon-simple {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-name-display {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  font-weight: 400;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* AI 消息的图片 */
.ai-imgs { 
  display: flex; 
  gap: 12px; 
  flex-wrap: wrap; 
  margin-top: 14px; 
}

.ai-imgs img {
  width: 280px;
  max-width: min(360px, 100%);
  height: auto;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  cursor: zoom-in;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.ai-imgs img:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

/* AI 消息的文件附件 - 更现代的设计 + SVG 图标 */
.ai-files { 
  display: flex; 
  gap: 10px; 
  flex-wrap: wrap; 
  margin-top: 12px; 
}

.pill { 
  display: inline-flex; 
  align-items: center; 
  gap: 8px; 
  padding: 9px 14px; 
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%);
  color: #374151;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.2s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  cursor: default;
}

.pill:hover {
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  border-color: #d1d5db;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.file-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  flex-shrink: 0;
}

.pill:hover .file-icon {
  color: #374151;
}

.file-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.ai-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding-top: 2px;
  color: #6b7280;
}

.action-btn {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.16s ease;
}

.action-btn:hover:not(:disabled) {
  border-color: #d5dbe8;
  color: #111827;
  background: #f8fafc;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}

.action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.action-btn.primary {
  border-color: #e5e7eb;
  color: #6b7280;
  background: #fff;
}

.action-btn.primary:hover:not(:disabled) {
  background: #f8fafc;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}

.action-btn.primary.loading {
  cursor: wait;
  opacity: 0.8;
}

.action-icon {
  display: block;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Lightbox */
.lightbox {
  position: fixed; 
  inset: 0; 
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  display: flex; 
  align-items: center; 
  justify-content: center; 
  z-index: 9999;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.lightbox img { 
  max-width: 92vw; 
  max-height: 88vh; 
  border-radius: 12px; 
  background: #fff;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
}

.lightbox-close {
  position: absolute; 
  top: 28px; 
  right: 28px;
  width: 40px; 
  height: 40px; 
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.1);
  cursor: pointer;
  font-size: 18px;
  font-weight: 300;
  color: #374151;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.lightbox-close:hover {
  background: rgba(255, 255, 255, 1);
  transform: scale(1.05);
  color: #1f2937;
}
</style>
