import { useStorage } from '@vueuse/core'
import { DEFAULT_AUDIO_MODEL } from '@/constants/audio'

export const MODEL_CONFIG = {
  chat: 'gpt-4o-mini',
  noteChat: 'gpt-5-mini-2025-08-07',
  flashcard: 'gpt-5-mini-2025-08-07',
  title: 'gpt-4o-mini',
  audioTranscribe: DEFAULT_AUDIO_MODEL,
  audioRealtime: DEFAULT_AUDIO_MODEL,
} as const

export type ModelKey = keyof typeof MODEL_CONFIG
export type ModelSettings = Record<ModelKey, string>

export type Setting = {
  app_key: string
  model: string
  continuously: boolean
  models: ModelSettings
}

const applyDefaults = (value: Setting): Setting => {
  const mergedModels: ModelSettings = { ...MODEL_CONFIG, ...(value.models ?? {}) }
  if (value.model) mergedModels.chat = value.model

  value.models = mergedModels
  value.model = mergedModels.chat
  if (typeof value.app_key !== 'string') value.app_key = ''
  if (typeof value.continuously !== 'boolean') value.continuously = true
  return value
}

const setting = useStorage<Setting>(
  'setting',
  applyDefaults({
    app_key: '',
    model: MODEL_CONFIG.chat,
    continuously: true,
    models: { ...MODEL_CONFIG },
  }),
  undefined,
  { mergeDefaults: true },
)

applyDefaults(setting.value)

export const getModelFor = (key: ModelKey): string => {
  applyDefaults(setting.value)
  return setting.value.models[key] || MODEL_CONFIG.chat
}

const useSetting = () => setting

export default useSetting
