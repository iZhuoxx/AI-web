import { computed, getCurrentInstance, onBeforeUnmount, ref, shallowRef } from 'vue'
import { useStorage } from '@vueuse/core'
import { TRANSCRIBE_REALTIME_WS_ENDPOINT } from '@/constants/audio'
import type { TranscriptSegment } from '@/types/notes'
import { getModelFor } from '@/composables/setting'

export type NoiseReductionMode = 'none' | 'auto' | 'near_field' | 'far_field'

export interface RealtimeTranscriptionOptions {
  endpoint?: string
  modelKey?: string
  language?: string
  includeLogprobs?: boolean
  minConfidence?: number
  vadThreshold?: number
  silenceDurationMs?: number
  prefixPaddingMs?: number
  noiseReduction?: NoiseReductionMode
  sampleRate?: number
  debug?: boolean
  storageKey?: string
  maxStoredSegments?: number
}

type PendingBuffer = {
  text: string
  confidence?: number
}

const INTERNAL_TOKEN = import.meta.env.VITE_INTERNAL_TOKEN as string | undefined
const DEFAULT_SAMPLE_RATE = 16000
const MIN_SILENCE_MS = 200
const DEFAULT_STORAGE_KEY = 'note-transcription'
const DEFAULT_MAX_STORED_SEGMENTS = 500

const hasWindow = typeof window !== 'undefined'
const AudioContextCtor =
  (hasWindow && (window.AudioContext || (window as any).webkitAudioContext)) || null

const supportsRealtimeRecording = () => {
  if (!hasWindow) return false
  if (!AudioContextCtor) return false
  return typeof navigator.mediaDevices?.getUserMedia === 'function'
}

const toWebSocketUrl = (raw: string) => {
  if (/^wss?:\/\//i.test(raw)) return raw
  if (!hasWindow) return raw
  const base = new URL(raw, window.location.href)
  base.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
  return base.toString()
}

const floatTo16BitPCM = (input: Float32Array) => {
  const buffer = new ArrayBuffer(input.length * 2)
  const view = new DataView(buffer)
  for (let i = 0; i < input.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, input[i]))
    view.setInt16(i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
  }
  return buffer
}

const concatFloat32 = (a: Float32Array | null, b: Float32Array) => {
  if (!a || a.length === 0) return b.slice()
  const merged = new Float32Array(a.length + b.length)
  merged.set(a, 0)
  merged.set(b, a.length)
  return merged
}

const bufferToBase64 = (buffer: ArrayBuffer) => {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

const createPcmEncoder = (targetRate: number) => {
  let pending: Float32Array | null = null
  let lastSourceRate = targetRate

  return (chunk: Float32Array, sourceRate: number): ArrayBuffer | null => {
    if (!chunk.length) return null
    if (sourceRate === targetRate) {
      pending = null
      return floatTo16BitPCM(chunk)
    }

    if (lastSourceRate !== sourceRate) {
      pending = null
      lastSourceRate = sourceRate
    }

    const ratio = sourceRate / targetRate
    const data = concatFloat32(pending, chunk)
    const expectedSamples = Math.floor(data.length / ratio)
    if (expectedSamples <= 0) {
      pending = data
      return null
    }

    const output = new Int16Array(expectedSamples)
    let inputIndex = 0
    for (let i = 0; i < expectedSamples; i += 1) {
      const nextInputIndex = (i + 1) * ratio
      const start = Math.floor(inputIndex)
      const end = Math.min(Math.floor(nextInputIndex), data.length)
      if (end <= start) break
      let sum = 0
      for (let j = start; j < end; j += 1) {
        sum += data[j]
      }
      const sample = sum / (end - start)
      const clamped = Math.max(-1, Math.min(1, sample))
      output[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff
      inputIndex = nextInputIndex
    }

    const consumed = Math.floor(expectedSamples * ratio)
    pending = consumed < data.length ? data.slice(consumed) : null
    return output.buffer
  }
}

const rmsFromAudio = (data: Float32Array) => {
  if (!data.length) return 0
  let sum = 0
  for (let i = 0; i < data.length; i += 1) {
    sum += data[i] * data[i]
  }
  return Math.sqrt(sum / data.length)
}

const formatTimestamp = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.max(0, seconds - mins * 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

export function useRealtimeTranscription(options?: RealtimeTranscriptionOptions) {
  const endpoint = options?.endpoint?.trim() || TRANSCRIBE_REALTIME_WS_ENDPOINT
  const targetSampleRate = options?.sampleRate ?? DEFAULT_SAMPLE_RATE
  const preferredModel = options?.modelKey?.trim() || getModelFor('audioRealtime')
  const noiseReduction = options?.noiseReduction ?? 'near_field'
  const vadThreshold = options?.vadThreshold ?? 0.5
  const silenceDurationMs = options?.silenceDurationMs ?? 500
  const prefixPaddingMs = options?.prefixPaddingMs ?? 300
  const minConfidence = options?.minConfidence
  const includeLogprobs = options?.includeLogprobs ?? false
  const language = options?.language?.trim()
  const storageKey = options?.storageKey?.trim() || DEFAULT_STORAGE_KEY
  const maxStoredSegments = Math.max(1, options?.maxStoredSegments ?? DEFAULT_MAX_STORED_SEGMENTS)

  const canRecord = ref(supportsRealtimeRecording())
  const isRecording = ref(false)
  const isPaused = ref(false)
  const isConnected = ref(false)
  const connectionReady = ref(false)
  const connectionId = ref<string | null>(null)
  const duration = ref(0)
  const audioLevel = ref(0)
  const liveText = ref('')
  const segments = useStorage<TranscriptSegment[]>(`${storageKey}::segments`, [])
  const transcriptText = computed(() => segments.value.map(seg => seg.text).join('\n').trim())
  const errorMessage = ref<string | null>(null)

  const wsRef = shallowRef<WebSocket | null>(null)
  const mediaStreamRef = shallowRef<MediaStream | null>(null)
  const audioContextRef = shallowRef<AudioContext | null>(null)
  const processorRef = shallowRef<ScriptProcessorNode | AudioWorkletNode | null>(null)
  const sourceRef = shallowRef<MediaStreamAudioSourceNode | null>(null)

  const pendingBuffers = new Map<string, PendingBuffer>()
  const completedIds = new Set<string>()

  let durationTimer: number | null = null
  let resumeTimestamp = 0
  let accumulatedMs = 0
  let encoder = createPcmEncoder(targetSampleRate)
  let closeAfterStopTimer: number | null = null
  const minCommitBytes = Math.ceil(targetSampleRate * 0.1) * 2
  let pendingAudioBytes = 0

  const debugLog = (...args: any[]) => {
    if (!options?.debug) return
    // eslint-disable-next-line no-console
    console.debug('[realtime]', ...args)
  }

  const refreshCanRecord = async () => {
    if (!hasWindow) {
      canRecord.value = false
      return
    }
    if (!supportsRealtimeRecording()) {
      canRecord.value = false
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.getTracks().forEach(track => track.stop())
      canRecord.value = true
    } catch (_err) {
      canRecord.value = false
    }
  }

  const resetDuration = () => {
    if (durationTimer !== null) {
      window.clearInterval(durationTimer)
      durationTimer = null
    }
    accumulatedMs = 0
    resumeTimestamp = 0
    duration.value = 0
  }

  const startDuration = () => {
    resumeTimestamp = performance.now()
    if (durationTimer !== null) return
    durationTimer = window.setInterval(() => {
      if (!isRecording.value) {
        window.clearInterval(durationTimer!)
        durationTimer = null
        return
      }
      if (isPaused.value) {
        duration.value = Math.floor(accumulatedMs / 1000)
      } else {
        const elapsed = accumulatedMs + (performance.now() - resumeTimestamp)
        duration.value = Math.floor(elapsed / 1000)
      }
    }, 250)
  }

  const pauseDuration = () => {
    if (!isRecording.value || isPaused.value) return
    accumulatedMs += performance.now() - resumeTimestamp
    isPaused.value = true
  }

  const resumeDuration = () => {
    if (!isRecording.value || !isPaused.value) return
    resumeTimestamp = performance.now()
    isPaused.value = false
  }

  const finalizeDuration = () => {
    if (!isRecording.value) return
    const now = performance.now()
    if (!isPaused.value) {
      accumulatedMs += now - resumeTimestamp
    }
    duration.value = Math.floor(accumulatedMs / 1000)
    resetDuration()
  }

  const getElapsedSeconds = () => {
    if (!isRecording.value) {
      return Math.floor(accumulatedMs / 1000)
    }
    if (isPaused.value) {
      return Math.floor(accumulatedMs / 1000)
    }
    const elapsed = accumulatedMs + (performance.now() - resumeTimestamp)
    return Math.floor(elapsed / 1000)
  }

  const closeWebSocket = (immediate = false) => {
    if (closeAfterStopTimer !== null) {
      window.clearTimeout(closeAfterStopTimer)
      closeAfterStopTimer = null
    }
    const ws = wsRef.value
    if (!ws) return
    ws.onopen = null
    ws.onclose = null
    ws.onerror = null
    ws.onmessage = null
    if (ws.readyState === WebSocket.OPEN) {
      ws.close(immediate ? 1000 : undefined, immediate ? 'end' : undefined)
    }
    wsRef.value = null
    isConnected.value = false
    connectionReady.value = false
    connectionId.value = null
  }

  const cleanupAudioGraph = () => {
    const processor = processorRef.value
    if (processor) {
      try {
        (processor as ScriptProcessorNode).onaudioprocess = null
        processor.disconnect()
      } catch (_err) {
        // ignore
      }
      processorRef.value = null
    }
    const source = sourceRef.value
    if (source) {
      try {
        source.disconnect()
      } catch (_err) {
        // ignore
      }
      sourceRef.value = null
    }
    const ctx = audioContextRef.value
    if (ctx) {
      try {
        ctx.close()
      } catch (_err) {
        // ignore
      }
      audioContextRef.value = null
    }
    const stream = mediaStreamRef.value
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      mediaStreamRef.value = null
    }
  }

  const resetBuffers = () => {
    pendingBuffers.clear()
    completedIds.clear()
    encoder = createPcmEncoder(targetSampleRate)
    pendingAudioBytes = 0
  }

  const setError = (message: string) => {
    errorMessage.value = message
    debugLog('error', message)
  }

  const pushSegment = (text: string, confidence?: number) => {
    const normalized = text.trim()
    if (!normalized) return
    const timestamp = formatTimestamp(getElapsedSeconds())
    const id = `seg-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
    const nextSegments = [
      ...segments.value,
      {
        id,
        text: normalized,
        timestamp,
        confidence,
      },
    ]
    segments.value =
      nextSegments.length > maxStoredSegments
        ? nextSegments.slice(-maxStoredSegments)
        : nextSegments
    liveText.value = ''
  }

  const handleTextDelta = (itemId: string, delta: string, confidence?: number) => {
    if (!delta) return
    const buffer = pendingBuffers.get(itemId) ?? { text: '', confidence }
    buffer.text += delta
    if (confidence !== undefined) {
      buffer.confidence = confidence
    }
    pendingBuffers.set(itemId, buffer)
    liveText.value = buffer.text
  }

  const handleTextComplete = (itemId: string, text?: string, confidence?: number) => {
    const buffer = pendingBuffers.get(itemId)
    const finalText = (text ?? buffer?.text ?? '').trim()
    const finalConfidence = confidence ?? buffer?.confidence
    pendingBuffers.delete(itemId)
    if (!finalText) return
    pushSegment(finalText, finalConfidence)
  }

  const extractTextFromResponse = (response: any): { text: string; confidence?: number } => {
    if (!response) return { text: '' }
    if (typeof response.output_text === 'string') {
      return { text: response.output_text }
    }
    if (Array.isArray(response.output)) {
      const textParts: string[] = []
      let confidence: number | undefined
      for (const item of response.output) {
        if (item?.type === 'output_text' && typeof item.text === 'string') {
          textParts.push(item.text)
          if (item.confidence !== undefined) {
            confidence = Number(item.confidence)
          }
        }
      }
      return { text: textParts.join('').trim(), confidence }
    }
    if (Array.isArray(response.items)) {
      const textParts: string[] = []
      let confidence: number | undefined
      for (const item of response.items) {
        const transcription = item?.input_audio_transcription
        if (transcription?.text) {
          textParts.push(transcription.text)
          if (transcription.confidence !== undefined) {
            confidence = Number(transcription.confidence)
          }
        }
      }
      if (textParts.length) {
        return { text: textParts.join(' ').trim(), confidence }
      }
    }
    if (typeof response.text === 'string') {
      return { text: response.text }
    }
    return { text: '' }
  }

  const handleRealtimePayload = (payload: any) => {
    if (!payload) return
    if (payload.event === 'session_started') {
      connectionReady.value = true
      connectionId.value = payload.connection_id || null
      return
    }

    const type = payload.type
    if (!type && payload.event === 'error') {
      setError(payload.message || '实时转写服务返回错误')
      return
    }

    switch (type) {
      case 'error': {
        setError(payload.error || '实时转写服务错误')
        return
      }
      case 'transcription_session.created':
      case 'transcription_session.updated': {
        connectionReady.value = true
        if (payload.session?.id) {
          connectionId.value = payload.session.id
        }
        return
      }
      case 'session.updated': {
        connectionReady.value = true
        return
      }
      case 'transcript.text.delta': {
        const identifier = payload.transcript_id || payload.item_id || 'transcript'
        const delta =
          typeof payload.delta === 'string'
            ? payload.delta
            : typeof payload.delta?.text === 'string'
              ? payload.delta.text
              : typeof payload.text === 'string'
                ? payload.text
                : ''
        const conf =
          payload.confidence !== undefined
            ? Number(payload.confidence)
            : payload.delta?.confidence !== undefined
              ? Number(payload.delta.confidence)
              : undefined
        handleTextDelta(identifier, delta, conf)
        return
      }
      case 'transcript.text.done': {
        const identifier = payload.transcript_id || payload.item_id || 'transcript'
        const text =
          typeof payload.text === 'string'
            ? payload.text
            : typeof payload.transcript?.text === 'string'
              ? payload.transcript.text
              : typeof payload.delta === 'string'
                ? payload.delta
                : payload.delta?.text ?? undefined
        const conf =
          payload.confidence !== undefined
            ? Number(payload.confidence)
            : payload.transcript?.confidence !== undefined
              ? Number(payload.transcript.confidence)
              : payload.delta?.confidence !== undefined
                ? Number(payload.delta.confidence)
                : undefined
        handleTextComplete(identifier, text, conf)
        return
      }
      case 'transcript.segment.created':
      case 'transcript.segment.updated':
      case 'transcript.segment.completed': {
        const segment = payload.segment
        if (!segment) return
        const identifier = segment.id || payload.transcript_id || payload.item_id || 'segment'
        const text = typeof segment.text === 'string' ? segment.text : ''
        const conf =
          segment.confidence !== undefined
            ? Number(segment.confidence)
            : payload.confidence !== undefined
              ? Number(payload.confidence)
              : undefined
        if (!text) return
        if (type === 'transcript.segment.completed' || type === 'transcript.segment.updated') {
          handleTextComplete(identifier, text, conf)
        } else {
          handleTextDelta(identifier, text, conf)
        }
        return
      }
      case 'conversation.item.input_audio_transcription.delta': {
        const itemId = payload.item_id || 'item'
        const contentIndex = payload.content_index ?? 0
        const identifier = `${itemId}:${contentIndex}`
        const delta =
          typeof payload.delta === 'string'
            ? payload.delta
            : typeof payload.delta?.text === 'string'
              ? payload.delta.text
              : ''
        handleTextDelta(identifier, delta)
        return
      }
      case 'conversation.item.input_audio_transcription.completed': {
        const itemId = payload.item_id || 'item'
        const contentIndex = payload.content_index ?? 0
        const identifier = `${itemId}:${contentIndex}`
        const transcript =
          typeof payload.transcript === 'string'
            ? payload.transcript
            : payload.transcript?.text ?? ''
        let confidence: number | undefined
        if (payload.transcript?.confidence !== undefined) {
          confidence = Number(payload.transcript.confidence)
        } else if (Array.isArray(payload.logprobs) && payload.logprobs.length) {
          const probs = payload.logprobs
            .map((entry: any) => {
              const value = entry?.logprob
              return typeof value === 'number' ? Math.exp(value) : null
            })
            .filter((val: number | null): val is number => typeof val === 'number')
          if (probs.length) {
            confidence = probs.reduce((sum: number, val: number) => sum + val, 0) / probs.length
          }
        }
        handleTextComplete(identifier, transcript, confidence)
        return
      }
      case 'input_audio_buffer.committed': {
        pendingAudioBytes = 0
        return
      }
      case 'response.output_text.delta': {
        const itemId = payload.item_id || payload.response_id || 'response'
        const delta = typeof payload.delta === 'string' ? payload.delta : ''
        const conf = payload.confidence !== undefined ? Number(payload.confidence) : undefined
        handleTextDelta(itemId, delta, conf)
        return
      }
      case 'response.output_text.done': {
        const itemId = payload.item_id || payload.response_id || 'response'
        const text = typeof payload.output_text === 'string' ? payload.output_text : undefined
        const conf = payload.confidence !== undefined ? Number(payload.confidence) : undefined
        handleTextComplete(itemId, text, conf)
        return
      }
      case 'response.completed':
      case 'response.updated': {
        const response = payload.response
        if (!response) return
        const responseId = response.id || payload.response_id
        if (responseId && completedIds.has(responseId)) return
        const { text, confidence } = extractTextFromResponse(response)
        if (text) {
          if (responseId) {
            completedIds.add(responseId)
          }
          handleTextComplete(responseId || 'response', text, confidence)
        }
        return
      }
      case 'input_audio_transcription.delta': {
        const transcript = payload.transcript || payload.data
        if (transcript?.text) {
          handleTextDelta(payload.item_id || 'vad', transcript.text, transcript.confidence)
        } else if (typeof transcript === 'string') {
          handleTextDelta(payload.item_id || 'vad', transcript, payload.confidence)
        }
        return
      }
      case 'input_audio_transcription.completed': {
        const transcript = payload.transcript || payload.data
        const text = typeof transcript === 'string' ? transcript : transcript?.text
        const conf = transcript?.confidence ?? payload.confidence
        if (text) {
          handleTextComplete(payload.item_id || 'vad', text, conf)
        }
        return
      }
      default: {
        if (typeof payload.text === 'string' && payload.text.trim()) {
          const itemId = payload.item_id || payload.response_id || 'response'
          if (type && type.endsWith('.delta')) {
            handleTextDelta(itemId, payload.text)
          } else if (type && (type.endsWith('.done') || type.endsWith('.completed'))) {
            handleTextComplete(itemId, payload.text)
          }
        }
      }
    }
  }

  const connectWebSocket = async () => {
    if (!hasWindow) throw new Error('实时转写仅支持浏览器环境')
    const url = new URL(toWebSocketUrl(endpoint))
    url.searchParams.set('model_key', preferredModel)
    url.searchParams.set('sample_rate', String(targetSampleRate))
    url.searchParams.set('vad_threshold', String(vadThreshold))
    url.searchParams.set('silence_duration_ms', String(Math.max(MIN_SILENCE_MS, silenceDurationMs)))
    url.searchParams.set('prefix_padding_ms', String(Math.max(0, prefixPaddingMs)))
    url.searchParams.set('noise_reduction', noiseReduction)
    if (includeLogprobs) {
      url.searchParams.set('include_logprobs', '1')
    }
    if (minConfidence !== undefined) {
      url.searchParams.set('min_confidence', String(Math.max(0, Math.min(1, minConfidence))))
    }
    if (language) {
      url.searchParams.set('language', language)
    }
    if (INTERNAL_TOKEN) {
      url.searchParams.set('token', INTERNAL_TOKEN)
    }

    return await new Promise<void>((resolve, reject) => {
      let settled = false
      const fulfill = () => {
        if (settled) return
        settled = true
        resolve()
      }
      const fail = (err: Error) => {
        if (settled) return
        settled = true
        reject(err)
      }

      try {
        const ws = new WebSocket(url.toString())
        ws.binaryType = 'arraybuffer'
        ws.onopen = () => {
          isConnected.value = true
          connectionReady.value = false
          errorMessage.value = null
          wsRef.value = ws
          fulfill()
        }
        ws.onerror = event => {
          debugLog('ws error', event)
          setError('实时转写连接失败，请稍后重试')
          try {
            ws.close()
          } catch (_err) {
            // ignore
          }
          fail(new Error('websocket connection failed'))
        }
        ws.onclose = () => {
          debugLog('ws closed')
          isConnected.value = false
          connectionReady.value = false
          liveText.value = ''
          wsRef.value = null
          if (!settled) {
            fail(new Error('websocket closed before ready'))
          }
        }
        ws.onmessage = async message => {
          if (typeof message.data === 'string') {
            try {
              const payload = JSON.parse(message.data)
              handleRealtimePayload(payload)
            } catch (err) {
              debugLog('non-json payload', message.data, err)
            }
          } else if (message.data instanceof Blob) {
            try {
              const text = await message.data.text()
              const payload = JSON.parse(text)
              handleRealtimePayload(payload)
            } catch (err) {
              debugLog('binary payload parse failed', err)
            }
          } else if (message.data instanceof ArrayBuffer) {
            // ignore binary frames from server for now
            debugLog('binary frame received', (message.data as ArrayBuffer).byteLength)
          }
        }
      } catch (err) {
        reject(err)
      }
    })
  }

  const ensureAudioNodes = async () => {
    if (!AudioContextCtor) throw new Error('当前浏览器不支持 AudioContext')
    const constraints: MediaStreamConstraints = {
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: false,
        channelCount: 1,
      },
    }
    const stream = await navigator.mediaDevices.getUserMedia(constraints)
    mediaStreamRef.value = stream
    let audioContext: AudioContext
    try {
      audioContext = new AudioContextCtor({
        sampleRate: targetSampleRate,
        latencyHint: 'interactive',
      }) as AudioContext
    } catch (_err) {
      audioContext = new (AudioContextCtor as typeof AudioContext)()
    }
    audioContextRef.value = audioContext
    if (audioContext.state === 'suspended') {
      await audioContext.resume()
    }

    const source = audioContext.createMediaStreamSource(stream)
    sourceRef.value = source

    const processor = audioContext.createScriptProcessor(4096, 1, 1)
    processorRef.value = processor
    processor.onaudioprocess = event => {
      if (!isRecording.value || isPaused.value) return
      const ws = wsRef.value
      if (!ws || ws.readyState !== WebSocket.OPEN) return
      const channelData = event.inputBuffer.getChannelData(0)
      const chunk = encoder(channelData, audioContext.sampleRate)
      if (chunk) {
        try {
          pendingAudioBytes += chunk.byteLength
          const audio = bufferToBase64(chunk)
          ws.send(
            JSON.stringify({
              type: 'input_audio_buffer.append',
              audio,
            }),
          )
        } catch (err) {
          debugLog('append failed', err)
        }
      }
      const level = rmsFromAudio(channelData)
      audioLevel.value = audioLevel.value * 0.6 + level * 0.4
    }

    source.connect(processor)
    // Keep processor alive without feeding audio back to speakers
    processor.connect(audioContext.destination)
  }

  const startRecording = async () => {
    if (isRecording.value) return
    await refreshCanRecord()
    if (!canRecord.value) {
      throw new Error('当前浏览器不支持实时录音')
    }
    errorMessage.value = null
    audioLevel.value = 0
    liveText.value = ''
    resetDuration()
    resetBuffers()
    await connectWebSocket()
    await ensureAudioNodes()
    isRecording.value = true
    isPaused.value = false
    startDuration()
  }

  const sendCommitAndScheduleClose = () => {
    const ws = wsRef.value
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    if (closeAfterStopTimer !== null) {
      window.clearTimeout(closeAfterStopTimer)
    }
    closeAfterStopTimer = window.setTimeout(() => {
      closeWebSocket(true)
    }, 5000)
  }

  const stopRecording = async () => {
    if (!isRecording.value) return
    finalizeDuration()
    isRecording.value = false
    isPaused.value = false
    cleanupAudioGraph()
    sendCommitAndScheduleClose()
    audioLevel.value = 0
  }

  const pauseRecording = async () => {
    if (!isRecording.value || isPaused.value) return
    pauseDuration()
  }

  const resumeRecording = async () => {
    if (!isRecording.value || !isPaused.value) return
    resumeDuration()
  }

  const cancelRecording = async () => {
    if (!isRecording.value && !isConnected.value) {
      cleanupAudioGraph()
      closeWebSocket(true)
      liveText.value = ''
      audioLevel.value = 0
      resetDuration()
      pendingAudioBytes = 0
      return
    }
    isRecording.value = false
    isPaused.value = false
    cleanupAudioGraph()
    closeWebSocket(true)
    resetDuration()
    audioLevel.value = 0
    liveText.value = ''
    pendingAudioBytes = 0
  }

  if (getCurrentInstance()) {
    onBeforeUnmount(() => {
      void cancelRecording()
    })
  }

  return {
    canRecord,
    isConnected,
    connectionReady,
    connectionId,
    isRecording,
    isPaused,
    duration,
    audioLevel,
    segments,
    liveText,
    transcriptText,
    errorMessage,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    cancelRecording,
  }
}
