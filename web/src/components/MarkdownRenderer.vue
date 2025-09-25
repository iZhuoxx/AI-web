<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import mdHighlight from 'markdown-it-highlightjs'
import 'highlight.js/styles/github.css' // 也可用 github-dark.css

const props = defineProps<{
  source: string
}>()

// markdown-it 实例：不开启 HTML，避免 XSS；开启 linkify 和换行
const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})
md.use(mdHighlight)

const html = ref(md.render(props.source || ''))

watch(() => props.source, (val) => {
  html.value = md.render(val || '')
})

/* 可选：让代码块可横向滚动 */
onMounted(() => {
  // 这里不需要额外逻辑，样式层处理即可
})
onBeforeUnmount(() => {})
</script>

<template>
  <div class="prose markdown-body" v-html="html" />
</template>

<style scoped>
.markdown-body pre {
  background: #0b1021; /* 深色底便于阅读 */
  color: #e5e7eb;
  padding: 12px 14px;
  border-radius: 10px;
  overflow-x: auto;
}
.markdown-body table { border-collapse: collapse; }
.markdown-body table th,
.markdown-body table td { border: 1px solid #e5e7eb; padding: 6px 10px; }
</style>
