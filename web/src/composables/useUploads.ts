// src/composables/useUploads.ts
import { ref } from 'vue'
import type { TFileInMessage } from '@/types'
import {
  DEFAULT_AUDIO_MODEL,
  TRANSCRIBE_ENDPOINT,
  isAudioFile,
} from '@/constants/audio'

export type GenericItem = {
  name: string
  size: number
  type: string
  file?: File
  viewUrl?: string
  text?: string
  truncated?: boolean
  fileId?: string
  purpose?: 'vision' | 'assistants'
  kind: 'text' | 'file' | 'audio'
  status: 'pending'|'ok'|'error'
  error?: string
}

const INTERNAL_TOKEN = import.meta.env.VITE_INTERNAL_TOKEN as string | undefined

const TEXTUAL_MIME_PREFIXES = ['text/']
const TEXTUAL_MIME_TYPES = new Set([
  'application/json',
  'application/xml',
  'application/x-yaml',
  'application/yaml',
  'application/javascript',
  'application/x-javascript',
  'application/typescript',
  'application/x-python',
  'application/x-python-code',
  'application/rtf',
])

const TEXT_EXTS = new Set(['txt','md','markdown','csv','tsv','json','yaml','yml','xml','html','htm','py','js','ts'])
function isTextLike(file: File): boolean {
  const mime = file.type || ''
  if (TEXTUAL_MIME_PREFIXES.some(prefix => mime.startsWith(prefix))) return true
  if (TEXTUAL_MIME_TYPES.has(mime)) return true
  const ext = file.name.includes('.') ? file.name.split('.').pop()?.toLowerCase() : ''
  if (ext && TEXT_EXTS.has(ext)) return true
  return false
}

function isPdf(file: File): boolean {
  const mime = (file.type || '').toLowerCase()
  if (mime === 'application/pdf') return true
  const ext = file.name.includes('.') ? file.name.split('.').pop()?.toLowerCase() : ''
  return ext === 'pdf'
}

export function useUploads() {
  // 图片
  const imageFiles = ref<File[]>([])
  const imagePreviews = ref<string[]>([])

  function addImages(files: File[]) {
    const imgs = files.filter(f => /^image\//.test(f.type))
    imageFiles.value = [...imageFiles.value, ...imgs]
    imgs.forEach(f => {
      const reader = new FileReader()
      reader.onload = () => imagePreviews.value.push(String(reader.result || ''))
      reader.readAsDataURL(f)
    })
  }
  function onPickImages(e: Event) {
    const input = e.target as HTMLInputElement
    addImages(Array.from(input.files || []))
    input.value = ''
  }
  function removeImage(idx: number) {
    imageFiles.value.splice(idx, 1)
    imagePreviews.value.splice(idx, 1)
  }

  // 通用文件
  const genericFiles = ref<GenericItem[]>([])
  async function addGenericFiles(files: File[]) {
    const others = files.filter(f => !/^image\//.test(f.type))
    for (const f of others) {
      if (isAudioFile(f)) {
        genericFiles.value.push({
          name: f.name,
          size: f.size,
          type: f.type || 'audio/mpeg',
          file: f,
          status: 'pending',
          kind: 'audio',
        })
        continue
      }
      const pdf = isPdf(f)
      if (!pdf && !isTextLike(f)) {
        console.warn('忽略不支持的文件', f.name)
        continue
      }
      genericFiles.value.push({
        name: f.name,
        size: f.size,
        type: f.type || 'application/octet-stream',
        file: f,
        // 为前端预览生成一个临时 blob URL（刷新页面会失效）
        viewUrl: URL.createObjectURL(f),
        status: 'pending',
        kind: pdf ? 'file' : 'text',
      })
    }
    await ensureUploads()
  }
  function removeGenericFile(idx: number) {
    const it = genericFiles.value[idx]
    if (it?.viewUrl) URL.revokeObjectURL(it.viewUrl)
    genericFiles.value.splice(idx, 1)
  }

  async function ensureUploads() {
    for (const it of genericFiles.value) {
      if (it.kind === 'audio') continue
      if (it.status !== 'pending' || !it.file) continue
      try {
        const fd = new FormData()
        fd.append('file', it.file as File)

        const r = await fetch('/api/files/', {
          method: 'POST',
          body: fd,
          credentials: 'include',
          headers: { 'X-API-KEY': INTERNAL_TOKEN ?? '' },
        })
        if (!r.ok) {
          const text = await r.text().catch(()=> '')
          throw new Error(`upload failed: HTTP ${r.status}${text?` - ${text}`:''}`)
        }
        const data = await r.json().catch(()=> ({}))
        if (typeof data?.text === 'string' && data.text.trim()) {
          it.text = data.text
          it.truncated = Boolean(data?.truncated)
          it.kind = 'text'
          it.status = 'ok'
          it.file = undefined
        } else if (data?.file_id) {
          it.fileId = String(data.file_id)
          if (data?.purpose === 'vision' || data?.purpose === 'assistants') {
            it.purpose = data.purpose
          }
          it.kind = 'file'
          it.status = 'ok'
          it.file = undefined
        } else {
          throw new Error('empty payload in response')
        }
      } catch (e) {
        console.error('file upload error:', e)
        it.status = 'error'
      }
    }
  }

  // 粘贴 & 拖拽
  async function onPaste(e: ClipboardEvent) {
    const items = Array.from(e.clipboardData?.items || [])
    const files: File[] = []
    for (const it of items) {
      if (it.kind === 'file') {
        const f = it.getAsFile()
        if (f) files.push(f)
      }
    }
    if (!files.length) return
    const imgs = files.filter(f => /^image\//.test(f.type))
    const others = files.filter(f => !/^image\//.test(f.type))
    if (imgs.length) addImages(imgs)
    if (others.length) await addGenericFiles(others)
  }
  const dragOver = ref(false)
  function onDragOver(e: DragEvent) { e.preventDefault(); dragOver.value = true }
  function onDragLeave(e: DragEvent) { e.preventDefault(); dragOver.value = false }
  async function onDrop(e: DragEvent) {
    e.preventDefault(); dragOver.value = false
    const files = Array.from(e.dataTransfer?.files || [])
    const imgs = files.filter(f => /^image\//.test(f.type))
    const others = files.filter(f => !/^image\//.test(f.type))
    if (imgs.length) addImages(imgs)
    if (others.length) await addGenericFiles(others)
  }

  // 工具
  function fileToDataURL(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result || ''))
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }
  function resetAll() {
    imageFiles.value = []
    imagePreviews.value = []
    // 回收本地 URL，避免内存泄漏
    genericFiles.value.forEach(it => it.viewUrl && URL.revokeObjectURL(it.viewUrl))
    genericFiles.value = []
  }

  async function transcribeAudioRequest(file: File): Promise<string> {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('model', DEFAULT_AUDIO_MODEL)
    fd.append('response_format', 'text')

    const headers: Record<string, string> = {}
    if (INTERNAL_TOKEN) {
      headers['X-API-KEY'] = INTERNAL_TOKEN
    }

    const res = await fetch(TRANSCRIBE_ENDPOINT, {
      method: 'POST',
      body: fd,
      credentials: 'include',
      headers,
    })

    if (!res.ok) {
      const errText = await res.text().catch(() => '')
      throw new Error(errText || `transcription failed: HTTP ${res.status}`)
    }

    const data = await res.json().catch(() => ({})) as { text?: string }
    const text = (data?.text || '').trim()
    if (!text) {
      throw new Error('transcription returned empty text')
    }
    return text
  }

  async function ensureAudioTranscriptions() {
    for (const it of genericFiles.value) {
      if (it.kind !== 'audio') continue
      if (it.status === 'ok') continue
      if (!it.file) continue
      try {
        const text = await transcribeAudioRequest(it.file)
        it.text = text
        it.truncated = false
        it.status = 'ok'
        it.error = undefined
        it.file = undefined
      } catch (err: any) {
        console.error('audio transcription error', err)
        it.status = 'error'
        it.error = err?.message || String(err)
      }
    }
  }

  /**
   生成消息中可用的文件数组
   * - 附带提取后的纯文本
   * - 保留临时 viewUrl（仅用于当前会话内展示）
   */
  function filesForChat(): TFileInMessage[] {
    return genericFiles.value
      .filter(it => it.status === 'ok' && (typeof it.text === 'string' || it.fileId))
      .map<TFileInMessage>(it => ({
        name: it.name,
        type: it.type,
        text: it.text,
        truncated: it.truncated,
        fileId: it.fileId,
        purpose: it.purpose,
        viewUrl: it.viewUrl,
      }))
  }

  return {
    // state
    imageFiles, imagePreviews,
    genericFiles, dragOver,
    // actions
    onPickImages, addImages, removeImage,
    addGenericFiles, onPaste, onDragOver, onDragLeave, onDrop,
    removeGenericFile, ensureUploads, ensureAudioTranscriptions, fileToDataURL, resetAll,
    // for chat
    filesForChat,
  }
}
