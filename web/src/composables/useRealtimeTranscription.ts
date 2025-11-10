import { computed, onBeforeUnmount, ref } from 'vue'
import { DEFAULT_AUDIO_MODEL, TRANSCRIBE_REALTIME_WS_ENDPOINT } from '@/constants/audio'
import type { TranscriptSegment } from '@/types/notes'

const INTERNAL_TOKEN = (import.meta.env.VITE_INTERNAL_TOKEN as string | undefined)?.trim()
const DEFAULT_WS_PATH = TRANSCRIBE_REALTIME_WS_ENDPOINT
const TARGET_SAMPLE_RATE = 24000

export interface RealtimeTranscriptionOptions {
  model?: string
  language?: string
  includeLogprobs?: boolean
  wsEndpoint?: string
  sampleRate?: number
  minConfidence?: number
}

interface RealtimeEventPayload {
  type?: string
  event?: string
  [key: string]: any
}

const chunkSize = 0x8000
const MIN_FLUSH_BYTES = 1600  // ensure some audio before final flush

const base64Encode = (buffer: Uint8Array) => {
  let binary = ''
  for (let i = 0; i < buffer.length; i += chunkSize) {
    const subArray = buffer.subarray(i, i + chunkSize)
    binary += String.fromCharCode.apply(null, Array.from(subArray) as number[])
  }
  return btoa(binary)
}

const downsampleBuffer = (buffer: Float32Array, inputRate: number, targetRate: number) => {
  if (targetRate === inputRate) {
    return buffer
  }
  const ratio = inputRate / targetRate
  const outLength = Math.round(buffer.length / ratio)
  const result = new Float32Array(outLength)
  let outputOffset = 0
  let inputOffset = 0
  while (outputOffset < result.length) {
    const nextOffset = Math.round((outputOffset + 1) * ratio)
    let accum = 0
    let count = 0
    for (let i = inputOffset; i < nextOffset && i < buffer.length; i++) {
      accum += buffer[i]
      count++
    }
    result[outputOffset] = count ? accum / count : 0
    outputOffset++
    inputOffset = nextOffset
  }
  return result
}

const floatTo16BitPCM = (buffer: Float32Array) => {
  const clamped = new DataView(new ArrayBuffer(buffer.length * 2))
  let index = 0
  for (let i = 0; i < buffer.length; i++) {
    let s = Math.max(-1, Math.min(1, buffer[i]))
    s = s < 0 ? s * 0x8000 : s * 0x7fff
    clamped.setInt16(index, s, true)
    index += 2
  }
  return new Uint8Array(clamped.buffer)
}

const formatTimestamp = (totalSeconds: number) => {
  const seconds = Math.max(0, Math.floor(totalSeconds))
  const minutesPart = Math.floor(seconds / 60)
  const secondsPart = seconds % 60
  return `${minutesPart.toString().padStart(2, '0')}:${secondsPart.toString().padStart(2, '0')}`
}

const resolveWsUrl = (path: string) => {
  if (/^wss?:\/\//i.test(path)) {
    return path
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${protocol}//${host}${normalizedPath}`
}

const supportsRecording = () => {
  if (typeof window === 'undefined') return false
  if (typeof navigator === 'undefined') return false
  return typeof navigator.mediaDevices?.getUserMedia === 'function' && typeof window.WebSocket !== 'undefined'
}

const clampConfidence = (value: unknown): number | null => {
  const numeric =
    typeof value === 'number'
      ? value
      : typeof value === 'string'
        ? Number.parseFloat(value)
        : Number.NaN
  if (!Number.isFinite(numeric)) return null
  return Math.max(0, Math.min(1, numeric))
}

const probabilityFromLogprob = (value: unknown): number | null => {
  const numeric =
    typeof value === 'number'
      ? value
      : typeof value === 'string'
        ? Number.parseFloat(value)
        : Number.NaN
  if (!Number.isFinite(numeric)) return null
  const probability = Math.exp(numeric)
  if (!Number.isFinite(probability)) return null
  return Math.max(0, Math.min(1, probability))
}

const collectConfidenceSignals = (source: unknown, depth = 0): number[] => {
  if (source == null || depth > 4) return []
  const results: number[] = []
  if (Array.isArray(source)) {
    for (const entry of source) {
      results.push(...collectConfidenceSignals(entry, depth + 1))
    }
    return results
  }
  if (typeof source === 'object') {
    const obj = source as Record<string, unknown>
    const directKeys: Array<keyof typeof obj> = ['confidence', 'probability']
    for (const key of directKeys) {
      if (obj[key] !== undefined) {
        const value = clampConfidence(obj[key])
        if (value !== null) {
          results.push(value)
        }
      }
    }
    const logprobKeys: Array<keyof typeof obj> = ['avg_logprob', 'logprob']
    for (const key of logprobKeys) {
      if (obj[key] !== undefined) {
        const value = probabilityFromLogprob(obj[key])
        if (value !== null) {
          results.push(value)
        }
      }
    }
    const nestedKeys: Array<keyof typeof obj> = [
      'items',
      'segments',
      'words',
      'alternatives',
      'tokens',
      'elements',
      'logprobs',
      'data',
    ]
    for (const key of nestedKeys) {
      if (obj[key] !== undefined) {
        results.push(...collectConfidenceSignals(obj[key], depth + 1))
      }
    }
  }
  return results
}

const evaluateConfidenceFromPayload = (payload: RealtimeEventPayload): number | null => {
  const direct =
    clampConfidence(payload.confidence) ??
    clampConfidence(payload.transcript?.confidence) ??
    clampConfidence(payload.segment?.confidence)
  if (direct !== null) return direct

  const avgLogprob =
    probabilityFromLogprob(payload.avg_logprob) ??
    probabilityFromLogprob(payload.transcript?.avg_logprob) ??
    probabilityFromLogprob(payload.segment?.avg_logprob)
  if (avgLogprob !== null) return avgLogprob

  const collected = [
    ...collectConfidenceSignals(payload.transcript),
    ...collectConfidenceSignals(payload.segment),
    ...collectConfidenceSignals(payload),
  ]
  if (collected.length) {
    const sum = collected.reduce((acc, value) => acc + value, 0)
    const average = sum / collected.length
    if (Number.isFinite(average)) {
      return Math.max(0, Math.min(1, average))
    }
  }
  return null
}

export function useRealtimeTranscription(options?: RealtimeTranscriptionOptions) {
  const wsEndpoint = options?.wsEndpoint?.trim() || DEFAULT_WS_PATH
  const targetSampleRate = options?.sampleRate ?? TARGET_SAMPLE_RATE

  const model = ref(options?.model?.trim() || DEFAULT_AUDIO_MODEL)
  const language = ref(options?.language?.trim() || '')
  const includeLogprobs = ref(Boolean(options?.includeLogprobs))
  const minConfidence = ref(
    typeof options?.minConfidence === 'number'
      ? Math.max(0, Math.min(1, options.minConfidence))
      : 0.4,
  )

  const isRecording = ref(false)
  const isPaused = ref(false)
  const isConnected = ref(false)
  const connectionReady = ref(false)
  const duration = ref(0)
  const audioLevel = ref(0)
  const segments = ref<TranscriptSegment[]>([])
  const liveText = ref('')
  const errorMessage = ref<string | null>(null)

  let ws: WebSocket | null = null
  let connectPromise: Promise<void> | null = null
  let mediaStream: MediaStream | null = null
  let audioContext: AudioContext | null = null
  let sourceNode: MediaStreamAudioSourceNode | null = null
  let processorNode: ScriptProcessorNode | null = null
  let durationTimer: number | null = null
  let manualClose = false
  let muteNode: GainNode | null = null
  let lastLowConfidenceWarning = 0
  let pendingFinalizationResolvers: Array<() => void> = []
  let hasPendingFinalizationSignal = false
  let pendingByteCount = 0
  let hasSentAudio = false

  const resetState = () => {
    duration.value = 0
    audioLevel.value = 0
    segments.value = []
    liveText.value = ''
    errorMessage.value = null
    lastLowConfidenceWarning = 0
    connectionReady.value = false
    isConnected.value = false
    hasPendingFinalizationSignal = false
    pendingByteCount = 0
    hasSentAudio = false
    if (pendingFinalizationResolvers.length) {
      const resolvers = [...pendingFinalizationResolvers]
      pendingFinalizationResolvers = []
      for (const resolve of resolvers) {
        resolve()
      }
    }
  }

  const shouldAcceptConfidence = (confidence: number | null) => {
    if (confidence === null) return true
    if (confidence >= minConfidence.value) return true
    const now = typeof performance !== 'undefined' ? performance.now() : Date.now()
    if (now - lastLowConfidenceWarning > 2000) {
      errorMessage.value = '语音置信度较低，已跳过部分文本'
      lastLowConfidenceWarning = now
    }
    return false
  }

  const waitForServerFinalization = (timeout = 2000) => {
    if (hasPendingFinalizationSignal) {
      hasPendingFinalizationSignal = false
      return Promise.resolve()
    }
    return new Promise<void>(resolve => {
      const timer = setTimeout(() => {
        pendingFinalizationResolvers = pendingFinalizationResolvers.filter(fn => fn !== fulfill)
        hasPendingFinalizationSignal = false
        resolve()
      }, timeout)
      const fulfill = () => {
        clearTimeout(timer)
        hasPendingFinalizationSignal = false
        resolve()
      }
      pendingFinalizationResolvers.push(fulfill)
    })
  }

  const notifyServerFinalized = () => {
    hasPendingFinalizationSignal = true
    if (!pendingFinalizationResolvers.length) return
    const resolvers = [...pendingFinalizationResolvers]
    pendingFinalizationResolvers = []
    for (const resolve of resolvers) {
      resolve()
    }
  }

  const updateAudioLevel = (buffer: Float32Array) => {
    let sumSquares = 0
    for (let i = 0; i < buffer.length; i++) {
      const sample = buffer[i]
      sumSquares += sample * sample
    }
    const rms = Math.sqrt(sumSquares / buffer.length)
    audioLevel.value = Number.isFinite(rms) ? Math.min(1, rms * 3) : 0
  }

  const startDurationTimer = () => {
    stopDurationTimer()
    durationTimer = window.setInterval(() => {
      if (isRecording.value && !isPaused.value) {
        duration.value += 1
      }
    }, 1000)
  }

  const stopDurationTimer = () => {
    if (durationTimer !== null) {
      window.clearInterval(durationTimer)
      durationTimer = null
    }
  }

  const closeWebSocket = () => {
    if (ws) {
      manualClose = true
      ws.close()
      ws = null
      connectPromise = null
    }
  }

  const canStream = () => Boolean(ws && ws.readyState === WebSocket.OPEN)

  const sendFrame = (frame: Record<string, unknown>) => {
    if (!canStream()) return
    try {
      ws!.send(JSON.stringify(frame))
    } catch (err) {
      errorMessage.value = err instanceof Error ? err.message : '音频发送失败'
    }
  }

  const cleanupAudio = async () => {
    processorNode?.disconnect()
    sourceNode?.disconnect()
    processorNode = null
    sourceNode = null
    if (muteNode) {
      muteNode.disconnect()
      muteNode = null
    }
    if (audioContext) {
      try {
        await audioContext.close()
      } catch {
        /* ignore */
      }
    }
    audioContext = null
    if (mediaStream) {
      for (const track of mediaStream.getTracks()) {
        track.stop()
      }
    }
    mediaStream = null
  }

  const ensureConnection = () => {
    if (connectPromise) return connectPromise
    connectPromise = new Promise<void>((resolve, reject) => {
      try {
        const params = new URLSearchParams()
        params.set('model', model.value)
        if (language.value) params.set('language', language.value)
        if (includeLogprobs.value) params.set('include_logprobs', '1')
        if (INTERNAL_TOKEN) params.set('token', INTERNAL_TOKEN)
        params.set('sample_rate', String(targetSampleRate))
        params.set('min_confidence', minConfidence.value.toFixed(3))

        const url = `${resolveWsUrl(wsEndpoint)}?${params.toString()}`
        manualClose = false
        ws = new WebSocket(url)

        ws.addEventListener('open', () => {
          isConnected.value = true
          connectionReady.value = true
          resolve()
        })

        ws.addEventListener('close', () => {
          isConnected.value = false
          connectionReady.value = false
          connectPromise = null
          ws = null
          notifyServerFinalized()
          if (!manualClose && isRecording.value) {
            errorMessage.value = '实时转写连接已中断'
            void stopRecording()
          }
        })

        ws.addEventListener('error', event => {
          errorMessage.value = '实时转写连接失败'
          connectPromise = null
          try {
            ws?.close()
          } catch {
            /* ignore */
          }
          notifyServerFinalized()
          reject(event)
        })

        ws.addEventListener('message', event => {
          try {
            const payload = JSON.parse(event.data as string) as RealtimeEventPayload
            handleServerEvent(payload)
          } catch {
            /* ignore non-JSON frames */
          }
        })
      } catch (err) {
        errorMessage.value = err instanceof Error ? err.message : '无法连接实时转写服务'
        connectPromise = null
        reject(err)
      }
    })
    return connectPromise
  }

const coerceText = (value: unknown): string => {
  if (!value) return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    return value.map(item => coerceText(item)).filter(Boolean).join(' ')
  }
  if (typeof value === 'object') {
    const maybeText = (value as Record<string, unknown>).text
    if (typeof maybeText === 'string') return maybeText
    const maybeValue = (value as Record<string, unknown>).value
    if (typeof maybeValue === 'string') return maybeValue
    const maybeContent = (value as Record<string, unknown>).content
    if (Array.isArray(maybeContent)) return coerceText(maybeContent)
  }
  return ''
}

const appendLiveText = (text?: string) => {
  if (typeof text !== 'string') return
  if (!text.trim()) return
  liveText.value += text
}

  const finalizeSegmentFromPayload = (payload: RealtimeEventPayload, fallback?: string) => {
    const textSource =
      coerceText(payload.text) ||
      coerceText(payload.transcript?.text) ||
      coerceText(payload.response?.output_text) ||
    coerceText(payload.response?.output) ||
    coerceText(payload.segment?.text) ||
    fallback ||
    liveText.value
  const cleaned = textSource.trim()
  if (!cleaned) {
    liveText.value = ''
    notifyServerFinalized()
    return
  }
  const confidence = evaluateConfidenceFromPayload(payload)
  if (!shouldAcceptConfidence(confidence)) {
    liveText.value = ''
    notifyServerFinalized()
    return
  }
  const offsetMs =
    (typeof payload.offset_ms === 'number' ? payload.offset_ms : undefined) ??
    (typeof payload.transcript?.offset_ms === 'number' ? payload.transcript.offset_ms : undefined) ??
    (typeof payload.segment?.offset_ms === 'number' ? payload.segment.offset_ms : undefined)
  const seconds = typeof offsetMs === 'number' ? Math.max(0, Math.round(offsetMs / 1000)) : duration.value
  const segment: TranscriptSegment = {
    id: payload.id || `segment-${Date.now()}`,
    timestamp: formatTimestamp(seconds),
    text: cleaned,
    speaker: payload.speaker || payload.transcript?.speaker || payload.segment?.speaker,
    confidence: confidence ?? undefined,
  }
  segments.value = [...segments.value, segment]
  liveText.value = ''
  notifyServerFinalized()
}

const handleServerEvent = (payload: RealtimeEventPayload) => {
  const eventType = payload.type || payload.event
  switch (eventType) {
      case 'session.created':
      case 'session.updated':
      case 'session_started':
      case 'transcription_session.created':
      case 'transcription_session.updated':
        connectionReady.value = true
        if (typeof payload.min_confidence === 'number') {
          minConfidence.value = Math.max(0, Math.min(1, payload.min_confidence))
        }
        break
      case 'transcript.text.delta':
        if (typeof payload.delta === 'string') {
          liveText.value += payload.delta
        }
        break
      case 'transcript.delta':
        if (typeof payload.text === 'string') {
          liveText.value += payload.text
        }
        break
      case 'response.output_text.delta':
        if (typeof payload.delta === 'string') {
          appendLiveText(payload.delta)
        }
        break
      case 'transcription.delta':
      case 'input_audio_buffer.transcription.delta':
        appendLiveText(coerceText(payload.delta) || coerceText(payload.text))
        break
      case 'transcript.text.done': {
        const text = (payload.text || payload.transcript?.text || '').trim()
        if (text) {
          const confidence = evaluateConfidenceFromPayload(payload)
          if (!shouldAcceptConfidence(confidence)) {
            liveText.value = ''
            notifyServerFinalized()
            break
          }
          const offsetMs = payload.offset_ms ?? payload.transcript?.offset_ms
          const seconds = typeof offsetMs === 'number' ? Math.max(0, Math.round(offsetMs / 1000)) : duration.value
          const segment: TranscriptSegment = {
            id: payload.id || `segment-${Date.now()}`,
            timestamp: formatTimestamp(seconds),
            text,
            speaker: payload.speaker || payload.transcript?.speaker,
            confidence: confidence ?? undefined,
          }
          segments.value = [...segments.value, segment]
        }
        liveText.value = ''
        notifyServerFinalized()
        break
      }
      case 'response.output_text.done':
      case 'response.completed':
      case 'transcription.completed':
      case 'input_audio_buffer.transcription.completed':
        finalizeSegmentFromPayload(payload)
        break
      case 'response.error':
      case 'error':
        if (payload.message) {
          errorMessage.value = String(payload.message)
        }
        notifyServerFinalized()
        break
      default: {
        if (typeof eventType === 'string') {
          if (eventType.endsWith('.delta')) {
            appendLiveText(coerceText(payload.delta) || coerceText(payload.text))
          } else if (eventType.endsWith('.done') || eventType.endsWith('.completed')) {
            finalizeSegmentFromPayload(payload)
          }
        }
        break
      }
    }
  }

  const handleAudioProcess = (event: AudioProcessingEvent) => {
    if (!isRecording.value) return
    const buffer = event.inputBuffer.getChannelData(0)
    updateAudioLevel(buffer)
    if (isPaused.value || !canStream()) {
      return
    }
    const downsampled = downsampleBuffer(buffer, audioContext?.sampleRate ?? targetSampleRate, targetSampleRate)
    const pcm16 = floatTo16BitPCM(downsampled)
    if (!pcm16.length) return
    pendingByteCount = Math.min(pendingByteCount + pcm16.length, MIN_FLUSH_BYTES)
    hasSentAudio = true
    sendFrame({
      type: 'input_audio_buffer.append',
      audio: base64Encode(pcm16),
    })
  }

  const setupAudioPipeline = async () => {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } })
    try {
      audioContext = new AudioContext({ sampleRate: targetSampleRate })
    } catch {
      audioContext = new AudioContext()
    }
    sourceNode = audioContext.createMediaStreamSource(mediaStream)
    processorNode = audioContext.createScriptProcessor(4096, 1, 1)
    processorNode.onaudioprocess = handleAudioProcess
    sourceNode.connect(processorNode)
    muteNode = audioContext.createGain()
    muteNode.gain.value = 0
    processorNode.connect(muteNode)
    muteNode.connect(audioContext.destination)
  }

  const startRecording = async () => {
    if (isRecording.value) return
    if (!supportsRecording()) {
      const message = '当前浏览器不支持实时录音或 WebSocket'
      errorMessage.value = message
      throw new Error(message)
    }
    resetState()
    await ensureConnection()
    await setupAudioPipeline()
    isRecording.value = true
    isPaused.value = false
    audioLevel.value = 0
    startDurationTimer()
    if (audioContext?.state === 'suspended') {
      await audioContext.resume()
    }
  }

  const pauseRecording = async () => {
    if (!isRecording.value || isPaused.value) return
    isPaused.value = true
    try {
      await audioContext?.suspend()
    } catch {
      /* ignore */
    }
  }

  const resumeRecording = async () => {
    if (!isRecording.value || !isPaused.value) return
    isPaused.value = false
    try {
      await audioContext?.resume()
    } catch {
      /* ignore */
    }
  }

  const stopRecording = async () => {
    if (!isRecording.value) return
    isRecording.value = false
    isPaused.value = false
    stopDurationTimer()
    const shouldFlush = hasSentAudio && pendingByteCount >= MIN_FLUSH_BYTES
    if (shouldFlush) {
      sendFrame({ type: 'input_audio_buffer.commit' })
      pendingByteCount = 0
    } else {
      pendingByteCount = 0
    }
    hasSentAudio = false
    if (shouldFlush) {
      await waitForServerFinalization()
    }
    await cleanupAudio()
    closeWebSocket()
    audioLevel.value = 0
    if (liveText.value.trim()) {
      const segment: TranscriptSegment = {
        id: `segment-${Date.now()}`,
        timestamp: formatTimestamp(duration.value),
        text: liveText.value.trim(),
      }
      segments.value = [...segments.value, segment]
      liveText.value = ''
    }
  }

  const cancelRecording = async () => {
    if (!isRecording.value) {
      await cleanupAudio()
      closeWebSocket()
      notifyServerFinalized()
      return
    }
    liveText.value = ''
    segments.value = []
    await stopRecording()
  }

  onBeforeUnmount(() => {
    stopDurationTimer()
    void cleanupAudio()
    closeWebSocket()
  })

  const transcriptText = computed(() => {
    const finished = segments.value.map(segment => segment.text).join('\n')
    return [finished, liveText.value.trim()].filter(Boolean).join('\n')
  })

  const setModel = (next: string) => {
    if (!next || next === model.value) return
    model.value = next
  }

  const setLanguage = (next: string) => {
    language.value = (next || '').trim()
  }

  const setIncludeLogprobs = (value: boolean) => {
    includeLogprobs.value = value
  }

  const setMinConfidence = (value: number) => {
    if (!Number.isFinite(value)) return
    minConfidence.value = Math.max(0, Math.min(1, value))
  }

  return {
    canRecord: computed(() => supportsRecording()),
    isConnected,
    connectionReady,
    isRecording,
    isPaused,
    duration,
    audioLevel,
    segments,
    liveText,
    transcriptText,
    errorMessage,
    model,
    language,
    includeLogprobs,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    cancelRecording,
    setModel,
    setLanguage,
    setIncludeLogprobs,
    minConfidence,
    setMinConfidence,
  }
}

export type UseRealtimeTranscriptionReturn = ReturnType<typeof useRealtimeTranscription>
