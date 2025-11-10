<template>
  <a-card class="rec-panel" :body-style="panelBodyStyle">
    <div class="row">
      <!-- 左侧：录制按钮 + 时间 -->
      <div class="left-group">
        <button
          class="rec-btn"
          :class="{ on: isRecording, disabled: !canRecord }"
          type="button"
          :disabled="!canRecord"
          @click="handlePrimaryAction"
          :title="isRecording ? '停止' : '开始'"
          aria-label="Record"
        >
          <component :is="isRecording ? SquareIcon : MicIcon" class="btn-icon" />
        </button>

        <!-- 时间显示（与主背景一致、无边框） -->
        <div class="time">
          <svg viewBox="0 0 24 24" class="clk" aria-hidden="true">
            <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6" fill="none" opacity="0.8" />
            <path d="M12 7v5l3 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="t">{{ formattedDuration }}</span>
        </div>
      </div>

      <!-- 中间：波形（与主背景一致、无边框） -->
      <div class="wave" :class="{ on: isRecording }" role="img" aria-label="audio level">
        <span
          v-for="(bar, i) in waveBars"
          :key="i"
          class="bar"
          :style="{ '--h': bar + 'px', '--d': (i * 14) + 'ms' }"
        />
      </div>

      <!-- 右侧：仅错误/不可用提示（不显示“连接中”） -->
      <div v-if="statusText" class="hint" :class="statusClass">
        <span class="dot" /> {{ statusText }}
      </div>
    </div>

    <!-- 实时转写（可选） -->
    <div v-if="liveText" class="live">{{ liveText }}</div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { MicIcon, SquareIcon } from 'lucide-vue-next'
import type { TranscriptSegment } from '@/types/notes'

const props = defineProps<{
  canRecord: boolean
  isConnected?: boolean
  connectionReady?: boolean
  isRecording: boolean
  isPaused: boolean
  duration: number
  segments?: TranscriptSegment[]
  liveText?: string
  audioLevel: number
  errorMessage?: string
}>()

const emit = defineEmits<{
  (e: 'start'): void
  (e: 'stop'): void
  (e: 'pause'): void
  (e: 'resume'): void
}>()

const panelBodyStyle = { padding: '12px 14px' } // 更扁

const formattedDuration = computed(() => {
  const m = Math.floor(props.duration / 60).toString().padStart(2, '0')
  const s = (props.duration % 60).toString().padStart(2, '0')
  return `${m}:${s}`
})

/* 只显示不可用/错误；不显示“连接中”/“就绪”/“录制中” */
const statusText = computed(() => {
  if (!props.canRecord) return '麦克风不可用'
  if (props.errorMessage) return props.errorMessage
  return ''
})

const statusClass = computed(() => {
  if (!props.canRecord || props.errorMessage) return 'err'
  return 'muted'
})

/* 流动感波形 */
const waveBars = computed(() => {
  const bars = 26
  const base = Math.min(1, Math.max(0, props.audioLevel || 0))
  const intensity = props.isRecording ? base : base * 1.2
  const arr: number[] = []
  for (let i = 0; i < bars; i++) {
    const m = Math.sin((i + 1) * 0.42) * 0.35 + 0.9
    const h = 6 + (intensity * 40 + 8) * m
    arr.push(h)
  }
  return arr
})

const handlePrimaryAction = () => {
  if (!props.canRecord) return
  if (props.isRecording) emit('stop')
  else emit('start')
}
</script>

<style scoped>
/* 统一浅蓝主背景变量 */
:host, .rec-panel, .rec-btn, .wave, .hint, .live, .time{
  --panel-bg: linear-gradient(145deg, rgba(248,250,255,0.96), rgba(232,243,255,0.9));
  --text: #0f172a;
  --muted: #475569;
  --blue-plain: #7ca9ff; /* 浅蓝（默认按钮） */
  --blue-hover: #2563eb; /* hover 深一点 */
  --blue-hover2: #1d4ed8;
  --red: #dc2626;        /* 停止色 */
}

/* Panel 更扁：无边框，极轻阴影 */
.rec-panel{
  border: none;
  border-radius:14px;
  background: var(--panel-bg);
  box-shadow: none;
}

.row{
  display:flex; align-items:center; gap:12px; flex-wrap:wrap;
}

.left-group{
  display:flex; align-items:center; gap:10px;
}

/* 按钮更小、默认浅蓝；hover 深一点；停止态无动效 */
.rec-btn{
  width:35px; height:35px; border-radius:12px;
  display:grid; place-items:center;
  background: linear-gradient(135deg, var(--blue-plain), #5d86fa);
  color:#fff;
  border:none;
  box-shadow: 0 6px 14px rgba(37,99,235,0.18);
  transition: background .15s ease, transform .12s ease, opacity .12s ease;
}
.rec-btn:hover:not(.on):not(.disabled){
  background: linear-gradient(135deg, var(--blue-hover), var(--blue-hover2));
  transform: translateY(-1px);
}
.rec-btn.on{ /* 停止按钮：仅颜色变化，无脉冲等动效 */
  background: linear-gradient(135deg, #ef4444, var(--red));
  transform: none;
}
.rec-btn.disabled{ opacity:.5; cursor:not-allowed; }
.rec-btn .btn-icon{ width:18px; height:18px; }

/* 时间：与主背景一致、无边框、更轻盈 */
.time{
  display:flex; align-items:center; gap:6px;
  padding:6px 10px;
  border-radius:999px;
  background: var(--panel-bg); /* 与面板一致 */
  color: var(--text);
  font-weight:600; font-variant-numeric: tabular-nums;
  /* 无边框，无阴影，保持扁平 */
}
.time .clk{ width:15px; height:15px; stroke-width:1.6; opacity:.85; }
.time .t{ font-size:13px; letter-spacing:.02em; }
.time {
  background: transparent;
}
/* 波形：与主背景一致、无边框、柔光条形 */
.wave{
  flex:1; min-width:240px; height:44px;
  display:flex; align-items:flex-end; gap:6px;
  padding:0 8px;
  border-radius:12px;
  background: var(--panel-bg); /* 与面板一致 */
  overflow:hidden;
  /* 无边框、极轻蒙版增加质感 */
  mask-image: radial-gradient(white 85%, transparent 100%);
}
.wave .bar{
  --h: 12px; --d: 0ms;
  flex:1; height:10px;
  transform-origin:50% 100%;
  transform:scaleY(calc(var(--h)/12));
  border-radius:999px;
  background:
    linear-gradient(180deg, rgba(37,99,235,0.80), rgba(99,102,241,0.38), rgba(255,255,255,0.18));
  box-shadow: 0 3px 8px rgba(37,99,235,0.14);
  filter: saturate(1.02) brightness(1.03);
  opacity:.9;
  transition:transform .25s cubic-bezier(.2,.7,.25,1) var(--d), opacity .2s ease var(--d);
}
.wave:not(.on) .bar{ transform:scaleY(.3); opacity:.45; }

/* 仅错误/不可用提示（不显示“连接中”） */
.hint{
  display:inline-flex; align-items:center; gap:8px;
  padding:6px 10px; border-radius:10px; font-size:12.5px; font-weight:600;
  background: var(--panel-bg);
  color: var(--muted);
}
.hint .dot{ width:6px; height:6px; border-radius:50%; background:#64748b; }
.hint.err{ color:#b91c1c; }
.hint.err .dot{ background:#b91c1c; }

/* 实时转写（可选） */
.live{
  margin-top:8px; padding:8px 10px; border-radius:10px;
  background: var(--panel-bg);
  color: var(--text);
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  font-size:13px;
}
</style>
