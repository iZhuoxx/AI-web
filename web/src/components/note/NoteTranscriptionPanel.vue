<template>
  <a-card class="transcription-panel" :bordered="false" :body-style="{ padding: '0', height: '100%' }">
    <!-- Body -->
    <div class="panel-body">
      <div class="floating-controls">
        <a-segmented
          v-model:value="density"
          :options="densityOptions"
          class="density density--floating"
        />
        <div class="body-actions">
          <div
            class="search-pill"
            :class="{ 'search-pill--active': searchActive }"
            role="button"
            tabindex="0"
            @click.stop="activateSearch"
            @keydown.enter.prevent="activateSearch"
            @keydown.space.prevent="activateSearch"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" class="search-pill__icon">
              <path
                d="M21.53 20.47l-3.66-3.66C19.195 15.24 20 13.214 20 11c0-4.97-4.03-9-9-9s-9 4.03-9 9 4.03 9 9 9c2.215 0 4.24-.804 5.808-2.13l3.66 3.66c.147.146.34.22.53.22s.385-.073.53-.22c.295-.293.295-.767.002-1.06zM3.5 11c0-4.135 3.365-7.5 7.5-7.5s7.5 3.365 7.5 7.5-3.365 7.5-7.5 7.5-7.5-3.365-7.5-7.5z"
              />
            </svg>
            <template v-if="searchActive">
              <input
                ref="inlineSearchInputRef"
                class="search-pill__input"
                type="search"
                :placeholder="placeholderText"
                v-model="searchValue"
                @click.stop
                @input="onUserInput"
                @keydown.enter="handleSearch"
                @blur="handleSearchBlur"
              />
              <button
                v-if="searchValue"
                type="button"
                class="search-pill__clear"
                @click.stop="clearSearch"
                aria-label="清空搜索"
              >
                ✕
              </button>
            </template>
          </div>
          <a-tooltip placement="bottom" title="复制全部文字">
            <button
              type="button"
              class="body-action-btn"
              @click="copyAll"
              :disabled="!hasContent"
              aria-label="复制全部文字"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" class="body-action-icon">
                <path
                  d="M16 1H4a2 2 0 0 0-2 2v12h2V3h12V1zm3 4H8a2 2 0 0 0-2 2v15h13a2 2 0 0 0 2-2V5zm-2 15H8V7h9v13z"
                />
              </svg>
            </button>
          </a-tooltip>
          <a-tooltip placement="bottom" title="清空筛选">
            <button
              type="button"
              class="body-action-btn"
              @click="handleClearAction"
              :disabled="!searchValue && !hasContent"
              aria-label="清空筛选"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" class="body-action-icon">
                <path d="M5 5h14v2H5V5zm2 4h10l-1 11H8L7 9zm5-7a3 3 0 0 1 3 3H9a3 3 0 0 1 3-3z" />
              </svg>
            </button>
          </a-tooltip>
        </div>
      </div>
      <div
        class="transcription-list"
        ref="scrollRef"
        :class="[{ [`density-${density}`]: true }, { 'is-empty': !filteredSegments.length }]"
      >
        <a-empty v-if="!filteredSegments.length" description="暂无有效转写">
          <template #image>
            <i class="empty-icon lucide lucide-audio-lines"></i>
          </template>
        </a-empty>

        <transition-group
          v-else
          name="stream"
          tag="div"
          class="segments-group"
        >
          <div
            v-for="segment in filteredSegments"
            :key="segment.id"
            class="segment"
            :class="{ live: segment.isLive }"
          >
            <div class="meta">
              <span class="timestamp chip">{{ segment.timestamp }}</span>
              <span v-if="segment.speaker" class="speaker chip">{{ segment.speaker }}</span>
              <span v-if="segment.isLive" class="pill">实时</span>
            </div>
            <div class="text" :class="{ 'text--live': segment.isLive }">
              <span class="text__body" v-html="highlight(segment.text)" />
              <span v-if="segment.isLive" class="text__cursor" />
            </div>
          </div>
        </transition-group>
      </div>

      <transition name="fade">
        <button
          v-show="showScrollBtn"
          class="float-scroll"
          type="button"
          aria-label="滚动到底部并开启自动滚动"
          @click="enableAutoAndScroll"
        >
          <svg viewBox="0 0 24 24" class="chevron-down" aria-hidden="true">
            <path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
      </transition>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import type { TranscriptSegment } from '@/types/notes'

const props = defineProps<{
  segments: TranscriptSegment[]
  liveText?: string
  isRecording: boolean
}>()

const scrollRef = ref<HTMLDivElement | null>(null)
const searchValue = ref('')
const userTyped = ref(false) // 是否为用户输入
const showSearchInput = ref(false)
const inlineSearchInputRef = ref<HTMLInputElement | null>(null)
// 自动滚动：无UI开关，滚动与按钮控制
const autoScroll = ref(true)
const showScrollBtn = ref(false)
const density = ref<'comfortable' | 'cozy' | 'compact'>('cozy')
const densityOptions = [
  { label: '舒适', value: 'comfortable' },
  { label: '适中', value: 'cozy' },
  { label: '紧凑', value: 'compact' },
]

const placeholderText = computed(() => '按内容、时间或说话人搜索')
const searchActive = computed(() => showSearchInput.value || Boolean(searchValue.value))

interface DisplaySegment extends TranscriptSegment { isLive?: boolean }

const animatedLiveText = ref('')
let liveAnimationFrame: number | null = null

const buildLiveTimestamp = () =>
  props.isRecording ? '实时' : props.segments.at(-1)?.timestamp || '实时'

const displaySegments = computed<DisplaySegment[]>(() => {
  const base = props.segments.map(segment => ({ ...segment })) as DisplaySegment[]
  const liveContent = animatedLiveText.value.trim()
  if (liveContent) {
    base.push({
      id: 'live-preview',
      timestamp: buildLiveTimestamp(),
      text: liveContent,
      isLive: true,
    })
  }
  return base
})

const normalizedSearch = computed(() => searchValue.value.trim().toLowerCase())

const filteredSegments = computed(() => {
  const query = normalizedSearch.value
  const segments = displaySegments.value
  if (!query) return segments
  return segments.filter(segment => {
    const body = segment.text.toLowerCase()
    const time = String(segment.timestamp).toLowerCase()
    const speaker = (segment.speaker || '').toLowerCase()
    return body.includes(query) || time.includes(query) || speaker.includes(query)
  })
})

const hasContent = computed(() => displaySegments.value.length > 0)

const exportSegments = computed<TranscriptSegment[]>(() => {
  const base = props.segments.map(segment => ({ ...segment }))
  const liveRaw = (props.liveText || '').trim()
  if (liveRaw) {
    base.push({
      id: 'live-preview',
      timestamp: buildLiveTimestamp(),
      text: liveRaw,
    })
  }
  return base
})

const stopLiveAnimation = () => {
  if (liveAnimationFrame !== null) {
    cancelAnimationFrame(liveAnimationFrame)
    liveAnimationFrame = null
  }
}

const animateLiveText = (nextRaw: string) => {
  const next = (nextRaw || '').replace(/\r?\n/g, ' ').trim()
  stopLiveAnimation()

  if (!next) {
    animatedLiveText.value = ''
    return
  }

  const current = animatedLiveText.value
  let prefixLength = 0
  const maxPrefix = Math.min(current.length, next.length)
  while (prefixLength < maxPrefix && current[prefixLength] === next[prefixLength]) {
    prefixLength += 1
  }

  animatedLiveText.value = prefixLength ? next.slice(0, prefixLength) : ''
  const remaining = next.slice(prefixLength)

  if (!remaining.length || remaining.length <= 4 || next.length > 600) {
    animatedLiveText.value = next
    return
  }

  let progress = 0
  const stepSize = Math.max(1, Math.ceil(remaining.length / 12))

  const step = () => {
    progress = Math.min(remaining.length, progress + stepSize)
    animatedLiveText.value = next.slice(0, prefixLength + progress)
    if (progress < remaining.length) {
      liveAnimationFrame = requestAnimationFrame(step)
    } else {
      liveAnimationFrame = null
    }
  }

  liveAnimationFrame = requestAnimationFrame(step)
}

// ---- 搜索行为 ----
const onUserInput = () => { userTyped.value = true }
const clearSearch = () => {
  searchValue.value = ''
  userTyped.value = false
  showSearchInput.value = true
  nextTick(() => inlineSearchInputRef.value?.focus())
}

const activateSearch = () => {
  if (!showSearchInput.value) showSearchInput.value = true
  nextTick(() => inlineSearchInputRef.value?.focus())
}

const handleSearchBlur = () => {
  if (!searchValue.value) {
    showSearchInput.value = false
  }
}

const handleClearAction = () => {
  clearSearch()
  message.success('已清空搜索条件')
}

const escapeHtml = (str: string) =>
  str
    .replaceAll(/&/g, '&amp;')
    .replaceAll(/</g, '&lt;')
    .replaceAll(/>/g, '&gt;')
    .replaceAll(/"/g, '&quot;')
    .replaceAll(/'/g, '&#39;')

const highlight = (text: string) => {
  const q = normalizedSearch.value
  const safe = escapeHtml(text)
  if (!q) return safe
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  return safe.replace(regex, '<mark>$1</mark>')
}

watch(
  () => props.liveText || '',
  value => { animateLiveText(value) },
  { immediate: true },
)

const copyAll = async () => {
  if (!hasContent.value) return
  const text = exportSegments.value.map(s => `[${s.timestamp}] ${s.text}`).join('\n')
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制到剪贴板')
  } catch (err) {
    console.error(err)
    message.error('复制失败，请手动选择文本')
  }
}

const handleSearch = async () => {
  await nextTick()
  if (searchValue.value && scrollRef.value) {
    scrollRef.value.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// ---- 滚动逻辑 ----
const scrollToBottom = () => {
  const el = scrollRef.value
  if (!el) return
  el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
}

const enableAutoAndScroll = () => {
  autoScroll.value = true
  scrollToBottom()
}

const isAtBottom = (el: HTMLDivElement) => {
  const threshold = 8
  return el.scrollHeight - el.scrollTop - el.clientHeight <= threshold
}

const onScroll = () => {
  const el = scrollRef.value
  if (!el) return
  if (!isAtBottom(el)) {
    autoScroll.value = false
    showScrollBtn.value = true
  } else {
    showScrollBtn.value = false
  }
}

watch(
  () => displaySegments.value.length,
  async () => {
    await nextTick()
    if (autoScroll.value && !searchValue.value) {
      scrollToBottom()
    }
  },
)

watch(
  () => animatedLiveText.value,
  async () => {
    await nextTick()
    if (autoScroll.value && !searchValue.value) {
      scrollToBottom()
    }
  },
)

onMounted(() => {
  scrollRef.value?.addEventListener('scroll', onScroll, { passive: true })
})

onUnmounted(() => {
  scrollRef.value?.removeEventListener('scroll', onScroll)
  stopLiveAnimation()
})
</script>

<style scoped>
/* ===== Theme tokens ===== */
:root {
  --panel-bg: #fff;
  --border: rgba(15, 23, 42, 0.08);
  --muted: rgba(0, 0, 0, 0.45);   
  --text: rgba(15, 23, 42, 0.9);
  --chip-bg: rgba(2, 6, 23, 0.04);
  --chip-text: rgba(2, 6, 23, 0.65);
  --pill-bg: rgba(22, 119, 255, 0.12);
  --pill-text: #1677ff;
}

@media (prefers-color-scheme: dark) {
  :root {
    --panel-bg: linear-gradient(180deg, rgba(15, 23, 42, 0.5), rgba(15, 23, 42, 0.65));
    --border: rgba(255, 255, 255, 0.12);
    --muted: rgba(255, 255, 255, 0.55);
    --text: rgba(255, 255, 255, 0.9);
    --chip-bg: rgba(255, 255, 255, 0.06);
    --chip-text: rgba(255, 255, 255, 0.75);
    --pill-bg: rgba(22, 119, 255, 0.18);
    --pill-text: #7db3ff;
  }
}

.transcription-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-radius: 16px;
  overflow: hidden;
  background: #fff;
}

.density :deep(.ant-segmented-item) { padding: 2px 8px; }

.panel-body {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: #fff;
  padding: 0;
}

.floating-controls {
  position: absolute;
  top: 10px;
  right: 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  z-index: 2;
  background: transparent;
  border-radius: 999px;
  padding: 0;
}

.density--floating :deep(.ant-segmented-item) {
  padding: 1px 7px;
  font-size: 12px;
}

.body-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.body-action-btn {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  border: none;
  background: transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #0f172a;
  cursor: pointer;
  transition: transform 0.15s ease, background-color 0.2s ease, color 0.2s ease;
}

.body-action-btn:hover {
  background: rgba(15, 23, 42, 0.08);
  transform: translateY(-1px);
}

.body-action-btn:active {
  transform: translateY(0);
}

.body-action-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
  background: transparent;
}

.body-action-icon {
  width: 14px;
  height: 14px;
  fill: currentColor;
}

.search-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  padding: 0;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: transparent;
  color: #475569;
  cursor: pointer;
  overflow: hidden;
  transition: border-color 0.2s ease, width 0.25s ease, padding 0.25s ease;
}

.search-pill--active {
  cursor: text;
  width: clamp(190px, 26vw, 320px);
  padding: 0 12px;
  gap: 6px;
  justify-content: flex-start;
  border-color: rgba(37, 99, 235, 0.45);
  background: #fff;
}

.search-pill__icon {
  width: 16px;
  height: 16px;
  fill: currentColor;
  flex-shrink: 0;
}

.search-pill__input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 13px;
  color: #0f172a;
  min-width: 0;
}

.search-pill__clear {
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 4px;
}

.search-pill__clear:hover {
  color: #1f2937;
}

/* 列表 */
.transcription-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 0 56px;
  background: #fff;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 16px;
  padding-right: 4px;
}

.segments-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

/* 空状态：完全居中 */
.transcription-list.is-empty {
  align-items: center;
  justify-content: center;
}

.density-comfortable .segment { padding-bottom: 14px; gap: 8px; }
.density-cozy .segment { padding-bottom: 10px; gap: 6px; }
.density-compact .segment { padding-bottom: 6px; gap: 4px; }

.segment {
  display: flex;
  flex-direction: column;
  border-bottom: 1px dashed var(--border);
  position: relative;
}
.segment:last-child { border-bottom: none; }
.segment.live {
  border-bottom-color: rgba(22, 119, 255, 0.32);
}
.segment.live .meta { color: var(--pill-text); }

.meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--muted);
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--chip-bg);
  color: var(--chip-text);
  border: 1px solid var(--border);
}
.timestamp { font-family: 'JetBrains Mono', 'Fira Code', monospace; }
.speaker { background: rgba(22, 119, 255, 0.06); color: var(--pill-text); border-color: rgba(22,119,255,0.25); }

.pill {
  background: var(--pill-bg);
  color: var(--pill-text);
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
}

.text {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text);
}
.text__body {
  flex: 1;
  display: inline-block;
}
.text__cursor {
  width: 10px;
  height: 1.2em;
  border-radius: 2px;
  background: var(--pill-text);
  opacity: 0.65;
  margin-top: 4px;
  animation: cursorBlink 1s steps(2, start) infinite;
}
.text--live {
  color: var(--pill-text);
}
.text--live .text__cursor {
  opacity: 0.9;
}
.text__body mark {
  background: rgba(255, 214, 102, 0.6);
  border-radius: 4px;
  padding: 0 2px;
}

/* 回到底部按钮 */
.float-scroll {
  position: sticky;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 999px;
  background: #fff;
  color: #0f172a;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.12);
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}

.float-scroll:hover {
  transform: translate(-50%, -2px);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.16);
  border-color: rgba(37, 99, 235, 0.35);
}

.float-scroll:active {
  transform: translate(-50%, 0);
}

.chevron-down {
  width: 20px;
  height: 20px;
}

.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* 空图标尺寸 */
.empty-icon { font-size: 36px; opacity: .4; }

/* 自定义搜索（白底与主题一致） */
.search-group {
  position: relative;
  width: 100%;
}
.search-input {
  width: 100%;
  height: 42px;
  padding-left: 2.25rem;
  padding-right: 2rem;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: #fff;
  outline: none;
  color: var(--text);
  transition: box-shadow .2s, transform .06s, color .2s;
  box-shadow: 0 0 0 1px rgba(2,6,23,0.02), 0 4px 18px -12px rgba(2,6,23,0.3);
}
/* 系统“占位符”颜色（跨内核 + scoped 友好）*/
.search-input::placeholder,
.search-input::-webkit-input-placeholder,
.search-input::-moz-placeholder,
.search-input:-ms-input-placeholder {
  color: var(--muted);
  opacity: 1; /* 有些内核会降低 placeholder 的不透明度 */
}

/* 系统填充且非用户输入：把文字整体灰掉（依赖 .sys-filled 类） */
.search-input.sys-filled {
  color: var(--muted);
}

.search-input:hover {
  box-shadow: 0 0 0 1px rgba(2,6,23,0.05), 0 6px 22px -12px rgba(2,6,23,0.35);
}
.search-input:focus {
  box-shadow: 0 0 0 2px rgba(22,119,255,0.25), 0 6px 22px -12px rgba(2,6,23,0.38);
}
.search-input:active { transform: scale(0.995); }

/* 放大镜 icon：始终可见（z-index 提高，避免被输入框盖住） */
.search-icon {
  position: absolute;
  left: 0.8rem;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  fill: var(--muted);
  pointer-events: none;
  z-index: 2;
}

/* 清空按钮 */
.clear-btn {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  font-size: 14px;
  line-height: 1;
  color: var(--muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  z-index: 3;
}
.clear-btn:hover { background: rgba(2,6,23,0.06); }

.stream-enter-active,
.stream-leave-active,
.stream-move {
  transition: opacity .2s ease, transform .2s ease;
}
.stream-enter-from,
.stream-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
.stream-move {
  transition: transform .2s ease;
}

@keyframes cursorBlink {
  0%, 100% { opacity: 0.2; }
  50% { opacity: 0.95; }
}

/* 备用：Ant 搜索宽度（未用） */
:deep(.ant-input-search) { min-width: 260px; }
</style>
