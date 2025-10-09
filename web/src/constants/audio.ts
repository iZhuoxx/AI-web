export const DEFAULT_AUDIO_MODEL = 'gpt-4o-transcribe'

export const AUDIO_EXTENSIONS = Object.freeze([
  'mp3',
  'wav',
  'm4a',
  'aac',
  'ogg',
  'oga',
  'flac',
  'webm',
  'm4b',
  'm4p',
]) as readonly string[]

export const TRANSCRIBE_ENDPOINT =
  import.meta.env.VITE_TRANSCRIBE_ENDPOINT?.trim() || '/api/audio/transcriptions'

const AUDIO_MIME_PREFIX = 'audio/'

export function isAudioFile(file: File): boolean {
  const mime = (file.type || '').toLowerCase()
  if (mime.startsWith(AUDIO_MIME_PREFIX)) {
    return true
  }
  const name = file.name || ''
  const ext = name.includes('.') ? name.split('.').pop()?.toLowerCase() : ''
  if (!ext) return false
  return AUDIO_EXTENSIONS.includes(ext)
}
