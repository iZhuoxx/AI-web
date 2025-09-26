<script setup lang="ts">
import dayjs from 'dayjs'
import { ClearOutlined, LoadingOutlined, SettingOutlined } from '@ant-design/icons-vue'
import Message from './components/message.vue'
import SettingModal from './components/setting.vue'

import useSetting from '@/composables/setting'
import useMessages from '@/composables/messages'
import { useResponsesStream } from '@/composables/useResponsesStream'
import { ref, onMounted, nextTick } from 'vue'


const textareaRef = ref<HTMLTextAreaElement | null>(null)


const autoResize = () => {
  const el = textareaRef.value
  if (!el) return
  const MAX = 240 // 你当前设置的最大高度（px），可按需调整

  // 先归零再测量，避免只增不减
  el.style.height = '0px'
  const h = Math.min(el.scrollHeight, MAX)
  el.style.height = h + 'px'

  // 高度未到上限 -> 隐藏滚动条；到上限 -> 显示滚动条
  if (el.scrollHeight > MAX) {
    el.style.overflowY = 'auto'
  } else {
    el.style.overflowY = 'hidden'
  }
}

onMounted(() => nextTick(autoResize))

const setting = useSetting()
const messages = useMessages()

const state = reactive({
  message: '',
  loadding: false,
  visible: false,
})

const createdAt = dayjs().format('YYYY-MM-DD HH:mm:ss')

// Abort controller to cancel streaming
let controller: AbortController | null = null

// Build conversation context
const buildMessage = () => {
  const _messages: string[] = []
  const lastMessages = messages.getLastMessages(10)
  for (let i = 0; i < lastMessages.length; i++) {
    const element = lastMessages[i]
    _messages.push(`${element.type === 0 ? 'AI' : 'User'}:\n${element.msg}`)
  }
  return _messages.join('\n\n') + '\nAI:\n'
}

function parseTextDelta(line: string): string | null {
  try {
    const evt = JSON.parse(line)
    if (evt?.type === 'response.output_text.delta' && typeof evt.delta === 'string') {
      return evt.delta
    }
  } catch {}
  return null
}

const sendMessage = async (event: { preventDefault: () => void }) => {
  event.preventDefault()
  const content = state.message.trim()
  if (!content) return

  state.loadding = true

  // 把用户消息入列（以便后面取历史）
  messages.addMessage({ username: 'user', msg: content, type: 1 })

  // 读取设置
  const s = setting.value
  const useHistory      = !!s.continuously
  const selectedModel   = s.model || 'gpt-4o-mini'
  const systemPrompt    = (s as any).systemPrompt || ''
  const temperature     = typeof (s as any).temperature === 'number' ? (s as any).temperature : 0.7
  const maxOutputTokens = typeof (s as any).maxTokens === 'number' ? (s as any).maxTokens : undefined

  // 组装 inputs（Responses API）
  const inputs: any[] = []

  if (systemPrompt) {
    // system 用 input_text
    inputs.push({
      role: 'system',
      content: [{ type: 'input_text', text: systemPrompt }],
    })
  }

  if (useHistory) {
    const last = messages.getLastMessages(10)
    for (const m of last) {
      const role = m.type === 1 ? 'user' : 'assistant'
      const text = (m.msg ?? '').trim()
      if (!text) continue // 过滤占位的空 assistant

      inputs.push({
        role,
        content: [{
          //用户/系统用 input_text；助手历史用 output_text
          type: role === 'assistant' ? 'output_text' : 'input_text',
          text,
        }],
      })
    }
  } else {
    inputs.push({
      role: 'user',
      content: [{ type: 'input_text', text: content }],
    })
  }

  // 清空输入并收缩文本域，然后占位一条 assistant
  state.message = ''
  await nextTick()
  autoResize()
  messages.addMessage({ username: 'chatGPT', msg: '', type: 0 })

  // 开始流式
  controller?.abort()
  controller = new AbortController()

  const body: Record<string, any> = {
    model: String(selectedModel),
    input: inputs,
    temperature: Number(temperature),
  }
  if (typeof maxOutputTokens === 'number') {
    body.max_output_tokens = maxOutputTokens
  }

  try {
    for await (const line of useResponsesStream(body, { signal: controller.signal })) {
      const delta = parseTextDelta(line)
      if (!delta) continue
      const list = messages.messages.value
      if (!list.length) break
      list[list.length - 1].msg += delta
    }
  } catch (e: any) {
    if (e?.name !== 'AbortError') {
      const list = messages.messages.value
      if (list.length) list[list.length - 1].msg += `\n[error] ${e?.message ?? e}`
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
</script>

<template>
  <div id="layout">
    <!-- 顶部栏 -->
    <header id="header" class="bg-white/80 backdrop-blur text-gray-900 h-12 flex items-center shadow-sm">
      <div class="header-container">
        <div class="header-inner">
          <div class="left">
            <LoadingOutlined v-if="state.loadding" class="mr-2" />
            <span class="title">Hybrid GPT</span>
            <a-tooltip>
              <template #title>Clear local chat history</template>
              <a-popconfirm
                title="你确定要清空消息记录吗?"
                ok-text="是的"
                cancel-text="取消"
                @confirm="clearMessages"
              >
                <ClearOutlined class="icon" />
              </a-popconfirm>
            </a-tooltip>

            <a-tooltip>
              <template #title>Settings</template>
              <SettingOutlined class="icon" @click="state.visible = true" />
            </a-tooltip>
          </div>
        </div>
      </div>
    </header>

    <!-- 中间内容 -->
    <div id="layout-body">
      <main id="main">
        <div class="container">
          <div class="chat-container">
            <div class="meta">
              <div class="meta-line">Channel created</div>
              <div class="meta-line">{{ createdAt }}</div>
            </div>

            <!-- 消息列表 -->
            <Message
              v-for="(msg, idx) in messages.messages.value"
              :key="idx"
              :message="msg"
              :class="msg.type === 1 ? 'send' : 'replay'"
            />
          </div>
        </div>
      </main>
    </div>

    <!-- 底部输入区（新增 composer-inner，使输入框更窄更精致） -->
    <footer id="footer" class="chat-footer">
      <div class="composer">
        <div class="composer-inner">
          <textarea
            ref="textareaRef"
            v-model="state.message"
            placeholder="发消息..."
            @input="autoResize"
            @keydown.enter.exact.prevent="sendMessage($event)"
            @keydown.enter.shift.exact.stop
            class="composer-input"
            rows="1"
          ></textarea>

          <div class="composer-actions">
            <button
              class="action-btn stop"
              @click="stopStreaming"
              :disabled="!state.loadding"
            >停止</button>
            <button
              class="action-btn send"
              @click="sendMessage($event)"
            >发送</button>
          </div>
        </div>
      </div>
    </footer>

    <setting-modal v-model:visible="state.visible" />
  </div>
</template>

<style scoped>
/* ====== 布局基础 ====== */
#layout {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  background: #f7f7f8; /* ChatGPT 类似的浅灰背景 */
}

#layout-body {
  flex: 1 1 0%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

#main {
  flex: 1 1 0%;
  padding: 24px 0;
}

/* 居中容器：用于中部和底部主列（保留） */
.container {
  max-width: 780px;
  margin: 0 auto;
  padding: 0 16px; /* 小屏左右留点空 */
}

/* 顶部栏：改为全宽靠左 */
#header {
  position: sticky;
  top: 0;
  z-index: 10;
}
.header-container {
  width: 100%;
  padding: 0 16px;
}
#header .header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  /* 不使用 .container 的 max-width 约束，保持全宽 */
}
#header .title {
  font-weight: 600;
}
#header .icon {
  margin-left: 12px;
  cursor: pointer;
  color: #6b7280; /* gray-500 */
  transition: color .15s ease, transform .15s ease;
}
#header .icon:hover {
  color: #111827; /* gray-900 */
  transform: translateY(-1px);
}

.container { max-width: 900px; } 


/* 统一居中容器：主列 */
.container{
  width: 100%;
  max-width: 900px;
  margin-inline: auto;
  padding-inline: 16px;     /* 两侧基础留白 */
  box-sizing: border-box;
}

/* 给聊天列一个“左侧内边距”，看起来整体更靠右 */
.chat-container{
  padding-left: var(--chat-offset);
}


#header .header-container{ padding-inline: 16px; }
#footer .composer{ padding-inline: 16px; }
.composer-inner{ max-width: 640px; margin-inline: auto; }

html, body, #layout-body{ scrollbar-gutter: stable both-edges; }

.message-row{ padding-inline: 8px; } 


/* 底部输入区 */
#footer {
  border-top: 1px solid #e5e7eb;
  background: #fff;
}

/* 原有的 .composer 保留为容器，新增 .composer-inner 控制宽度 */
.composer {
  position: relative;
  padding: 12px 0;
}

.composer-inner {
  /* 关键：让输入框更窄更美观 */
  max-width: 640px;        /* 可根据喜好调成 600~680 */
  margin: 0 auto;
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

/* 输入框样式优化 */
.composer-input {
  flex: 1 1 auto;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;      /* 比原先超大圆角更稳重 */
  padding: 10px 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,.03);
  transition: border-color .15s ease, box-shadow .15s ease;
}
.composer-input:focus-within {
  border-color: #93c5fd; /* blue-300 */
  box-shadow: 0 0 0 3px rgba(147,197,253,.35);
}

/* 操作按钮收紧间距 */
.composer-actions {
  display: flex;
  gap: 8px;
}
</style>
