<script setup lang="ts">
import {
  LoadingOutlined,
  PictureOutlined, CloseOutlined, PaperClipOutlined,
  SendOutlined, PauseCircleOutlined,
  AudioOutlined, AudioFilled,
  PlusCircleOutlined
} from '@ant-design/icons-vue'

import Message from './components/message.vue'

import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed, watch } from 'vue'
import useMessages from '@/composables/messages'
import { useChat } from '@/composables/useChat'
import { useUploads } from '@/composables/useUploads'
import { useSpeechToText } from '@/composables/useSpeechToText'
import useSetting from '@/composables/setting'
import { MODEL_OPTIONS } from '@/constants/models'

const messages = useMessages()
const { loadding, send, stop } = useChat()

const {
  imageFiles, imagePreviews, genericFiles, dragOver,
  onPickImages, addGenericFiles, removeGenericFile,
  onPaste, onDragOver, onDragLeave, onDrop,
  ensureUploads, ensureAudioTranscriptions, fileToDataURL, removeImage, resetAll,
  filesForChat,
  addImages,                
} = useUploads()

const setting = useSetting()
const speech = useSpeechToText()
const isAudioRecording = speech.isRecording
const isAudioTranscribing = speech.isTranscribing
const canUseMicrophone = speech.canRecord
const lastTranscript = speech.lastTranscript
const audioErrorMessage = speech.errorMessage
const startAudioRecording = speech.startRecording
const stopRecordingAndTranscribe = speech.stopRecordingAndTranscribe
const cancelAudioRecording = speech.cancelRecording

const modelOptions = MODEL_OPTIONS
const selectedModel = computed({
  get: () => setting.value.model,
  set: (val: string) => {
    if (val) {
      setting.value.model = val
    }
  },
})

const audioStatusMessage = ref('')
const transcriptPreview = computed(() => {
  const preview = lastTranscript.value.trim()
  if (!preview) return ''
  return preview.length > 160 ? `${preview.slice(0, 160)}…` : preview
})
const audioErrorText = computed(() => audioErrorMessage.value || '')
const hasPendingUploads = computed(() => genericFiles.value.some(it => it.status === 'pending'))

const chatMessages = messages.messages
const hasMessages = computed(() => chatMessages.value.length > 0)

const handlePaste = (event: ClipboardEvent) => {
  void onPaste(event)
}

const state = reactive({ message: '' })
const hasPayload = computed(() =>
  state.message.trim().length > 0 || imageFiles.value.length > 0 || genericFiles.value.length > 0
)
const canSend = computed(() => hasPayload.value && !hasPendingUploads.value)

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const MAX_TEXTAREA_H = 240
const autoResize = () => {
  const el = textareaRef.value; if (!el) return
  el.style.height = '0px'
  const h = Math.min(el.scrollHeight, MAX_TEXTAREA_H)
  el.style.height = h + 'px'
  el.style.overflowY = el.scrollHeight > MAX_TEXTAREA_H ? 'auto' : 'hidden'
}

const setAudioStatus = (message: string) => {
  audioStatusMessage.value = message
}

const clearAudioError = () => {
  audioErrorMessage.value = null
}

const appendTranscriptToComposer = async (text: string) => {
  const trimmed = text.trim()
  if (!trimmed) return
  if (!state.message) {
    state.message = trimmed
  } else {
    const needsSpace = !state.message.endsWith('\n') && !state.message.endsWith(' ')
    state.message = `${state.message}${needsSpace ? ' ' : ''}${trimmed}`
  }
  await nextTick()
  autoResize()
}

watch(hasPendingUploads, (pending) => {
  if (pending) {
    if (!audioStatusMessage.value) {
      setAudioStatus('音频正在转写中…')
    }
  } else if (!isAudioRecording.value && !isAudioTranscribing.value) {
    if (!audioErrorText.value) {
      audioStatusMessage.value = ''
    }
  }
})

const handleTranscript = async (text: string, label?: string) => {
  const cleaned = text.trim()
  if (!cleaned) {
    audioErrorMessage.value = '语音识别结果为空，请重试'
    setAudioStatus('')
    return
  }
  await appendTranscriptToComposer(cleaned)
  setAudioStatus('')
  lastTranscript.value = ''
  audioErrorMessage.value = null
}

function isFileDrag(e: DragEvent) {
  const types = e.dataTransfer?.types
  return !!types && Array.from(types).includes('Files')
}

function globalDragOver(e: DragEvent) {
  if (!isFileDrag(e)) return
  e.preventDefault()
}

function globalDrop(e: DragEvent) {
  if (!isFileDrag(e)) return
  e.preventDefault()

  const target = e.target as HTMLElement | null
  if (target && target.closest?.('.composer')) return

  const files = Array.from(e.dataTransfer?.files || [])
  const imgs = files.filter(f => /^image\//.test(f.type))
  const others = files.filter(f => !/^image\//.test(f.type))
  if (imgs.length) addImages(imgs)
  if (others.length) addGenericFiles(others)
}

async function toggleRecording() {
  if (!canUseMicrophone.value) {
    audioErrorMessage.value = '当前浏览器暂不支持录音'
    return
  }
  clearAudioError()
  if (isAudioRecording.value) {
    setAudioStatus('录音完成，正在转写…')
    try {
      const result = await stopRecordingAndTranscribe()
      await handleTranscript(result.text, '语音录制')
    } catch (err: any) {
      audioErrorMessage.value = err?.message || '语音转写失败'
      setAudioStatus('语音转写失败')
    }
    return
  }

  try {
    await startAudioRecording()
    setAudioStatus('录音中，再次点击停止并转写')
  } catch (err: any) {
    audioErrorMessage.value = err?.message || '无法开始录音'
    setAudioStatus('')
  }
}

async function cancelRecordingIfNeeded() {
  if (!isAudioRecording.value) return
  await cancelAudioRecording()
  setAudioStatus('录音已取消')
}

onMounted(() => {
  nextTick(autoResize)
  document.addEventListener('paste', handlePaste)
  window.addEventListener('dragover', globalDragOver)
  window.addEventListener('drop', globalDrop)
})

onBeforeUnmount(() => {
  document.removeEventListener('paste', handlePaste)
  window.removeEventListener('dragover', globalDragOver)
  window.removeEventListener('drop', globalDrop)
})

function clearMessages() {
  messages.clearMessages()
}

async function onSend(ev?: Event | { preventDefault?: () => void }) {
  ev?.preventDefault?.()
  const text = state.message.trim()
  if (!text && !imageFiles.value.length && !genericFiles.value.length) return
  if (hasPendingUploads.value) {
    await ensureAudioTranscriptions()
  }
  if (hasPendingUploads.value) {
    setAudioStatus('仍有文件处理中，请稍后再试')
    return
  }

  // 1) 先确保文本文件上传，拿到提取结果
  await ensureUploads()
  await ensureAudioTranscriptions()

  // 2) 图片转 dataURL（仅前端展示 & 传给视觉模型）
  const imagesDataUrls: string[] = []
  for (const f of imageFiles.value) {
    imagesDataUrls.push(await fileToDataURL(f))
  }

  // 3) 生成聊天用文件对象（包含提取后的文本）
  const files = filesForChat()

  // 4) 立即清空输入与选择
  state.message = ''
  resetAll()
  audioStatusMessage.value = ''
  lastTranscript.value = ''
  audioErrorMessage.value = null
  await nextTick(); autoResize()

  // 5) 发送
  await send({ text, imagesDataUrls, files })
}

async function handlePrimaryAction() {
  if (loadding.value) {
    stop()
    return
  }
  if (!canSend.value) {
    if (hasPendingUploads.value) {
      setAudioStatus('文件处理中，请稍候')
    }
    return
  }
  await onSend()
}
</script>


<template>
  <div id="layout">
    <header id="header">
      <div class="header-container">
        <div class="header-inner">
          <div class="left">
            <LoadingOutlined v-if="loadding" class="header-spinner" />
            <button class="new-convo" type="button" @click="clearMessages">
              <PlusCircleOutlined class="new-convo__icon" />
              <span class="new-convo__label">新对话</span>
            </button>

            <div class="model-select">
              <a-select
                v-model:value="selectedModel"
                class="model-select__control"
                size="small"
                dropdown-class-name="model-select__dropdown"
                :dropdownMatchSelectWidth="false"
              >
                <a-select-option v-for="model in modelOptions" :key="model" :value="model">
                  {{ model }}
                </a-select-option>
              </a-select>
            </div>
          </div>
        </div>
      </div>
    </header>

    <div id="layout-body">
      <main id="main">
        <div class="container" :class="{ 'container--empty': !hasMessages }">
          <div class="chat-container" :class="{ 'chat-container--empty': !hasMessages }">
            <div v-if="!hasMessages" class="welcome-placeholder">
              有什么可以帮您的吗？
            </div>
            <template v-else>
              <Message
                v-for="(msg, idx) in chatMessages"
                :key="idx"
                :message="msg"
                :class="msg.type === 1 ? 'send' : 'replay'"
              />
            </template>
          </div>

          <div class="composer-stage" :class="{ 'composer-stage--empty': !hasMessages }">
            <div class="composer" :class="{ 'drag-over': dragOver }" @dragover.prevent="onDragOver" @dragleave="onDragLeave" @drop="onDrop">
              <div class="composer-inner">
                <div class="composer-accessories">
                  <label class="icon-btn" title="选择图片">
                    <input type="file" accept="image/*" multiple style="display:none" @change="onPickImages" />
                    <PictureOutlined />
                  </label>
                  <label class="icon-btn" title="选择文本、PDF 或音频">
                    <input
                      type="file"
                      multiple
                      accept="text/*,.txt,.md,.markdown,.csv,.tsv,.json,.yaml,.yml,.xml,.html,.htm,.py,.js,.ts,.pdf,application/json,application/xml,application/x-yaml,application/javascript,application/x-python,application/rtf,application/pdf,audio/*,.mp3,.wav,.m4a,.aac,.ogg,.oga,.flac,.webm"
                      style="display:none"
                      @change="(e:any)=>addGenericFiles(Array.from(e.target.files||[]))"
                    />
                    <PaperClipOutlined />
                  </label>
                  <button
                    v-if="canUseMicrophone"
                    class="icon-btn mic-btn"
                    :class="{ recording: isAudioRecording }"
                    type="button"
                    :disabled="isAudioTranscribing"
                    @click="toggleRecording"
                    :title="isAudioRecording ? '停止录音并转写' : '开始录音'"
                  >
                    <LoadingOutlined v-if="isAudioTranscribing" />
                    <AudioFilled v-else-if="isAudioRecording" />
                    <AudioOutlined v-else />
                  </button>
                </div>
                <textarea
                  ref="textareaRef"
                  v-model="state.message"
                  placeholder="发消息..."
                  @input="autoResize"
                  @keydown.enter.exact.prevent="handlePrimaryAction"
                  @keydown.enter.shift.exact.stop
                  class="composer-input"
                  rows="1"
                />
                <button
                  class="primary-action"
                  :class="{ 'is-stop': loadding }"
                  :disabled="!loadding && !canSend"
                  @click="handlePrimaryAction"
                  type="button"
                >
                  <PauseCircleOutlined v-if="loadding" />
                  <SendOutlined v-else />
                </button>
              </div>

              <div v-if="imagePreviews.length" class="preview-bar">
                <div v-for="(src,i) in imagePreviews" :key="'img-'+i" class="preview-item">
                  <img :src="src" alt="preview" />
                  <button class="preview-remove" @click="removeImage(i)"><CloseOutlined /></button>
                </div>
              </div>

              <div v-if="genericFiles.length" class="file-list">
                <div v-for="(f, i) in genericFiles" :key="'file-'+i" class="file-pill" :class="f.status">
                  <span class="name">{{ f.name }}</span>
                  <span class="meta">{{ (f.size/1024/1024).toFixed(2) }}MB</span>
                  <span class="status" v-if="f.status==='pending'">上传中…</span>
                  <span class="status ok" v-else-if="f.status==='ok'">就绪</span>
                  <span class="status error" v-else>失败</span>
                  <button class="pill-remove" @click="removeGenericFile(i)"><CloseOutlined /></button>
                </div>
              </div>

              <div
                v-if="isAudioRecording || isAudioTranscribing || audioStatusMessage || audioErrorText || transcriptPreview"
                class="audio-status"
              >
                <div class="audio-status__icon">
                  <LoadingOutlined v-if="isAudioTranscribing" />
                  <AudioFilled v-else-if="isAudioRecording" />
                  <AudioOutlined v-else />
                </div>
                <div class="audio-status__body">
                  <div v-if="audioStatusMessage" class="audio-status__message">{{ audioStatusMessage }}</div>
                  <div v-if="transcriptPreview && !audioErrorText" class="audio-status__preview">
                    {{ transcriptPreview }}
                  </div>
                  <div v-if="audioErrorText" class="audio-status__error">{{ audioErrorText }}</div>
                </div>
                <button
                  v-if="isAudioRecording"
                  class="audio-status__action"
                  type="button"
                  @click="cancelRecordingIfNeeded"
                >
                  取消
                </button>
              </div>

            </div>
          </div>
        </div>
      </main>
    </div>

  </div>
</template>

<style scoped>
/* ====== 布局基础 ====== */
#layout { display: flex; flex-direction: column; width: 100%; height: 100%; background: #f7f7f8; }
#layout-body { flex: 1 1 0%; overflow-y: auto; display: flex; flex-direction: column; }
#main { flex: 1 1 auto; display: flex; padding: 24px 0 0; }



/* 顶部栏 */
#header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: transparent;
  box-shadow: none;
  padding: 20px 0 12px;
}
.header-container { width: 100%; padding: 0 24px; }
#header .header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
#header .left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.header-spinner {
  color: #2563eb;
  font-size: 16px;
}
.new-convo {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 14px;
  height: 36px;
  border-radius: 999px;
  border: 0px;
  background: rgba(255, 255, 255, 0.12);
  color: #161c2f;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background .2s ease, border-color .2s ease, color .2s ease;
}
.new-convo:hover {
  background: rgba(37, 99, 235, 0.18);
  border-color: rgba(37, 99, 235, 0.45);
  color: #1e40af;
}
.new-convo__icon {
  font-size: 18px;
}
.model-select {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.model-select :deep(.ant-select-selector) {
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  min-height: 30px !important;
  padding: 0 4px !important; 
}

.model-select :deep(.ant-select:not(.ant-select-disabled):hover .ant-select-selector) {
  border-color: transparent !important;
}
.model-select :deep(.ant-select-focused .ant-select-selector) {
  border-color: transparent !important;
  box-shadow: none !important;
}

.model-select :deep(.ant-select-selection-item),
.model-select :deep(.ant-select-selection-placeholder) {
  font-size: 17px;
  line-height: 30px;            /* 与 min-height 对齐，保证垂直居中 */
  display: inline-flex;
  align-items: center;           /* 垂直居中 */
  justify-content: center;       /* 水平居中（像 ChatGPT 居中展示）*/
  width: 100%;
  padding: 0;
  margin: 0;
  color: #111827;              
}

.model-select__control {
  min-width: auto;               
}

.model-select :deep(.ant-select-arrow) {
  color: #6b7280;
  font-size: 10px;
  right: 0;                      
}

.model-select :deep(.ant-select-dropdown) {
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);  
}

.model-select :deep(.ant-select-selector:hover) {
  background: rgba(0,0,0,0.04) !important;
  border-radius: 8px !important;
}

.model-select__dropdown {
  width: auto !important;
  min-width: max-content !important;   /* 让宽度以最长选项为准 */
  border-radius: 8px;
}

.model-select__dropdown .ant-select-item,
.model-select__dropdown .ant-select-item-option-content {
  white-space: nowrap;
}

.model-select__dropdown {
  z-index: 2000;
}

.chat-container {
  flex: 1 1 auto;
  padding: 16px 0 16px;
  padding-left: var(--chat-offset);
  display: flex;
  flex-direction: column;
  gap: 16px;
  justify-content: flex-end;
  overflow-y: auto;
}


.chat-container--empty::-webkit-scrollbar {
  display: none;
}
.welcome-placeholder {
  font-size: 24px;
  line-height: 1.8;
  font-weight: 500;
  color: #1f2937;
  max-width: 520px;
}

.composer-stage {
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  margin-top: auto;

  padding-left: var(--chat-offset, 0);
  padding-bottom: var(--composer-bottom-padding);
}

.composer-stage--empty {

  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  margin-top: 0;
  padding-left: 0;
  padding-bottom: 0;
  align-self: center;
}


.composer {
  width: 100%;
  border-radius: 20px;
  position: relative;
  transition: border-color .2s ease, background .2s ease;
}
.composer.drag-over {
  border: 1px dashed rgba(59, 130, 246, 0.6);
  background: rgba(59, 130, 246, 0.08);
}
.composer-inner {
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
}
.composer-stage--empty .composer-inner {
  max-width: 720px;
}

.composer-accessories {
  display: flex;
  gap: 8px;
}

.icon-btn {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  background: rgba(255, 255, 255, 0.65);
  color: #334155;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
  transition: background .15s ease, border-color .15s ease, box-shadow .15s ease;
}
.icon-btn:hover {
  background: rgba(241, 245, 249, 0.85);
  border-color: rgba(148, 163, 184, 0.65);
}

.icon-btn:active {
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.15);
}
.mic-btn.recording {
  border-color: rgba(34, 197, 94, 0.55);
  background: rgba(34, 197, 94, 0.16);
  color: #15803d;
  box-shadow: 0 10px 22px rgba(34, 197, 94, 0.25);
}
.mic-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

.composer-input {
  flex: 1 1 auto;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.55);
  background: rgba(248, 250, 252, 0.6);
  padding: 12px 16px;
  font-size: 15px;
  line-height: 1.6;
  min-height: 52px;
  max-height: 260px;
  resize: none;
  color: #0f172a;
  transition: border-color .2s ease, box-shadow .2s ease, background .2s ease;
  box-shadow: 0 15px 35px rgba(15, 23, 42, 0.06);
}
.composer-input:focus-visible {
  outline: none;
  border-color: rgba(59, 130, 246, 0.85);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18);
  background: rgba(255, 255, 255, 0.92);
}

.primary-action {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  border: 1px solid rgba(37, 99, 235, 0.5);
  background: #2563eb;
  color: #fff;
  box-shadow: 0 20px 32px rgba(37, 99, 235, 0.25);
  transition: transform .15s ease, box-shadow .15s ease, background .15s ease, border-color .15s ease;
}


.primary-action:hover {
  transform: translateY(-1px);
  background: #1d4ed8;
  border-color: #1d4ed8;
}
.primary-action:active {
  transform: translateY(0);
}
.primary-action:disabled {
  opacity: .55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}
.primary-action.is-stop {
  border-color: rgba(14, 165, 233, 0.65);
  background: #0ea5e9;
  box-shadow: 0 20px 32px rgba(14, 165, 233, 0.28);
}
.primary-action.is-stop:hover {
  background: #0284c7;
  border-color: #0284c7;
}

.audio-status {
  margin-top: 12px;
  padding: 8px 12px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(148, 163, 184, 0.12);
  border: 1px solid rgba(148, 163, 184, 0.32);
}
.audio-status__icon {
  font-size: 16px;
  color: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
}
.audio-status__body {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.audio-status__message {
  font-size: 13px;
  color: #1f2937;
  font-weight: 500;
}
.audio-status__preview {
  font-size: 12px;
  color: #374151;
  line-height: 1.4;
}
.audio-status__error {
  font-size: 12px;
  color: #dc2626;
}
.audio-status__action {
  border: none;
  background: transparent;
  color: #dc2626;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  transition: background .15s ease;
}
.audio-status__action:hover {
  background: rgba(220, 38, 38, 0.08);
}

.preview-bar,
.file-list {
  width: 100%;
  max-width: 680px;
  margin: 12px auto 0;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.composer-stage--empty .preview-bar,
.composer-stage--empty .file-list {
  max-width: 680px;
}
.preview-item { position: relative; width: 84px; height: 84px; border-radius: 10px; overflow: hidden; border: 1px solid #e5e7eb; }
.preview-item img { width: 100%; height: 100%; object-fit: cover; display:block; }
.preview-remove { position: absolute; top: 4px; right: 4px; border: none; background: rgba(0,0,0,.45); color: #fff; width: 20px; height: 20px; border-radius: 6px; display:flex; align-items:center; justify-content:center; }

.file-pill { position: relative; display:flex; align-items:center; gap:8px; padding: 6px 10px; border: 1px solid #e5e7eb; border-radius: 999px; background: #f9fafb; }
.file-pill .name { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-pill .meta { color: #6b7280; font-size: 12px; }
.file-pill .status { font-size: 12px; color: #6b7280; }
.file-pill.ok { background: #eefdf3; border-color: #b6f0c5; }
.file-pill.error { background: #fef2f2; border-color: #fecaca; }
.pill-remove { border:none; background: transparent; color:#6b7280; }
.pill-remove:hover { color:#111827; }

/* ====== 容器基础 ====== */
.container {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  max-width: 900px;
  margin: 0 auto;

  /* 这里的底部 padding 会把输入框顶高，聊天态我们改小 */
  padding: 0 16px 12px; /* ← 原本是 48px，改小让输入框更贴底 */
  transition: padding .3s ease;
}

/* 空态：把整列内容居中（注意：头部是 48px，不是 20px） */
.container--empty {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;   /* 垂直居中整列 */
  align-items: center;
  gap: 20px;
  padding: 0 16px;
  min-height: calc(100vh - 48px); /* ← 修正你误写的 20px */
  position: relative;        /* 便于子项 transform 视觉位移 */
}

/* 聊天区（空态）不要拉伸填满，否则会把输入区“挤低” */
.chat-container--empty {
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  padding: 0;
  gap: 16px;
  text-align: center;
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
}

/* ====== 输入区：聊天态吸底，空态居中 ====== */

/* 可调参数：空态整体上移 & 聊态底部留白 */
:global(:root) {
  --empty-vertical-offset: -10vh;
  --composer-bottom-padding: 12px;
}
/* 聊天态（默认）：吸底 */
.composer-stage {
  width: 100%;
  max-width: 720px;
  margin: 0 auto;

  /* 关键：吸底 */
  margin-top: auto;

  /* 左侧缩进 + 底部留白（变量可调） */
  padding-left: var(--chat-offset, 0);
  padding-bottom: var(--composer-bottom-padding);
}

/* 兼容安全区（手机底部手势条）——只保留这一份，删掉你上面那份固定 20px 的版本 */
@supports (padding: env(safe-area-inset-bottom)) {
  .composer-stage {
    padding-bottom: calc(var(--composer-bottom-padding) + env(safe-area-inset-bottom));
  }
}

/* 空态：不要吸底，和欢迎文案一起居中 */
.composer-stage--empty {
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  margin-top: 0;        /* 不吸底 */
  padding-left: 0;
  padding-bottom: 0;
  align-self: center;   /* 水平居中 */
}

/* 空态：欢迎文案 + 输入区 整体上移一点（看起来更舒服） */
.container--empty > .chat-container--empty,
.container--empty > .composer-stage.composer-stage--empty {
  transform: translateY(var(--empty-vertical-offset));
}




</style>
