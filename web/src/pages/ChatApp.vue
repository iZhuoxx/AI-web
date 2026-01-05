<script setup lang="ts">
import {
  LoadingOutlined,
  CloseOutlined,
  PaperClipOutlined,
  SendOutlined,
  PauseCircleOutlined,
  AudioOutlined,
  StopOutlined,
  PlusCircleOutlined,
} from '@ant-design/icons-vue'
import { message as antdMessage } from 'ant-design-vue'
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed, watch } from 'vue'
import Message from '.././components/message.vue'
import { useChat } from '@/composables/useChat'
import { useUploads } from '@/composables/useUploads'
import { useRealtimeTranscription } from '@/composables/useRealtimeTranscription'
import useSetting from '@/composables/setting'
import { MODEL_OPTIONS } from '@/constants/models'

const DEFAULT_CHAT_TOOLS = [{ type: 'image_generation' }]
const { loadding, send, stop, messagesStore } = useChat({
  storageKey: 'chat-app-messages',
  tools: DEFAULT_CHAT_TOOLS,
  modelKey: 'chat',
})

const {
  imageFiles,
  imagePreviews,
  genericFiles,
  dragOver,
  addGenericFiles,
  removeGenericFile,
  onPaste,
  onDragOver,
  onDragLeave,
  onDrop,
  ensureUploads,
  ensureAudioTranscriptions,
  fileToDataURL,
  removeImage,
  resetAll,
  filesForChat,
  addImages,
} = useUploads()

const setting = useSetting()

const realtime = useRealtimeTranscription({ includeLogprobs: true, minConfidence: 0 })
const canUseMicrophone = realtime.canRecord
const isAudioRecording = realtime.isRecording
const liveTranscript = realtime.liveText
const transcriptAggregate = realtime.transcriptText
const audioErrorMessage = realtime.errorMessage
const startRealtimeRecording = realtime.startRecording
const stopRealtimeRecording = realtime.stopRecording
const realtimeSegments = realtime.segments

const modelOptions = MODEL_OPTIONS
const selectedModel = computed({
  get: () => setting.value.models.chat,
  set: (val: string) => {
    if (val) {
      setting.value.models.chat = val
      setting.value.model = val
    }
  },
})

const isAudioProcessing = ref(false)
const hasPendingUploads = computed(() => genericFiles.value.some(it => it.status === 'pending'))

const chatMessages = messagesStore.messages
const hasMessages = computed(() => chatMessages.value.length > 0)

const handlePaste = (event: ClipboardEvent) => {
  void onPaste(event)
}

const state = reactive({ message: '' })
const hasPayload = computed(
  () =>
    state.message.trim().length > 0 ||
    imageFiles.value.length > 0 ||
    genericFiles.value.length > 0,
)
const canSend = computed(() => hasPayload.value && !hasPendingUploads.value)

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const chatRef = ref<HTMLElement | null>(null)
const layoutBodyRef = ref<HTMLElement | null>(null)
const MAX_TEXTAREA_H = 240
const autoResize = () => {
  const el = textareaRef.value
  if (!el) return
  el.style.height = '0px'
  const h = Math.min(el.scrollHeight, MAX_TEXTAREA_H)
  el.style.height = `${h}px`
  el.style.overflowY = el.scrollHeight > MAX_TEXTAREA_H ? 'auto' : 'hidden'
}

const clearAudioError = () => {
  audioErrorMessage.value = null
}

const delay = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms))

const waitForFinalTranscript = async (timeoutMs = 2000): Promise<string> => {
  const deadline = Date.now() + timeoutMs
  let lastSeen = ''
  while (Date.now() < deadline) {
    const current = transcriptAggregate.value.trim()
    if (current && current !== lastSeen) {
      lastSeen = current
      if (!isAudioRecording.value) {
        return current
      }
    }
    if (!isAudioRecording.value && current) {
      return current
    }
    await delay(120)
  }
  return transcriptAggregate.value.trim()
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

const handleAttachmentSelection = (event: Event) => {
  const input = event.target as HTMLInputElement | null
  if (!input?.files) return
  const files = Array.from(input.files)
  if (!files.length) return
  const images = files.filter(file => /^image\//.test(file.type))
  const others = files.filter(file => !/^image\//.test(file.type))
  if (images.length) addImages(images)
  if (others.length) addGenericFiles(others)
  input.value = ''
}

const resetRecordingBuffers = () => {
  liveTranscript.value = ''
  realtimeSegments.value = []
}

const sendTranscriptionMessage = async (text: string) => {
  const cleaned = text.trim()
  if (!cleaned) {
    throw new Error('实时转写结果为空，请重试')
  }
  state.message = cleaned
  await onSend()
}

async function toggleRecording() {
  if (!canUseMicrophone.value) {
    const msg = '当前浏览器暂不支持录音'
    audioErrorMessage.value = msg
    antdMessage.error(msg)
    return
  }
  clearAudioError()
  if (isAudioRecording.value) {
    isAudioProcessing.value = true
    try {
      await stopRealtimeRecording()
      const finalText = await waitForFinalTranscript()
      await sendTranscriptionMessage(finalText)
      clearAudioError()
      antdMessage.success('语音已转写到对话')
    } catch (err: any) {
      const fallbackMessage = err?.message || '实时转写失败'
      audioErrorMessage.value = fallbackMessage
      antdMessage.error(fallbackMessage)
    } finally {
      resetRecordingBuffers()
      isAudioProcessing.value = false
    }
    return
  }

  try {
    isAudioProcessing.value = true
    resetRecordingBuffers()
    await startRealtimeRecording()
  } catch (err: any) {
    const fallbackMessage = err?.message || '无法启动实时转写'
    audioErrorMessage.value = fallbackMessage
    antdMessage.error(fallbackMessage)
  } finally {
    isAudioProcessing.value = false
  }
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
  messagesStore.clearMessages()
}

async function onSend(ev?: Event | { preventDefault?: () => void }) {
  ev?.preventDefault?.()
  const text = state.message.trim()
  if (!text && !imageFiles.value.length && !genericFiles.value.length) return

  await ensureUploads()
  await ensureAudioTranscriptions()
  if (hasPendingUploads.value) {
    antdMessage.info('仍有文件处理中，请稍后再试')
    return
  }

  const imagesDataUrls: string[] = []
  for (const file of imageFiles.value) {
    imagesDataUrls.push(await fileToDataURL(file))
  }
  const files = filesForChat()

  state.message = ''
  resetAll()
  resetRecordingBuffers()
  clearAudioError()
  await nextTick()
  autoResize()

  await send({ text, imagesDataUrls, files, reasoning: { summary: 'auto' } })
}

// Auto-scroll logic
const isAutoScroll = ref(true)
const showScrollToBottom = ref(false)
const BOTTOM_THRESHOLD = 12

const scrollToBottom = async () => {
  await nextTick()
  const el = layoutBodyRef.value
  if (!el) return
  try {
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  } catch {
    el.scrollTop = el.scrollHeight
  }
}

const scrollToBottomAndEnableAuto = async () => {
  await scrollToBottom()
  isAutoScroll.value = true
  showScrollToBottom.value = false
}

const onChatScroll = () => {
  const el = layoutBodyRef.value
  if (!el) return
  const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - BOTTOM_THRESHOLD
  if (!atBottom) {
    if (isAutoScroll.value) isAutoScroll.value = false
    showScrollToBottom.value = true
  } else {
    showScrollToBottom.value = false
  }
}

watch([chatMessages, loadding], async () => {
  if (isAutoScroll.value) {
    await scrollToBottom()
  }
}, { deep: true })

onMounted(() => {
  if (chatMessages.value.length) {
    isAutoScroll.value = true
    showScrollToBottom.value = false
    void scrollToBottom()
  }
})

async function handlePrimaryAction() {
  if (loadding.value) {
    stop()
    return
  }
  if (!canSend.value) {
    if (hasPendingUploads.value) {
      antdMessage.info('文件处理中,请稍候')
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
            <button class="new-convo" type="button" @click="clearMessages">
              <PlusCircleOutlined class="new-convo__icon" />
              <span class="new-convo__label">新对话</span>
            </button>

            <div class="model-select">
              <a-select
                v-model:value="selectedModel"
                class="model-select__control"
                size="small"
                dropdown-class-name="rounded-dropdown model-select__dropdown"
                :dropdownMatchSelectWidth="false"
              >
                <a-select-option v-for="model in modelOptions" :key="model" :value="model">
                  <div class="model-option">
                    <svg class="model-icon" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z"/>
                    </svg>
                    <span>{{ model }}</span>
                  </div>
                </a-select-option>
              </a-select>
            </div>
          </div>
        </div>
      </div>
    </header>

    <div class="content-divider"></div>

    <div id="layout-body">
      <div
        id="main-scroll"
        ref="layoutBodyRef"
        :class="{ 'main-scroll--empty': !hasMessages }"
        @scroll="onChatScroll"
      >
        <main id="main">
          <div class="container" :class="{ 'container--empty': !hasMessages }">
            <div
              ref="chatRef"
              class="chat-container"
              :class="{ 'chat-container--empty': !hasMessages }"
            >
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

            <!-- Composer inside scrollable area when no messages -->
            <div v-if="!hasMessages" class="composer-stage composer-stage--empty">
              <div class="composer" :class="{ 'drag-over': dragOver }" @dragover.prevent="onDragOver" @dragleave="onDragLeave" @drop="onDrop">
                <div class="composer-inner">
                  <div class="composer-accessories">
                    <label class="icon-btn" title="上传附件">
                      <input
                        type="file"
                        multiple
                    accept="image/*,.c,.cpp,.cs,.css,.csv,.doc,.docx,.gif,.go,.html,.java,.jpeg,.jpg,.js,.json,.md,.pdf,.php,.pkl,.png,.pptx,.py,.rb,.tar,.tex,.ts,.txt,.webp,.xlsx,.xml,.zip,.mp3"
                    style="display:none"
                    @change="handleAttachmentSelection"
                  />
                      <PaperClipOutlined />
                    </label>
                    <button
                      v-if="canUseMicrophone"
                      class="icon-btn mic-btn"
                      :class="{ recording: isAudioRecording }"
                      type="button"
                      :disabled="isAudioProcessing"
                      @click="toggleRecording"
                      :title="isAudioRecording ? '停止实时转写' : '开始实时转写'"
                    >
                      <LoadingOutlined v-if="isAudioProcessing" />
                      <StopOutlined v-else-if="isAudioRecording" />
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
              </div>
            </div>
          </div>
        </main>
      </div>

      <!-- Composer at bottom when there are messages -->
      <div v-if="hasMessages" class="composer-wrapper">
        <div class="composer-stage">
          <div class="composer" :class="{ 'drag-over': dragOver }" @dragover.prevent="onDragOver" @dragleave="onDragLeave" @drop="onDrop">
            <div class="composer-inner">
              <div class="composer-accessories">
                <label class="icon-btn" title="上传附件">
                  <input
                    type="file"
                    multiple
                    accept="image/*,.c,.cpp,.cs,.css,.csv,.doc,.docx,.gif,.go,.html,.java,.jpeg,.jpg,.js,.json,.md,.pdf,.php,.pkl,.png,.pptx,.py,.rb,.tar,.tex,.ts,.txt,.webp,.xlsx,.xml,.zip,.mp3"
                    style="display:none"
                    @change="handleAttachmentSelection"
                  />
                  <PaperClipOutlined />
                </label>
                <button
                  v-if="canUseMicrophone"
                  class="icon-btn mic-btn"
                  :class="{ recording: isAudioRecording }"
                  type="button"
                  :disabled="isAudioProcessing"
                  @click="toggleRecording"
                  :title="isAudioRecording ? '停止实时转写' : '开始实时转写'"
                >
                  <LoadingOutlined v-if="isAudioProcessing" />
                  <StopOutlined v-else-if="isAudioRecording" />
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
          </div>
        </div>
      </div>

      <!-- Scroll to bottom button -->
      <button
        v-if="showScrollToBottom && hasMessages"
        class="scroll-fab"
        type="button"
        aria-label="滚动到底部"
        @click="scrollToBottomAndEnableAuto"
      >
        <svg viewBox="0 0 24 24" class="chevron-down" aria-hidden="true">
          <path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
#layout { 
  display: flex; 
  flex-direction: column; 
  width: 100%; 
  height: 100vh;
  background: #fff; 
  overflow: hidden;
}

#layout-body {
  flex: 1 1 0%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  position: relative;
}

#main-scroll {
  flex: 1 1 auto;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

#main-scroll.main-scroll--empty {
  overflow-y: hidden;
  scrollbar-width: none;
}

/* Hide scrollbars entirely on welcome view */
#main-scroll.main-scroll--empty::-webkit-scrollbar {
  display: none;
}

/* Only show scrollbar when there are messages */
#main-scroll::-webkit-scrollbar {
  width: 8px;
}

#main-scroll::-webkit-scrollbar-track {
  background: #fff;
}

#main-scroll::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 4px;
}

#main-scroll::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

/* Firefox */
#main-scroll {
  scrollbar-width: thin;
  scrollbar-color: #d1d5db #fff;
}

#main { 
  flex: 1 1 auto;
  display: flex; 
  flex-direction: column; 
  padding: 0; 
  min-height: 100%;
  position: relative;
}

.composer-wrapper {
  flex-shrink: 0;
  width: 100%;
  background: #fff;
  border-top: 1px solid rgba(229, 231, 235, 0.5);
  position: relative;
  z-index: 5;
}

.content-divider { 
  width: calc(100% - 48px); 
  height: 1px; 
  background: #e5e7eb; 
  margin: 4px 24px 0; 
  align-self: center; 
  border-radius: 999px; 
  flex-shrink: 0;
}

#header {
  flex-shrink: 0;
  background: transparent;
  box-shadow: none;
  padding: 20px 0 12px;
}
.header-container { width: 100%; padding: 0 24px; }
#header .header-inner { display: flex; align-items: center; justify-content: space-between; }
#header .left { display: flex; align-items: center; gap: 16px; }
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
.new-convo:hover { background: rgba(37, 99, 235, 0.18); border-color: rgba(37, 99, 235, 0.45); color: #1e40af; }
.new-convo__icon { font-size: 18px; }
.model-select { display: inline-flex; align-items: center; gap: 6px; }

.model-select :deep(.ant-select-selector) {
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  min-height: 30px !important;
  padding: 0 4px !important; 
}
.model-select :deep(.ant-select:not(.ant-select-disabled):hover .ant-select-selector) { border-color: transparent !important; }
.model-select :deep(.ant-select-focused .ant-select-selector) { border-color: transparent !important; box-shadow: none !important; }
.model-select :deep(.ant-select-selection-item),
.model-select :deep(.ant-select-selection-placeholder) {
  font-size: 17px;
  line-height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 0;
  margin: 0;
  color: #111827;
}
.model-select__control { min-width: auto; }
.model-select :deep(.ant-select-arrow) { color: #6b7280; font-size: 10px; right: 0; }
.model-select :deep(.ant-select-dropdown) { box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12); }
.model-select :deep(.ant-select-selector:hover) { background: rgba(0,0,0,0.04) !important; border-radius: 8px !important; }

/* Dropdown styling */
:deep(.rounded-dropdown.model-select__dropdown) {
  width: auto !important;
  min-width: max-content !important;
  border-radius: 12px !important;
  z-index: 2000;
  padding: 6px 0 !important;
  overflow: hidden !important;
}

:deep(.model-select__dropdown .rc-virtual-list) {
  padding: 0 !important;
  margin: 0 !important;
}

:deep(.model-select__dropdown .rc-virtual-list-holder) {
  padding: 0 !important;
  margin: 0 !important;
}

:deep(.model-select__dropdown .rc-virtual-list-holder-inner) {
  padding: 0 !important;
  margin: 0 !important;
}

:deep(.model-select__dropdown .ant-select-item) {
  padding: 10px 14px;
  line-height: 1.5;
  font-size: 14px;
  white-space: nowrap;
  border-radius: 0 !important;
}

:deep(.model-select__dropdown .ant-select-item-option-content) {
  white-space: nowrap;
}

/* Model option with icon */
.model-option {
  display: flex;
  align-items: center;
  gap: 10px;
}

.model-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: #10a37f;
}

.container {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
  padding: 0 16px 12px;
  min-height: 100%;
}

.container--empty {
  justify-content: flex-start;
  align-items: center;
  gap: 20px;
  padding-top: clamp(120px, 26vh, 240px);
  padding-bottom: clamp(140px, 22vh, 240px);
}

/* Chat container without scrollbar */
.chat-container {
  flex: 1 1 auto;
  min-height: 0;
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: visible;
}

.chat-container--empty {
  flex: 1 1 auto;
  align-items: center;
  justify-content: center;
  padding: 0;
  overflow: visible;
}

/* Hide any accidental scrollbars on chat container */
.chat-container::-webkit-scrollbar { 
  display: none; 
}

.chat-container:not(.chat-container--empty) {
  justify-content: flex-start;
}

.welcome-placeholder {
  font-size: 24px;
  line-height: 1.8;
  font-weight: 500;
  color: #1f2937;
  max-width: 520px;
  text-align: center;
}

.composer-stage {
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  padding: 12px 16px;
  padding-bottom: var(--composer-bottom-padding, 12px);
  background: transparent;
}

.composer-stage--empty {
  /* When empty, composer is centered with the welcome message */
  padding: 0 16px;
  margin-top: 12px;
}

.container {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
  padding: 16px 16px 12px;
  min-height: 0;
  flex: 1 1 auto;
}

.container--empty {
  justify-content: flex-start;
  align-items: center;
  gap: 20px;
  min-height: 100vh;
  padding-top: clamp(120px, 28vh, 260px);
  padding-bottom: clamp(150px, 24vh, 260px); /* Add space to account for header while keeping content lower */
}

.container--empty > .chat-container--empty {
  /* Center the welcome message when no messages */
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
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

.composer-accessories { display: flex; gap: 8px; }

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
  cursor: pointer;
}
.icon-btn:hover { 
  background: rgba(241, 245, 249, 0.85); 
  border-color: rgba(148, 163, 184, 0.65); 
}
.icon-btn:active { box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.15); }
.mic-btn.recording { 
  border-color: rgba(34, 197, 94, 0.55); 
  background: rgba(34, 197, 94, 0.16); 
  color: #15803d; 
  box-shadow: 0 10px 22px rgba(34, 197, 94, 0.25); 
}
.mic-btn:disabled { opacity: 0.55; cursor: not-allowed; box-shadow: none; }

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
  cursor: pointer;
  box-shadow: 0 20px 32px rgba(37, 99, 235, 0.25);
  transition: transform .15s ease, box-shadow .15s ease, background .15s ease, border-color .15s ease;
}
.primary-action:hover { 
  transform: translateY(-1px); 
  background: #1d4ed8; 
  border-color: #1d4ed8; 
}
.primary-action:active { transform: translateY(0); }
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

.preview-bar,
.file-list {
  width: 100%;
  max-width: 680px;
  margin: 12px auto 0;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.preview-item { 
  position: relative; 
  width: 84px; 
  height: 84px; 
  border-radius: 10px; 
  overflow: hidden; 
  border: 1px solid #e5e7eb; 
}
.preview-item img { 
  width: 100%; 
  height: 100%; 
  object-fit: cover; 
  display: block; 
}
.preview-remove { 
  position: absolute; 
  top: 4px; 
  right: 4px; 
  border: none; 
  background: rgba(0,0,0,.45); 
  color: #fff; 
  width: 20px; 
  height: 20px; 
  border-radius: 6px; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  cursor: pointer;
}

.file-pill { 
  position: relative; 
  display: flex; 
  align-items: center; 
  gap: 8px; 
  padding: 6px 10px; 
  border: 1px solid #e5e7eb; 
  border-radius: 999px; 
  background: #f9fafb; 
}
.file-pill .name { 
  max-width: 220px; 
  overflow: hidden; 
  text-overflow: ellipsis; 
  white-space: nowrap; 
}
.file-pill .meta { color: #6b7280; font-size: 12px; }
.file-pill .status { font-size: 12px; color: #6b7280; }
.file-pill.ok { background: #eefdf3; border-color: #b6f0c5; }
.file-pill.error { background: #fef2f2; border-color: #fecaca; }
.pill-remove { 
  border: none; 
  background: transparent; 
  color: #6b7280; 
  cursor: pointer;
}
.pill-remove:hover { color: #111827; }

/* Scroll to bottom button - ChatGPT style */
.scroll-fab {
  position: fixed;
  left: calc(50% + 100px); /* shift slightly right so it doesn't overlap center content */
  bottom: 100px;
  transform: translateX(-50%);
  z-index: 10;
  
  width: 40px;
  height: 40px;
  border-radius: 999px;
  
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: #fff;
  color: #0f172a;
  
  display: inline-flex;
  align-items: center;
  justify-content: center;
  
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.10);
  cursor: pointer;
  
  transition: transform .12s ease, box-shadow .15s ease, border-color .15s ease;
  
  animation: fadeIn 0.2s ease-in-out;
}

.scroll-fab:hover {
  transform: translateX(-50%) translateY(-2px);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
  border-color: rgba(0, 0, 0, 0.18);
}

.scroll-fab:active { 
  transform: translateX(-50%) translateY(0); 
}

.scroll-fab .chevron-down { 
  width: 20px; 
  height: 20px; 
  display: block; 
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

:global(:root) {
  --composer-bottom-padding: 12px;
  --chat-offset: 0;
}

@supports (padding: env(safe-area-inset-bottom)) {
  :global(:root) {
    --composer-bottom-padding: calc(12px + env(safe-area-inset-bottom));
  }
}
</style>

<style>
.loader-dots { display: inline-flex; gap: 4px; }
.loader-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #64748b;
  animation: loaderDots 1.2s infinite ease-in-out;
}
.loader-dots span:nth-child(2) { animation-delay: 0.15s; }
.loader-dots span:nth-child(3) { animation-delay: 0.3s; }
@keyframes loaderDots {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Global dropdown rounded corners for model select */
.rounded-dropdown.model-select__dropdown {
  border-radius: 12px !important;
  overflow: hidden !important;
  padding: 6px 0 !important;
}

.model-select__dropdown .rc-virtual-list {
  padding: 0 !important;
  margin: 0 !important;
}

.model-select__dropdown .rc-virtual-list-holder {
  padding: 0 !important;
  margin: 0 !important;
}

.model-select__dropdown .rc-virtual-list-holder-inner {
  padding: 0 !important;
  margin: 0 !important;
}

.model-select__dropdown .ant-select-item {
  border-radius: 0 !important;
}
</style>
