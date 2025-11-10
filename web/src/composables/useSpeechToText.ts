import { ref, computed, type Ref } from 'vue'
import {
  DEFAULT_AUDIO_MODEL,
  TRANSCRIBE_ENDPOINT,
} from '@/constants/audio'

export type TranscriptionResult = {
  text: string
  model?: string
  language?: string
  response_format?: string
}

export type SpeechToTextOptions = {
  endpoint?: string
  model?: string
  language?: string
}

const INTERNAL_TOKEN = import.meta.env.VITE_INTERNAL_TOKEN as string | undefined

const supportsMediaRecorder = () => {
  if (typeof window === 'undefined') return false
  if (typeof navigator === 'undefined') return false
  const hasDevices = typeof navigator.mediaDevices?.getUserMedia === 'function'
  return Boolean((window as any).MediaRecorder && hasDevices)
}

export function useSpeechToText(options?: SpeechToTextOptions) {
  const endpoint = options?.endpoint?.trim() || TRANSCRIBE_ENDPOINT
  const chosenModel = ref(options?.model || DEFAULT_AUDIO_MODEL)
  const chosenLanguage = ref(options?.language || '')

  const isRecording = ref(false)
  const isTranscribing = ref(false)
  const lastTranscript = ref('')
  const errorMessage = ref<string | null>(null)
  const canRecord = computed(() => supportsMediaRecorder())

  let mediaRecorder: MediaRecorder | null = null
  let mediaStream: MediaStream | null = null
  let recordedChunks: BlobPart[] = []

  const headers: Record<string, string> = INTERNAL_TOKEN
    ? { 'X-API-KEY': INTERNAL_TOKEN }
    : {}

  const cleanupStream = () => {
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop())
      mediaStream = null
    }
    mediaRecorder = null
    isRecording.value = false
  }

  const resetChunks = () => {
    recordedChunks = []
  }

  const collectBlob = () => {
    if (!recordedChunks.length) return null
    const mimeType = mediaRecorder?.mimeType || 'audio/webm'
    return new Blob(recordedChunks, { type: mimeType })
  }

  const transcribeBlob = async (blob: Blob): Promise<TranscriptionResult> => {
    const file = new File([blob], `recording-${Date.now()}.webm`, {
      type: blob.type || 'audio/webm',
    })

    const fd = new FormData()
    fd.append('file', file)
    fd.append('model', chosenModel.value)
    fd.append('response_format', 'json')
    if (chosenLanguage.value) {
      fd.append('language', chosenLanguage.value)
    }
     fd.append('min_confidence', String(0.5));
    isTranscribing.value = true
    errorMessage.value = null

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        body: fd,
        credentials: 'include',
        headers,
      })
      if (!res.ok) {
        const errText = await res.text().catch(() => '')
        throw new Error(errText || `transcription failed: HTTP ${res.status}`)
      }
      const data = await res.json().catch(() => ({})) as TranscriptionResult
      const text = (data?.text || '').trim()
      if (!text) {
        throw new Error('transcription succeeded but returned empty text')
      }
      lastTranscript.value = text
      return { ...data, text }
    } catch (err: any) {
      errorMessage.value = err?.message || 'transcription failed'
      throw err
    } finally {
      isTranscribing.value = false
    }
  }

  const startRecording = async () => {
    if (!canRecord.value) {
      throw new Error('当前环境不支持录音')
    }
    if (isRecording.value) return
    resetChunks()
    errorMessage.value = null

    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(mediaStream)
    mediaRecorder.addEventListener('dataavailable', event => {
      if (event.data && event.data.size > 0) {
        recordedChunks.push(event.data)
      }
    })
    mediaRecorder.start()
    isRecording.value = true
  }

  const stopRecording = async () => {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
      const blob = collectBlob()
      resetChunks()
      cleanupStream()
      return blob
    }

    return await new Promise<Blob | null>(resolve => {
      const recorder = mediaRecorder as MediaRecorder
      recorder.addEventListener('stop', () => {
        const blob = collectBlob()
        resetChunks()
        cleanupStream()
        resolve(blob)
      }, { once: true })
      recorder.stop()
    })
  }

  const cancelRecording = async () => {
    if (!mediaRecorder) {
      cleanupStream()
      resetChunks()
      return
    }
    resetChunks()
    if (mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
    } else {
      cleanupStream()
    }
  }

  const stopRecordingAndTranscribe = async (): Promise<TranscriptionResult> => {
    const blob = await stopRecording()
    if (!blob) {
      throw new Error('未捕获到有效的录音数据')
    }
    return transcribeBlob(blob)
  }

  const setModel = (model: string) => {
    if (model.trim()) {
      chosenModel.value = model.trim()
    }
  }

  const setLanguage = (language: string) => {
    chosenLanguage.value = (language || '').trim()
  }

  return {
    isRecording,
    isTranscribing,
    canRecord,
    lastTranscript: lastTranscript as Ref<string>,
    errorMessage,
    startRecording,
    stopRecording,
    stopRecordingAndTranscribe,
    cancelRecording,
    transcribeBlob,
    setModel,
    setLanguage,
    endpoint,
    chosenModel,
  }
}
