<!-- src/App.vue -->
<script setup lang="ts">
import dayjs from 'dayjs'
import {
  ClearOutlined, LoadingOutlined, SettingOutlined,
  PictureOutlined, CloseOutlined, PaperClipOutlined
} from '@ant-design/icons-vue'

import Message from './components/message.vue'
import SettingModal from './components/setting.vue'

import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
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
  addImages,                 // ✅ 全局拖拽会用到
} = useUploads()

const state = reactive({ message: '', visible: false })
const createdAt = dayjs().format('YYYY-MM-DD HH:mm:ss')

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const MAX_TEXTAREA_H = 240
const autoResize = () => {
  const el = textareaRef.value; if (!el) return
  el.style.height = '0px'
  const h = Math.min(el.scrollHeight, MAX_TEXTAREA_H)
  el.style.height = h + 'px'
  el.style.overflowY = el.scrollHeight > MAX_TEXTAREA_H ? 'auto' : 'hidden'
}

/** 仅当拖拽内容包含文件时返回 true */
function isFileDrag(e: DragEvent) {
  const types = e.dataTransfer?.types
  return !!types && Array.from(types).includes('Files')
}

/** 这些函数要有稳定引用，方便 removeEventListener */
function globalDragOver(e: DragEvent) {
  if (!isFileDrag(e)) return
  e.preventDefault()
}

function globalDrop(e: DragEvent) {
  if (!isFileDrag(e)) return
  e.preventDefault()

  // 如果在输入区域(composer)里放下，就让本地 @drop 处理，避免重复
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
  window.addEventListener('paste', onPaste)

  // ✅ 全屏拖拽，仅对“文件”生效；具名函数，便于移除
  window.addEventListener('dragover', globalDragOver)
  window.addEventListener('drop', globalDrop)
})

onBeforeUnmount(() => {
  window.removeEventListener('paste', onPaste)
  window.removeEventListener('dragover', globalDragOver)
  window.removeEventListener('drop', globalDrop)
})

function clearMessages() {
  messages.clearMessages()
}

async function onSend(ev: { preventDefault: () => void }) {
  ev.preventDefault()
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
</script>


<template>
  <div id="layout">
    <header id="header" class="bg-white/80 backdrop-blur text-gray-900 h-12 flex items-center shadow-sm">
      <div class="header-container">
        <div class="header-inner">
          <div class="left">
            <LoadingOutlined v-if="loadding" class="mr-2" />
            <span class="title">极客AI工具箱</span>

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
        <div class="container">
          <div class="chat-container">
            <div class="meta">
              <div class="meta-line">Channel created</div>
              <div class="meta-line">{{ createdAt }}</div>
            </div>

            <Message
              v-for="(msg, idx) in messages.messages.value"
              :key="idx"
              :message="msg"
              :class="msg.type === 1 ? 'send' : 'replay'"
            />
          </div>
        </div>
      </main>
    </div>

    <footer id="footer" class="chat-footer">
      <div class="composer" :class="{ 'drag-over': dragOver }" @dragover.prevent="onDragOver" @dragleave="onDragLeave" @drop="onDrop">
        <div class="composer-inner">
          <textarea
            ref="textareaRef"
            v-model="state.message"
            placeholder="发消息..."
            @input="autoResize"
            @keydown.enter.exact.prevent="onSend($event)"
            @keydown.enter.shift.exact.stop
            class="composer-input"
            rows="1"
          />
          <div class="composer-actions">
            <label class="action-btn upload" title="选择图片">
              <input type="file" accept="image/*" multiple style="display:none" @change="onPickImages" />
              <PictureOutlined />
            </label>
            <label class="action-btn upload" title="选择文本类文件或 PDF">
              <input
                type="file"
                multiple
                accept="text/*,.txt,.md,.markdown,.csv,.tsv,.json,.yaml,.yml,.xml,.html,.htm,.py,.js,.ts,.pdf,application/json,application/xml,application/x-yaml,application/javascript,application/x-python,application/rtf,application/pdf"
                style="display:none"
                @change="(e:any)=>addGenericFiles(Array.from(e.target.files||[]))"
              />
              <PaperClipOutlined />
            </label>
            <button class="action-btn stop" @click="stop" :disabled="!loadding">停止</button>
            <button class="action-btn send" @click="onSend($event)">发送</button>
          </div>
        </div>

        <!-- 图片预览 -->
        <div v-if="imagePreviews.length" class="preview-bar">
          <div v-for="(src,i) in imagePreviews" :key="'img-'+i" class="preview-item">
            <img :src="src" alt="preview" />
            <button class="preview-remove" @click="removeImage(i)"><CloseOutlined /></button>
          </div>
        </div>

        <!-- 文件胶囊 -->
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
    </footer>

    <setting-modal v-model:visible="state.visible" />
  </div>
</template>

<style scoped>
/* ====== 布局基础 ====== */
#layout { display: flex; flex-direction: column; width: 100vw; height: 100vh; background: #f7f7f8; }
#layout-body { flex: 1 1 0%; overflow-y: auto; display: flex; flex-direction: column; }
#main { flex: 1 1 0%; padding: 24px 0; }
.container { max-width: 900px; margin: 0 auto; padding: 0 16px; }

/* 顶部栏 */
#header { position: sticky; top: 0; z-index: 10; }
.header-container { width: 100%; padding: 0 16px; }
#header .header-inner { display: flex; align-items: center; justify-content: space-between; height: 48px; }
#header .title { font-weight: 600; }
#header .icon { margin-left: 12px; cursor: pointer; color: #6b7280; transition: color .15s ease, transform .15s ease; }
#header .icon:hover { color: #111827; transform: translateY(-1px); }

/* 聊天容器 */
.chat-container{ padding-left: var(--chat-offset); }

/* 底部输入区 */
#footer { border-top: 1px solid #e5e7eb; background: #fff; }
.composer { position: relative; padding: 12px 0; border-radius: 12px; }
.composer.drag-over { outline: 2px dashed #93c5fd; outline-offset: 4px; background: rgba(147,197,253,.08); }
.composer-inner { max-width: 640px; margin: 0 auto; display: flex; align-items: stretch; gap: 10px; }
.composer-input { flex: 1 1 auto; background: #fff; border: 1px solid #e5e7eb; border-radius: 16px; padding: 10px 14px; box-shadow: 0 2px 8px rgba(0,0,0,.03); transition: border-color .15s ease, box-shadow .15s ease; }
.composer-input:focus-within { border-color: #93c5fd; box-shadow: 0 0 0 3px rgba(147,197,253,.35); }
.composer-actions { display: flex; gap: 8px; flex: 0 0 auto; }
.action-btn { height: 36px; padding: 0 12px; border: 1px solid #e5e7eb; background: #f3f4f6; color: #111827; border-radius: 10px; display:flex; align-items:center; gap:6px; flex-shrink: 0; min-width: 72px; justify-content: center; white-space: nowrap; appearance: none; -webkit-appearance: none; box-shadow: 0 2px 6px rgba(0,0,0,.04); transition: background .15s ease, border-color .15s ease, box-shadow .15s ease, color .15s ease; }
.action-btn:hover { background: #eef2f7; border-color: #dde3ea; }
.action-btn:active { box-shadow: inset 0 1px 2px rgba(0,0,0,.08); }
.action-btn.upload { width: 36px; justify-content: center; padding: 0; }

/* 预览条 */
.preview-bar { max-width: 640px; margin: 8px auto 0; display: flex; gap: 8px; flex-wrap: wrap; }
.preview-item { position: relative; width: 84px; height: 84px; border-radius: 10px; overflow: hidden; border: 1px solid #e5e7eb; }
.preview-item img { width: 100%; height: 100%; object-fit: cover; display:block; }
.preview-remove { position: absolute; top: 4px; right: 4px; border: none; background: rgba(0,0,0,.45); color: #fff; width: 20px; height: 20px; border-radius: 6px; display:flex; align-items:center; justify-content:center; }

/* 文件胶囊列表 */
.file-list { max-width: 640px; margin: 8px auto 0; display: flex; gap: 8px; flex-wrap: wrap; }
.file-pill { position: relative; display:flex; align-items:center; gap:8px; padding: 6px 10px; border: 1px solid #e5e7eb; border-radius: 999px; background: #f9fafb; }
.file-pill .name { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-pill .meta { color: #6b7280; font-size: 12px; }
.file-pill .status { font-size: 12px; color: #6b7280; }
.file-pill.ok { background: #eefdf3; border-color: #b6f0c5; }
.file-pill.error { background: #fef2f2; border-color: #fecaca; }
.pill-remove { border:none; background: transparent; color:#6b7280; }
.pill-remove:hover { color:#111827; }
.action-btn.send { font-weight: 600; background: #2563eb; color: #fff; border-color: #2563eb; }
.action-btn.send:hover { background: #1d4ed8; border-color: #1d4ed8; }
.action-btn.send:disabled { opacity: .6; cursor: not-allowed; }
.action-btn.stop[disabled] {
  opacity: .5;
  cursor: not-allowed;
  pointer-events: none; /* 视觉与交互双保险 */
}

/* 移动端键盘遮挡与安全区 */
@supports (padding: env(safe-area-inset-bottom)) {
  #footer .composer { padding-bottom: calc(12px + env(safe-area-inset-bottom)); }
}
</style>
