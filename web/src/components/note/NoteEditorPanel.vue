<template>
  <div class="note-editor-panel">
    <header class="note-editor__header">
      <button class="header-back" type="button" aria-label="返回" @click="handleBack">
        <ArrowLeftIcon class="header-back__icon" />
      </button>

      <div class="note-title" :class="{ 'note-title--editing': isEditingTitle }" @click="beginTitleEdit">
        <span
          class="note-title__label"
          :class="{
            'note-title__label--placeholder': !noteTitle.trim(),
            'note-title__label--hidden': isEditingTitle,
          }"
        >
          {{ noteTitle || '未命名笔记' }}
        </span>
        <input
          v-if="isEditingTitle"
          ref="titleInputRef"
          v-model="noteTitleInput"
          class="note-title__input"
          placeholder="输入笔记标题"
          @blur="commitTitleEdit"
          @keydown.enter.prevent="commitTitleEdit"
          @keydown.esc.prevent="cancelTitleEdit"
        />
      </div>

      <div class="note-header__actions">
        <a-tag v-if="isGenerating" class="status-tag" color="processing">AI 正在生成...</a-tag>
        <a-tag v-else-if="isSaving" class="status-tag" color="default">保存中...</a-tag>
        <a-tag v-else-if="showSavedIndicator" class="status-tag" color="success">已保存</a-tag>

        <div class="note-header__toolbar" v-if="editorInstance">
          <button
            class="toolbar-btn"
            type="button"
            aria-label="撤销"
            :disabled="!canUndo"
            @click="undo"
          >
            <UndoIcon class="icon" />
          </button>

          <button
            class="toolbar-btn"
            type="button"
            aria-label="重做"
            :disabled="!canRedo"
            @click="redo"
          >
            <RedoIcon class="icon" />
          </button>

          <a-dropdown
            :trigger="['click']"
            overlay-class-name="rounded-dropdown note-export-dropdown"
            :get-popup-container="getToolbarPopupContainer"
          >
            <template #overlay>
              <a-menu :selectable="false" @click="handleExportClick">
                <a-menu-item key="markdown">
                  <template #icon>
                    <FileMarkdownOutlined />
                  </template>
                  导出 Markdown
                </a-menu-item>
                <a-menu-item key="html">
                  <template #icon>
                    <Html5Outlined />
                  </template>
                  导出 HTML
                </a-menu-item>
                <a-menu-item key="pdf">
                  <template #icon>
                    <FilePdfOutlined />
                  </template>
                  导出 PDF
                </a-menu-item>
                <a-menu-item key="txt">
                  <template #icon>
                    <FileTextOutlined />
                  </template>
                  导出 TXT
                </a-menu-item>
              </a-menu>
            </template>
            <button class="toolbar-btn" type="button" aria-label="导出">
              <DownloadIcon class="icon" />
            </button>
          </a-dropdown>

          <button
            v-if="showFullscreenToggle"
            class="toolbar-btn"
            type="button"
            :aria-label="isFullscreenComputed ? '退出全屏' : '全屏编辑'"
            @click="emit('toggle-fullscreen')"
          >
            <component :is="isFullscreenComputed ? Minimize2Icon : Maximize2Icon" class="icon" />
          </button>
        </div>
      </div>
    </header>

    <section class="note-editor__body">
      <BubbleMenu
        v-if="editorInstance"
        :editor="editorInstance"
        :tippy-options="{ maxWidth: 'none', duration: 120, animation: 'shift-away', offset: [0, 8], interactive: true }"
        :should-show="shouldShowBubbleMenu"
      >
        <div class="bubble-toolbar">
          <div class="bubble-toolbar__group">
            <a-dropdown
              :trigger="['click']"
              overlay-class-name="rounded-dropdown block-style-dropdown"
              :get-popup-container="getToolbarPopupContainer"
            >
              <template #overlay>
                <a-menu :selectable="false" @click="handleHeadingSelect">
                  <a-menu-item key="paragraph">
                    <div class="block-style-item block-style-item--body">正文</div>
                  </a-menu-item>
                  <a-menu-item key="h1">
                    <div class="block-style-item block-style-item--h1">标题 1</div>
                  </a-menu-item>
                  <a-menu-item key="h2">
                    <div class="block-style-item block-style-item--h2">标题 2</div>
                  </a-menu-item>
                  <a-menu-item key="h3">
                    <div class="block-style-item block-style-item--h3">标题 3</div>
                  </a-menu-item>
                  <a-menu-item key="h4">
                    <div class="block-style-item block-style-item--h4">标题 4</div>
                  </a-menu-item>
                  <a-menu-item key="h5">
                    <div class="block-style-item block-style-item--h5">标题 5</div>
                  </a-menu-item>
                </a-menu>
              </template>
              <button class="toolbar-btn bubble-btn block-style-btn" type="button" aria-label="段落样式">
                <Heading1Icon class="icon" />
                <ChevronDownIcon class="dropdown-icon" />
              </button>
            </a-dropdown>

            <a-dropdown
              :trigger="['click']"
              overlay-class-name="rounded-dropdown list-style-dropdown"
              :get-popup-container="getToolbarPopupContainer"
            >
              <template #overlay>
                <a-menu :selectable="false" @click="handleListSelect">
                  <a-menu-item key="bulletList">
                    <template #icon>
                      <span class="menu-leading-icon menu-leading-icon--bullet">•</span>
                    </template>
                    项目符号列表
                  </a-menu-item>
                  <a-menu-item key="orderedList">
                    <template #icon>
                      <span class="menu-leading-icon menu-leading-icon--ordered">1.</span>
                    </template>
                    编号列表
                  </a-menu-item>
                  <a-menu-item key="taskList">
                    <template #icon>
                      <span class="menu-leading-icon menu-leading-icon--task">✓</span>
                    </template>
                    待办列表
                  </a-menu-item>
                </a-menu>
              </template>
              <button class="toolbar-btn bubble-btn" type="button" aria-label="列表样式">
                <ListIcon class="icon" />
                <ChevronDownIcon class="dropdown-icon" />
              </button>
            </a-dropdown>

            <div class="color-merge-btn">
              <button
                class="toolbar-btn bubble-btn color-merge-btn__chip-btn"
                :class="{ 'is-active': isHighlightActive }"
                type="button"
                aria-label="应用当前高亮"
                @click="toggleCurrentHighlight"
              >
                <span
                  class="color-merge-btn__chip"
                  :style="{
                    backgroundColor: currentHighlightColor || '#fffbe6',
                    color: currentTextColor,
                    borderColor: currentHighlightColor ? 'rgba(0,0,0,0.16)' : 'rgba(0,0,0,0.22)',
                  }"
                >
                  A
                </span>
              </button>

              <a-dropdown
                :trigger="['click']"
                overlay-class-name="rounded-dropdown color-merge-dropdown-overlay"
                :get-popup-container="getToolbarPopupContainer"
              >
                <template #overlay>
                  <div class="color-merge-dropdown">
                    <div class="color-merge-dropdown__section">
                      <div class="color-merge-dropdown__title">字体颜色</div>
                      <div class="color-merge-dropdown__swatches">
                        <button
                          v-for="color in textColorPalette"
                          :key="color"
                          type="button"
                          class="color-merge-dropdown__item"
                          :class="{ 'is-selected': currentTextColor === color }"
                          @click="setTextColor(color)"
                        >
                          <span class="color-merge-dropdown__letter" :style="{ color }">A</span>
                        </button>
                      </div>
                    </div>
                    <div class="color-merge-dropdown__section">
                      <div class="color-merge-dropdown__title">背景颜色</div>
                      <div class="color-merge-dropdown__swatches">
                        <button
                          type="button"
                          class="color-merge-dropdown__item"
                          :class="{ 'is-selected': !currentHighlightColor }"
                          @click="clearHighlight"
                        >
                          <span class="color-merge-dropdown__none">无</span>
                        </button>
                        <button
                          v-for="color in highlightColorPalette"
                          :key="color"
                          type="button"
                          class="color-merge-dropdown__item"
                          :class="{ 'is-selected': currentHighlightColor === color }"
                          @click="setHighlightColor(color)"
                        >
                          <span class="color-merge-dropdown__swatch" :style="{ backgroundColor: color }" />
                        </button>
                      </div>
                    </div>
                    <button type="button" class="color-merge-dropdown__reset" @click="resetTextAndHighlight">
                      恢复默认
                    </button>
                  </div>
                </template>
                <button class="toolbar-btn bubble-btn color-merge-btn__arrow" type="button" aria-label="选择文字和高亮颜色">
                  <ChevronDownIcon class="dropdown-icon dropdown-icon--light" />
                </button>
              </a-dropdown>
            </div>
          </div>

          <div class="bubble-toolbar__group">
            <button
              class="toolbar-btn bubble-btn"
              :class="{ 'is-active': isBoldActive }"
              type="button"
              aria-label="加粗"
              @click="toggleBold"
            >
              <span class="text-control text-control--bold">B</span>
            </button>

            <button
              class="toolbar-btn bubble-btn"
              :class="{ 'is-active': isItalicActive }"
              type="button"
              aria-label="斜体"
              @click="toggleItalic"
            >
              <span class="text-control text-control--italic">I</span>
            </button>

            <button
              class="toolbar-btn bubble-btn"
              :class="{ 'is-active': isUnderlineActive }"
              type="button"
              aria-label="下划线"
              @click="toggleUnderline"
            >
              <span class="text-control text-control--underline">U</span>
            </button>

            <button
              class="toolbar-btn bubble-btn"
              :class="{ 'is-active': isStrikeActive }"
              type="button"
              aria-label="删除线"
              @click="toggleStrike"
            >
              <span class="text-control text-control--strike">S</span>
            </button>

            <button
              class="toolbar-btn bubble-btn"
              :class="{ 'is-active': isCodeActive }"
              type="button"
              aria-label="行内代码"
              @click="toggleCode"
            >
              <CodeIcon class="icon" />
            </button>

            <button class="toolbar-btn bubble-btn" type="button" aria-label="插入链接" @click="openLinkModal">
              <Link2Icon class="icon" />
            </button>

            <button
              class="toolbar-btn bubble-btn"
              :class="{ 'is-active': isBlockquoteActive }"
              type="button"
              aria-label="引用"
              @click="toggleBlockquote"
            >
              <QuoteIcon class="icon" />
            </button>

            <button
              class="toolbar-btn bubble-btn"
              :class="{ 'is-active': isCodeBlockActive }"
              type="button"
              aria-label="代码块"
              @click="toggleCodeBlock"
            >
              <BracesIcon class="icon" />
            </button>

            <button
              class="toolbar-btn bubble-btn"
              type="button"
              aria-label="分隔线"
              @click="setHorizontalRule"
            >
              <MinusIcon class="icon" />
            </button>
          </div>
        </div>
      </BubbleMenu>

      <div class="editor-divider"></div>

      <div 
        ref="editorWrapperRef"
        class="tiptap-editor-wrapper"
        :class="{ 'is-scrolling': isEditorScrolling }"
      >
        <editor-content
          v-if="editorInstance"
          :editor="editorInstance"
        />
      </div>
    </section>

    <a-modal
      v-model:visible="linkModalVisible"
      title="插入链接"
      ok-text="插入"
      cancel-text="取消"
      :width="480"
      :maskClosable="false"
      centered
      destroy-on-close
      wrap-class-name="rounded-modal"
      @ok="applyLink"
      @cancel="closeLinkModal"
    >
      <a-form layout="vertical">
        <a-form-item label="链接文字">
          <a-input v-model:value="linkForm.label" placeholder="显示的文字 (可选)" />
        </a-form-item>
        <a-form-item label="URL">
          <a-input v-model:value="linkForm.url" placeholder="https://example.com" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import type { MenuProps } from 'ant-design-vue'
import { message } from 'ant-design-vue'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import { BubbleMenu } from '@tiptap/vue-3/menus'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import { TextStyle } from '@tiptap/extension-text-style'
import { Color } from '@tiptap/extension-color'
import Highlight from '@tiptap/extension-highlight'
import Link from '@tiptap/extension-link'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import Placeholder from '@tiptap/extension-placeholder'
import { Markdown } from 'tiptap-markdown'
import {
  FileMarkdownOutlined,
  Html5Outlined,
  FilePdfOutlined,
  FileTextOutlined,
} from '@ant-design/icons-vue'
import {
  ArrowLeftIcon,
  ChevronDownIcon,
  DownloadIcon,
  Link2Icon,
  ListIcon,
  Maximize2Icon,
  Minimize2Icon,
  Heading1Icon,
  CodeIcon,
  QuoteIcon,
  BracesIcon,
  MinusIcon,
  UndoIcon,
  RedoIcon,
} from 'lucide-vue-next'
import type { ActiveNoteForEditor } from '@/types/notes'

const props = defineProps<{
  note: ActiveNoteForEditor | null
  isGenerating: boolean
  isFullscreen?: boolean
}>()

const emit = defineEmits<{
  (e: 'back'): void
  (e: 'toggle-fullscreen'): void
  (e: 'user-edit'): void
  (e: 'change', payload: { title: string; content: string }): void
  (e: 'save', payload: { title: string; content: string }): void
}>()

// 文本与高亮颜色配置
const textColorPalette = ['#111111', '#1d4ed8', '#0ea5e9', '#16a34a', '#eab308', '#ef4444', '#f97316', '#9333ea']
const highlightColorPalette = ['#fef3c7', '#fde68a', '#fcd34d', '#d9f99d', '#bae6fd', '#fbcfe8', '#f5d0fe', '#fecaca']
const currentTextColor = ref('#111111')
const currentHighlightColor = ref<string | null>('#fde68a')

const getToolbarPopupContainer = (triggerNode?: HTMLElement): HTMLElement => {
  return triggerNode?.parentElement ?? document.body
}

const shouldShowBubbleMenu = ({ state, editor }: { state: any; editor: any }) => {
  const { selection } = state
  if (selection.empty) return false
  if (!editor?.view?.hasFocus?.()) return false
  if (editor?.isActive?.('codeBlock')) return false
  return true
}

// 笔记状态
const noteTitle = ref('未命名笔记')
const noteTitleInput = ref('')
const noteContent = ref('')
const currentNoteId = ref<string | null>(null)
const userEdited = ref(false)
const isSaving = ref(false)
const showSavedIndicator = ref(false)
const autoSaveTimer = ref<number | null>(null)
const pendingContent = ref<string | null>(null)

// 标题编辑
const isEditingTitle = ref(false)
const titleInputRef = ref<HTMLInputElement | null>(null)

// 链接弹窗
const linkModalVisible = ref(false)
const linkForm = reactive({ label: '', url: '' })

const showFullscreenToggle = computed(() => typeof props.isFullscreen === 'boolean')
const isFullscreenComputed = computed(() => props.isFullscreen === true)

// Editor 实例（用于 editor-content 组件）
const editorInstance = computed(() => editor.value ?? undefined)

// 工具栏按钮状态
const isBoldActive = computed(() => editor.value?.isActive('bold') ?? false)
const isItalicActive = computed(() => editor.value?.isActive('italic') ?? false)
const isUnderlineActive = computed(() => editor.value?.isActive('underline') ?? false)
const isStrikeActive = computed(() => editor.value?.isActive('strike') ?? false)
const isCodeActive = computed(() => editor.value?.isActive('code') ?? false)
const isBlockquoteActive = computed(() => editor.value?.isActive('blockquote') ?? false)
const isCodeBlockActive = computed(() => editor.value?.isActive('codeBlock') ?? false)
const isHighlightActive = computed(() => editor.value?.isActive('highlight') ?? false)
const canUndo = computed(() => editor.value?.can().undo() ?? false)
const canRedo = computed(() => editor.value?.can().redo() ?? false)
const isApplyingContent = ref(false)
const isEditorScrolling = ref(false)
const editorWrapperRef = ref<HTMLElement | null>(null)
const scrollHideTimer = ref<number | null>(null)

// 编辑器操作方法
const toggleBold = () => editor.value?.chain().focus().toggleBold().run()
const toggleItalic = () => editor.value?.chain().focus().toggleItalic().run()
const toggleUnderline = () => editor.value?.chain().focus().toggleUnderline().run()
const toggleStrike = () => editor.value?.chain().focus().toggleStrike().run()
const toggleCode = () => editor.value?.chain().focus().toggleCode().run()
const toggleBlockquote = () => editor.value?.chain().focus().toggleBlockquote().run()
const toggleCodeBlock = () => editor.value?.chain().focus().toggleCodeBlock().run()
const setHorizontalRule = () => editor.value?.chain().focus().setHorizontalRule().run()
const undo = () => editor.value?.chain().focus().undo().run()
const redo = () => editor.value?.chain().focus().redo().run()

const applyContentToEditor = (content: string) => {
  pendingContent.value = content
  if (!editor.value) return
  isApplyingContent.value = true
  const target = pendingContent.value ?? ''
  editor.value.commands.setContent(target || '')
  pendingContent.value = null
  nextTick(() => {
    isApplyingContent.value = false
  })
}

const handleEditorScroll = () => {
  isEditorScrolling.value = true
  
  if (scrollHideTimer.value !== null) {
    clearTimeout(scrollHideTimer.value)
  }
  
  scrollHideTimer.value = window.setTimeout(() => {
    isEditorScrolling.value = false
  }, 1000)
}

const detachScrollListener = () => {
  if (editorWrapperRef.value) {
    editorWrapperRef.value.removeEventListener('scroll', handleEditorScroll)
  }
  if (scrollHideTimer.value !== null) {
    clearTimeout(scrollHideTimer.value)
    scrollHideTimer.value = null
  }
}

const attachScrollListener = () => {
  nextTick(() => {
    detachScrollListener()
    
    if (editorWrapperRef.value) {
      editorWrapperRef.value.addEventListener('scroll', handleEditorScroll, { passive: true })
    }
  })
}

// 创建 Tiptap 编辑器
const editor = useEditor({
  extensions: [
    StarterKit.configure({
      heading: {
        levels: [1, 2, 3, 4, 5],
      },
      codeBlock: {
        HTMLAttributes: {
          class: 'tiptap-code-block',
        },
      },
    }),
    Underline,
    TextStyle,
    Color,
    Highlight.configure({
      multicolor: true,
    }),
    Link.configure({
      openOnClick: false,
      HTMLAttributes: {
        target: '_blank',
        rel: 'noopener noreferrer',
        class: 'tiptap-link',
      },
    }),
    TaskList.configure({
      HTMLAttributes: {
        class: 'tiptap-task-list',
      },
    }),
    TaskItem.configure({
      nested: true,
      HTMLAttributes: {
        class: 'tiptap-task-item',
      },
    }),
    Placeholder.configure({
      placeholder: 'AI 生成的内容会出现在这里，也可以直接记录课堂笔记...',
    }),
    Markdown.configure({
      html: true,
      transformPastedText: true,
      transformCopiedText: true,
    }),
  ],
  editorProps: {
    attributes: {
      class: 'tiptap-content',
    },
  },
  onUpdate: ({ editor }) => {
    if (isApplyingContent.value) return
    const markdownStorage = (editor.storage as any).markdown
    noteContent.value = markdownStorage?.getMarkdown?.() || editor.getHTML()
    markUserEdit()
  },
})

const markUserEdit = () => {
  userEdited.value = true
  emit('user-edit')
  emit('change', { title: noteTitle.value, content: noteContent.value })
}

// 工具栏操作
const handleHeadingSelect: NonNullable<MenuProps['onClick']> = ({ key }) => {
  if (!editor.value) return
  
  if (key === 'paragraph') {
    editor.value.chain().focus().setParagraph().run()
  } else {
    const level = parseInt(String(key).replace('h', '')) as 1 | 2 | 3 | 4 | 5
    editor.value.chain().focus().setHeading({ level }).run()
  }
}

const handleListSelect: NonNullable<MenuProps['onClick']> = ({ key }) => {
  if (!editor.value) return
  
  switch (key) {
    case 'bulletList':
      editor.value.chain().focus().toggleBulletList().run()
      break
    case 'orderedList':
      editor.value.chain().focus().toggleOrderedList().run()
      break
    case 'taskList':
      editor.value.chain().focus().toggleTaskList().run()
      break
  }
}

const setTextColor = (color: string) => {
  currentTextColor.value = color
  editor.value?.chain().focus().setColor(color).run()
}

const setHighlightColor = (color: string) => {
  currentHighlightColor.value = color
  editor.value?.chain().focus().setHighlight({ color }).run()
}

const toggleCurrentHighlight = () => {
  if (!editor.value) return
  if (editor.value.isActive('highlight')) {
    clearHighlight()
    return
  }
  const color = currentHighlightColor.value || '#fde68a'
  editor.value.chain().focus().setHighlight({ color }).run()
}

const clearHighlight = () => {
  currentHighlightColor.value = null
  editor.value?.chain().focus().unsetHighlight().run()
}

const resetTextAndHighlight = () => {
  currentTextColor.value = '#111111'
  currentHighlightColor.value = '#fde68a'
  editor.value?.chain().focus().unsetColor().unsetHighlight().run()
}

// 链接弹窗逻辑
const openLinkModal = () => {
  if (!editor.value) return
  
  const { from, to } = editor.value.state.selection
  const text = editor.value.state.doc.textBetween(from, to)
  
  const attrs = editor.value.getAttributes('link')
  
  linkForm.label = text
  linkForm.url = attrs.href || ''
  linkModalVisible.value = true
}

const closeLinkModal = () => {
  linkModalVisible.value = false
  linkForm.label = ''
  linkForm.url = ''
}

const applyLink = () => {
  if (!linkForm.url.trim()) {
    message.warning('请输入链接地址')
    return
  }

  const url = linkForm.url.startsWith('http') ? linkForm.url : `https://${linkForm.url}`
  
  if (!editor.value) return
  
  if (linkForm.label.trim()) {
    editor.value
      .chain()
      .focus()
      .insertContent(`<a href="${url}" target="_blank" rel="noopener noreferrer">${linkForm.label}</a>`)
      .run()
  } else {
    editor.value.chain().focus().setLink({ href: url }).run()
  }
  
  closeLinkModal()
}

// 导出入口
const handleExportClick: NonNullable<MenuProps['onClick']> = ({ key }) => {
  const safeTitle = (noteTitle.value || 'note').replace(/[\\/:*?"<>|]/g, '_')
  
  switch (key) {
    case 'markdown':
      exportMarkdown(safeTitle)
      break
    case 'html':
      exportHTML(safeTitle)
      break
    case 'pdf':
      exportPDF(safeTitle)
      break
    case 'txt':
      exportTXT(safeTitle)
      break
  }
}

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

const exportMarkdown = (filename: string) => {
  if (!editor.value) return
  
  const markdownStorage = (editor.value.storage as any).markdown
  const markdown = markdownStorage?.getMarkdown?.() || editor.value.getText()
  
  const blob = new Blob([markdown], { type: 'text/markdown' })
  downloadBlob(blob, `${filename}.md`)
  message.success('已导出 Markdown 文件')
}

const exportHTML = (filename: string) => {
  const html = editor.value?.getHTML() || ''
  const fullHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${noteTitle.value}</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
      padding: 40px;
      line-height: 1.8;
      color: #1f2937;
      max-width: 800px;
      margin: 0 auto;
    }
    h1 { font-size: 28px; font-weight: 700; margin: 20px 0 12px; }
    h2 { font-size: 22px; font-weight: 600; margin: 16px 0 8px; }
    h3 { font-size: 18px; font-weight: 600; margin: 12px 0 6px; }
    p { margin: 0.85em 0; }
    a { color: #2563eb; text-decoration: underline; }
    code { background: rgba(175, 184, 193, 0.2); padding: 2px 6px; border-radius: 4px; }
    pre { background: #0d1117; color: #e6edf3; padding: 16px; border-radius: 8px; overflow-x: auto; }
    blockquote { border-left: 4px solid #d1d5db; padding-left: 16px; color: #6b7280; margin: 1em 0; }
    ul, ol { margin: 0.85em 0; padding-left: 2em; }
  </style>
</head>
<body>
  ${html}
</body>
</html>`
  const blob = new Blob([fullHtml], { type: 'text/html' })
  downloadBlob(blob, `${filename}.html`)
  message.success('已导出 HTML 文件')
}

const exportTXT = (filename: string) => {
  const text = editor.value?.getText() || ''
  const blob = new Blob([text], { type: 'text/plain' })
  downloadBlob(blob, `${filename}.txt`)
  message.success('已导出 TXT 文件')
}

const exportPDF = (filename: string) => {
  const html = editor.value?.getHTML() || ''
  const printWindow = window.open('', '_blank')
  
  if (!printWindow) {
    message.error('浏览器阻止了弹窗')
    return
  }
  
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>${filename}</title>
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
            padding: 40px;
            line-height: 1.8;
            color: #1f2937;
          }
          h1 { font-size: 28px; font-weight: 700; margin: 20px 0 12px; page-break-after: avoid; }
          h2 { font-size: 22px; font-weight: 600; margin: 16px 0 8px; page-break-after: avoid; }
          h3 { font-size: 18px; font-weight: 600; margin: 12px 0 6px; page-break-after: avoid; }
          p { margin: 0.85em 0; }
          a { color: #2563eb; text-decoration: underline; }
          code { background: rgba(175, 184, 193, 0.2); padding: 2px 6px; border-radius: 4px; }
          pre { 
            background: #f5f5f5; 
            padding: 16px; 
            border-radius: 8px; 
            overflow-x: auto;
            page-break-inside: avoid;
          }
          blockquote { 
            border-left: 4px solid #d1d5db; 
            padding-left: 16px; 
            color: #6b7280; 
            margin: 1em 0;
            page-break-inside: avoid;
          }
          ul, ol { margin: 0.85em 0; padding-left: 2em; }
          @media print {
            body { padding: 20px; }
          }
        </style>
      </head>
      <body>${html}</body>
    </html>
  `)
  
  printWindow.document.close()
  printWindow.focus()
  
  setTimeout(() => {
    printWindow.print()
    message.success('已打开打印对话框')
  }, 250)
}

// 笔记加载
const loadNote = (note: ActiveNoteForEditor) => {
  currentNoteId.value = note.id
  noteTitle.value = note.title || '未命名笔记'
  noteTitleInput.value = noteTitle.value
  noteContent.value = note.content || ''
  userEdited.value = false
  applyContentToEditor(noteContent.value)
  emit('change', { title: noteTitle.value, content: noteContent.value })
}

const resetNoteState = () => {
  noteTitle.value = '未命名笔记'
  noteTitleInput.value = noteTitle.value
  noteContent.value = ''
  currentNoteId.value = null
  userEdited.value = false
  applyContentToEditor('')
  emit('change', { title: noteTitle.value, content: noteContent.value })
}

watch(
  () => props.note,
  (newNote) => {
    if (!newNote) {
      resetNoteState()
      return
    }
    if (currentNoteId.value !== newNote.id || !userEdited.value) {
      loadNote(newNote)
    }
  },
  { immediate: true, deep: true }
)

watch(
  () => editor.value,
  (instance) => {
    if (instance && pendingContent.value !== null) {
      applyContentToEditor(pendingContent.value)
    }
    if (instance) {
      attachScrollListener()
    } else {
      detachScrollListener()
    }
  },
)

onMounted(() => {
  attachScrollListener()
})

// 自动保存
const performSave = async () => {
  if (!userEdited.value) return
  isSaving.value = true
  showSavedIndicator.value = false
  
  try {
    const saveData = { title: noteTitle.value, content: noteContent.value }
    emit('save', saveData)
    
    await new Promise(resolve => setTimeout(resolve, 300))
    
    userEdited.value = false
    isSaving.value = false
    showSavedIndicator.value = true
    
    setTimeout(() => {
      showSavedIndicator.value = false
    }, 3000)
  } catch (error) {
    isSaving.value = false
    message.error('保存失败')
    console.error('Save error:', error)
  }
}

const scheduleAutoSave = () => {
  if (autoSaveTimer.value !== null) {
    clearTimeout(autoSaveTimer.value)
  }
  autoSaveTimer.value = window.setTimeout(() => {
    performSave()
  }, 2000)
}

watch([noteTitle, noteContent], () => {
  if (userEdited.value) {
    scheduleAutoSave()
  }
})

const handleBack = async () => {
  if (userEdited.value) {
    await performSave()
  }
  emit('back')
}

// 标题编辑
const beginTitleEdit = () => {
  if (isEditingTitle.value) return
  isEditingTitle.value = true
  noteTitleInput.value = noteTitle.value
  nextTick(() => {
    titleInputRef.value?.focus()
    titleInputRef.value?.select()
  })
}

const commitTitleEdit = () => {
  if (!isEditingTitle.value) return
  isEditingTitle.value = false
  const value = noteTitleInput.value.trim() || '未命名笔记'
  if (value === noteTitle.value) return
  noteTitle.value = value
  noteTitleInput.value = value
  markUserEdit()
}

const cancelTitleEdit = () => {
  if (!isEditingTitle.value) return
  isEditingTitle.value = false
  noteTitleInput.value = noteTitle.value
}

// 插入 Markdown（供外部调用，用于 AI 回复）
const insertMarkdown = (markdown: string) => {
  if (!editor.value) return
  
  editor.value.commands.insertContent('\n\n' + markdown)
  
  nextTick(() => {
    if (editorWrapperRef.value) {
      editorWrapperRef.value.scrollTop = editorWrapperRef.value.scrollHeight
    }
  })
}

// 暴露方法
defineExpose({
  insertMarkdown,
})

onBeforeUnmount(() => {
  detachScrollListener()
  editor.value?.destroy()
  if (autoSaveTimer.value !== null) {
    clearTimeout(autoSaveTimer.value)
  }
})
</script>

<style scoped>
.note-editor-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 10px 12px 12px;
  background: #fff;
  overflow: visible;
}

.note-editor__header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 8px;
  flex-shrink: 0;
}

.header-back {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #111;
  cursor: pointer;
  transition: background 0.2s ease;
}

.header-back:hover {
  background: #f5f5f5;
}

.header-back__icon {
  width: 18px;
  height: 18px;
}

.note-title {
  flex: 1;
  min-width: 0;
  min-height: 36px;
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: text;
  border-radius: 8px;
}

.note-title__label {
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  color: #111;
  white-space: nowrap;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background 0.18s ease, box-shadow 0.18s ease, opacity 0.12s ease;
}

.note-title__label--placeholder {
  color: rgba(0, 0, 0, 0.35);
}

.note-title__label--hidden {
  opacity: 0;
}

.note-title--editing .note-title__label {
  background: rgba(37, 99, 235, 0.08);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.3);
}

.note-title__input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  padding: 4px 10px;
  border-radius: 8px;
  border: none;
  background: transparent;
  font-size: 16px;
  font-weight: 500;
  color: #111;
  outline: none;
  box-sizing: border-box;
}

.note-header__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.status-tag {
  border-radius: 999px;
  font-size: 12px;
}

.note-header__toolbar {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding-left: 4px;
}

.note-editor__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-top: 0;
  min-height: 0;
  overflow: visible;
}

.bubble-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.08);
}

.bubble-toolbar__group {
  display: flex;
  align-items: center;
  gap: 2px;
}

.block-style-btn {
  min-width: 40px;
  padding: 0 6px;
}

.block-style-item {
  padding: 4px 8px;
  font-size: 15px;
  font-weight: 400;
}

.toolbar-btn {
  height: 32px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #111;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}

.bubble-btn {
  height: 30px;
}

.toolbar-btn:disabled {
  color: rgba(0, 0, 0, 0.35);
  cursor: not-allowed;
  opacity: 0.5;
}

.toolbar-btn:hover:not(:disabled) {
  background: #f5f5f5;
}

.toolbar-btn:active:not(:disabled) {
  background: #e8e8e8;
}

.toolbar-btn.is-active {
  background: #e3f2fd;
  color: #1d4ed8;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.2);
}

.dropdown-icon {
  width: 14px;
  height: 14px;
}

.text-control {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  font-weight: 600;
}

.text-control--bold {
  font-size: 14px;
}

.text-control--italic {
  font-size: 14px;
  font-style: italic;
}

.text-control--underline {
  font-size: 14px;
  text-decoration: underline;
}

.text-control--strike {
  font-size: 14px;
  text-decoration: line-through;
}

.color-merge-btn {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.color-merge-btn__chip-btn,
.color-merge-btn__arrow {
  padding: 0 6px;
}

.color-merge-btn__chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 22px;
  font-weight: 700;
  font-size: 15px;
  border-radius: 6px;
  border: 1px solid rgba(0, 0, 0, 0.14);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.55);
  background: #fffbe6;
}

.dropdown-icon--light {
  color: #888;
}

.color-merge-dropdown {
  padding: 12px 14px;
  min-width: 230px;
  display: grid;
  gap: 12px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.12);
}

.color-merge-dropdown__section {
  display: grid;
  gap: 8px;
}

.color-merge-dropdown__title {
  font-size: 13px;
  color: #666;
}

.color-merge-dropdown__swatches {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(36px, 1fr));
  gap: 6px;
}

.color-merge-dropdown__item {
  height: 32px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
}

.color-merge-dropdown__item:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.08);
}

.color-merge-dropdown__item.is-selected {
  border-color: rgba(37, 99, 235, 0.35);
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.25);
}

.color-merge-dropdown__letter {
  font-weight: 700;
  font-size: 16px;
}

.color-merge-dropdown__swatch {
  width: 22px;
  height: 14px;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.4);
}

.color-merge-dropdown__none {
  font-size: 12px;
  color: #666;
}

.color-merge-dropdown__reset {
  margin-top: 2px;
  width: 100%;
  height: 32px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #f7f7f7;
  color: #444;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.12s ease;
}

.color-merge-dropdown__reset:hover {
  background: #f0f4ff;
  transform: translateY(-1px);
}

.editor-divider {
  height: 1px;
  background: rgba(5, 5, 5, 0.06);
  margin: 4px 0 10px;
  flex-shrink: 0;
}

.icon {
  width: 16px;
  height: 16px;
}

/* 编辑器容器 - 只负责布局，滚动条样式由父组件管理 */
.tiptap-editor-wrapper {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

:deep(.tiptap-content) {
  outline: none;
  padding: 8px 0 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  font-size: 16px;
  line-height: 2;
  color: #1f2937;
  min-height: 100%;
}

/* 占位符 */
:deep(.tiptap-content p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  color: rgba(0, 0, 0, 0.35);
  pointer-events: none;
  height: 0;
}

/* 段落和标题 */
:deep(.tiptap-content p) {
  margin: 0.65em 0;
  font-size: 17px;
  line-height: 1.8;
}

:deep(.tiptap-content h1) {
  font-size: 32px;
  font-weight: 700;
  line-height: 1.3;
  margin-top: 20px;
  margin-bottom: 12px;
  color: #111827;
}

:deep(.tiptap-content h2) {
  font-size: 28px;
  font-weight: 600;
  line-height: 1.35;
  margin-top: 16px;
  margin-bottom: 8px;
  color: #111827;
}

:deep(.tiptap-content h3) {
  font-size: 23px;
  font-weight: 600;
  line-height: 1.4;
  margin-top: 12px;
  margin-bottom: 6px;
  color: #111827;
}

:deep(.tiptap-content h4) {
  font-size: 20px;
  font-weight: 600;
  line-height: 1.4;
  margin-top: 10px;
  margin-bottom: 6px;
  color: #111827;
}

:deep(.tiptap-content h5) {
  font-size: 18px;
  font-weight: 600;
  line-height: 1.35;
  margin-top: 8px;
  margin-bottom: 4px;
  color: #111827;
}

/* 列表 */
:deep(.tiptap-content ul),
:deep(.tiptap-content ol) {
  margin: 0.65em 0;
  padding-left: 2em;
  line-height: 1.8;
}

:deep(.tiptap-content li) {
  margin: 0.35em 0;
}

/* 待办列表 */
:deep(.tiptap-task-list) {
  list-style: none;
  padding-left: 0;
  margin: 0.4em 0;
}

:deep(.tiptap-task-item) {
  display: flex;
  align-items: center;
  gap: 0.5em;
  margin: 0.25em 0;
}

:deep(.tiptap-task-item > label) {
  flex: 0 0 auto;
  margin: 0;
  display: inline-flex;
  align-items: center;
}

:deep(.tiptap-task-item > div) {
  flex: 1;
}

:deep(.tiptap-task-item input[type="checkbox"]) {
  cursor: pointer;
  width: 16px;
  height: 16px;
  margin: 0;
  position: relative;
  top: 0;
}

/* 文本样式 */
:deep(.tiptap-content strong) {
  font-weight: 600;
  color: #111827;
}

:deep(.tiptap-content em) {
  font-style: italic;
}

:deep(.tiptap-content u) {
  text-decoration: underline;
}

:deep(.tiptap-content s) {
  text-decoration: line-through;
}

/* 链接 */
:deep(.tiptap-content a),
:deep(.tiptap-link) {
  color: #2563eb;
  text-decoration: underline;
  text-decoration-color: rgba(37, 99, 235, 0.3);
  text-underline-offset: 2px;
  transition: all 0.2s ease;
  cursor: pointer;
}

:deep(.tiptap-content a:hover),
:deep(.tiptap-link:hover) {
  color: #1d4ed8;
  text-decoration-color: rgba(29, 78, 216, 0.5);
}

/* 代码 */
:deep(.tiptap-content code) {
  font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
  font-size: 0.9em;
  background: rgba(175, 184, 193, 0.2);
  padding: 0.2em 0.4em;
  border-radius: 4px;
  color: #1f2937;
}

:deep(.tiptap-content pre) {
  background: #0d1117;
  color: #e6edf3;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 1.2em 0;
}

:deep(.tiptap-content pre code) {
  background: none;
  padding: 0;
  color: inherit;
  font-size: 0.875em;
  line-height: 1.6;
}

/* 高亮 */
:deep(.tiptap-content mark) {
  background-color: #fde68a;
  padding: 0.1em 0.2em;
  border-radius: 2px;
}

/* 引用 */
:deep(.tiptap-content blockquote) {
  border-left: 4px solid #d1d5db;
  padding-left: 1em;
  margin: 1em 0;
  color: #6b7280;
  font-style: italic;
}

/* 水平线 */
:deep(.tiptap-content hr) {
  border: none;
  border-top: 2px solid #e5e7eb;
  margin: 2em 0;
}
</style>

<style>
/* 弹窗全局样式 - 不带 scoped */
.rounded-modal .ant-modal-content {
  border-radius: 28px !important;
  overflow: hidden;
}

.rounded-modal .ant-modal-header {
  border-radius: 28px 28px 0 0 !important;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.rounded-modal .ant-modal-body {
  padding: 20px 24px;
}

.rounded-modal .ant-modal-footer {
  border-radius: 0 0 28px 28px !important;
  padding: 16px 24px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.rounded-modal .ant-modal-title {
  font-size: 18px;
  font-weight: 700;
}

.rounded-modal .ant-input,
.rounded-modal .ant-input-number-input,
.rounded-modal .ant-select-selector,
.rounded-modal .ant-input-textarea-show-count textarea {
  border-radius: 12px !important;
}

.rounded-modal .ant-btn {
  border-radius: 12px !important;
  padding: 6px 16px;
  height: auto;
  font-weight: 600;
  font-size: 14px;
}

.rounded-dropdown .ant-dropdown-menu {
  border-radius: 12px !important;
  overflow: hidden;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
  padding: 6px 0;
}

.rounded-dropdown .ant-dropdown-menu-item {
  border-radius: 0;
  padding: 10px 14px;
  line-height: 1.5;
  font-size: 14px;
}

/* Export dropdown styles */
:deep(.note-export-dropdown .ant-dropdown-menu-item) {
  padding: 10px 14px;
  line-height: 1.5;
  font-size: 14px;
}

:deep(.note-export-dropdown .ant-dropdown-menu-item .ant-dropdown-menu-title-content) {
  display: flex;
  align-items: center;
}

:deep(.note-export-dropdown .ant-dropdown-menu-item .anticon) {
  font-size: 14px;
  margin-right: 12px;
}

/* Export dropdown icon colors */
:deep(.note-export-dropdown .ant-dropdown-menu-item:nth-child(1) .anticon) {
  color: #6366f1;
}

:deep(.note-export-dropdown .ant-dropdown-menu-item:nth-child(2) .anticon) {
  color: #f97316;
}

:deep(.note-export-dropdown .ant-dropdown-menu-item:nth-child(3) .anticon) {
  color: #ef4444;
}

:deep(.note-export-dropdown .ant-dropdown-menu-item:nth-child(4) .anticon) {
  color: #0ea5e9;
}

.list-style-dropdown .menu-leading-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  font-weight: 700;
  font-size: 14px;
}

.list-style-dropdown .menu-leading-icon--bullet {
  color: #10b981;
  font-size: 18px;
}

.list-style-dropdown .menu-leading-icon--ordered {
  color: #0ea5e9;
  font-size: 13px;
}

.list-style-dropdown .menu-leading-icon--task {
  color: #8b5cf6;
  font-size: 13px;
}
</style>
