<script setup lang="ts">
import dayjs from 'dayjs'
import { ClearOutlined, LoadingOutlined, RedoOutlined, SettingOutlined } from '@ant-design/icons-vue'
import Message from './components/message.vue'
import SettingModal from './components/setting.vue'

import useSetting from '@/composables/setting'
import useMessages from '@/composables/messages'
import { creditSummary } from '@/api'

// NEW: streaming composable
import { useResponsesStream } from '@/composables/useResponsesStream'

const setting = useSetting()
const messages = useMessages()

const state = reactive({
  message: '',
  loadding: false,
  visible: false,
  summary: {} as any,
})
const createdAt = dayjs().format('YYYY-MM-DD HH:mm:ss')

// Abort controller to cancel streaming
let controller: AbortController | null = null

// Build conversation context (your original logic)
const buildMessage = () => {
  const _messages: string[] = []
  const lastMessages = messages.getLastMessages(10)
  for (let i = 0; i < lastMessages.length; i++) {
    const element = lastMessages[i]
    if (element.type === 0) {
      _messages.push('AI:\n' + element.msg)
    } else {
      _messages.push('User:\n' + element.msg)
    }
  }
  return _messages.join('\n\n') + '\nAI:\n'
}

// Parse one semantic event line and return text delta if present
function parseTextDelta(line: string): string | null {
  try {
    const evt = JSON.parse(line)
    if (evt?.type === 'response.output_text.delta' && typeof evt.delta === 'string') {
      return evt.delta
    }
  } catch {
    // ignore non-JSON lines
  }
  return null
}

const sendMessage = async (event: { preventDefault: () => void }) => {
  event.preventDefault()
  const content = state.message.trim()
  if (!content) return

  state.loadding = true

  // 1) push user message
  messages.addMessage({
    username: 'user',
    msg: content,
    type: 1,
  })

  // 2) build prompt depending on "continuously"
  const question = setting.value.continuously
    ? buildMessage()
    : `User:\n${content}\n\nAI:\n`

  // clear input
  state.message = ''

  // 3) push assistant placeholder to receive stream
  messages.addMessage({
    username: 'chatGPT',
    msg: '',
    type: 0,
  })

  // 4) stream from backend
  controller?.abort()
  controller = new AbortController()

  const body = {
    model: 'gpt-4o-mini',
    input: [
      { role: 'user', content: [{ type: 'input_text', text: question }] }
    ]
  }


  try {
    for await (const line of useResponsesStream(body, { signal: controller.signal })) {
      const delta = parseTextDelta(line)
      if (!delta) continue
      const last = messages.messages.value[messages.messages.value.length - 1]
      last.msg += delta
    }
  } catch (e: any) {
    if (e?.name !== 'AbortError') {
      const last = messages.messages.value[messages.messages.value.length - 1]
      last.msg += `\n[error] ${e?.message ?? e}`
    }
  } finally {
    controller = null
    state.loadding = false
  }
}

function stopStreaming() {
  controller?.abort()
  controller = null
  state.loadding = false
}

const clearMessages = () => {
  messages.clearMessages()
}

const totalAvailable = computed(() => {
  const total = (state.summary?.total_available || 0) as number
  return total.toFixed(2)
})

const refushCredit = async () => {
  state.loadding = true
  state.summary = await creditSummary()
  state.loadding = false
}

onMounted(async () => {
  await refushCredit()
})
</script>

<template>
  <div id="layout">
    <header id="header" class="bg-dark-50 text-white h-10 select-none">
      <LoadingOutlined v-if="state.loadding" class="pl-3 cursor-pointer" />
      <span class="text-size-5 pl-5">ChatGPT</span>

      <a-tooltip>
        <template #title>Clear local chat history</template>
        <a-popconfirm
          title="Are you sure to clear all local messages?"
          ok-text="Yes"
          cancel-text="Cancel"
          @confirm="clearMessages"
        >
          <ClearOutlined class="pl-3 cursor-pointer" />
        </a-popconfirm>
      </a-tooltip>

      <a-tooltip>
        <template #title>Settings</template>
        <SettingOutlined class="pl-3 cursor-pointer" @click="state.visible = true" />
      </a-tooltip>

      <span class="float-right pr-3 pt-2">
        Balance: {{ totalAvailable }}
        <a-tooltip>
          <template #title>Refresh balance</template>
          <RedoOutlined @click="refushCredit" />
        </a-tooltip>
      </span>
    </header>

    <div id="layout-body">
      <main id="main">
        <div class="flex-1 relative flex flex-col">
          <div class="flex-1 inset-0 overflow-hidden bg-transparent bg-bottom bg-cover flex flex-col">
            <div class="flex-1 w-full self-center">
              <div class="relative px-3 py-1 m-auto flex flex-col">
                <div class="mx-0 my-1 self-center text-xs text-gray-400">Channel created</div>
                <div class="mx-0 my-1 self-center text-xs text-gray-400">{{ createdAt }}</div>

                <Message
                  v-for="(msg, idx) in messages.messages.value"
                  :key="idx"
                  :message="msg"
                  :class="msg.type === 1 ? 'send' : 'replay'"
                />

              </div>
            </div>
          </div>
        </div>
      </main>
    </div>

    <footer id="footer">
      <div class="relative p-4 w-full overflow-hidden text-gray-600 focus-within:text-gray-400 flex items-center">
        <a-textarea
          v-model:value="state.message"
          :auto-size="{ minRows: 3, maxRows: 5 }"
          placeholder="Type your message..."
          @pressEnter="sendMessage($event)"
          class="appearance-none pl-10 py-2 w-full bg-white border border-gray-300 rounded-full text-sm placeholder-gray-800 focus:outline-none focus:border-blue-500 focus:shadow-outline-blue"
        />
        <span class="absolute inset-y-0 right-0 bottom-6 pr-6 flex items-end gap-2">
          <a-button shape="round" @click="stopStreaming" :disabled="!state.loadding">Stop</a-button>
          <a-button shape="round" type="primary" @click="sendMessage($event)">Send</a-button>
        </span>
      </div>
    </footer>

    <setting-modal v-model:visible="state.visible" />
  </div>
</template>

<style scoped>
body,
html {
  margin: 0;
  padding: 0;
}

#layout {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  background-color: #f0f2f5;
}

#header {
  box-shadow: 2px 5px 5px 0px rgba(102, 102, 102, 0.5);
  flex-shrink: 0;
}

#layout-body {
  flex-grow: 2;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

#footer {
  border-top: 1px rgb(228, 228, 228) solid;
  width: 100%;
  flex-shrink: 0;
}

#main {
  flex-grow: 2;
}

.replay {
  float: left;
  clear: both;
}

.send {
  float: right;
  clear: both;
}
</style>
