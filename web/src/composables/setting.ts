import { useStorage } from '@vueuse/core'
import { watch } from 'vue'
import { useAiConfig } from '@/composables/aiConfig'
import type { Locale } from '@/i18n'

export type ModelKey = string
export type ModelSettings = Record<ModelKey, string>

export type Setting = {
  app_key: string
  continuously: boolean
  models: ModelSettings
  locale: Locale
}

const aiConfig = useAiConfig()

const applyDefaults = (value: Setting): Setting => {
  // Merge server defaults with local overrides (keys only, not model ids).
  const defaults = aiConfig.value.modelDefaults ?? {}
  const mergedModels: ModelSettings = { ...defaults, ...(value.models ?? {}) }

  value.models = mergedModels
  if (typeof value.app_key !== 'string') value.app_key = ''
  if (typeof value.continuously !== 'boolean') value.continuously = true
  if (!value.locale) value.locale = 'zh-CN'
  return value
}

const setting = useStorage<Setting>(
  'setting',
  applyDefaults({
    app_key: '',
    continuously: true,
    models: {},
    locale: 'zh-CN',
  }),
  undefined,
  { mergeDefaults: true },
)

applyDefaults(setting.value)

export const getModelFor = (key: ModelKey): string => {
  // Resolve a scene key to the stored model key with default fallback.
  applyDefaults(setting.value)
  const defaults = aiConfig.value.modelDefaults ?? {}
  return setting.value.models[key] || defaults[key] || defaults.chat || ''
}

const useSetting = () => setting

export default useSetting

watch(
  () => aiConfig.value.modelDefaults,
  () => {
    applyDefaults(setting.value)
    setting.value = { ...setting.value, models: { ...setting.value.models } }
  },
  { deep: true },
)
