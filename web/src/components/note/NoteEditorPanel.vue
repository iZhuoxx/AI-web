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
      </div>
    </header>

    <section class="note-editor__body">
      <div class="format-toolbar">
        <div class="format-toolbar__left">
          <!-- 段落样式：H1 图标按钮 + 下拉菜单（Body / H1 / H2 / H3） -->
          <a-dropdown
            :trigger="['click']"
            :get-popup-container="getToolbarPopupContainer"
          >
            <template #overlay>
              <a-menu :selectable="false" @click="handleBlockStyleSelect">
                <a-menu-item v-for="item in blockStyleMenuItems" :key="item.key">
                  <div :class="['block-style-item', `block-style-item--${item.key}`]">
                    {{ item.label }}
                  </div>
                </a-menu-item>
              </a-menu>
            </template>
            <button
              class="toolbar-btn block-style-btn"
              type="button"
              aria-label="段落样式"
              @mousedown.prevent
            >
              <Heading1Icon class="icon" />
              <ChevronDownIcon class="dropdown-icon" />
            </button>
          </a-dropdown>

          <!-- 列表 -->
          <a-dropdown
            :trigger="['click']"
            :get-popup-container="getToolbarPopupContainer"
          >
            <template #overlay>
              <a-menu :selectable="false" @click="handleListSelect">
                <a-menu-item v-for="item in listMenuItems" :key="item.key">
                  {{ item.label }}
                </a-menu-item>
              </a-menu>
            </template>
            <button class="toolbar-btn" type="button" aria-label="列表样式" @mousedown.prevent>
              <ListIcon class="icon" />
              <ChevronDownIcon class="dropdown-icon" />
            </button>
          </a-dropdown>

          <!-- 文本颜色 -->
          <a-dropdown
            :trigger="['click']"
            :get-popup-container="getToolbarPopupContainer"
          >
            <template #overlay>
              <div class="color-dropdown">
                <button
                  v-for="color in textColorPalette"
                  :key="color"
                  type="button"
                  class="color-dropdown__swatch"
                  :style="{ backgroundColor: color }"
                  @mousedown.prevent
                  @click="handleTextColorSelect(color)"
                />
              </div>
            </template>
            <button class="toolbar-btn color-picker-btn" type="button" aria-label="文字颜色" @mousedown.prevent>
              <span class="color-preview" :style="{ backgroundColor: currentTextColor }" />
              <ChevronDownIcon class="dropdown-icon" />
            </button>
          </a-dropdown>

          <!-- 高亮 -->
          <div class="highlight-control">
            <button
              class="toolbar-btn highlight-btn"
              type="button"
              aria-label="应用高亮"
              @mousedown.prevent
              @click="handleHighlightButtonClick"
            >
              <HighlighterIcon class="icon" />
              <span class="highlight-color-indicator" :style="{ backgroundColor: currentHighlightColor }" />
            </button>
            <a-dropdown
              :trigger="['click']"
              :get-popup-container="getToolbarPopupContainer"
            >
              <template #overlay>
                <div class="color-dropdown">
                  <button
                    v-for="color in highlightColorPalette"
                    :key="color"
                    type="button"
                    class="color-dropdown__swatch color-dropdown__swatch--highlight"
                    :style="{ backgroundColor: color }"
                    @mousedown.prevent
                    @click="handleHighlightColorSelect(color)"
                  />
                </div>
              </template>
              <button
                class="toolbar-btn highlight-dropdown-btn"
                type="button"
                aria-label="选择高亮颜色"
                @mousedown.prevent
              >
                <ChevronDownIcon class="dropdown-icon" />
              </button>
            </a-dropdown>
          </div>

          <!-- 加粗 / 斜体 / 链接 -->
          <button class="toolbar-btn" type="button" aria-label="加粗" @mousedown.prevent @click="applyTextCommand('bold')">
            <span class="text-control text-control--bold">B</span>
          </button>
          <button class="toolbar-btn" type="button" aria-label="斜体" @mousedown.prevent @click="applyTextCommand('italic')">
            <span class="text-control text-control--italic">I</span>
          </button>
          <button class="toolbar-btn" type="button" aria-label="插入链接" @mousedown.prevent @click="openLinkModal">
            <Link2Icon class="icon" />
          </button>
        </div>

        <div class="format-toolbar__right">
          <!-- 导出 -->
          <a-dropdown
            :trigger="['click']"
            :get-popup-container="getToolbarPopupContainer"
          >
            <template #overlay>
              <a-menu :selectable="false" @click="handleExportClick">
                <a-menu-item v-for="item in exportMenuItems" :key="item.key">
                  {{ item.label }}
                </a-menu-item>
              </a-menu>
            </template>
            <button class="toolbar-btn" type="button" aria-label="导出" @mousedown.prevent>
              <DownloadIcon class="icon" />
            </button>
          </a-dropdown>

          <!-- 全屏切换 -->
          <button
            v-if="showFullscreenToggle"
            class="toolbar-btn"
            type="button"
            :aria-label="isFullscreenComputed ? '退出全屏' : '全屏编辑'"
            @mousedown.prevent
            @click="emit('toggle-fullscreen')"
          >
            <component :is="isFullscreenComputed ? Minimize2Icon : Maximize2Icon" class="icon" />
          </button>
        </div>
      </div>

      <div class="editor-divider"></div>

      <div
        ref="editorRef"
        class="note-editor__surface"
        :data-placeholder="contentPlaceholder"
        contenteditable="true"
        @input="handleEditorInput"
        @mouseup="handleEditorMouseUp"
        @keyup="handleEditorKeyup"
      ></div>
    </section>

    <!-- 链接弹窗 -->
    <a-modal
      v-model:visible="linkModalVisible"
      title="插入链接"
      ok-text="插入"
      cancel-text="取消"
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
import {
  ArrowLeftIcon,
  ChevronDownIcon,
  DownloadIcon,
  HighlighterIcon,
  Link2Icon,
  ListIcon,
  Maximize2Icon,
  Minimize2Icon,
  Heading1Icon,
} from 'lucide-vue-next'
import type { ActiveNoteForEditor } from '@/types/notes'

type SimpleMenuItem = {
  key: string
  label: string
}

const listMenuItems: SimpleMenuItem[] = [
  { key: 'unordered', label: '项目符号列表' },
  { key: 'ordered', label: '编号列表' },
]

const exportMenuItems: SimpleMenuItem[] = [
  { key: 'pdf', label: '导出 PDF' },
  { key: 'txt', label: '导出 TXT' },
]

/**
 * 段落样式：Body / Head1 / Head2 / Head3
 * 所有字号、行高、行间距都在这里统一定义
 */
type BlockStyleKey = 'body' | 'h1' | 'h2' | 'h3'

interface BlockStyleDef {
  key: BlockStyleKey
  label: string
  fontSize: number
  lineHeight: number
  marginTop: number
  marginBottom: number
  fontWeight?: number | string
}

const blockStyleDefs: BlockStyleDef[] = [
  { key: 'body', label: 'Body', fontSize: 15, lineHeight: 1.7, marginTop: 4, marginBottom: 4 },
  { key: 'h1', label: 'Head 1', fontSize: 28, lineHeight: 1.3, marginTop: 20, marginBottom: 12, fontWeight: 700 },
  { key: 'h2', label: 'Head 2', fontSize: 22, lineHeight: 1.35, marginTop: 16, marginBottom: 8, fontWeight: 600 },
  { key: 'h3', label: 'Head 3', fontSize: 18, lineHeight: 1.4, marginTop: 12, marginBottom: 6, fontWeight: 600 },
]

const blockStyleMap: Record<BlockStyleKey, BlockStyleDef> = blockStyleDefs.reduce((acc, def) => {
  acc[def.key] = def
  return acc
}, {} as Record<BlockStyleKey, BlockStyleDef>)

const blockStyleMenuItems = blockStyleDefs.map(def => ({
  key: def.key,
  label: def.label,
}))

// 颜色配置
const textColorPalette = ['#111111', '#1d4ed8', '#0ea5e9', '#16a34a', '#eab308', '#ef4444', '#f97316', '#9333ea']
const highlightColorPalette = [
  '#fef3c7',
  '#fde68a',
  '#fcd34d',
  '#d9f99d',
  '#bae6fd',
  '#fbcfe8',
  '#f5d0fe',
  '#fecaca',
]
const defaultTextColor = textColorPalette[0]
const defaultHighlightColor = highlightColorPalette[1] || '#fde68a'

const getToolbarPopupContainer = (triggerNode?: HTMLElement): HTMLElement => {
  if (triggerNode?.parentElement) {
    return triggerNode.parentElement
  }
  return triggerNode ?? document.body
}

const contentPlaceholder =
  'AI 生成的内容会出现在这里，也可以直接记录课堂笔记...'

const props = defineProps<{
  note: ActiveNoteForEditor | null
  isGenerating: boolean
  isFullscreen?: boolean
  showSyncButton?: boolean
}>()

const emit = defineEmits<{
  (e: 'back'): void
  (e: 'toggle-fullscreen'): void
  (e: 'user-edit'): void
  (e: 'request-sync'): void
  (e: 'change', payload: { title: string; content: string }): void
  (e: 'save', payload: { title: string; content: string }): void
}>()

const noteTitle = ref('未命名笔记')
const noteTitleInput = ref('')
const noteContent = ref('')
const userEdited = ref(false)
const currentNoteId = ref<string | null>(null)

const isEditingTitle = ref(false)
const titleInputRef = ref<HTMLInputElement | null>(null)
const editorRef = ref<HTMLDivElement | null>(null)

const linkModalVisible = ref(false)
const linkForm = reactive({ label: '', url: '' })

const isSaving = ref(false)
const showSavedIndicator = ref(false)
const autoSaveTimer = ref<number | null>(null)

const currentTextColor = ref(defaultTextColor)
const currentHighlightColor = ref(defaultHighlightColor)

const cachedSelectionRange = ref<Range | null>(null)
const currentBlockStyle = ref<BlockStyleKey>('body')

const showFullscreenToggle = computed(() => typeof props.isFullscreen === 'boolean')
const isFullscreenComputed = computed(() => props.isFullscreen === true)

const emitChange = () => emit('change', { title: noteTitle.value, content: noteContent.value })

const updateEditorHtml = (html: string) => {
  if (editorRef.value && editorRef.value.innerHTML !== html) {
    editorRef.value.innerHTML = html
  }
}

const resetNoteState = () => {
  noteTitle.value = '未命名笔记'
  noteTitleInput.value = noteTitle.value
  noteContent.value = ''
  currentNoteId.value = null
  userEdited.value = false
  updateEditorHtml('')
  emitChange()
}

const loadNote = (note: ActiveNoteForEditor) => {
  currentNoteId.value = note.id
  noteTitle.value = note.title || '未命名笔记'
  noteTitleInput.value = noteTitle.value
  noteContent.value = note.content || ''
  userEdited.value = false
  updateEditorHtml(noteContent.value)
  emitChange()
}

watch(
  () => props.note,
  newNote => {
    if (!newNote) {
      resetNoteState()
      return
    }
    if (currentNoteId.value !== newNote.id || !userEdited.value) {
      loadNote(newNote)
    }
  },
  { immediate: true, deep: true },
)

// 自动保存
const performSave = async () => {
  if (!userEdited.value) return
  isSaving.value = true
  showSavedIndicator.value = false
  try {
    emit('save', { title: noteTitle.value, content: noteContent.value })
    await new Promise(resolve => setTimeout(resolve, 500))
    userEdited.value = false
    isSaving.value = false
    showSavedIndicator.value = true
    setTimeout(() => {
      showSavedIndicator.value = false
    }, 3000)
  } catch {
    isSaving.value = false
    message.error('保存失败')
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

const syncEditorContent = () => {
  noteContent.value = editorRef.value?.innerHTML ?? ''
}

const markUserEdit = () => {
  userEdited.value = true
  emit('user-edit')
  emitChange()
}

// 在编辑器为空或没有有效选区时，创建一行 block 并应用样式，
// 同时把光标移动到这行的末尾
const ensureEmptyEditorBlock = (key: BlockStyleKey): HTMLElement | null => {
  const editor = editorRef.value
  if (!editor) return null

  // 如果已经有 block，就直接用第一个
  let block = editor.querySelector<HTMLElement>('p,div,li')
  if (!block) {
    block = document.createElement('p')
    block.innerHTML = '' // 不放 &nbsp;，方便后续输入
    editor.appendChild(block)
  }

  applyBlockStyleToBlock(block, key)

  // 把光标放到这一行末尾
  const range = document.createRange()
  range.selectNodeContents(block)
  range.collapse(false)

  const selection = window.getSelection()
  if (selection) {
    selection.removeAllRanges()
    selection.addRange(range)
  }

  cachedSelectionRange.value = range.cloneRange()
  currentBlockStyle.value = key
  syncEditorContent()
  markUserEdit()

  return block
}


// 把一个段落元素设置成指定的样式，并清理内部 font-size，保证一行字号统一
const applyBlockStyleToBlock = (block: HTMLElement, key: BlockStyleKey) => {
  const def = blockStyleMap[key]
  if (!def) return

  block.dataset.blockStyle = key
  block.style.fontSize = `${def.fontSize}px`
  block.style.lineHeight = String(def.lineHeight)
  block.style.fontWeight = def.fontWeight ? String(def.fontWeight) : ''
  block.style.marginTop = `${def.marginTop}px`
  block.style.marginBottom = `${def.marginBottom}px`

  // 删除子元素上的 font-size，让这一行使用统一字号
  const withFontSize = block.querySelectorAll<HTMLElement>('*')
  withFontSize.forEach(el => {
    if (el.style.fontSize) {
      el.style.removeProperty('font-size')
      if (!el.getAttribute('style') || el.getAttribute('style')!.trim() === '') {
        el.removeAttribute('style')
      }
    }
  })
}

/**
 * 统一编辑器中每个块级行的样式：
 * - 根据 data-block-style 重新应用对应的段落样式
 * - 如果没有 data-block-style，当作 body
 * 这样在“删除行首导致两行合并”时，合并后的整行会统一使用上一行的样式，
 * 同时清掉第二行内容原本携带的 font-size。
 */
const normalizeEditorBlocks = () => {
  const editor = editorRef.value
  if (!editor) return

  const blocks = editor.querySelectorAll<HTMLElement>('p,div,li')
  blocks.forEach(block => {
    let key = (block.dataset.blockStyle as BlockStyleKey) || 'body'
    if (!block.dataset.blockStyle) {
      block.dataset.blockStyle = key
    }
    applyBlockStyleToBlock(block, key)
  })
}

// 选区缓存 + 当前段落样式更新
const cacheSelectionRange = () => {
  const selection = window.getSelection()
  const editor = editorRef.value
  if (!selection || selection.rangeCount === 0 || !editor) return
  const range = selection.getRangeAt(0)
  if (!editor.contains(range.startContainer)) return

  cachedSelectionRange.value = range.cloneRange()

  let node: Node | null = range.startContainer
  while (node && node !== editor) {
    if (node instanceof HTMLElement && ['P', 'DIV', 'LI'].includes(node.tagName)) {
      const key = (node.dataset.blockStyle as BlockStyleKey) || 'body'
      currentBlockStyle.value = key
      break
    }
    node = node.parentNode
  }
}

const restoreSelectionRange = () => {
  const selection = window.getSelection()
  const editor = editorRef.value
  if (!selection || !cachedSelectionRange.value || !editor) return
  if (!editor.contains(cachedSelectionRange.value.commonAncestorContainer)) return
  selection.removeAllRanges()
  selection.addRange(cachedSelectionRange.value)
}

/// 段落样式应用：
// - 光标（无选区）→ 作用于光标所在的那一整行
// - 有选区 → 作用于所有被选中覆盖到的行
const applyBlockStyle = (key: BlockStyleKey) => {
  const editor = editorRef.value
  if (!editor) return

  editor.focus()

  let selection = window.getSelection()

  // 1）没有选区或者 range 数量为 0：典型场景是编辑器刚刚被点击、还没有真实内容
  if (!selection || selection.rangeCount === 0) {
    ensureEmptyEditorBlock(key)
    return
  }

  // 先尝试恢复缓存选区（避免 execCommand / 点击按钮时丢失光标）
  restoreSelectionRange()
  selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) {
    ensureEmptyEditorBlock(key)
    return
  }

  const range = selection.getRangeAt(0)

  // 选区不在编辑器内：也当成空编辑器处理
  if (!editor.contains(range.commonAncestorContainer)) {
    ensureEmptyEditorBlock(key)
    return
  }

  const blocks: HTMLElement[] = []

  if (range.collapsed) {
    // 光标模式：找到所在段落
    let node: Node | null = range.startContainer
    while (node && node !== editor) {
      if (node instanceof HTMLElement && ['P', 'DIV', 'LI'].includes(node.tagName)) {
        blocks.push(node)
        break
      }
      node = node.parentNode
    }

    // 没有找到块（典型场景：第一行是直接挂在 editor 上的文本节点）
    if (blocks.length === 0) {
      const p = document.createElement('p')

      // 把编辑器现有子节点全部挪进这个 p 里，保证"这一行"真的有块容器
      while (editor.firstChild) {
        p.appendChild(editor.firstChild)
      }
      editor.appendChild(p)
      blocks.push(p)

      // ⭐ 重置光标到这一行末尾，避免光标跳到开头
      const newRange = document.createRange()
      newRange.selectNodeContents(p)
      newRange.collapse(false)
      const sel = window.getSelection()
      if (sel) {
        sel.removeAllRanges()
        sel.addRange(newRange)
      }
      cachedSelectionRange.value = newRange.cloneRange()
    }
  } else {
    // 选中多行：找所有与选区相交的段落
    const allBlocks = editor.querySelectorAll<HTMLElement>('p,div,li')
    allBlocks.forEach(el => {
      const blockRange = document.createRange()
      blockRange.selectNodeContents(el)
      if (
        range.compareBoundaryPoints(Range.END_TO_START, blockRange) < 0 &&
        range.compareBoundaryPoints(Range.START_TO_END, blockRange) > 0
      ) {
        blocks.push(el)
      }
    })
    if (blocks.length === 0) {
      const p = document.createElement('p')
      p.innerHTML = '&nbsp;'
      editor.appendChild(p)
      blocks.push(p)
    }
  }

  blocks.forEach(block => applyBlockStyleToBlock(block, key))

  currentBlockStyle.value = key
  syncEditorContent()
  markUserEdit()
  cacheSelectionRange()
}

// 文本颜色
const applyTextColor = (color: string) => {
  const editor = editorRef.value
  if (!editor) return
  currentTextColor.value = color
  editor.focus()
  restoreSelectionRange()

  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return

  document.execCommand('foreColor', false, color)
  syncEditorContent()
  markUserEdit()
  cacheSelectionRange()
}

const handleTextColorSelect = (color: string) => {
  applyTextColor(color)
}

// 高亮
const applyHighlight = (color: string) => {
  const editor = editorRef.value
  if (!editor) return
  editor.focus()
  restoreSelectionRange()

  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return

  if (!document.execCommand('hiliteColor', false, color)) {
    document.execCommand('backColor', false, color)
  }

  syncEditorContent()
  markUserEdit()
  cacheSelectionRange()
}

const handleHighlightButtonClick = () => {
  applyHighlight(currentHighlightColor.value)
}

const handleHighlightColorSelect = (color: string) => {
  currentHighlightColor.value = color
  applyHighlight(color)
}

// 工具栏事件
const handleBack = async () => {
  if (userEdited.value) {
    await performSave()
  }
  emit('back')
}

const handleListSelect: NonNullable<MenuProps['onClick']> = ({ key }) => {
  const editor = editorRef.value
  if (!editor) return
  editor.focus()
  restoreSelectionRange()
  const cmd = String(key) === 'ordered' ? 'insertOrderedList' : 'insertUnorderedList'
  document.execCommand(cmd, false)
  syncEditorContent()
  markUserEdit()
  cacheSelectionRange()
}

const handleBlockStyleSelect: NonNullable<MenuProps['onClick']> = ({ key }) => {
  applyBlockStyle(key as BlockStyleKey)
}

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

const handleEditorInput = () => {
  normalizeEditorBlocks()   // 保证每次输入后，整行字号统一
  syncEditorContent()
  markUserEdit()
  cacheSelectionRange()
}

const handleEditorMouseUp = () => {
  cacheSelectionRange()
}

const handleEditorKeyup = () => {
  cacheSelectionRange()
}

const applyTextCommand = (command: string) => {
  const editor = editorRef.value
  if (!editor) return
  editor.focus()
  restoreSelectionRange()
  document.execCommand(command, false)
  syncEditorContent()
  markUserEdit()
  cacheSelectionRange()
}

// 链接
const openLinkModal = () => {
  cacheSelectionRange()
  const selection = window.getSelection()
  linkForm.label = selection?.toString() ?? ''
  linkForm.url = ''
  linkModalVisible.value = true
}

const closeLinkModal = () => {
  linkModalVisible.value = false
  linkForm.label = ''
  linkForm.url = ''
}

const normalizeUrl = (url: string) => {
  const value = url.trim()
  if (!value) return ''
  if (/^https?:\/\//i.test(value)) return value
  return `https://${value}`
}

const escapeHtml = (value: string) =>
  value.replace(/[&<>"']/g, ch => {
    switch (ch) {
      case '&': return '&amp;'
      case '<': return '&lt;'
      case '>': return '&gt;'
      case '"': return '&quot;'
      case "'": return '&#39;'
      default: return ch
    }
  })

const applyLink = () => {
  const url = normalizeUrl(linkForm.url)
  if (!url) {
    message.warning('请输入有效的链接地址')
    return
  }
  const text = linkForm.label.trim() || url
  const editor = editorRef.value
  if (!editor) return
  editor.focus()
  restoreSelectionRange()
  const safeLabel = escapeHtml(text)
  document.execCommand(
    'insertHTML',
    false,
    `<a href="${url}" target="_blank" rel="noopener noreferrer" class="note-editor__link">${safeLabel}</a>`,
  )
  closeLinkModal()
  syncEditorContent()
  markUserEdit()
  cacheSelectionRange()
}

// 导出
const triggerDownload = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

type ExportFormat = 'pdf' | 'txt'

const handleExportClick: NonNullable<MenuProps['onClick']> = ({ key }) => {
  exportNote(key === 'pdf' ? 'pdf' : 'txt')
}

const exportNote = (format: ExportFormat) => {
  const safeTitle = (noteTitle.value || 'notes').replace(/[\\/:*?"<>|]/g, '_')
  if (format === 'txt') {
    const plain = editorRef.value?.innerText ?? ''
    const blob = new Blob([plain], { type: 'text/plain;charset=utf-8' })
    triggerDownload(blob, `${safeTitle}.txt`)
    message.success('已导出 TXT 文件')
    return
  }

  const printWindow = window.open('', '_blank', 'width=900,height=700')
  if (!printWindow) {
    message.error('浏览器阻止了弹窗，无法导出 PDF')
    return
  }

  const html = `
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>${safeTitle}</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        padding: 40px;
        line-height: 1.6;
        color: #111;
      }
      a { color: #1677ff; text-decoration: none; }
    </style>
  </head>
  <body>${noteContent.value}</body>
</html>`
  printWindow.document.open()
  printWindow.document.write(html)
  printWindow.document.close()
  printWindow.focus()
  printWindow.print()
  message.success('已打开打印对话框，可选择「保存为 PDF」完成导出')
}

onMounted(() => {
  updateEditorHtml(noteContent.value)
  nextTick(() => {
    normalizeEditorBlocks() // 初始化时也统一一遍行样式
    cacheSelectionRange()
  })
})

onBeforeUnmount(() => {
  if (autoSaveTimer.value !== null) {
    clearTimeout(autoSaveTimer.value)
  }
  if (editorRef.value) {
    editorRef.value.innerHTML = ''
  }
})
</script>


<style scoped>
.note-editor-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px 24px;
  background: #fff;
  overflow: visible;
}

.note-editor__header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 12px;
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
  padding: 6px 12px;
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
  padding: 6px 12px;
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
  gap: 8px;
}

.status-tag {
  border-radius: 999px;
  font-size: 12px;
}

.note-editor__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-top: 4px;
  min-height: 0;
  overflow: visible;
}

.format-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  flex-shrink: 0;
  position: relative;
  z-index: 10;
}

.format-toolbar__left,
.format-toolbar__right {
  display: flex;
  align-items: center;
  gap: 1px;
  flex-wrap: wrap;
}

/* 段落样式按钮：只显示 H1 图标 + 下拉箭头 */
.block-style-btn {
  min-width: 40px;
  padding: 0 6px;
}

/* 下拉项的演示样式（保证视觉层级一致） */
.block-style-item {
  padding: 4px 8px;
}

.block-style-item--body {
  font-size: 15px;
}

.block-style-item--h1 {
  font-size: 26px;
  font-weight: 700;
}

.block-style-item--h2 {
  font-size: 20px;
  font-weight: 600;
}

.block-style-item--h3 {
  font-size: 17px;
  font-weight: 600;
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
  transition: background 0.2s ease;
}

.toolbar-btn:disabled {
  color: rgba(0, 0, 0, 0.35);
  cursor: not-allowed;
}

.toolbar-btn:hover:not(:disabled) {
  background: #f5f5f5;
}

.toolbar-btn:active:not(:disabled) {
  background: #e8e8e8;
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

.color-picker-btn {
  min-width: 44px;
  gap: 6px;
}

.color-preview {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.25);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.4);
}

.highlight-control {
  display: inline-flex;
  align-items: stretch;
  gap: 0;
  border-radius: 6px;
  overflow: hidden;
  transition: background 0.2s ease;
}

.highlight-control:hover {
  background: #f5f5f5;
}

.highlight-control:active {
  background: #e8e8e8;
}

.highlight-btn {
  flex-direction: column;
  padding: 4px 8px 6px;
  gap: 4px;
  border-radius: 0;
  border-top-left-radius: 6px;
  border-bottom-left-radius: 6px;
}

.highlight-control:hover .highlight-btn,
.highlight-control:hover .highlight-dropdown-btn {
  background: transparent;
}

.highlight-control:not(:hover) .highlight-btn:hover,
.highlight-control:not(:hover) .highlight-dropdown-btn:hover {
  background: #f5f5f5;
}

.highlight-btn .icon {
  width: 18px;
  height: 18px;
}

.highlight-color-indicator {
  width: 20px;
  height: 6px;
  border-radius: 999px;
  border: 1px solid rgba(0, 0, 0, 0.2);
}

.highlight-dropdown-btn {
  width: 24px;
  min-width: 24px;
  padding: 0 6px;
  border-radius: 0;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-left: 1px solid rgba(0, 0, 0, 0.06);
}

.color-dropdown {
  padding: 8px;
  display: grid;
  grid-template-columns: repeat(4, 28px);
  gap: 6px;
}

.color-dropdown__swatch {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: transparent;
  cursor: pointer;
  padding: 0;
  transition: transform 0.15s ease;
}

.color-dropdown__swatch:hover {
  transform: scale(1.05);
}

.color-dropdown__swatch:active {
  transform: scale(0.98);
}

.color-dropdown__swatch--highlight {
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.05);
}

.editor-divider {
  height: 1px;
  background: rgba(5, 5, 5, 0.06);
  margin: 12px 0;
  flex-shrink: 0;
}

/* 编辑区：基础行高给个默认值，具体每个段落由 blockStyle 覆盖 */
.note-editor__surface {
  flex: 1;
  min-height: 0;
  border: none;
  outline: none;
  padding: 8px 0 20px;
  line-height: 1.7;
  color: #111;
  overflow-y: auto;
  font-size: 15px;
}

.note-editor__surface:focus {
  outline: none;
}

.note-editor__surface:empty:before {
  content: attr(data-placeholder);
  color: rgba(0, 0, 0, 0.35);
  pointer-events: none;
}

.note-editor__surface a,
.note-editor__surface .note-editor__link {
  color: #2563eb;
  text-decoration: underline;
}

.icon {
  width: 16px;
  height: 16px;
}

/* 滚动条样式 */
.note-editor__surface::-webkit-scrollbar {
  width: 8px;
}

.note-editor__surface::-webkit-scrollbar-track {
  background: transparent;
}

.note-editor__surface::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
}

.note-editor__surface::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.15);
}
</style>
