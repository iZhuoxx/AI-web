<template>
  <a-card class="rec-panel" :body-style="panelBodyStyle">
    <div class="row">
      <!-- 左侧：录制按钮与计时 -->
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

        <!-- 时间显示（与主背景一致） -->
        <div class="time">
          <svg viewBox="0 0 24 24" class="clk" aria-hidden="true">
            <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6" fill="none" opacity="0.8" />
            <path d="M12 7v5l3 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="t">{{ formattedDuration }}</span>
        </div>
      </div>

      <!-- 中间：对称波形显示 -->
      <div class="wave-wrapper" role="img" aria-label="audio level">
        <div class="wave" :class="{ on: isRecording }">
          <span
            v-for="(bar, i) in waveBars"
            :key="i"
            class="bar"
            :style="{ 
              '--h': bar + '%',
              '--d': (i * 6) + 'ms',
              '--opacity': bar > 20 ? 0.95 : 0.6
            }"
          />
        </div>
      </div>

      <!-- 右侧：错误/不可用提示 -->
      <div v-if="statusText" class="hint" :class="statusClass">
        <span class="dot" /> {{ statusText }}
      </div>
    </div>

    <!-- 实时转写文案 -->
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

const panelBodyStyle = { padding: '12px 14px' }

const formattedDuration = computed(() => {
  const m = Math.floor(props.duration / 60).toString().padStart(2, '0')
  const s = (props.duration % 60).toString().padStart(2, '0')
  return `${m}:${s}`
})

const statusText = computed(() => {
  if (!props.canRecord) return '麦克风不可用'
  if (props.errorMessage) return props.errorMessage
  return ''
})

const statusClass = computed(() => {
  if (!props.canRecord || props.errorMessage) return 'err'
  return 'muted'
})

/* 中心对称的音频频谱 */
const waveBars = computed(() => {
  const bars = 64
  const base = Math.min(1, Math.max(0, props.audioLevel || 0))
  const intensity = props.isRecording ? base : base * 0.6
  const arr: number[] = []
  const time = Date.now() * 0.003 // 加快动画节奏
  
  for (let i = 0; i < bars; i++) {
    // 多层波形叠加模拟真实频谱
    const wave1 = Math.sin((i + 1) * 0.28 + time) * 0.5
    const wave2 = Math.sin((i + 1) * 0.45 + time * 1.5) * 0.4
    const wave3 = Math.sin((i + 1) * 0.68 + time * 0.8) * 0.35
    const wave4 = Math.sin((i + 1) * 0.92 + time * 1.2) * 0.25
    
    // 中心对称：中间频段能量更高
    const distanceFromCenter = Math.abs(i - bars / 2) / (bars / 2)
    const centerBoost = Math.pow(1 - distanceFromCenter, 1.2) * 0.6 + 0.4
    
    const combined = (wave1 + wave2 + wave3 + wave4) * centerBoost
    
    // 提升动态范围，让波动更明显
    const baseHeight = 15 // 提高最小高度
    const dynamicHeight = intensity * 120 * (combined + 1.2) * centerBoost // 扩大动态范围
    const finalHeight = baseHeight + dynamicHeight
    
    arr.push(Math.max(12, Math.min(98, finalHeight)))
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
:host, .rec-panel, .rec-btn, .wave-wrapper, .hint, .live, .time{
  --panel-bg: linear-gradient(145deg, rgba(248,250,255,0.96), rgba(232,243,255,0.9));
  --text: #0f172a;
  --muted: #475569;
  --blue-plain: #7ca9ff;
  --blue-hover: #2563eb;
  --blue-hover2: #1d4ed8;
  --red: #dc2626;
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
.rec-btn.on{
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
  background: transparent;
  color: var(--text);
  font-weight:600; font-variant-numeric: tabular-nums;
}
.time .clk{ width:15px; height:15px; stroke-width:1.6; opacity:.85; }
.time .t{ font-size:13px; letter-spacing:.02em; }

/* 波形容器 - 中心对称布局 */
.wave-wrapper{
  flex:1; 
  min-width:240px; 
  height:50px;
  position: relative;
  padding:0 10px;
  border-radius:12px;
  background: var(--panel-bg);
  overflow:hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 波形容器 */
.wave{
  width: 100%;
  height: 100%;
  display:flex; 
  align-items:center;
  justify-content: space-between;
  gap: 2px; /* 更小的间距让频谱更密集 */
  position: relative;
  z-index: 2;
}

/* 频谱条 - 中心对称上下扩散 */
.wave .bar{
  --h: 10%;
  --d: 0ms;
  --opacity: 0.6;
  flex: 1;
  max-width: 3px; /* 更细的频谱条 */
  min-width: 1.5px;
  height: var(--h);
  max-height: 48px; /* 增加最大高度 */
  border-radius: 2px;
  background: linear-gradient(
    180deg,
    rgba(37,99,235,0.9) 0%,
    rgba(99,102,241,0.8) 25%,
    rgba(139,92,246,0.75) 50%,
    rgba(99,102,241,0.8) 75%,
    rgba(37,99,235,0.9) 100%
  );
  opacity: var(--opacity);
  box-shadow: 
    0 0 6px rgba(37,99,235,0.4),
    0 0 12px rgba(99,102,241,0.2);
  transition: 
    height 0.15s cubic-bezier(0.25, 0.46, 0.45, 0.94) var(--d),
    opacity 0.12s ease var(--d);
  transform-origin: center center;
  position: relative;
}

/* 录制状态下的动画 - 增强波动效果 */
.wave.on .bar{
  animation: pulse-bar 1s ease-in-out infinite;
}

@keyframes pulse-bar {
  0%, 100% {
    filter: brightness(1) saturate(1);
    transform: scaleY(1);
  }
  50% {
    filter: brightness(1.2) saturate(1.3);
    transform: scaleY(1.05);
  }
}

/* 非录制状态：显著降低高度 */
.wave:not(.on) .bar{ 
  height: calc(var(--h) * 0.2);
  opacity: calc(var(--opacity) * 0.45);
}

/* 添加微妙的发光效果 */
.wave.on::before{
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(
    ellipse at center,
    rgba(37,99,235,0.08) 0%,
    transparent 65%
  );
  pointer-events: none;
  animation: glow-pulse 2.5s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%, 100% {
    opacity: 0.4;
  }
  50% {
    opacity: 0.8;
  }
}

/* 仅错误/不可用提示 */
.hint{
  display:inline-flex; align-items:center; gap:8px;
  padding:6px 10px; border-radius:10px; font-size:12.5px; font-weight:600;
  background: var(--panel-bg);
  color: var(--muted);
}
.hint .dot{ width:6px; height:6px; border-radius:50%; background:#64748b; }
.hint.err{ color:#b91c1c; }
.hint.err .dot{ background:#b91c1c; }

/* 实时转写 */
.live{
  margin-top:8px; padding:8px 10px; border-radius:10px;
  background: var(--panel-bg);
  color: var(--text);
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  font-size:13px;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .wave-wrapper {
    min-width: 200px;
  }
  
  .wave {
    gap: 1.5px;
  }
  
  .wave .bar {
    max-width: 2.5px;
    min-width: 1px;
  }
}
</style>
