<template>
  <div class="rich-editor">
    <div class="toolbar">
      <a-space size="small" wrap>
        <a-button size="small" @click="execCommand('bold')" title="Bold">
          <strong>B</strong>
        </a-button>
        <a-button size="small" @click="execCommand('italic')" title="Italic">
          <em>I</em>
        </a-button>
        <a-button size="small" @click="execCommand('underline')" title="Underline">
          <span class="underline">U</span>
        </a-button>
        <a-divider type="vertical" />
        <a-button size="small" @click="formatBlock('h1')" title="Heading 1">H1</a-button>
        <a-button size="small" @click="formatBlock('h2')" title="Heading 2">H2</a-button>
        <a-button size="small" @click="formatBlock('h3')" title="Heading 3">H3</a-button>
        <a-divider type="vertical" />
        <a-button size="small" @click="execCommand('insertUnorderedList')" title="Bullet list">• List</a-button>
        <a-button size="small" @click="execCommand('insertOrderedList')" title="Numbered list">1. List</a-button>
        <a-divider type="vertical" />
        <a-button size="small" @click="formatBlock('pre')" title="Code block">
          <code>&lt;/&gt;</code>
        </a-button>
      </a-space>
    </div>
    <div
      ref="editorRef"
      class="editor-surface"
      contenteditable
      :data-placeholder="placeholder"
      @input="handleInput"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{
  modelValue: string
  placeholder?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const editorRef = ref<HTMLDivElement | null>(null)

const updateInnerHtml = (html: string) => {
  if (!editorRef.value) return
  if (editorRef.value.innerHTML !== html) {
    editorRef.value.innerHTML = html
  }
}

watch(
  () => props.modelValue,
  (value) => {
    updateInnerHtml(value || '')
  },
  { immediate: true },
)

const handleInput = () => {
  emit('update:modelValue', editorRef.value?.innerHTML ?? '')
}

const execCommand = (command: string) => {
  document.execCommand(command, false)
  editorRef.value?.focus()
}

const formatBlock = (tag: string) => {
  document.execCommand('formatBlock', false, tag)
  editorRef.value?.focus()
}

onMounted(() => {
  updateInnerHtml(props.modelValue || '')
})

onBeforeUnmount(() => {
  if (!editorRef.value) return
  editorRef.value.innerHTML = ''
})
</script>

<style scoped>
.rich-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toolbar {
  padding: 8px 12px;
  border: 1px solid var(--border-muted, #d9d9d9);
  border-radius: 8px;
  background: #fafafa;
}

.toolbar strong,
.toolbar em,
.toolbar .underline,
.toolbar code {
  font-size: 13px;
}

.toolbar .underline {
  text-decoration: underline;
}

.editor-surface {
  min-height: 320px;
  border: 1px solid var(--border-muted, #d9d9d9);
  border-radius: 8px;
  padding: 12px;
  overflow-y: auto;
  line-height: 1.6;
}

.editor-surface:focus {
  outline: 2px solid #1677ff33;
}

.editor-surface:empty:before {
  content: attr(data-placeholder);
  color: rgba(0, 0, 0, 0.35);
  pointer-events: none;
}
</style>
