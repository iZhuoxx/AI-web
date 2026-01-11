import { useStorage } from '@vueuse/core'
import { watch } from 'vue'
import { useAiConfig } from '@/composables/aiConfig'

export type ModelKey = string
export type ModelSettings = Record<ModelKey, string>

export type Setting = {
  app_key: string
  continuously: boolean
  models: ModelSettings
}

const aiConfig = useAiConfig()

const applyDefaults = (value: Setting): Setting => {
  const defaults = aiConfig.value.modelDefaults ?? {}
  const mergedModels: ModelSettings = { ...defaults, ...(value.models ?? {}) }

  value.models = mergedModels
  if (typeof value.app_key !== 'string') value.app_key = ''
  if (typeof value.continuously !== 'boolean') value.continuously = true
  return value
}

const setting = useStorage<Setting>(
  'setting',
  applyDefaults({
    app_key: '',
    continuously: true,
    models: {},
  }),
  undefined,
  { mergeDefaults: true },
)

applyDefaults(setting.value)

export const getModelFor = (key: ModelKey): string => {
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
