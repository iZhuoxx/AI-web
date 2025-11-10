<template>
  <div class="note-chat-panel">
    <header class="chat-header compact">
      <div class="header-inner">
        <div class="header-left">
          <LoadingOutlined v-if="loadding" class="header-spinner" />
          <button
            class="new-convo"
            :class="{ selected: newConvoSelected }"
            type="button"
            @click="clearMessages"
          >
            <PlusCircleOutlined class="new-convo__icon" />
            <span class="new-convo__label">新对话</span>
          </button>
        </div>
      </div>
    </header>

    <div class="chat-main">
      <div
        ref="scrollContainer"
        class="messages"
        :class="{ 'messages--empty': !hasMessages }"
        @scroll="onMessagesScroll"
      >
        <div v-if="!hasMessages" class="empty-hint">暂无对话，开始输入或录音吧。</div>
        <template v-else>
          <Message
            v-for="(msg, idx) in chatMessages"
            :key="idx"
            :message="msg"
            :class="msg.type === 1 ? 'send' : 'replay'"
          />
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
                accept="image/*,text/*,.txt,.md,.markdown,.csv,.tsv,.json,.yaml,.yml,.xml,.html,.htm,.py,.js,.ts,.pdf,application/json,application/xml,application/x-yaml,application/javascript,application/x-python,application/rtf,application/pdf,audio/*,.mp3,.wav,.m4a,.aac,.ogg,.oga,.flac,.webm"
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

      <!-- 居中底部“下箭头”悬浮按钮：不在底部时显示 -->
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
  PlusCircleOutlined,
} from '@ant-design/icons-vue'
import { message as antdMessage } from 'ant-design-vue'
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed, watch } from 'vue'
import Message from '@/components/message.vue'
import { useChat } from '@/composables/useChat'
import { useUploads } from '@/composables/useUploads'
import { useRealtimeTranscription } from '@/composables/useRealtimeTranscription'
import useSetting from '@/composables/setting'

// 固定模型为 GPT-5
const setting = useSetting()
setting.value.model = 'gpt-5'

// chat 相关
const NOTE_CHAT_TOOLS = [{ type: 'image_generation' }]
const { loadding, send, stop, messagesStore } = useChat({
  storageKey: 'notes-chat-messages',
  tools: NOTE_CHAT_TOOLS,
})

// 上传/拖拽/音频转写 相关
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

const chatMessages = messagesStore.messages
const hasMessages = computed(() => chatMessages.value.length > 0)

// 输入区
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

  if (hasPendingUploads.value) {
    await ensureAudioTranscriptions()
  }
  if (hasPendingUploads.value) {
    antdMessage.info('仍有文件处理中，请稍后再试')
    return
  }

  await ensureUploads()
  await ensureAudioTranscriptions()

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

  await send({ text, imagesDataUrls, files })
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

// ===== 新增：自动滚逻辑 =====
const scrollContainer = ref<HTMLDivElement | null>(null)
const isAutoScroll = ref(true) // 是否开启自动滚
const showScrollToBottom = ref(false) // 是否显示“向下”按钮
const BOTTOM_THRESHOLD = 12 // 判定在底部的阈值(px)

// 平滑滚到底部（不支持时回退瞬时）
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

// 点击“向下” => 滚到底并开启自动滚
const scrollToBottomAndEnableAuto = async () => {
  await scrollToBottom()
  isAutoScroll.value = true
  showScrollToBottom.value = false
}

// 消息列表滚动事件（用户上滑 => 关闭自动滚并显示按钮）
const onMessagesScroll = () => {
  const el = scrollContainer.value
  if (!el) return
  const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - BOTTOM_THRESHOLD
  if (!atBottom) {
    if (isAutoScroll.value) isAutoScroll.value = false
    showScrollToBottom.value = true
  } else {
    // 到底部隐藏按钮；是否开启自动滚由用户点击按钮决定
    showScrollToBottom.value = false
  }
}

// 只有在 isAutoScroll 为 true 时，收到新消息才自动滚动
watch([chatMessages, loadding], async () => {
  if (isAutoScroll.value) {
    await scrollToBottom()
  }
}, { immediate: true })

// ===== “新对话”按钮选中高亮（短暂） =====
const newConvoSelected = ref(false)
const clearMessages = () => {
  messagesStore.clearMessages()
  newConvoSelected.value = true
  setTimeout(() => (newConvoSelected.value = false), 600)
}

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
.note-chat-panel { display:flex; flex-direction:column; height:100%; min-height:0; background:#fff; }

/* 更扁、更紧凑的顶部栏 */
.chat-header { padding:8px 12px; border-bottom:none; background:#fff; }
.chat-header.compact { padding:6px 10px; }
.header-inner { display:flex; justify-content:flex-end; align-items:center; gap:8px; }
.header-left { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-left:auto; justify-content:flex-end; }
.header-spinner { color:#2563eb; font-size:16px; }

/* 新对话按钮：默认白底，仅选中(聚焦/按下)时蓝色 */
.new-convo {
  display:inline-flex; align-items:center; gap:6px; padding:0 10px; height:28px;
  border:1px solid rgba(148,163,184,0.35);
  background:#fff; color:#1f2937; font-size:13px; font-weight:500; cursor:pointer;
  border-radius:999px; transition:background .18s ease, color .18s ease, box-shadow .18s ease, transform .12s ease, border-color .18s ease;
}
.new-convo:hover {
  border-color:rgba(37,99,235,0.45);
  background:rgba(37,99,235,0.12);
  color:#1d4ed8;
}
.new-convo:focus-visible {
  outline:none;
  box-shadow:0 0 0 2px rgba(37,99,235,0.2);
}
.new-convo:active {
  transform:translateY(1px);
}
.new-convo.selected {
  border-color:rgba(148,163,184,0.35);
  background:#fff;
  color:#1f2937;
  box-shadow:none;
}
.new-convo__icon { font-size:16px; color:inherit; }
.new-convo__label { line-height:1; }

.chat-main { position:relative; /* 让悬浮按钮定位到容器内部 */ flex:1; display:flex; flex-direction:column; min-height:0; background:#fff; }
.messages { flex:1; min-height:0; overflow-y:auto; padding:12px 14px; display:flex; flex-direction:column; gap:14px; background:#fff; }
.messages--empty { justify-content:center; align-items:center; color:#94a3b8; font-size:13px; }
.empty-hint { text-align:center; }

.composer { border-top:1px solid #eef2f7; background:#fff; padding:12px 14px; display:flex; flex-direction:column; gap:10px; }
.composer.drag-over { border-color:rgba(37,99,235,0.45); background:rgba(37,99,235,0.06); }
.composer-inner { display:flex; align-items:flex-end; gap:10px; }
.composer-accessories { display:flex; gap:6px; }
.icon-btn { width:32px; height:32px; display:inline-flex; align-items:center; justify-content:center; border-radius:10px; border:1px solid rgba(148,163,184,0.35); background:#fff; color:#334155; transition:background .15s ease, border-color .15s ease; }
.icon-btn:hover { background:rgba(241,245,249,0.9); border-color:rgba(148,163,184,0.6); }
.icon-btn:active { border-color:rgba(37,99,235,0.4); }
.mic-btn.recording { border-color:rgba(34,197,94,0.55); background:rgba(34,197,94,0.16); color:#15803d; }
.mic-btn:disabled { opacity:.55; cursor:not-allowed; }

.composer-input { flex:1; border-radius:12px; border:1px solid rgba(148,163,184,0.45); background:#fff; padding:10px 12px; font-size:14px; min-height:40px; max-height:220px; resize:none; line-height:1.6; color:#0f172a; transition:border-color .2s, box-shadow .2s; }
.composer-input:focus-visible { outline:none; border-color:rgba(59,130,246,0.85); box-shadow:0 0 0 3px rgba(59,130,246,0.18); }

.primary-action { width:36px; height:36px; display:inline-flex; align-items:center; justify-content:center; border-radius:12px; border:1px solid rgba(37,99,235,0.45); background:#2563eb; color:#fff; transition:transform .15s ease, box-shadow .15s ease, background .15s ease; }
.primary-action:hover { transform:translateY(-1px); box-shadow:0 10px 18px rgba(37,99,235,0.25); background:#1d4ed8; }
.primary-action:disabled { opacity:.55; cursor:not-allowed; transform:none; box-shadow:none; }
.primary-action.is-stop { border-color:rgba(14,165,233,0.55); background:#0ea5e9; }

.preview-bar,
.file-list { width:100%; display:flex; gap:8px; flex-wrap:wrap; }
.preview-item { position:relative; width:84px; height:84px; border-radius:10px; overflow:hidden; border:1px solid #e5e7eb; }
.preview-item img { width:100%; height:100%; object-fit:cover; display:block; }
.preview-remove { position:absolute; top:4px; right:4px; border:none; background:rgba(0,0,0,0.45); color:#fff; width:20px; height:20px; border-radius:6px; display:flex; align-items:center; justify-content:center; cursor:pointer; }

.file-pill { position:relative; display:flex; align-items:center; gap:8px; padding:6px 10px; border:1px solid #e5e7eb; border-radius:999px; background:#f9fafb; font-size:12px; color:#0f172a; }
.file-pill.ok { background:#eefdf3; border-color:#b6f0c5; }
.file-pill.error { background:#fef2f2; border-color:#fecaca; }
.pill-remove { border:none; background:transparent; color:#6b7280; cursor:pointer; }
.pill-remove:hover { color:#1f2937; }

/* 居中底部下箭头按钮（ChatGPT 风格） */
.scroll-fab {
  position: absolute;
  left: 50%;
  /* 按你的输入区高度微调：72~100px 都可 */
  bottom: 84px;
  transform: translateX(-50%);
  z-index: 6;

  width: 40px;
  height: 40px;
  border-radius: 999px;

  border: 1px solid rgba(0,0,0,0.1);
  background: #fff;
  color: #0f172a;

  display: inline-flex;
  align-items: center;
  justify-content: center;

  box-shadow: 0 6px 18px rgba(0,0,0,0.10);
  cursor: pointer;

  transition: transform .12s ease, box-shadow .15s ease, border-color .15s ease, background .15s ease, opacity .15s ease;
}
.scroll-fab:hover {
  transform: translateX(-50%) translateY(-1px);
  box-shadow: 0 10px 24px rgba(0,0,0,0.14);
  border-color: rgba(0,0,0,0.18);
}
.scroll-fab:active { transform: translateX(-50%) translateY(0); }
.scroll-fab .chevron-down { width: 20px; height: 20px; display: block; }
</style>
