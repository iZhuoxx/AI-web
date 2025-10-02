<!-- src/App.vue -->
<script setup lang="ts">
import {
  ClearOutlined, LoadingOutlined, SettingOutlined,
  PictureOutlined, CloseOutlined, PaperClipOutlined,
  SendOutlined, PauseCircleOutlined
} from '@ant-design/icons-vue'

import Message from './components/message.vue'
import SettingModal from './components/setting.vue'

import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import useMessages from '@/composables/messages'
import { useChat } from '@/composables/useChat'
import { useUploads } from '@/composables/useUploads'

const messages = useMessages()
const { loadding, send, stop } = useChat()

const {
  imageFiles, imagePreviews, genericFiles, dragOver,
  onPickImages, addGenericFiles, removeGenericFile,
  onPaste, onDragOver, onDragLeave, onDrop,
  ensureUploads, fileToDataURL, removeImage, resetAll,
  filesForChat,
  addImages,                
} = useUploads()

const chatMessages = messages.messages
const hasMessages = computed(() => chatMessages.value.length > 0)

const handlePaste = (event: ClipboardEvent) => {
  void onPaste(event)
}

const state = reactive({ message: '', visible: false })
const hasPayload = computed(
  () => state.message.trim().length > 0 || imageFiles.value.length > 0 || genericFiles.value.length > 0
)

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const MAX_TEXTAREA_H = 240
const autoResize = () => {
  const el = textareaRef.value; if (!el) return
  el.style.height = '0px'
  const h = Math.min(el.scrollHeight, MAX_TEXTAREA_H)
  el.style.height = h + 'px'
  el.style.overflowY = el.scrollHeight > MAX_TEXTAREA_H ? 'auto' : 'hidden'
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

  // 1) 先确保文本文件上传，拿到提取结果
  await ensureUploads()

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
  await nextTick(); autoResize()

  // 5) 发送
  await send({ text, imagesDataUrls, files })
}

async function handlePrimaryAction() {
  if (loadding.value) {
    stop()
    return
  }
  if (!hasPayload.value) return
  await onSend()
}
</script>


<template>
  <div id="layout">
    <header id="header" class="bg-white/80 backdrop-blur text-gray-900 h-12 flex items-center shadow-sm">
      <div class="header-container">
        <div class="header-inner">
          <div class="left">
            <LoadingOutlined v-if="loadding" class="mr-2" />
            <span class="title">Kooii AI工具箱</span>

            <a-tooltip>
              <a-popconfirm
                title="你确定要清空消息记录吗?"
                ok-text="是的"
                cancel-text="取消"
                @confirm="clearMessages"
              >
                <ClearOutlined class="icon" />
              </a-popconfirm>
            </a-tooltip>

            <a-tooltip>
              <template #title>Settings</template>
              <SettingOutlined class="icon" @click="state.visible = true" />
            </a-tooltip>
          </div>
        </div>
      </div>
    </header>

    <div id="layout-body">
      <main id="main">
        <div class="container" :class="{ 'container--empty': !hasMessages }">
          <div class="chat-container" :class="{ 'chat-container--empty': !hasMessages }">
            <div v-if="!hasMessages" class="welcome-placeholder">
              请问有什么可以帮助您的吗？
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
                  <label class="icon-btn" title="选择文本类文件或 PDF">
                    <input
                      type="file"
                      multiple
                      accept="text/*,.txt,.md,.markdown,.csv,.tsv,.json,.yaml,.yml,.xml,.html,.htm,.py,.js,.ts,.pdf,application/json,application/xml,application/x-yaml,application/javascript,application/x-python,application/rtf,application/pdf"
                      style="display:none"
                      @change="(e:any)=>addGenericFiles(Array.from(e.target.files||[]))"
                    />
                    <PaperClipOutlined />
                  </label>
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
                  :disabled="!loadding && !hasPayload"
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

    <setting-modal v-model:visible="state.visible" />
  </div>
</template>

<style scoped>
/* ====== 布局基础 ====== */
#layout { display: flex; flex-direction: column; width: 100vw; height: 100vh; background: #f7f7f8; }
#layout-body { flex: 1 1 0%; overflow-y: auto; display: flex; flex-direction: column; }
#main { flex: 1 1 auto; display: flex; padding: 24px 0 0; }
.container { flex: 1 1 auto; display: flex; flex-direction: column; max-width: 900px; margin: 0 auto; padding: 0 16px 48px; transition: padding .3s ease; }
.container--empty {
  flex: 1 1 auto;
  justify-content: center;
  align-items: center;
  gap: 48px;
  padding: 0 16px;
  min-height: calc(100vh - 48px);
}

/* 顶部栏 */
#header { position: sticky; top: 0; z-index: 10; }
.header-container { width: 100%; padding: 0 16px; }
#header .header-inner { display: flex; align-items: center; justify-content: space-between; height: 48px; }
#header .title { font-weight: 600; }
#header .icon { margin-left: 12px; cursor: pointer; color: #6b7280; transition: color .15s ease, transform .15s ease; }
#header .icon:hover { color: #111827; transform: translateY(-1px); }

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
.chat-container--empty {
  align-items: center;
  justify-content: center;
  padding: 0;
  gap: 32px;
  text-align: center;
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
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
  padding-left: var(--chat-offset);
  padding-bottom: 48px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: padding .3s ease, transform .3s ease, margin .3s ease;
  margin-top: auto;
}
.composer-stage--empty {
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  padding-left: 0;
  padding-bottom: 0;
  align-items: center;
  transform: none;
  margin-top: 0;
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

@supports (padding: env(safe-area-inset-bottom)) {
  .composer-stage { padding-bottom: calc(48px + env(safe-area-inset-bottom)); }
}
</style>
