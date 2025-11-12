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
              :notes="panelNotes"
              :isGenerating="isGeneratingNotes"
              :isFullscreen="true"
              :showSyncButton="showSyncButton"
              @toggle-fullscreen="exitFullscreen"
              @user-edit="handleNoteEdited"
              @request-sync="restoreAutoSync"
              @change="handleEditorChange"
              @save="handleSaveNote"
            />
            <NotebookNotesList
              v-else
              :notes="notebookNotes"
              :selected-id="selectedNoteId"
              :notebook-title="notebookTitle"
              :loading="noteLoading"
              @select="handleNoteSelected"
              @create="handleCreateNote"
            />
          </div>
          <div v-else class="editor-workspace" :style="workspaceStyles">
            <section class="editor-column">
              <NotebookNotesList
                v-if="!selectedNoteId"
                :notes="notebookNotes"
                :selected-id="selectedNoteId"
                :notebook-title="notebookTitle"
                :loading="noteLoading"
                @select="handleNoteSelected"
                @create="handleCreateNote"
              />
              <div v-else class="editor-panel">
                <div class="editor-panel__header">
                  <a-button type="link" class="editor-panel__back" @click="handleReturnToBrowser">
                    <ChevronLeftIcon class="back-icon" />
                    返回笔记浏览
                  </a-button>
                </div>
                <NoteEditorPanel
                  :notes="panelNotes"
                  :isGenerating="isGeneratingNotes"
                  :isFullscreen="false"
                  :showSyncButton="showSyncButton"
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
                    <NoteChatPanel
                      v-if="activeTab === 'chat'"
                      ref="noteChatPanelRef"
                      @has-messages-change="handleChatMessagesChange"
                    />
                    <NoteTranscriptionPanel
                      v-else-if="activeTab === 'realtime'"
                      :segments="transcriptSegments"
                      :live-text="liveText"
                      :isRecording="isRecording"
                    />
                    <NoteFlashcardsPanel v-else-if="activeTab === 'flashcards'" />
                    <NoteQuizPanel v-else-if="activeTab === 'quiz'" />
                    <NoteMindMapPanel
                      v-else-if="activeTab === 'learning'"
                      :materials="mindMapMaterials"
                      :keywords="keywords"
                      :isLoading="isMindMapLoading"
                    />
                    <NoteMaterialsPanel
                      v-else
                      :attachments="notebookAttachments"
                      :notebook-id="activeNotebookId"
                      :loading="noteLoading"
                      @updated="handleMaterialsUpdated"
                    />
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
  ChevronLeftIcon,
  ChevronUpIcon,
  ClipboardListIcon,
  FolderOpenIcon,
  MapIcon,
  MessageSquareIcon,
  MicIcon,
  PlusCircleIcon,
  SparklesIcon,
} from 'lucide-vue-next'
import type { KeywordItem, LearningMaterial, NoteItem, TranscriptSegment } from '@/types/notes'
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
import { useNotes } from '@/composables/useNotes'
import { useAuth } from '@/composables/useAuth'
import { useRealtimeTranscription } from '@/composables/useRealtimeTranscription'

const auth = useAuth()
const notesStore = useNotes()
const route = useRoute()
const router = useRouter()

type InsightTabKey = 'chat' | 'realtime' | 'flashcards' | 'quiz' | 'learning' | 'materials'
type InsightTabIcon = typeof SparklesIcon

interface InsightTabOption {
  key: InsightTabKey
  label: string
  icon: InsightTabIcon
}

const panelNotes = ref<NoteItem[]>([])
const editorDraft = reactive({ title: '', content: '' })
const selectedNoteId = ref<string | null>(null)
const isEditingNotebookTitle = ref(false)
const notebookTitleInput = ref('')
const titleInputRef = ref<HTMLInputElement | null>(null)
const tabsNavRef = ref<HTMLElement | null>(null)
const noteChatPanelRef = ref<NoteChatPanelExposed | null>(null)
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
  { key: 'flashcards', label: '闪卡', icon: SparklesIcon },
  { key: 'quiz', label: '测验', icon: ClipboardListIcon },
  { key: 'learning', label: '思维导图', icon: MapIcon },
  { key: 'materials', label: '资料库', icon: FolderOpenIcon },
]
const showNewChatButton = computed(() => activeTab.value === 'chat' && chatHasMessages.value)
const leftPaneWidth = ref(45)
const dragContainer = ref<HTMLElement | null>(null)
const verticalDragging = ref(false)
const mindMapMaterials = ref<LearningMaterial[]>([])
const isMindMapLoading = ref(false)
let mindMapTimer: number | null = null
const mindMapMaterialTypes: LearningMaterial['type'][] = ['article', 'video', 'document']

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
const notebookNotes = computed(() => notesStore.notesForEditor.value)
const noteLoading = computed(() => notesStore.state.noteLoading)
const saving = computed(() => notesStore.state.saving)
const notebookTitle = computed(() => notesStore.state.active?.title || '未命名笔记本')
const showSyncButton = computed(() => Boolean(selectedNoteId.value) && !shouldAutoSyncNotes.value)
const isEditorRoute = computed(() => route.name === 'note-editor')
const activeNotebookId = computed(() => notesStore.state.active?.id ?? null)
const notebookAttachments = computed(() => notesStore.state.active?.attachments ?? [])
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
  notesStore.setDraft(selectedNoteId.value, { title: editorDraft.title, content: editorDraft.content })
}

const resetEditorState = () => {
  selectedNoteId.value = null
  panelNotes.value = []
  editorDraft.title = ''
  editorDraft.content = ''
  hasPendingChanges.value = false
  shouldAutoSyncNotes.value = true
}

const loadNoteIntoEditor = (noteId: string) => {
  const note = notebookNotes.value.find(item => item.id === noteId)
  if (!note) return
  syncingFromStore.value = true
  const draft = notesStore.getDraft(noteId)
  const title = draft?.title ?? note.title ?? '未命名笔记'
  const content = draft?.content ?? note.content ?? ''
  selectedNoteId.value = noteId
  editorDraft.title = title
  editorDraft.content = content
  panelNotes.value = [{ id: noteId, title, content }]
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
    notesStore.clearActiveNote()
    resetEditorState()
    await router.replace({ name: 'notes-list' })
    return
  }
  if (notesStore.state.active?.id === id) return
  try {
    await notesStore.openNote(id)
    resetEditorState()
  } catch (err) {
    message.error('无法打开笔记，请稍后再试')
    notesStore.clearActiveNote()
    resetEditorState()
    await router.replace({ name: 'notes-list' })
  }
}

watch(
  () => notesStore.state.active?.id,
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
      notesStore.clearActiveNote()
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
    panelNotes.value = [{ id: selectedNoteId.value, title: editorDraft.title || '实时记录', content: '' }]
    hasPendingChanges.value = true
    persistDraft()
    nextTick(() => {
      syncingFromStore.value = false
    })
    return
  }
  const html = text.replace(/\n/g, '<br>')
  editorDraft.content = html
  panelNotes.value = [{ id: selectedNoteId.value, title: editorDraft.title || '实时记录', content: html }]
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
  editorDraft.title = payload.title
  editorDraft.content = payload.content
  if (panelNotes.value.length) {
    panelNotes.value[0] = { ...panelNotes.value[0], title: payload.title, content: payload.content }
  }
  if (syncingFromStore.value) return
  hasPendingChanges.value = true
  persistDraft()
}

const handleSaveNote = async (payload: { title: string; content: string }) => {
  if (!notesStore.state.active || !selectedNoteId.value) {
    message.warning('请选择要编辑的笔记')
    return
  }
  editorDraft.title = payload.title
  editorDraft.content = payload.content
  try {
    const previousId = selectedNoteId.value
    const updatedNote = await notesStore.saveActiveNote(
      { title: payload.title, content: payload.content },
      { noteId: previousId },
    )
    const nextId = updatedNote?.id ?? previousId
    if (previousId && previousId !== nextId) {
      notesStore.clearDraft(previousId)
    }
    notesStore.clearDraft(nextId)
    hasPendingChanges.value = false
    await nextTick()
    loadNoteIntoEditor(nextId)
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
    const created = await notesStore.addNoteToActive({ title: '新建笔记', content: '' })
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
    await notesStore.updateActiveNotebookTitle(nextTitle)
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
  tabIndicator.width = btnRect.width
  tabIndicator.left = btnRect.left - navRect.left
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
  await ensureNoteLoaded(activeNotebookId.value)
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

const waitForOngoingSave = async () => {
  if (!notesStore.state.saving) return
  await new Promise<void>((resolve) => {
    const stop = watch(
      () => notesStore.state.saving,
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
      const draft = notesStore.getDraft(noteId)
      const needsSave = Boolean(hasPendingChanges.value || hasUnsavedChanges.value || draft)
      if (needsSave) {
        try {
          const updatedNote = await notesStore.saveActiveNote(
            { title: editorDraft.title, content: editorDraft.content },
            { noteId },
          )
          const nextId = updatedNote?.id ?? noteId
          if (nextId !== noteId) {
            notesStore.clearDraft(noteId)
          }
          notesStore.clearDraft(nextId)
        } catch {
          message.error('返回前保存笔记失败，请稍后重试')
          leavingEditor.value = false
          return
        }
      } else {
        notesStore.clearDraft(noteId)
      }
    }
    await router.push({ name: 'notes-list' })
    notesStore.clearActiveNote()
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
  if (mindMapTimer !== null) {
    window.clearTimeout(mindMapTimer)
    mindMapTimer = null
  }
  void cancelRecording()
})

const STOPWORDS = new Set([
  'the','and','you','are','for','with','that','have','this','from','your','just','will','they',
  '我们','你们','他们','这个','那个','的','是','以及','还有','而且','但是','或者','因此','那么','一个','或者','以及','的','了','呢','吧','啊','吗','是','在','和','到','就','还','也','很','让','能',
])

const isChineseToken = (w: string) => /[\u4e00-\u9fa5]/.test(w)

const segmentText = (text: string) => {
  const list: string[] = []
  const trySeg = (locale: string) => {
    try {
      const S: any = (Intl as any).Segmenter
      if (!S) return
      const seg = new S(locale, { granularity: 'word' })
      for (const it of seg.segment(text)) if (it.isWordLike) list.push(it.segment)
    } catch (err) {
      // ignore segmentation error
    }
  }
  trySeg('zh-Hans')
  trySeg('en')
  if (!list.length) list.push(...text.split(/[\s,.;:，。！？、]+/g))
  return list
}

const extractKeywords = (text: string, limit = 12) => {
  const t = text.trim()
  if (!t) return [] as KeywordItem[]
  const map = new Map<string, { text: string; score: number }>()
  const add = (w: string) => {
    const raw = w.trim()
    if (!raw) return
    const low = raw.toLowerCase()
    if (STOPWORDS.has(low) || STOPWORDS.has(raw)) return
    if (/^\d+(\.\d+)?$/.test(raw)) return
    if (low.length < 2 && !isChineseToken(raw)) return
    const existing = map.get(low)
    if (existing) existing.score += 1
    else map.set(low, { text: raw, score: 1 })
  }
  for (const tk of segmentText(t)) add(tk)
  return Array.from(map.values())
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((entry, index) => ({ id: `${entry.text}-${index}`, text: entry.text, relevance: entry.score }))
}

const keywords = computed<KeywordItem[]>(() => extractKeywords(transcriptText.value))

const scheduleMindMapUpdate = () => {
  if (mindMapTimer !== null) {
    window.clearTimeout(mindMapTimer)
    mindMapTimer = null
  }
  if (keywords.value.length < 3) {
    mindMapMaterials.value = []
    isMindMapLoading.value = false
    return
  }
  isMindMapLoading.value = true
  const snapshot = keywords.value.slice(0, 6)
  mindMapTimer = window.setTimeout(() => {
    mindMapMaterials.value = snapshot.map((k, i) => {
      const type = mindMapMaterialTypes[i % mindMapMaterialTypes.length]
      return {
        id: `material-${k.id}-${i}`,
        title: `${k.text} ${type === 'video' ? '讲解' : type === 'document' ? '文档' : '进阶指南'}`,
        description: `结合「${k.text}」主题的精选${type === 'video' ? '视频' : type === 'document' ? '文档资料' : '文章与教程'}，帮助你构建清晰的思维导图。`,
        type,
        url: `https://www.google.com/search?q=${encodeURIComponent(k.text)}`,
        relevance: k.relevance,
        keywords: snapshot.map(item => item.text),
      }
    })
    isMindMapLoading.value = false
  }, 800)
}

watch(keywords, scheduleMindMapUpdate, { deep: true, immediate: true })
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
  padding: 14px 18px 18px;
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
  gap: 12px;
  position: relative;
  padding-bottom: 8px;
}

.tabs-nav__btn {
  border: none;
  background: transparent;
  padding: 4px 0;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  transition: color 0.2s ease;
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tabs-nav__btn:hover {
  color: #111827;
}

.tabs-nav__btn--active {
  color: #1d4ed8;
  font-weight: 600;
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
