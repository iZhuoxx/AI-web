<script setup lang="ts">
import { onMounted, ref, watch, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'
import mdHighlight from 'markdown-it-highlightjs'
import 'highlight.js/styles/github.css' // 你的高亮主题

const props = defineProps<{
  source: string
}>()

// markdown-it：禁用 HTML，避免 XSS；link 自动化；换行
const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})
md.use(mdHighlight)

const html = ref(md.render(props.source || ''))
const mdRef = ref<HTMLElement | null>(null)

// 给每个 <pre> 注入“复制”按钮
function enhanceCodeBlocks(root: HTMLElement) {
  const pres = root.querySelectorAll('pre')
  pres.forEach((pre) => {
    if (pre.querySelector('.copy-btn')) return // 避免重复
    pre.style.position = 'relative'

    const btn = document.createElement('button')
    btn.className = 'copy-btn'
    btn.type = 'button'
    btn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M16 1H4a2 2 0 0 0-2 2v12h2V3h12V1zm3 4H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H8V7h11v14z" />
      </svg>
      <span>复制</span>
    `.trim()

    btn.addEventListener('click', async (e) => {
      e.stopPropagation()
      const code = pre.querySelector('code')
      const text = code?.textContent ?? ''
      try {
        await navigator.clipboard.writeText(text)
        btn.classList.add('copied')
        btn.querySelector('span')!.textContent = '已复制'
        setTimeout(() => {
          btn.classList.remove('copied')
          btn.querySelector('span')!.textContent = '复制'
        }, 1200)
      } catch {
        btn.querySelector('span')!.textContent = '失败'
        setTimeout(() => (btn.querySelector('span')!.textContent = '复制'), 1200)
      }
    })

    pre.appendChild(btn)
  })
}

watch(
  () => props.source,
  async (val) => {
    html.value = md.render(val || '')
    await nextTick()
    if (mdRef.value) enhanceCodeBlocks(mdRef.value)
  },
  { immediate: true }
)

onMounted(() => {
  if (mdRef.value) enhanceCodeBlocks(mdRef.value)
})
</script>

<template>
  <!-- 用 ref 包裹渲染容器，以便增强代码块 -->
  <div ref="mdRef" class="prose markdown-body" v-html="html" />
</template>

<style scoped>
/* 你原有样式 */
.markdown-body pre {
  background: #0b1021;
  color: #e5e7eb;
  padding: 12px 14px;
  border-radius: 10px;
  overflow-x: auto;
}

/* 表格 */
.markdown-body table { border-collapse: collapse; }
.markdown-body table th,
.markdown-body table td { border: 1px solid #e5e7eb; padding: 6px 10px; }

/* 复制按钮 */
:deep(.copy-btn) {
  position: absolute;
  top: 6px;
  right: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 1;
  padding: 6px 8px;
  border: 1px solid var(--border-muted, #e5e7eb);
  background: #fff;
  color: #374151;
  border-radius: 6px;
  cursor: pointer;
  opacity: 0;
  transition: opacity .15s ease, transform .15s ease, background .15s ease, border-color .15s ease;
  user-select: none;
}
.markdown-body pre:hover :deep(.copy-btn) { opacity: 1; }
:deep(.copy-btn:hover) { background: #f9fafb; transform: translateY(-1px); }
:deep(.copy-btn svg) { fill: currentColor; }

/* 点击后的小状态 */
:deep(.copy-btn.copied) {
  border-color: #10a37f;
  color: #10a37f;
}

/* 暗色主题的适配（如果跟随系统） */
@media (prefers-color-scheme: dark) {
  :deep(.copy-btn) {
    background: #1f2937;
    color: #e5e7eb;
    border-color: #374151;
  }
  :deep(.copy-btn:hover) { background: #111827; }
}
</style>
