import { ref } from 'vue'
import type { TFileInMessage } from '@/types/chat'
import { transcribeAudio } from '@/services/api/ai'
import { uploadOpenAIFile } from '@/services/api/attachments'

export type GenericItem = {
  name: string
  size: number
  type: string
  file?: File
  text?: string
  truncated?: boolean
  fileId?: string
  kind: 'file' | 'audio'
  status: 'pending'|'ok'|'error'
  error?: string
}

const ALLOWED_FILE_EXTS = new Set([
  'c','cpp','cs','css','csv','doc','docx','gif','go','html','java','jpeg','jpg','js','json',
  'md','pdf','php','pkl','png','pptx','py','rb','tar','tex','ts','txt','webp','xlsx','xml','zip',
])

function getExt(file: File): string {
  const ext = file.name.includes('.') ? file.name.split('.').pop() || '' : ''
  return ext.toLowerCase()
}

function isMp3(file: File): boolean {
  const mime = (file.type || '').toLowerCase()
  if (mime === 'audio/mpeg' || mime === 'audio/mp3') return true
  return getExt(file) === 'mp3'
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
  const audioJobs = new Map<GenericItem, Promise<void>>()

  async function addGenericFiles(files: File[]) {
    const others = files.filter(f => !/^image\//.test(f.type))
    for (const f of others) {
      if (isMp3(f)) {
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
      const ext = getExt(f)
      if (!ALLOWED_FILE_EXTS.has(ext)) {
        console.warn('忽略不支持的文件', f.name)
        continue
      }
      genericFiles.value.push({
        name: f.name,
        size: f.size,
        type: f.type || 'application/octet-stream',
        file: f,
        status: 'pending',
        kind: 'file',
      })
    }
    await ensureUploads()
  }
  function removeGenericFile(idx: number) {
    genericFiles.value.splice(idx, 1)
  }

  async function ensureUploads() {
    for (const it of genericFiles.value) {
      if (it.kind === 'audio') {
        queueAudioTranscription(it)
        continue
      }
      if (it.status !== 'pending' || !it.file) continue
      try {
        const resp = await uploadOpenAIFile(it.file as File, {
          purpose: 'assistants',
          expiresAfterAnchor: 'created_at',
          expiresAfterSeconds: 2592000,
        })
        if (!resp?.id) {
          throw new Error('empty file id in response')
        }
        it.fileId = String(resp.id)
        it.kind = it.kind ?? 'file'
        it.status = 'ok'
        it.file = undefined
      } catch (e) {
        console.error('file upload error:', e)
        it.status = 'error'
      }
    }
  }

  async function transcribeAudioRequest(file: File): Promise<string> {
    const data = await transcribeAudio(file, { responseFormat: 'json' })
    const text = (data?.text || '').trim()
    if (!text) {
      throw new Error('transcription returned empty text')
    }
    return text
  }

  function queueAudioTranscription(it: GenericItem) {
    if (!it.file || audioJobs.has(it) || it.status === 'ok') return
    it.status = 'pending'
    const job = transcribeAudioRequest(it.file)
      .then(text => {
        it.text = text
        it.truncated = false
        it.status = 'ok'
        it.error = undefined
        it.file = undefined
        it.kind = 'file'
      })
      .catch((err: any) => {
        console.error('audio transcription error', err)
        it.status = 'error'
        it.error = err?.message || String(err)
      })
      .finally(() => {
        audioJobs.delete(it)
      })
    audioJobs.set(it, job)
  }

  function ensureAudioJobs() {
    for (const it of genericFiles.value) {
      if (it.kind === 'audio' && it.file) {
        queueAudioTranscription(it)
      }
    }
  }

  async function waitForAudioJobs() {
    if (!audioJobs.size) return
    const jobs = Array.from(audioJobs.values())
    await Promise.allSettled(jobs)
  }

  async function ensureAudioTranscriptions() {
    ensureAudioJobs()
    await waitForAudioJobs()
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
    genericFiles.value = []
    audioJobs.clear()
  }

  /**
   生成消息中可用的文件数组
   */
  function filesForChat(): TFileInMessage[] {
    return genericFiles.value
      .filter(it => it.status === 'ok' && (it.fileId || typeof it.text === 'string'))
      .map<TFileInMessage>(it => ({
        name: it.name,
        type: it.type,
        text: it.text,
        truncated: it.truncated,
        fileId: it.fileId,
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
