import { ref } from 'vue'
import { fetchAiConfig } from '@/services/api/ai'
import type { AiConfigOption } from '@/services/api/types'

export type AiConfigState = {
  modelOptions: AiConfigOption[]
  modelDefaults: Record<string, string>
  toolOptions: AiConfigOption[]
  toolDefaults: Record<string, string[]>
}

// Client-side cache of the server's AI configuration (keys + defaults).
const state = ref<AiConfigState>({
  modelOptions: [],
  modelDefaults: {},
  toolOptions: [],
  toolDefaults: {},
})

const loaded = ref(false)

export const initAiConfig = async () => {
  if (loaded.value) return
  try {
    // Fetch once on app startup to drive model/tool selectors and defaults.
    const data = await fetchAiConfig()
    state.value = {
      modelOptions: Array.isArray(data.model_options) ? data.model_options : [],
      modelDefaults: data.model_defaults ?? {},
      toolOptions: Array.isArray(data.tool_options) ? data.tool_options : [],
      toolDefaults: data.tool_defaults ?? {},
    }
  } finally {
    loaded.value = true
  }
}

export const useAiConfig = () => state
export const useAiConfigLoaded = () => loaded
