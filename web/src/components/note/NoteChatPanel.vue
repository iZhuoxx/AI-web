<template>
  <div class="note-chat-panel">
    <div class="chat-main">
      <div
        ref="scrollContainer"
        class="messages"
        :class="{ 'messages--empty': !hasMessages && !loadding }"
        @scroll="onMessagesScroll"
      >
        <div v-if="!hasMessages && !loadding" class="empty-hint">暂无对话，开始输入或录音吧。</div>
        <template v-else>
          <Message
            v-for="(msg, idx) in chatMessages"
            :key="idx"
            :message="msg"
            :class="msg.type === 1 ? 'send' : 'replay'"
            @open-citation="emit('open-citation', $event)"
          />
          <!-- 等待回复时的加载气泡（尚未开始助手回复时显示） -->
          <div v-if="loadding && !hasAssistantMessageStarted" class="loading-bubble">
            <div class="loader-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </template>
      </div>

      <form
        class="composer"
        :class="{ 'drag-over': dragOver }"
        @submit.prevent="handlePrimaryAction"
        @dragover.prevent="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
      >
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
            placeholder="输入消息..."
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
            type="submit"
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
          <div
            v-for="(f, i) in genericFiles"
            :key="'file-'+i"
            class="file-pill"
            :class="f.status"
          >
            <span class="name">{{ f.name }}</span>
            <span class="meta">{{ (f.size/1024/1024).toFixed(2) }}MB</span>
            <span class="status" v-if="f.status==='pending'">上传中…</span>
            <span class="status ok" v-else-if="f.status==='ok'">就绪</span>
            <span class="status error" v-else>失败</span>
            <button class="pill-remove" @click="removeGenericFile(i)"><CloseOutlined /></button>
          </div>
        </div>
      </form>

      <!-- 底部回到最新的悬浮按钮 -->
      <button
        v-if="showScrollToBottom"
        class="scroll-fab"
        type="button"
        aria-label="滚动到底部并开启自动滚动"
        @click="scrollToBottomAndEnableAuto()"
      >
        <svg viewBox="0 0 24 24" class="chevron-down" aria-hidden="true">
          <path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  LoadingOutlined,
  CloseOutlined,
  PaperClipOutlined,
  SendOutlined,
  PauseCircleOutlined,
  AudioOutlined,
  StopOutlined,
} from '@ant-design/icons-vue'
import { message as antdMessage } from 'ant-design-vue'
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed, watch, shallowRef } from 'vue'
import Message from '@/components/message.vue'
import { useChat } from '@/composables/useChat'
import { useUploads } from '@/composables/useUploads'
import { useRealtimeTranscription } from '@/composables/useRealtimeTranscription'
import { useNotebookStore } from '@/composables/useNotes'

export type NoteChatPanelExposed = {
  startNewConversation: () => void
}

const emit = defineEmits<{
  (e: 'has-messages-change', value: boolean): void
  (e: 'open-citation', payload: {
    fileId: string
    filename?: string
    index?: number
    startIndex?: number
    endIndex?: number
    quote?: string
    label?: number
  }): void
}>()

// 当前笔记本的向量库 ID，用于 file_search
const notebookStore = useNotebookStore()
const vectorStoreId = computed(() => notebookStore.notebooksState.activeNotebook?.openaiVectorStoreId || null)
const chatTools = computed(() => {
  const tools = []
  if (vectorStoreId.value) {
    tools.push({
      type: 'file_search',
      vector_store_ids: [vectorStoreId.value],
    })
  }
  return tools
})

// chat 相关：按 notebook id 生成独立的存储 key
const activeNotebookId = computed(() => notebookStore.activeNotebook.value?.id ?? null)
type ChatInstance = ReturnType<typeof useChat>
const chatInstance = shallowRef<ChatInstance | null>(null)

const createChatInstance = (id: string | number | null) => {
  if (!id) {
    chatInstance.value?.stop?.()
    chatInstance.value = null
    return
  }

  chatInstance.value?.stop?.()
  const instance = useChat({
    storageKey: 'notes-chat-messages' + id,
    tools: () => chatTools.value,
    includes: () => (vectorStoreId.value ? ['file_search_call.results'] : []),
    modelKey: 'noteChat',
  })
  instance.messagesStore.setPreferredTools?.(chatTools.value ?? null)
  chatInstance.value = instance
}

watch(activeNotebookId, id => createChatInstance(id), { immediate: true })

// 同步 tools 变化（例如 notebook 切换后 vector store id 变化）
watch(
  [chatTools, chatInstance],
  ([value, instance]) => {
    instance?.messagesStore.setPreferredTools?.(value ?? null)
  },
  { immediate: true },
)

const loadding = computed(() => chatInstance.value?.loadding.value ?? false)
const messagesStore = computed(() => chatInstance.value?.messagesStore ?? null)
const chatMessages = computed(() => messagesStore.value?.messages.value ?? [])
const send: ChatInstance['send'] = async payload => {
  if (!chatInstance.value) return
  return chatInstance.value.send(payload)
}
const stop = () => {
  chatInstance.value?.stop()
}

// 上传、拖拽与实时转写相关的状态
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

const realtime = useRealtimeTranscription({ includeLogprobs: true, minConfidence: 0 })
const canUseMicrophone = realtime.canRecord
const isAudioRecording = realtime.isRecording
const liveTranscript = realtime.liveText
const transcriptAggregate = realtime.transcriptText
const audioErrorMessage = realtime.errorMessage
const startRealtimeRecording = realtime.startRecording
const stopRealtimeRecording = realtime.stopRecording
const realtimeSegments = realtime.segments

const hasMessages = computed(() => chatMessages.value.length > 0)
watch(hasMessages, value => emit('has-messages-change', value), { immediate: true })

// 记录助手回复是否已经开始
const messageCountBeforeSend = ref(0)
const hasAssistantMessageStarted = computed(() => {
  if (!loadding.value) return false
  return chatMessages.value.length > messageCountBeforeSend.value
})

// 输入区状态
const state = reactive({ message: '' })
const hasPendingUploads = computed(() => genericFiles.value.some(it => it.status === 'pending'))
const hasPayload = computed(
  () =>
    state.message.trim().length > 0 ||
    imageFiles.value.length > 0 ||
    genericFiles.value.length > 0,
)
const canSend = computed(() => hasPayload.value && !hasPendingUploads.value)

// 文本区域自适应
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const MAX_TEXTAREA_H = 240
const autoResize = () => {
  const el = textareaRef.value
  if (!el) return
  el.style.height = '0px'
  const h = Math.min(el.scrollHeight, MAX_TEXTAREA_H)
  el.style.height = `${h}px`
  el.style.overflowY = el.scrollHeight > MAX_TEXTAREA_H ? 'auto' : 'hidden'
}

// 录音/转写
const clearAudioError = () => { audioErrorMessage.value = null }
const delay = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms))
const waitForFinalTranscript = async (timeoutMs = 2000): Promise<string> => {
  const deadline = Date.now() + timeoutMs
  let lastSeen = ''
  while (Date.now() < deadline) {
    const current = transcriptAggregate.value.trim()
    if (current && current !== lastSeen) {
      lastSeen = current
      if (!isAudioRecording.value) return current
    }
    if (!isAudioRecording.value && current) return current
    await delay(120)
  }
  return transcriptAggregate.value.trim()
}
const sendTranscriptionMessage = async (text: string) => {
  const cleaned = text.trim()
  if (!cleaned) throw new Error('实时转写结果为空，请重试')
  state.message = cleaned
  await onSend()
}
const isAudioProcessing = ref(false)
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
const resetRecordingBuffers = () => {
  liveTranscript.value = ''
  realtimeSegments.value = []
}

// 发送消息
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

  // 记录发送前的消息数量，用于判定助手是否开始回复
  messageCountBeforeSend.value = chatMessages.value.length

  await send({ text, imagesDataUrls, files, reasoning: { summary: 'auto' } })
}

// 主按钮（发送/停止）
async function handlePrimaryAction() {
  if (loadding.value) {
    stop()
    return
  }
  if (!canSend.value) {
    if (hasPendingUploads.value) antdMessage.info('文件处理中，请稍候')
    return
  }
  await onSend()
}

// 自动滚动逻辑
const scrollContainer = ref<HTMLDivElement | null>(null)
const isAutoScroll = ref(true)
const showScrollToBottom = ref(false)
const BOTTOM_THRESHOLD = 12

const scrollToBottom = async () => {
  await nextTick()
  const el = scrollContainer.value
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

const onMessagesScroll = () => {
  const el = scrollContainer.value
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

const startNewConversation = () => {
  stop()
  const store = messagesStore.value
  if (store) {
    store.clearMessages()
    store.resetLastCompletedResponseId?.()
  }
  isAutoScroll.value = true
  showScrollToBottom.value = false
}

defineExpose<NoteChatPanelExposed>({
  startNewConversation,
})

// 生命周期
const handlePaste = (event: ClipboardEvent) => { void onPaste(event) }

onMounted(() => {
  nextTick(autoResize)
  document.addEventListener('paste', handlePaste)
  if (chatMessages.value.length) {
    isAutoScroll.value = true
    showScrollToBottom.value = false
    void scrollToBottom()
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('paste', handlePaste)
  stop()
})

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
</script>

<style scoped>
.note-chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  min-width: 0;
  background: #fff;
  overflow-x: hidden;
}

.chat-main {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  background: #fff;
  overflow-x: hidden;
}

.messages {
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
  box-sizing: border-box;
  width: 100%;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 0px;
  background: #fff;
  scrollbar-width: thin;
  scrollbar-color: #d1d5db #fff;
}

.messages::-webkit-scrollbar {
  width: 8px;
}

.messages::-webkit-scrollbar-track {
  background: #fff;
}

.messages::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 4px;
}

.messages::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

.messages--empty { 
  justify-content: center; 
  align-items: center; 
  color: #94a3b8; 
  font-size: 13px; 
}

.empty-hint { 
  text-align: center; 
}

/* Loading bubble */
.loading-bubble {
  align-self: flex-start;
  background: #f1f5f9;
  border-radius: 16px;
  padding: 12px 18px;
  max-width: 80%;
  animation: fadeIn 0.2s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.loader-dots { 
  display: inline-flex; 
  gap: 4px; 
}

.loader-dots span { 
  width: 8px; 
  height: 8px; 
  border-radius: 50%; 
  background: #64748b; 
  animation: loaderDots 1.2s infinite ease-in-out; 
}

.loader-dots span:nth-child(2) { 
  animation-delay: 0.15s; 
}

.loader-dots span:nth-child(3) { 
  animation-delay: 0.3s; 
}

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

.composer { 
  border-top: 1px solid #eef2f7; 
  background: #fff; 
  padding: 12px 14px; 
  display: flex; 
  flex-direction: column; 
  gap: 10px;
  box-sizing: border-box;
  width: 100%;
} 

.composer.drag-over { 
  border-color: rgba(37, 99, 235, 0.45); 
  background: rgba(37, 99, 235, 0.06); 
}

.composer-inner { 
  display: flex; 
  align-items: center; 
  gap: 10px;
  min-width: 0;
} 

.composer-accessories { 
  display: flex; 
  align-items: center;
  gap: 6px; 
}

.icon-btn { 
  width: 32px; 
  height: 32px; 
  display: inline-flex; 
  align-items: center; 
  justify-content: center; 
  border-radius: 10px; 
  border: 1px solid rgba(148, 163, 184, 0.35); 
  background: #fff; 
  color: #334155; 
  cursor: pointer;
  transition: background .15s ease, border-color .15s ease; 
}

.icon-btn:hover { 
  background: rgba(241, 245, 249, 0.9); 
  border-color: rgba(148, 163, 184, 0.6); 
}

.icon-btn:active { 
  border-color: rgba(37, 99, 235, 0.4); 
}

.mic-btn.recording { 
  border-color: rgba(34, 197, 94, 0.55); 
  background: rgba(34, 197, 94, 0.16); 
  color: #15803d; 
}

.mic-btn:disabled { 
  opacity: .55; 
  cursor: not-allowed; 
}

.composer-input { 
  flex: 1; 
  min-width: 0;
  border-radius: 12px; 
  border: 1px solid rgba(148, 163, 184, 0.45); 
  background: #fff; 
  padding: 10px 12px; 
  font-size: 14px; 
  min-height: 40px; 
  max-height: 220px; 
  resize: none; 
  line-height: 1.6; 
  color: #0f172a; 
  transition: border-color .2s, box-shadow .2s; 
}

.composer-input:focus-visible { 
  outline: none; 
  border-color: rgba(59, 130, 246, 0.85); 
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18); 
}

.primary-action { 
  width: 36px; 
  height: 36px; 
  display: inline-flex; 
  align-items: center; 
  justify-content: center; 
  border-radius: 12px; 
  border: 1px solid rgba(37, 99, 235, 0.45); 
  background: #2563eb; 
  color: #fff; 
  cursor: pointer;
  transition: transform .15s ease, box-shadow .15s ease, background .15s ease; 
}

.primary-action:hover { 
  transform: translateY(-1px); 
  box-shadow: 0 10px 18px rgba(37, 99, 235, 0.25); 
  background: #1d4ed8; 
}

.primary-action:disabled { 
  opacity: .55; 
  cursor: not-allowed; 
  transform: none; 
  box-shadow: none; 
}

.primary-action.is-stop { 
  border-color: rgba(14, 165, 233, 0.55); 
  background: #0ea5e9; 
}

.preview-bar,
.file-list { 
  width: 100%; 
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
  background: rgba(0, 0, 0, 0.45); 
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
  font-size: 12px; 
  color: #0f172a; 
}

.file-pill.ok { 
  background: #eefdf3; 
  border-color: #b6f0c5; 
}

.file-pill.error { 
  background: #fef2f2; 
  border-color: #fecaca; 
}

.pill-remove { 
  border: none; 
  background: transparent; 
  color: #6b7280; 
  cursor: pointer; 
}

.pill-remove:hover { 
  color: #1f2937; 
}

/* 居中底部下箭头按钮（ChatGPT 风格） */
.scroll-fab {
  position: absolute;
  left: 50%;
  bottom: 84px;
  transform: translateX(-50%);
  z-index: 6;
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
  animation: fadeInButton 0.2s ease-in-out;
}

@keyframes fadeInButton {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
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
</style>
