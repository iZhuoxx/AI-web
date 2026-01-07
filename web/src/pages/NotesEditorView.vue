<template>
  <div class="notes-page">
    <div class="page-content">
      <div v-if="!auth.state.ready" class="notes-placeholder notes-placeholder--center">
        <a-spin />
        <span class="placeholder-text">正在加载用户信息...</span>
      </div>

      <div v-else-if="!auth.isAuthenticated.value" class="notes-placeholder notes-placeholder--center">
        <a-empty description="请先登录后查看笔记" />
      </div>

      <div v-else class="editor-view">
        <header class="editor-view__topbar">
          <button
            class="topbar-back"
            type="button"
            :disabled="leavingEditor"
            @click="handleBackToList"
          >
            <ArrowLeftIcon class="topbar-back__icon" />
          </button>
          <div
            class="topbar-title"
            :class="{
              'topbar-title--editable': !!activeNotebookId,
              'topbar-title--editing': isEditingNotebookTitle,
            }"
            @click="beginNotebookTitleEdit"
          >
            <span
              class="topbar-title__label"
              :class="{ 'topbar-title__label--hidden': isEditingNotebookTitle }"
            >
              {{ notebookTitle }}
            </span>
            <input
              v-if="isEditingNotebookTitle"
              ref="titleInputRef"
              v-model="notebookTitleInput"
              class="topbar-title__input"
              @blur="commitNotebookTitleEdit"
              @keydown.enter.prevent="commitNotebookTitleEdit"
              @keydown.esc.prevent="cancelNotebookTitleEdit"
            />
          </div>
          <a-tag v-if="saving" class="saving-tag" color="processing">保存中...</a-tag>
        </header>

        <div v-if="noteLoading && !notebookNotes.length" class="editor-view__placeholder">
          <a-spin />
          <span>正在打开笔记...</span>
        </div>

        <template v-else>
          <div v-if="isNotesFullscreen" class="editor-view__fullscreen">
            <NoteEditorPanel
              v-if="selectedNoteId"
              :note="activeNoteForEditor"
              :isGenerating="isGeneratingNotes"
              :isFullscreen="true"
              :showSyncButton="showSyncButton"
              @back="handleReturnToBrowser"
              @toggle-fullscreen="exitFullscreen"
              @user-edit="handleNoteEdited"
              @request-sync="restoreAutoSync"
              @change="handleEditorChange"
              @save="handleSaveNote"
            />
            <NotebookNotesList
              v-else
              :notes="orderedNotebookNotes"
              :selected-id="selectedNoteId"
              :notebook-title="notebookTitle"
              :loading="noteLoading"
              @select="handleNoteSelected"
              @create="handleCreateNote"
              @reorder="handleNoteReorder"
              @reorder-preview="handleNoteReorderPreview"
            />
          </div>
          <div v-else class="editor-workspace" :style="workspaceStyles">
            <section class="editor-column">
              <NotebookNotesList
                v-if="!selectedNoteId"
                :notes="orderedNotebookNotes"
                :selected-id="selectedNoteId"
                :notebook-title="notebookTitle"
                :loading="noteLoading"
                @select="handleNoteSelected"
                @create="handleCreateNote"
                @reorder="handleNoteReorder"
                @reorder-preview="handleNoteReorderPreview"
              />
              <div v-else class="editor-panel">
                <NoteEditorPanel
                  :note="activeNoteForEditor"
                  :isGenerating="isGeneratingNotes"
                  :isFullscreen="false"
                  :showSyncButton="showSyncButton"
                  @back="handleReturnToBrowser"
                  @toggle-fullscreen="enterFullscreen"
                  @user-edit="handleNoteEdited"
                  @request-sync="restoreAutoSync"
                  @change="handleEditorChange"
                  @save="handleSaveNote"
                />
              </div>
            </section>
            <div class="workspace-handle" @mousedown="startVerticalDrag">
              <span></span>
            </div>
            <section class="insight-column">
              <div v-if="showRecordingPanel" class="insight-card insight-card--recording">
                <NoteRecordingPanel
                  :canRecord="canRecord"
                  :isConnected="isConnected"
                  :connectionReady="connectionReady"
                  :isRecording="isRecording"
                  :isPaused="isPaused"
                  :duration="duration"
                  :segments="transcriptSegments"
                  :liveText="liveText"
                  :audioLevel="audioLevel"
                  :errorMessage="recordingError || undefined"
                  @start="handleStartRecording"
                  @stop="handleStopRecording"
                  @pause="handlePauseRecording"
                  @resume="handleResumeRecording"
                />
              </div>

              <div class="insight-stack">
                <div class="insight-stack__nav">
                  <div class="tabs-nav" ref="tabsNavRef">
                    <button
                      v-for="tab in tabOptions"
                      :key="tab.key"
                      class="tabs-nav__btn"
                      :class="{ 'tabs-nav__btn--active': activeTab === tab.key }"
                      type="button"
                      :ref="el => setTabButtonRef(tab.key, el as HTMLButtonElement | null)"
                      @click="handleTabChange(tab.key)"
                    >
                      <component :is="tab.icon" class="tabs-nav__icon" aria-hidden="true" />
                      <span>{{ tab.label }}</span>
                    </button>
                    <span class="tabs-nav__indicator" :style="tabsIndicatorStyle"></span>
                  </div>
                  <div class="insight-nav-actions">
                    <button
                      v-if="showNewChatButton"
                      class="new-chat-trigger"
                      type="button"
                      @click="handleStartNewChat"
                    >
                      <PlusCircleIcon class="new-chat-trigger__icon" />
                      <span>新对话</span>
                    </button>
                    <button class="recording-toggle" type="button" @click="toggleRecordingPanel">
                      <component :is="showRecordingPanel ? ChevronUpIcon : ChevronDownIcon" class="toggle-icon" />
                    </button>
                  </div>
                </div>

                <div class="insight-stack__panels">
                  <div class="tabs-panel">
                    <KeepAlive>
                      <NoteChatPanel
                        v-if="activeTab === 'chat'"
                        ref="noteChatPanelRef"
                        @has-messages-change="handleChatMessagesChange"
                        @open-citation="handleCitationOpen"
                      />
                      <NoteTranscriptionPanel
                        v-else-if="activeTab === 'realtime'"
                        :segments="transcriptSegments"
                        :live-text="liveText"
                        :isRecording="isRecording"
                      />
                      <NoteFlashcardsPanel v-else-if="activeTab === 'flashcards'" />
                      <NoteQuizPanel v-else-if="activeTab === 'quiz'" />
                      <NoteMindMapPanel v-else-if="activeTab === 'learning'" />
                      <NoteMaterialsPanel
                        v-else
                        ref="materialsPanelRef"
                        :attachments="notebookAttachments"
                        :notebook-id="activeNotebookId"
                        :loading="noteLoading"
                        @updated="handleMaterialsUpdated"
                      />
                    </KeepAlive>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import type { CSSProperties } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeftIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ClipboardListIcon,
  FolderOpenIcon,
  MessageSquareIcon,
  MicIcon,
  NetworkIcon,
  PlusCircleIcon,
  SparklesIcon,
  SquareStackIcon,
} from 'lucide-vue-next'
import type { ActiveNoteForEditor, TranscriptSegment } from '@/types/notes'
import NotebookNotesList from '@/components/note/NotebookNotesList.vue'
import NoteEditorPanel from '@/components/note/NoteEditorPanel.vue'
import NoteRecordingPanel from '@/components/note/NoteRecordingPanel.vue'
import NoteChatPanel from '@/components/note/NoteChatPanel.vue'
import type { NoteChatPanelExposed } from '@/components/note/NoteChatPanel.vue'
import NoteFlashcardsPanel from '@/components/note/NoteFlashcardsPanel.vue'
import NoteMindMapPanel from '@/components/note/NoteMindMapPanel.vue'
import NoteMaterialsPanel from '@/components/note/NoteMaterialsPanel.vue'
import NoteQuizPanel from '@/components/note/NoteQuizPanel.vue'
import NoteTranscriptionPanel from '@/components/note/NoteTranscriptionPanel.vue'
import { useNotebookStore } from '@/composables/useNotes'
import { useAuth } from '@/composables/useAuth'
import { useRealtimeTranscription } from '@/composables/useRealtimeTranscription'

const auth = useAuth()
const notebookStore = useNotebookStore()
const route = useRoute()
const router = useRouter()

type InsightTabKey = 'chat' | 'realtime' | 'flashcards' | 'quiz' | 'learning' | 'materials'
type InsightTabIcon = typeof SparklesIcon
type CitationOpenPayload = {
  fileId: string
  filename?: string
  index?: number
  startIndex?: number
  endIndex?: number
  quote?: string
  label?: number
}
type MaterialsPanelExposed = {
  focusAttachmentByCitation?: (payload: CitationOpenPayload) => Promise<boolean> | boolean
}

interface InsightTabOption {
  key: InsightTabKey
  label: string
  icon: InsightTabIcon
}

const activeNoteForEditor = ref<ActiveNoteForEditor | null>(null)
const editorDraft = reactive({ title: '', content: '' })
const selectedNoteId = ref<string | null>(null)
const isEditingNotebookTitle = ref(false)
const notebookTitleInput = ref('')
const titleInputRef = ref<HTMLInputElement | null>(null)
const tabsNavRef = ref<HTMLElement | null>(null)
const noteChatPanelRef = ref<NoteChatPanelExposed | null>(null)
const materialsPanelRef = ref<MaterialsPanelExposed | null>(null)
const tabButtonRefs = reactive<Partial<Record<InsightTabKey, HTMLButtonElement | null>>>({})
const tabIndicator = reactive({ width: 0, left: 0, visible: false })
const hasPendingChanges = ref(false)
const shouldAutoSyncNotes = ref(true)
const syncingFromStore = ref(false)
const leavingEditor = ref(false)
const isNotesFullscreen = ref(false)
const showRecordingPanel = ref(true)
const activeTab = ref<InsightTabKey>('chat')
const chatHasMessages = ref(false)
const tabOptions: InsightTabOption[] = [
  { key: 'chat', label: 'AI 助手', icon: MessageSquareIcon },
  { key: 'realtime', label: '实时字幕', icon: MicIcon },
  { key: 'flashcards', label: '闪卡', icon: SquareStackIcon },
  { key: 'quiz', label: '测验', icon: ClipboardListIcon },
  { key: 'learning', label: '思维导图', icon: NetworkIcon },
  { key: 'materials', label: '资料库', icon: FolderOpenIcon },
]
const showNewChatButton = computed(() => activeTab.value === 'chat' && chatHasMessages.value)
const leftPaneWidth = ref(45)
const dragContainer = ref<HTMLElement | null>(null)
const verticalDragging = ref(false)

const {
  canRecord,
  isConnected,
  connectionReady,
  isRecording,
  isPaused,
  duration,
  audioLevel,
  segments,
  liveText,
  transcriptText,
  errorMessage,
  startRecording,
  stopRecording,
  pauseRecording,
  resumeRecording,
  cancelRecording,
} = useRealtimeTranscription({ storageKey: 'notes-transcription' })

const transcriptSegments = computed<TranscriptSegment[]>(() => segments.value)
const recordingError = computed(() => errorMessage.value)
const isGeneratingNotes = computed(() => isRecording.value && !isPaused.value)
const localNotesOrder = ref<string[] | null>(null)
const notebookNotes = computed(() => notebookStore.notesForEditor.value)
const orderedNotebookNotes = computed(() => {
  const base = notebookNotes.value
  const order = localNotesOrder.value
  if (!order || !order.length) return base
  const map = new Map(base.map(n => [n.id, n]))
  const used = new Set<string>()
  const result = order
    .map(id => {
      const note = map.get(id)
      if (note && !used.has(id)) {
        used.add(id)
        return note
      }
      return null
    })
    .filter((n): n is typeof base[number] => Boolean(n))

  for (const note of base) {
    if (!used.has(note.id)) result.push(note)
  }
  return result
})
const noteLoading = computed(() => notebookStore.notebooksState.activeLoading)
const saving = computed(() => notebookStore.notebooksState.saving)
const notebookTitle = computed(() => notebookStore.notebooksState.activeNotebook?.title || '未命名笔记本')
const showSyncButton = computed(() => Boolean(selectedNoteId.value) && !shouldAutoSyncNotes.value)
const isEditorRoute = computed(() => route.name === 'note-editor')
const activeNotebookId = computed(() => notebookStore.notebooksState.activeNotebook?.id ?? null)
const notebookAttachments = computed(() => notebookStore.notebooksState.activeNotebook?.attachments ?? [])
const hasUnsavedChanges = computed(() => {
  if (!selectedNoteId.value) return false
  const note = notebookNotes.value.find(item => item.id === selectedNoteId.value)
  if (!note) return false
  const storedTitle = note.title || '未命名笔记'
  const storedContent = note.content || ''
  const draftTitle = editorDraft.title || '未命名笔记'
  const draftContent = editorDraft.content || ''
  return draftTitle !== storedTitle || draftContent !== storedContent
})
const workspaceStyles = computed<CSSProperties>(() => {
  const left = Math.min(72, Math.max(28, leftPaneWidth.value))
  const right = Math.max(28, 100 - left)
  return { gridTemplateColumns: `${left}fr 6px ${right}fr` }
})

const routeNotebookId = computed(() => {
  if (!isEditorRoute.value) return undefined
  const raw = route.params.id
  if (Array.isArray(raw)) return raw[0]
  if (typeof raw === 'string') return raw.trim() || undefined
  return undefined
})

const persistDraft = () => {
  if (!selectedNoteId.value) return
  notebookStore.setDraft(selectedNoteId.value, { title: editorDraft.title, content: editorDraft.content })
}

const resetEditorState = () => {
  selectedNoteId.value = null
  activeNoteForEditor.value = null
  editorDraft.title = ''
  editorDraft.content = ''
  hasPendingChanges.value = false
  shouldAutoSyncNotes.value = true
}

const loadNoteIntoEditor = (noteId: string) => {
  const note = notebookNotes.value.find(item => item.id === noteId)
  if (!note) return
  syncingFromStore.value = true
  const draft = notebookStore.getDraft(noteId)
  const title = draft?.title ?? note.title ?? '未命名笔记'
  const content = draft?.content ?? note.content ?? ''
  selectedNoteId.value = noteId
  editorDraft.title = title
  editorDraft.content = content
  activeNoteForEditor.value = { id: noteId, title, content }
  hasPendingChanges.value = !!draft
  shouldAutoSyncNotes.value = true
  nextTick(() => {
    syncingFromStore.value = false
  })
}

const ensureNoteLoaded = async (id?: string) => {
  if (!isEditorRoute.value) return
  if (!id) {
    message.warning('请选择要打开的笔记')
    notebookStore.clearActiveNotebook()
    resetEditorState()
    await router.replace({ name: 'notes-list' })
    return
  }
  if (notebookStore.notebooksState.activeNotebook?.id === id) return
  await notebookStore.openNotebook(id)
  resetEditorState()
}

watch(
  () => notebookStore.notebooksState.activeNotebook?.id,
  (currentId, previousId) => {
    if (!currentId || currentId !== previousId) {
      resetEditorState()
    }
  },
  { immediate: true },
)

watch(
  notebookNotes,
  (notes) => {
    if (!selectedNoteId.value) return
    if (!notes.some(note => note.id === selectedNoteId.value)) {
      resetEditorState()
    }
  },
  { deep: true },
)

watch(
  () => ({ ready: auth.state.ready, authed: auth.isAuthenticated.value }),
  async ({ ready, authed }) => {
    if (!ready) return
    if (!authed) {
      notebookStore.clearActiveNotebook()
      resetEditorState()
      if (isEditorRoute.value) {
        message.info('请先登录后查看笔记')
        await router.replace({ name: 'notes-list' })
      }
      return
    }
    if (isEditorRoute.value) await ensureNoteLoaded(routeNotebookId.value)
  },
  { immediate: true },
)

watch(
  routeNotebookId,
  async (id, previous) => {
    if (!auth.state.ready || !auth.isAuthenticated.value) return
    if (!isEditorRoute.value) return
    if (id && id !== previous) await ensureNoteLoaded(id)
  },
)

watch(activeTab, () => {
  nextTick(() => updateTabsIndicator())
})

watch(
  () => tabsNavRef.value,
  () => nextTick(() => updateTabsIndicator()),
)

const extractSegmentsAsNote = () => {
  if (!shouldAutoSyncNotes.value || !selectedNoteId.value) return
  syncingFromStore.value = true
  const text = transcriptText.value.trim()
  if (!text) {
    editorDraft.content = ''
    activeNoteForEditor.value = {
      id: selectedNoteId.value,
      title: editorDraft.title || '实时记录',
      content: '',
    }
    hasPendingChanges.value = true
    persistDraft()
    nextTick(() => {
      syncingFromStore.value = false
    })
    return
  }
  const html = text.replace(/\n/g, '<br>')
  editorDraft.content = html
  activeNoteForEditor.value = {
    id: selectedNoteId.value,
    title: editorDraft.title || '实时记录',
    content: html,
  }
  hasPendingChanges.value = true
  persistDraft()
  nextTick(() => {
    syncingFromStore.value = false
  })
}

watch(transcriptText, () => {
  if (!shouldAutoSyncNotes.value || !selectedNoteId.value) return
  extractSegmentsAsNote()
})

watch(isRecording, (value) => {
  if (value && selectedNoteId.value) {
    shouldAutoSyncNotes.value = true
    extractSegmentsAsNote()
  }
})

watch(recordingError, (value) => {
  if (value) message.error(value)
})

const handleEditorChange = (payload: { title: string; content: string }) => {
  if (!selectedNoteId.value) return
  if (syncingFromStore.value) return
  editorDraft.title = payload.title
  editorDraft.content = payload.content
  if (activeNoteForEditor.value) {
    activeNoteForEditor.value = {
      ...activeNoteForEditor.value,
      title: payload.title,
      content: payload.content,
    }
  } else {
    activeNoteForEditor.value = { id: selectedNoteId.value, ...payload }
  }
  if (syncingFromStore.value) return
  hasPendingChanges.value = true
  persistDraft()
}

const handleSaveNote = async (payload: { title: string; content: string }) => {
  const noteId = selectedNoteId.value
  if (!notebookStore.notebooksState.activeNotebook || !noteId) {
    message.warning('请选择要编辑的笔记')
    return
  }
  editorDraft.title = payload.title
  editorDraft.content = payload.content
  if (activeNoteForEditor.value) {
    activeNoteForEditor.value = {
      ...activeNoteForEditor.value,
      title: payload.title,
      content: payload.content,
    }
  }
  try {
    await notebookStore.saveNoteInActiveNotebook(
      { title: payload.title, content: payload.content },
      { noteId },
    )
    notebookStore.clearDraft(noteId)
    hasPendingChanges.value = false
    await nextTick()
  } catch {
    // 错误信息由 store 统一处理
  }
}

const handleNoteEdited = () => {
  if (!selectedNoteId.value) return
  shouldAutoSyncNotes.value = false
  hasPendingChanges.value = true
}

const restoreAutoSync = () => {
  if (!selectedNoteId.value) {
    message.info('请选择一个笔记以同步实时内容')
    return
  }
  shouldAutoSyncNotes.value = true
  extractSegmentsAsNote()
  message.success('已根据实时转写内容同步笔记')
  persistDraft()
}

const handleNoteSelected = (noteId: string) => {
  if (selectedNoteId.value && selectedNoteId.value !== noteId) {
    persistDraft()
  }
  loadNoteIntoEditor(noteId)
}

const handleReturnToBrowser = () => {
  persistDraft()
  resetEditorState()
}

const handleCreateNote = async () => {
  if (!activeNotebookId.value) {
    message.warning('请先选择一个笔记本')
    return
  }
  try {
    const created = await notebookStore.addNoteToActiveNotebook({ title: '新建笔记', content: '' })
    if (created?.id) {
      await nextTick()
      loadNoteIntoEditor(created.id)
    } else {
      resetEditorState()
    }
  } catch {
    // 错误信息已在 store 内提示
  }
}

const handleNotebookTitleChange = async (value: string) => {
  if (!activeNotebookId.value) return
  const nextTitle = value?.trim() || '未命名笔记本'
  if (nextTitle === notebookTitle.value) return
  try {
    await notebookStore.updateActiveNotebookTitle(nextTitle)
  } catch (err) {
    // 错误已在 store 中提示
  }
}

const beginNotebookTitleEdit = () => {
  if (!activeNotebookId.value) return
  if (isEditingNotebookTitle.value) return
  isEditingNotebookTitle.value = true
  notebookTitleInput.value = notebookTitle.value
  nextTick(() => {
    titleInputRef.value?.focus()
    titleInputRef.value?.select()
  })
}

const commitNotebookTitleEdit = async () => {
  if (!isEditingNotebookTitle.value) return
  isEditingNotebookTitle.value = false
  const value = notebookTitleInput.value.trim()
  if (!value || value === notebookTitle.value) return
  await handleNotebookTitleChange(value)
}

const cancelNotebookTitleEdit = () => {
  if (!isEditingNotebookTitle.value) return
  isEditingNotebookTitle.value = false
  notebookTitleInput.value = notebookTitle.value
}

const setTabButtonRef = (key: InsightTabKey, el: HTMLButtonElement | null) => {
  if (el) {
    tabButtonRefs[key] = el
    nextTick(() => updateTabsIndicator())
  } else if (tabButtonRefs[key]) {
    delete tabButtonRefs[key]
  }
}

const updateTabsIndicator = () => {
  const nav = tabsNavRef.value
  const btn = tabButtonRefs[activeTab.value]
  if (!nav || !btn) {
    tabIndicator.visible = false
    return
  }
  const navRect = nav.getBoundingClientRect()
  const btnRect = btn.getBoundingClientRect()
  tabIndicator.width = btnRect.width - 6
  tabIndicator.left = btnRect.left - navRect.left + 3
  tabIndicator.visible = true
}

const tabsIndicatorStyle = computed(() => ({
  width: `${tabIndicator.width}px`,
  transform: `translateX(${tabIndicator.left}px)`,
  opacity: tabIndicator.visible ? 1 : 0,
}))

const toggleRecordingPanel = () => {
  showRecordingPanel.value = !showRecordingPanel.value
}

const handleMaterialsUpdated = async () => {
  if (!activeNotebookId.value) return
  await notebookStore.reloadActiveNotebook()
  if (selectedNoteId.value) {
    await nextTick()
    loadNoteIntoEditor(selectedNoteId.value)
  }
}

const handleStartRecording = async () => {
  try {
    await startRecording()
  } catch (err: any) {
    message.error(err?.message || '无法开始录音')
  }
}

const handleStopRecording = async () => {
  await stopRecording()
}

const handlePauseRecording = async () => {
  await pauseRecording()
}

const handleResumeRecording = async () => {
  await resumeRecording()
}

const handleTabChange = (key: InsightTabKey) => {
  activeTab.value = key
}

const handleChatMessagesChange = (value: boolean) => {
  chatHasMessages.value = value
}

const handleNoteReorder = async (orderedIds: string[]) => {
  if (!orderedIds.length) return
  localNotesOrder.value = orderedIds
  try {
    await notebookStore.reorderActiveNotebookNotes(orderedIds)
    localNotesOrder.value = null
  } catch {
    // 错误由 store 提示
    localNotesOrder.value = null
  }
}

const handleNoteReorderPreview = (orderedIds: string[] | null) => {
  localNotesOrder.value = orderedIds ?? null
}

watch(activeNotebookId, () => {
  localNotesOrder.value = null
})

const handleCitationOpen = async (payload: CitationOpenPayload) => {
  if (!payload?.fileId) return
  activeTab.value = 'materials'
  await nextTick()
  const opened = materialsPanelRef.value?.focusAttachmentByCitation?.(payload)
  if (opened === false) {
    message.warning('未找到对应的资料')
  }
}

const handleStartNewChat = () => {
  noteChatPanelRef.value?.startNewConversation()
}

const enterFullscreen = () => {
  if (!selectedNoteId.value) return
  isNotesFullscreen.value = true
}

const exitFullscreen = () => {
  isNotesFullscreen.value = false
}

const startVerticalDrag = (event: MouseEvent) => {
  event.preventDefault()
  verticalDragging.value = true
  const target = event.currentTarget as HTMLElement | null
  dragContainer.value = target ? (target.closest('.editor-workspace') as HTMLElement | null) : null
}

const stopDragging = () => {
  verticalDragging.value = false
  dragContainer.value = null
}

const handleMouseMove = (event: MouseEvent) => {
  if (verticalDragging.value && dragContainer.value) {
    const rect = dragContainer.value.getBoundingClientRect()
    const relative = ((event.clientX - rect.left) / rect.width) * 100
    leftPaneWidth.value = Math.min(72, Math.max(28, relative))
  }
}

watch(notebookNotes, (list) => {
  if (localNotesOrder.value === null) return
  const ids = list.map(n => n.id)
  const next: string[] = []
  for (const id of localNotesOrder.value) {
    if (ids.includes(id) && !next.includes(id)) next.push(id)
  }
  for (const id of ids) {
    if (!next.includes(id)) next.push(id)
  }
  localNotesOrder.value = next
})

const waitForOngoingSave = async () => {
  if (!notebookStore.notebooksState.saving) return
  await new Promise<void>((resolve) => {
    const stop = watch(
      () => notebookStore.notebooksState.saving,
      (value) => {
        if (!value) {
          stop()
          resolve()
        }
      },
      { flush: 'post' },
    )
  })
}

const handleBackToList = async () => {
  if (leavingEditor.value) return
  const notebookId = activeNotebookId.value
  const noteId = selectedNoteId.value
  leavingEditor.value = true
  try {
    await waitForOngoingSave()
    if (notebookId && noteId) {
      const draft = notebookStore.getDraft(noteId)
      const needsSave = Boolean(hasPendingChanges.value || hasUnsavedChanges.value || draft)
      if (needsSave) {
        try {
          const updatedNote = await notebookStore.saveNoteInActiveNotebook(
            { title: editorDraft.title, content: editorDraft.content },
            { noteId },
          )
          const nextId = updatedNote?.id ?? noteId
          if (nextId !== noteId) {
            notebookStore.clearDraft(noteId)
          }
          notebookStore.clearDraft(nextId)
        } catch {
          message.error('返回前保存笔记失败，请稍后重试')
          leavingEditor.value = false
          return
        }
      } else {
        notebookStore.clearDraft(noteId)
      }
    }
    await router.push({ name: 'notes-list' })
    notebookStore.clearActiveNotebook()
    resetEditorState()
  } finally {
    leavingEditor.value = false
  }
}

onMounted(() => {
  window.addEventListener('mousemove', handleMouseMove)
  window.addEventListener('mouseup', stopDragging)
  window.addEventListener('resize', updateTabsIndicator)
  nextTick(() => updateTabsIndicator())
})

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', handleMouseMove)
  window.removeEventListener('mouseup', stopDragging)
  window.removeEventListener('resize', updateTabsIndicator)
  void cancelRecording()
})

</script>

<style scoped>
.notes-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f7f7f8;
}

.page-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 12px 12px 8px;
  box-sizing: border-box;
  background: #f7f7f8;
  min-height: 0;
}

.notes-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #4b5563;
  border-radius: 16px;
  padding: 24px;
}

.notes-placeholder--center {
  flex: 1;
  background: #fff;
  border: none;
  box-shadow: none;
}

.placeholder-text {
  font-size: 13px;
}

.editor-view {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  min-height: 0;
}

.editor-view__topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0 12px;
  background: transparent;
}

.topbar-back {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 12px;
  background: transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.18s ease, transform 0.18s ease;
}

.topbar-back:hover {
  background: rgba(148, 163, 184, 0.2);
  transform: translateX(-1px);
}

.topbar-back:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.topbar-back__icon {
  width: 20px;
  height: 20px;
  color: #1f2937;
}

.topbar-title {
  position: relative;
  display: inline-flex;
  align-items: center;
  border-radius: 12px;
  min-width: max-content;
  font-size: 20px;
  font-weight: 600;
  color: #0f172a;
}

.topbar-title--editable {
  cursor: text;
}

.topbar-title__label {
  padding: 4px 10px;
  border-radius: 12px;
  display: inline-block;
  white-space: nowrap;
  transition: background 0.18s ease, box-shadow 0.18s ease, opacity 0.12s ease;
}

.topbar-title__label--hidden {
  opacity: 0;
}

.topbar-title--editable:hover .topbar-title__label {
  background: rgba(148, 163, 184, 0.15);
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.6);
}

.topbar-title--editing .topbar-title__label {
  background: rgba(37, 99, 235, 0.12);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.4);
}

.topbar-title__input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  padding: 4px 10px;
  border-radius: 12px;
  border: none;
  background: transparent;
  font: inherit;
  color: inherit;
  outline: none;
  box-sizing: border-box;
}

.saving-tag {
  margin-left: auto;
}

.editor-view__placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
  justify-content: center;
  border-radius: 24px;
  background: #fff;
  border: none;
}

.editor-view__fullscreen {
  flex: 1;
  border-radius: 26px;
  background: transparent;
}

.editor-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  background: #fff;
  border-radius: 22px;
  padding: 10px 12px 12px;
  border: none;
  box-shadow: none;
  min-height: 0;
  overflow: hidden;
}

.editor-panel__header {
  display: flex;
  justify-content: flex-start;
}

.editor-panel__back {
  padding: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}

.editor-panel :deep(.note-editor-panel) {
  flex: 1;
  min-height: 0;
}

.back-icon {
  width: 16px;
  height: 16px;
}

.editor-workspace {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 6px minmax(0, 1fr);
  border-radius: 30px;
  background: #f7f7f8;
  overflow: visible;
  padding: 2px 4px 4px;
  gap: 4px;
  box-sizing: border-box;
  min-height: 0;
}

.editor-column,
.insight-column {
  padding: 0;
  background: transparent;
  min-height: 0;
  overflow: hidden;
}

.editor-column {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.editor-column > * {
  flex: 1;
  min-height: 0;
}

.insight-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.workspace-handle {
  width: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: col-resize;
  background: transparent;
}

.workspace-handle span {
  display: none;
}

.insight-card {
  background: #fff;
  border-radius: 22px;
  padding: 14px 18px;
  border: none;
  box-shadow: none;
}

.insight-card--recording {
  padding: 0;
}

.insight-stack {
  flex: 1;
  min-height: 0;
  background: #fff;
  border-radius: 22px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: none;
  box-shadow: none;
}

.insight-stack__nav {
  padding: 14px 18px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.insight-stack__nav .tabs-nav {
  flex: 1;
  min-width: 0;
}

.insight-nav-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.insight-stack__panels {
  flex: 1;
  min-height: 0;
  border-top: 1px solid rgba(148, 163, 184, 0.24);
  padding: 0 18px 6px;
  display: flex;
}

.tabs-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  position: relative;
  padding-bottom: 0;
}

.tabs-nav__btn {
  border: none;
  border-radius: 6px;
  background: transparent;
  padding: 6px 12px 8px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    color 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tabs-nav__btn:hover {
  color: #1d4ed8;
  background: rgba(191, 219, 254, 0.6);
}

.tabs-nav__btn--active {
  color: #1d4ed8;
  font-weight: 600;
  background: rgba(191, 219, 254, 0.85);
}

.tabs-nav__indicator {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2px;
  border-radius: 999px;
  background: #2563eb;
  transition: transform 0.25s ease, width 0.25s ease, opacity 0.2s ease;
  pointer-events: none;
}

.tabs-nav__icon {
  width: 14px;
  height: 14px;
}

.new-chat-trigger {
  border: 1px solid rgba(148, 163, 184, 0.32);
  background: #fff;
  padding: 0 14px;
  height: 34px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #1f2937;
  cursor: pointer;
  transition: background-color 0.18s ease, color 0.18s ease, border-color 0.18s ease, transform 0.15s ease;
}

.new-chat-trigger:hover {
  border-color: rgba(37, 99, 235, 0.45);
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  transform: translateY(-1px);
}

.new-chat-trigger:active {
  transform: translateY(0);
  background: rgba(37, 99, 235, 0.16);
}

.new-chat-trigger__icon {
  width: 16px;
  height: 16px;
}

.recording-toggle {
  border: 1px solid rgba(148, 163, 184, 0.32);
  background: #fff;
  width: 36px;
  height: 36px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.recording-toggle:hover {
  background: #f1f5f9;
  border-color: rgba(148, 163, 184, 0.5);
  transform: translateY(-1px);
}

.toggle-icon {
  width: 18px;
  height: 18px;
  color: #2563eb;
}

.tabs-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
  padding: 10px 0 0;
}

.tabs-panel > * {
  flex: 1;
  min-height: 0;
}

/* 默认滚动条样式 */
.editor-workspace :deep(*) {
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.5) transparent;
}

.editor-workspace :deep(::-webkit-scrollbar) {
  width: 6px;
  height: 6px;
  background: transparent;
}

.editor-workspace :deep(::-webkit-scrollbar-thumb) {
  background: rgba(148, 163, 184, 0.4);
  border-radius: 999px;
}

.editor-workspace :deep(::-webkit-scrollbar-thumb:hover) {
  background: rgba(148, 163, 184, 0.6);
}

/* Tiptap 编辑器专用滚动条样式 - 统一管理 */
.editor-workspace :deep(.tiptap-editor-wrapper) {
  scrollbar-width: thin;
  scrollbar-color: transparent transparent;
  transition: scrollbar-color 0.25s ease;
}

.editor-workspace :deep(.tiptap-editor-wrapper::-webkit-scrollbar) {
  width: 8px;
  height: 8px;
}

.editor-workspace :deep(.tiptap-editor-wrapper::-webkit-scrollbar-track) {
  background: transparent;
}

.editor-workspace :deep(.tiptap-editor-wrapper::-webkit-scrollbar-thumb) {
  background: transparent;
  border-radius: 4px;
  transition: background 0.25s ease;
}

/* 只在滚动时显示滚动条 */
.editor-workspace :deep(.tiptap-editor-wrapper.is-scrolling::-webkit-scrollbar-thumb) {
  background: rgba(148, 163, 184, 0.3);
}

.editor-workspace :deep(.tiptap-editor-wrapper.is-scrolling::-webkit-scrollbar-thumb:hover) {
  background: rgba(148, 163, 184, 0.5);
}

.editor-workspace :deep(.tiptap-editor-wrapper.is-scrolling) {
  scrollbar-color: rgba(148, 163, 184, 0.3) transparent;
}

@media (max-width: 1200px) {
  .editor-workspace {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto;
  }
  .workspace-handle {
    display: none;
  }
}

@media (max-width: 768px) {
  .page-content {
    padding: 10px;
  }
}
</style>
