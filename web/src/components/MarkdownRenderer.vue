<script setup lang="ts">
import { onMounted, ref, watch, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'
import mdHighlight from 'markdown-it-highlightjs'
import 'highlight.js/styles/github.css'

interface Citation {
  fileId: string
  filename?: string
  index?: number
  startIndex?: number
  endIndex?: number
  quote?: string
  label?: number
}

const props = defineProps<{
  source: string
  citations?: Citation[]
}>()

const emit = defineEmits<{
  (e: 'citation-click', payload: Citation): void
}>()

// Markdown-it 配置
const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: true, // 启用智能引号和其他排版优化
})
md.use(mdHighlight)

// 自定义渲染规则：优化链接
const defaultLinkRenderer = md.renderer.rules.link_open || function(tokens, idx, options, env, self) {
  return self.renderToken(tokens, idx, options)
}

md.renderer.rules.link_open = function(tokens, idx, options, env, self) {
  const token = tokens[idx]
  const hrefIndex = token.attrIndex('href')
  
  if (hrefIndex >= 0) {
    const href = token.attrs![hrefIndex][1]
    // 外部链接添加 target="_blank" 和 rel
    if (href.startsWith('http://') || href.startsWith('https://')) {
      token.attrPush(['target', '_blank'])
      token.attrPush(['rel', 'noopener noreferrer'])
    }
  }
  
  return defaultLinkRenderer(tokens, idx, options, env, self)
}

// 自定义渲染规则：优化代码块
md.renderer.rules.fence = function(tokens, idx, options, env, self) {
  const token = tokens[idx]
  const info = token.info ? md.utils.unescapeAll(token.info).trim() : ''
  const langName = info ? info.split(/\s+/g)[0] : ''
  const langClass = langName ? ` language-${md.utils.escapeHtml(langName)}` : ''
  
  let highlighted = ''
  if (options.highlight) {
    highlighted = options.highlight(token.content, langName, '') || md.utils.escapeHtml(token.content)
  } else {
    highlighted = md.utils.escapeHtml(token.content)
  }
  
  const langLabel = langName ? `<div class="code-block-lang">${md.utils.escapeHtml(langName)}</div>` : ''
  
  return `<pre class="code-block"><code class="hljs${langClass}">${highlighted}</code>${langLabel}</pre>\n`
}

const mdRef = ref<HTMLElement | null>(null)
const html = ref('')

// Citation 处理
const normalizeIndexValue = (val: unknown): number | null => {
  if (typeof val === 'number' && Number.isFinite(val)) return val
  if (typeof val === 'string' && val.trim() !== '' && !Number.isNaN(Number(val))) return Number(val)
  return null
}

interface CitationPoint extends Citation {
  label: number
}

/**
 * 给代码块添加复制按钮
 */
function enhanceCodeBlocks(root: HTMLElement) {
  const pres = root.querySelectorAll('pre.code-block')
  pres.forEach((pre) => {
    if (pre.querySelector('.copy-btn')) return
    const preElement = pre as HTMLPreElement
    preElement.style.position = 'relative'

    const btn = document.createElement('button')
    btn.className = 'copy-btn'
    btn.type = 'button'
    btn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
      <span>复制代码</span>
    `

    btn.addEventListener('click', async (e) => {
      e.stopPropagation()
      const code = pre.querySelector('code')
      const text = code?.textContent ?? ''
      
      try {
        await navigator.clipboard.writeText(text)
        btn.classList.add('copied')
        const span = btn.querySelector('span')
        if (span) span.textContent = '已复制!'
        
        setTimeout(() => {
          btn.classList.remove('copied')
          if (span) span.textContent = '复制代码'
        }, 1500)
      } catch {
        const span = btn.querySelector('span')
        if (span) {
          span.textContent = '复制失败'
          setTimeout(() => (span.textContent = '复制代码'), 1500)
        }
      }
    })

    pre.appendChild(btn)
  })
}

/**
 * 构建 citation pins（末尾展示）
 */
const buildCitationPins = (): CitationPoint[] => {
  if (!Array.isArray(props.citations) || !props.citations.length) return []
  
  const orderMap = new Map<string, number>()
  let nextLabel = 1

  return props.citations
    .map((cit, idx) => {
      const fileKey = cit.fileId || `__missing-${idx}`
      const providedLabel = normalizeIndexValue((cit as any).label)
      const hasProvidedLabel = typeof providedLabel === 'number' && providedLabel > 0
      
      let label: number
      if (hasProvidedLabel) {
        label = providedLabel!
        if (!orderMap.has(fileKey)) {
          orderMap.set(fileKey, label)
        }
        if (label >= nextLabel) {
          nextLabel = label + 1
        }
      } else if (orderMap.has(fileKey)) {
        label = orderMap.get(fileKey)!
      } else {
        label = nextLabel++
        orderMap.set(fileKey, label)
      }

      return {
        ...cit,
        label,
      }
    })
    .filter((cit): cit is CitationPoint => Boolean(cit.fileId && typeof cit.label === 'number'))
}

/**
 * 创建 citation pin 元素
 */
const createCitationPin = (cit: CitationPoint): HTMLElement => {
  const btn = document.createElement('button')
  btn.type = 'button'
  btn.className = 'md-citation-pin'
  btn.setAttribute('data-label', String(cit.label))
  btn.setAttribute('aria-label', `Citation ${cit.label}`)
  btn.addEventListener('click', () => emit('citation-click', cit))

  const num = document.createElement('span')
  num.className = 'md-citation-pin__num'
  num.textContent = String(cit.label)

  const tooltip = document.createElement('div')
  tooltip.className = 'md-citation-pin__tooltip'

  if (cit.quote?.trim()) {
    const quote = document.createElement('div')
    quote.className = 'md-citation-pin__quote'
    quote.textContent = cit.quote
    tooltip.appendChild(quote)
  }

  const title = document.createElement('div')
  title.className = 'md-citation-pin__title'
  title.textContent = cit.filename || cit.fileId
  tooltip.appendChild(title)

  btn.appendChild(num)
  btn.appendChild(tooltip)

  return btn
}

/**
 * 将 citation pins 追加到回复末尾
 */
const renderCitationsFooter = (root: HTMLElement): void => {
  if (!root) return
  
  root.querySelectorAll('.md-citation-footer').forEach(el => el.remove())

  const pins = buildCitationPins()
  if (!pins.length) return

  const footer = document.createElement('div')
  footer.className = 'md-citation-footer'

  pins.forEach(pin => {
    footer.appendChild(createCitationPin(pin))
  })

  const target =
    (root.lastElementChild as HTMLElement | null) ??
    root

  target.appendChild(footer)
}

/**
 * 渲染 Markdown 内容
 */
const renderMarkdown = async () => {
  // 先渲染 HTML
  html.value = md.render(props.source || '')
  
  // 等待 DOM 更新
  await nextTick()
  
  if (mdRef.value) {
    enhanceCodeBlocks(mdRef.value)
    renderCitationsFooter(mdRef.value)
  }
}

// 监听变化
watch(
  () => [props.source, props.citations],
  renderMarkdown,
  { deep: true }
)

onMounted(renderMarkdown)
</script>

<template>
  <div ref="mdRef" class="prose markdown-body" v-html="html" />
</template>

<style scoped>
/* 基础排版 */
.markdown-body {
  font-size: 18px;
  line-height: 1.8;
  color: #1f2937;
  word-wrap: break-word;
}

/* 段落 */
.markdown-body :deep(p) {
  margin: 0.85em 0;
}

.markdown-body :deep(p:first-child) {
  margin-top: 0;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

/* 标题 */
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin-top: 1.5em;
  margin-bottom: 0.6em;
  font-weight: 600;
  line-height: 1.4;
  color: #111827;
}

.markdown-body :deep(h1:first-child),
.markdown-body :deep(h2:first-child),
.markdown-body :deep(h3:first-child) {
  margin-top: 0;
}

.markdown-body :deep(h1) {
  font-size: 1.75em;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #e5e7eb;
}

.markdown-body :deep(h2) {
  font-size: 1.5em;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #e5e7eb;
}

.markdown-body :deep(h3) {
  font-size: 1.3em;
}

.markdown-body :deep(h4) {
  font-size: 1.15em;
}

.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  font-size: 1em;
}

/* 强调和加粗 */
.markdown-body :deep(strong),
.markdown-body :deep(b) {
  font-weight: 600;
  color: #111827;
}

.markdown-body :deep(em),
.markdown-body :deep(i) {
  font-style: italic;
}

/* 链接 */
.markdown-body :deep(a) {
  color: #2563eb;
  text-decoration: underline;
  text-decoration-color: rgba(37, 99, 235, 0.3);
  text-underline-offset: 2px;
  transition: all 0.2s ease;
}

.markdown-body :deep(a:hover) {
  color: #1d4ed8;
  text-decoration-color: rgba(29, 78, 216, 0.5);
}

/* 列表 */
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0.85em 0;
  padding-left: 2em;
  line-height: 1.9;
}

.markdown-body :deep(li) {
  margin: 0.5em 0;
}

.markdown-body :deep(ul ul),
.markdown-body :deep(ol ul),
.markdown-body :deep(ul ol),
.markdown-body :deep(ol ol) {
  margin: 0.3em 0;
}

.markdown-body :deep(li > p) {
  margin: 0.3em 0;
}

/* 行内代码 */
.markdown-body :deep(code) {
  font-family: 'SF Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
  background: rgba(175, 184, 193, 0.2);
  padding: 0.2em 0.4em;
  border-radius: 4px;
  color: #1f2937;
  font-weight: 400;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  border-radius: 0;
  color: inherit;
  font-size: inherit;
}

/* 代码块 */
.markdown-body :deep(pre.code-block) {
  background: #0d1117;
  color: #e6edf3;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  position: relative;
  margin: 1.2em 0;
  font-size: 14px;
  line-height: 1.6;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.markdown-body :deep(pre.code-block code) {
  display: block;
  padding: 0;
  margin: 0;
  background: transparent;
  color: inherit;
  font-family: 'SF Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
  white-space: pre;
  word-wrap: normal;
}

/* 代码块语言标签 */
.markdown-body :deep(.code-block-lang) {
  position: absolute;
  top: 8px;
  left: 16px;
  font-size: 11px;
  font-weight: 600;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  user-select: none;
  pointer-events: none;
  opacity: 0.7;
}

/* 引用块 */
.markdown-body :deep(blockquote) {
  margin: 1em 0;
  padding: 0 1em;
  border-left: 4px solid #d1d5db;
  color: #6b7280;
  font-style: italic;
}

.markdown-body :deep(blockquote p) {
  margin: 0.5em 0;
}

/* 分割线 */
.markdown-body :deep(hr) {
  height: 1px;
  padding: 0;
  margin: 2em 0;
  background-color: #e5e7eb;
  border: 0;
}

/* 表格 */
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1.2em 0;
  display: block;
  overflow-x: auto;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.markdown-body :deep(table th),
.markdown-body :deep(table td) {
  border: 1px solid #e5e7eb;
  padding: 10px 14px;
  text-align: left;
}

.markdown-body :deep(table th) {
  background: #f9fafb;
  font-weight: 600;
  color: #111827;
}

.markdown-body :deep(table tr:nth-child(even)) {
  background: #f9fafb;
}

.markdown-body :deep(table tr:hover) {
  background: #f3f4f6;
}

/* 图片 */
.markdown-body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 1em 0;
}

/* 复制按钮样式 */
.markdown-body :deep(.copy-btn) {
  position: absolute;
  top: 12px;
  right: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 1;
  padding: 6px 10px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.08);
  color: #e6edf3;
  border-radius: 6px;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s ease;
  user-select: none;
  backdrop-filter: blur(8px);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.markdown-body :deep(pre.code-block:hover .copy-btn) {
  opacity: 1;
}

.markdown-body :deep(.copy-btn:hover) {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.25);
  transform: translateY(-1px);
}

.markdown-body :deep(.copy-btn:active) {
  transform: translateY(0);
}

.markdown-body :deep(.copy-btn svg) {
  flex-shrink: 0;
}

.markdown-body :deep(.copy-btn.copied) {
  border-color: rgba(16, 163, 127, 0.5);
  background: rgba(16, 163, 127, 0.15);
  color: #3fb950;
}

/* Citation Pin 样式 */
.markdown-body :deep(.md-citation-footer) { 
  display: inline-flex; 
  gap: 8px; 
  flex-wrap: wrap; 
  align-items: center; 
  margin-left: 6px;
  margin-top: 0.5em;
}

.markdown-body :deep(.md-citation-pin) {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 0;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid rgba(99, 102, 241, 0.3);
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
  color: #4338ca;
  font-weight: 600;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  vertical-align: baseline;
  line-height: 1;
}

.markdown-body :deep(.md-citation-pin:hover) {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 16px rgba(79, 70, 229, 0.2);
  border-color: rgba(79, 70, 229, 0.5);
  background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
}

.markdown-body :deep(.md-citation-pin:active) {
  transform: translateY(-1px) scale(1.02);
}

.markdown-body :deep(.md-citation-pin__num) {
  line-height: 1;
  user-select: none;
}

/* Tooltip 样式 */
.markdown-body :deep(.md-citation-pin__tooltip) {
  position: absolute;
  top: 50%;
  left: calc(100% + 12px);
  transform: translateY(-50%) scale(0.95);
  transform-origin: left center;
  min-width: 200px;
  max-width: min(320px, 70vw);
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.06);
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
  z-index: 100;
}

.markdown-body :deep(.md-citation-pin:hover .md-citation-pin__tooltip) {
  opacity: 1;
  visibility: visible;
  transform: translateY(-50%) scale(1);
  pointer-events: auto;
}

.markdown-body :deep(.md-citation-pin__title) {
  font-weight: 600;
  font-size: 13px;
  color: #111827;
  line-height: 1.5;
  word-break: break-word;
}

.markdown-body :deep(.md-citation-pin__quote) {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.6;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f3f4f6;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 暗色模式适配 */
@media (prefers-color-scheme: dark) {
  .markdown-body {
    color: #e5e7eb;
  }

  .markdown-body :deep(h1),
  .markdown-body :deep(h2),
  .markdown-body :deep(h3),
  .markdown-body :deep(h4),
  .markdown-body :deep(h5),
  .markdown-body :deep(h6) {
    color: #f9fafb;
    border-bottom-color: #374151;
  }

  .markdown-body :deep(strong),
  .markdown-body :deep(b) {
    color: #f9fafb;
  }

  .markdown-body :deep(a) {
    color: #60a5fa;
    text-decoration-color: rgba(96, 165, 250, 0.3);
  }

  .markdown-body :deep(a:hover) {
    color: #93c5fd;
    text-decoration-color: rgba(147, 197, 253, 0.5);
  }

  .markdown-body :deep(code) {
    background: rgba(110, 118, 129, 0.4);
    color: #e5e7eb;
  }

  .markdown-body :deep(blockquote) {
    border-left-color: #4b5563;
    color: #9ca3af;
  }

  .markdown-body :deep(hr) {
    background-color: #374151;
  }

  .markdown-body :deep(table) {
    border-color: #374151;
  }

  .markdown-body :deep(table th) {
    background: #1f2937;
    color: #f9fafb;
  }

  .markdown-body :deep(table th),
  .markdown-body :deep(table td) {
    border-color: #374151;
  }

  .markdown-body :deep(table tr:nth-child(even)) {
    background: #1f2937;
  }

  .markdown-body :deep(table tr:hover) {
    background: #374151;
  }

  .markdown-body :deep(.md-citation-pin) {
    border-color: rgba(129, 140, 248, 0.3);
    background: linear-gradient(135deg, #312e81 0%, #3730a3 100%);
    color: #c7d2fe;
  }

  .markdown-body :deep(.md-citation-pin:hover) {
    border-color: rgba(129, 140, 248, 0.5);
    background: linear-gradient(135deg, #3730a3 0%, #4338ca 100%);
    box-shadow: 0 8px 16px rgba(99, 102, 241, 0.3);
  }

  .markdown-body :deep(.md-citation-pin__tooltip) {
    background: #1f2937;
    border-color: #374151;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4), 0 2px 8px rgba(0, 0, 0, 0.2);
  }

  .markdown-body :deep(.md-citation-pin__title) {
    color: #f9fafb;
  }

  .markdown-body :deep(.md-citation-pin__quote) {
    color: #d1d5db;
    border-bottom-color: #374151;
  }
}

/* 响应式优化 */
@media (max-width: 640px) {
  .markdown-body {
    font-size: 15px;
  }

  .markdown-body :deep(.md-citation-pin__tooltip) {
    left: auto;
    right: 0;
    transform: translateY(-50%) scale(0.95);
    transform-origin: right center;
  }

  .markdown-body :deep(.md-citation-pin:hover .md-citation-pin__tooltip) {
    transform: translateY(-50%) scale(1);
  }
}
</style>