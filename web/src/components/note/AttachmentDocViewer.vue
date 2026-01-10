<template>
  <div class="doc-viewer">
    <div class="doc-toolbar">
      <div class="toolbar-left">
        <FileTextIcon class="toolbar-icon" />
        <span class="toolbar-label">文档预览</span>
      </div>
      <div class="toolbar-right">
        <button class="toolbar-btn" type="button" @click="refresh">
          <RefreshCcwIcon class="toolbar-icon" />
        </button>
        <button class="toolbar-btn" type="button" @click="openInNewTab">
          <Maximize2Icon class="toolbar-icon" />
        </button>
      </div>
    </div>
    <div class="doc-body">
      <div ref="container" class="doc-canvas"></div>
      <div v-if="loading" class="overlay">
        <a-spin />
      </div>
      <div v-else-if="error" class="overlay overlay--error">{{ error }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { message } from 'ant-design-vue'
import { nextTick, ref, watch } from 'vue'
import { FileTextIcon, Maximize2Icon, RefreshCcwIcon } from 'lucide-vue-next'
import { renderAsync } from 'docx-preview'

const props = defineProps<{
  source: string
}>()

const loading = ref(true)
const error = ref<string | null>(null)
const container = ref<HTMLElement | null>(null)

const renderDoc = async () => {
  loading.value = true
  error.value = null
  await nextTick()
  if (!container.value) {
    loading.value = false
    return
  }
  try {
    const response = await fetch(props.source)
    if (!response.ok) throw new Error('文档加载失败')
    const buffer = await response.arrayBuffer()
    if (!container.value) return
    container.value.innerHTML = ''
    await renderAsync(buffer, container.value, undefined, {
      className: 'docx',
      inWrapper: true,
    })
  } catch (err: any) {
    const errMsg = err?.message || '文档预览失败'
    error.value = errMsg
    console.error('Failed to render document preview:', err)
    message.error(errMsg)
  } finally {
    loading.value = false
  }
}

const refresh = () => {
  renderDoc()
}

const openInNewTab = () => {
  window.open(props.source, '_blank', 'noopener')
}

watch(
  () => props.source,
  () => {
    renderDoc()
  },
  { immediate: true },
)
</script>

<style scoped>
.doc-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
}

.doc-toolbar {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid #edf0f5;
  gap: 10px;
}

.toolbar-left {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.toolbar-right {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.toolbar-icon {
  width: 16px;
  height: 16px;
  color: #1677ff;
}

.toolbar-label {
  font-weight: 600;
  color: #0f172a;
}

.toolbar-btn {
  height: 32px;
  min-width: 32px;
  padding: 0 10px;
  border-radius: 10px;
  border: 1px solid #e5e9f2;
  background: #f6f8fb;
  color: #1f2937;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toolbar-btn:hover {
  background: #eef4ff;
  color: #1677ff;
  border-color: #d7e5ff;
}

.doc-body {
  position: relative;
  flex: 1;
  min-height: 0;
  padding: 14px;
  background: linear-gradient(180deg, #f8fafc 0%, #f3f6fb 100%);
  overflow: auto;
}

.doc-canvas {
  position: relative;
  min-height: 100%;
  max-width: 960px;
  margin: 0 auto;
  background: #fff;
  padding: 12px;
  border-radius: 12px;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

.doc-canvas :deep(.docx) {
  padding: 0;
}

.overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
}

.overlay--error {
  color: #b91c1c;
  font-weight: 600;
}
</style>
