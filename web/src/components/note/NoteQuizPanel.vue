<template>
  <a-card class="quiz-panel" :bordered="false" :body-style="{ height: '100%', padding: 0 }">
    <div class="panel-shell">
      <div v-if="!activeNotebookId" class="empty-panel">
        <ClipboardListIcon class="empty-icon" />
        <div class="empty-title">请选择一个笔记以生成测验</div>
        <p class="empty-desc">打开任意笔记本后即可查看或生成测验题。</p>
      </div>

      <template v-else>
        <!-- Quiz Taking View (inside folder) -->
        <div v-if="selectedFolderId" class="quiz-view">
          <div class="quiz-scroll">
            <div class="quiz-topbar">
              <button class="back-btn" type="button" @click="goBackToList">
                <ArrowLeftIcon class="back-icon" />
              </button>
              <div class="quiz-head">
                <div class="quiz-name">{{ selectedFolder?.name || '测验' }}</div>
                <div v-if="selectedFolder?.description" class="quiz-desc">{{ selectedFolder.description }}</div>
              </div>
            </div>

            <div v-if="currentQuestion" class="quiz-content">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: `${progressPercent}%` }"></div>
              </div>
              <div class="progress-text">{{ currentIndex + 1 }} / {{ quizQueue.length }}</div>

              <div class="question-card">
                <div class="question-header">
                  <span class="question-number">Q{{ currentIndex + 1 }}</span>
                  <button
                    class="icon-btn ghost"
                    type="button"
                    @click="toggleFavorite(currentQuestion)"
                    :class="{ 'is-favorite': currentQuestion.isFavorite }"
                  >
                    <StarIcon class="icon" :class="{ filled: currentQuestion.isFavorite }" />
                  </button>
                </div>
                <div class="question-text">{{ currentQuestion.question }}</div>

                <div class="options-list">
                  <button
                    v-for="(option, idx) in currentQuestion.options"
                    :key="idx"
                    class="option-btn"
                    :class="getOptionClass(idx)"
                    :disabled="answered"
                    @click="selectAnswer(idx)"
                  >
                    <span class="option-letter">{{ optionLetters[idx] }}</span>
                    <span class="option-text">{{ option }}</span>
                    <CheckIcon v-if="answered && idx === currentQuestion.correctIndex" class="option-icon correct" />
                    <XIcon v-if="answered && selectedAnswer === idx && idx !== currentQuestion.correctIndex" class="option-icon wrong" />
                  </button>
                </div>

                <div v-if="answered" class="result-feedback">
                  <div v-if="isCorrect" class="feedback correct">
                    <CheckCircleIcon class="feedback-icon" />
                    <span>回答正确!</span>
                  </div>
                  <div v-else class="feedback wrong">
                    <XCircleIcon class="feedback-icon" />
                    <span>回答错误，正确答案是 {{ optionLetters[currentQuestion.correctIndex] }}</span>
                  </div>
                  <div v-if="currentQuestion.explaination" class="explanation-box">
                    <LightbulbIcon class="explanation-icon" />
                    <span>{{ currentQuestion.explaination }}</span>
                  </div>
                </div>
              </div>

              <div class="quiz-footer">
                <button
                  v-if="currentQuestion.hint && !answered"
                  class="hint-toggle-btn hint-toggle-btn--inline"
                  type="button"
                  @click="showHint = !showHint"
                >
                  <component :is="showHint ? ChevronUpIcon : ChevronDownIcon" class="hint-toggle-icon" />
                  提示
                </button>
                <div class="nav-group">
                  <button class="pill-btn" type="button" :disabled="currentIndex === 0" @click="prevQuestion">
                    上一题
                  </button>
                  <button
                    class="pill-btn pill-btn--primary"
                    type="button"
                    @click="nextQuestion"
                  >
                    {{ currentIndex >= quizQueue.length - 1 ? '完成' : '下一题' }}
                  </button>
                </div>
              </div>
              <div v-if="showHint && currentQuestion.hint && !answered" class="hint-content">
                {{ currentQuestion.hint }}
              </div>
            </div>
            <div v-else class="empty-inner">
              <p>此测验暂无题目</p>
            </div>
          </div>
        </div>

        <!-- Folder List View -->
        <div v-else class="list-view">
          <div class="folders-grid">
            <div
              v-for="folder in folders"
              :key="folder.id"
              class="folder-card"
              @click="enterFolder(folder.id)"
            >
              <div class="folder-card__head">
                <div class="folder-info">
                  <div class="folder-title">
                    <FolderIcon class="folder-icon" />
                    <span class="folder-title-text">{{ folder.name }}</span>
                  </div>
                  <div class="folder-meta">
                    <span class="meta-tag">{{ folder.questionIds.length }} 道题</span>
                  </div>
                </div>
              </div>
              <a-dropdown trigger="click" placement="bottomRight" overlay-class-name="rounded-dropdown quiz-actions-dropdown">
                <button class="folder-menu-btn" type="button" @click.stop>
                  <MoreVerticalIcon class="menu-icon" />
                </button>
                <template #overlay>
                  <a-menu @click="(e: any) => e.domEvent?.stopPropagation?.()">
                    <a-menu-item @click.stop="openEditFolderModal(folder)">
                      <template #icon>
                        <Edit3Icon class="dropdown-icon" />
                      </template>
                      重命名
                    </a-menu-item>
                    <a-menu-item @click.stop="promptDeleteFolder(folder)" class="delete-menu-item">
                      <template #icon>
                        <DeleteOutlined />
                      </template>
                      删除
                    </a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
            </div>
          </div>

          <a-button
            type="primary"
            class="generate-fab-center"
            size="large"
            :loading="generating"
            @click="openGenerateModal"
          >
            <SparklesIcon class="fab-icon" />
            生成测验
          </a-button>

          <div v-if="!folders.length && !loading" class="empty-inner">
            <p>还没有测验</p>
            <p class="muted">点击"生成测验"试试看。</p>
          </div>
        </div>
      </template>

      <div v-if="loading" class="panel-overlay">
        <a-spin />
      </div>
    </div>
  </a-card>

  <!-- Generate Modal -->
  <a-modal
    v-model:visible="generateModal.open"
    :confirm-loading="generateModal.loading"
    title="生成测验"
    okText="确认"
    cancelText="取消"
    :maskClosable="false"
    :width="560"
    centered
    destroy-on-close
    wrap-class-name="rounded-modal"
    @ok="handleGenerate"
    @cancel="closeGenerateModal"
  >
    <div class="generate-form">

      <label class="form-label">题目数量</label>
      <a-input
        v-model:value="generateModal.count"
        type="number"
        min="1"
        max="30"
        placeholder="默认 10 道题"
      />

      <label class="form-label">选择资料</label>
      <a-select
        v-model:value="generateModal.attachments"
        mode="multiple"
        style="width: 100%"
        placeholder="请选择用于生成的资料"
      >
        <a-select-option v-for="item in selectableAttachments" :key="item.id" :value="item.id">
          {{ item.filename || '未命名资料' }}
        </a-select-option>
      </a-select>

      <label class="form-label">你的重点和偏好?</label>
      <a-textarea
        v-model:value="generateModal.focus"
        :auto-size="{ minRows: 2, maxRows: 4 }"
        placeholder="让AI根据你的重点和偏好来定制化测验题"
      />
    </div>
  </a-modal>

  <RenameModal
    v-model="editFolderModal.open"
    v-model:value="editFolderModal.name"
    title="重命名测验"
    label="名称"
    placeholder="输入测验名称"
    :loading="editFolderModal.loading"
    @confirm="handleEditFolderSave"
    @cancel="closeEditFolderModal"
  />

  <!-- Delete Folder Confirmation -->
  <ConfirmModal
    v-model="deleteFolderModal.open"
    variant="danger"
    confirm-text="删除"
    cancel-text="取消"
    :on-confirm="handleDeleteFolder"
  >
    <template v-if="deleteFolderModal.target">
      要删除测验
      <span class="item-name-box">
        {{ deleteFolderModal.target.name }}
      </span>
      吗? 题目不会被删除。
    </template>
  </ConfirmModal>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { DeleteOutlined } from '@ant-design/icons-vue'
import {
  ArrowLeftIcon,
  CheckIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ClipboardListIcon,
  Edit3Icon,
  FolderIcon,
  LightbulbIcon,
  MoreVerticalIcon,
  SparklesIcon,
  StarIcon,
  XIcon,
  XCircleIcon,
} from 'lucide-vue-next'
import ConfirmModal from '@/components/common/ConfirmModal.vue'
import RenameModal from '@/components/common/RenameModal.vue'
import type { QuizQuestion, QuizFolder } from '@/types/quizzes'
import type { NoteAttachment } from '@/types/notes'
import {
  listQuizFolders,
  listQuizQuestions,
  generateQuizForNotebook,
  updateQuizQuestion,
  updateQuizFolder,
  deleteQuizFolder,
} from '@/services/api'
import { useNotebookStore } from '@/composables/useNotes'
import { getModelFor } from '@/composables/setting'

const notebookStore = useNotebookStore()

const loading = ref(false)
const generating = ref(false)
const folders = ref<QuizFolder[]>([])
const quizQuestions = ref<QuizQuestion[]>([])
const selectedFolderId = ref<string | null>(null)
const shuffleEnabled = ref(false)
const quizQueue = ref<QuizQuestion[]>([])
const currentIndex = ref(0)
const selectedAnswer = ref<number | null>(null)
const answered = ref(false)
const correctCount = ref(0)
const answeredCount = ref(0)
const showHint = ref(false)

const optionLetters = ['A', 'B', 'C', 'D']

const generateModal = reactive({
  open: false,
  loading: false,
  attachments: [] as string[],
  count: '',
  focus: '',
  folderName: '',
})

const editFolderModal = reactive({
  open: false,
  loading: false,
  name: '',
  target: null as QuizFolder | null,
})

const deleteFolderModal = reactive({
  open: false,
  target: null as QuizFolder | null,
})

const activeNotebookId = computed(() => notebookStore.activeNotebook.value?.id ?? null)
const attachments = computed<NoteAttachment[]>(() => notebookStore.activeNotebook.value?.attachments ?? [])
const selectableAttachments = computed(() =>
  attachments.value.filter(item => !!item.openaiFileId),
)

const selectedFolder = computed(() => folders.value.find(f => f.id === selectedFolderId.value) ?? null)

const questionsByFolderMap = computed(() => {
  const map = new Map<string, QuizQuestion[]>()
  for (const folder of folders.value) {
    const ids = new Set(folder.questionIds)
    const qs = quizQuestions.value.filter(q => ids.has(q.id))
    map.set(folder.id, qs)
  }
  return map
})

const activeFolderQuestions = computed(() => {
  if (!selectedFolder.value) return []
  return questionsByFolderMap.value.get(selectedFolder.value.id) ?? []
})

const currentQuestion = computed(() => quizQueue.value[currentIndex.value] ?? null)
const progressPercent = computed(() =>
  quizQueue.value.length ? ((currentIndex.value + 1) / quizQueue.value.length) * 100 : 0
)
const isCorrect = computed(() =>
  selectedAnswer.value !== null && currentQuestion.value && selectedAnswer.value === currentQuestion.value.correctIndex
)

const getErrorMessage = (err: unknown) => (err instanceof Error ? err.message : '请求失败')

const shuffleArray = <T,>(input: T[]): T[] => {
  const arr = [...input]
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr
}

const buildQuizQueue = () => {
  const base = [...activeFolderQuestions.value]
  quizQueue.value = shuffleEnabled.value ? shuffleArray(base) : base
  currentIndex.value = 0
  selectedAnswer.value = null
  answered.value = false
  correctCount.value = 0
  answeredCount.value = 0
}

const loadData = async () => {
  if (!activeNotebookId.value) return
  loading.value = true
  try {
    const [foldersData, questionsData] = await Promise.all([
      listQuizFolders({ notebookId: activeNotebookId.value }),
      listQuizQuestions({ notebookId: activeNotebookId.value }),
    ])
    folders.value = foldersData
    quizQuestions.value = questionsData
    if (import.meta.env.DEV && questionsData.length) {
      console.debug('[NoteQuizPanel] quiz question sample:', questionsData[0])
    }
  } catch (err) {
    console.error('Failed to load quiz data:', err)
    message.error(getErrorMessage(err))
    folders.value = []
    quizQuestions.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => activeNotebookId.value,
  id => {
    selectedFolderId.value = null
    if (id) {
      loadData()
    } else {
      folders.value = []
      quizQuestions.value = []
    }
  },
  { immediate: true },
)

const enterFolder = (folderId: string) => {
  selectedFolderId.value = folderId
  buildQuizQueue()
}

const goBackToList = () => {
  selectedFolderId.value = null
  currentIndex.value = 0
  selectedAnswer.value = null
  answered.value = false
  showHint.value = false
}

const selectAnswer = (idx: number) => {
  if (!answered.value) {
    selectedAnswer.value = idx
    confirmAnswer()
  }
}

const confirmAnswer = () => {
  if (selectedAnswer.value === null) return
  answered.value = true
  answeredCount.value += 1
  if (isCorrect.value) {
    correctCount.value += 1
  }
}

const nextQuestion = () => {
  if (currentIndex.value >= quizQueue.value.length - 1) {
    goBackToList()
    return
  }
  currentIndex.value += 1
  selectedAnswer.value = null
  answered.value = false
  showHint.value = false
}

const prevQuestion = () => {
  if (currentIndex.value > 0) {
    currentIndex.value -= 1
    selectedAnswer.value = null
    answered.value = false
    showHint.value = false
  }
}

const toggleShuffle = () => {
  shuffleEnabled.value = !shuffleEnabled.value
  buildQuizQueue()
}

const getOptionClass = (idx: number) => {
  if (!answered.value) {
    return selectedAnswer.value === idx ? 'selected' : ''
  }
  if (idx === currentQuestion.value?.correctIndex) {
    return 'correct'
  }
  if (selectedAnswer.value === idx && idx !== currentQuestion.value?.correctIndex) {
    return 'wrong'
  }
  return ''
}

const toggleFavorite = async (question: QuizQuestion) => {
  try {
    const updated = await updateQuizQuestion(question.id, {
      isFavorite: !question.isFavorite,
    })
    quizQuestions.value = quizQuestions.value.map(q =>
      q.id === updated.id ? updated : q
    )
    quizQueue.value = quizQueue.value.map(q =>
      q.id === updated.id ? updated : q
    )
  } catch (err) {
    console.error('Failed to toggle favorite:', err)
    message.error(getErrorMessage(err))
  }
}

const openGenerateModal = () => {
  if (!activeNotebookId.value) {
    message.warning('请先选择一个笔记本')
    return
  }
  if (!selectableAttachments.value.length) {
    message.warning('请先上传并同步资料到 OpenAI 后再生成测验')
    return
  }
  generateModal.attachments = selectableAttachments.value.map(item => item.id)
  generateModal.count = ''
  generateModal.focus = ''

  generateModal.open = true
}

const closeGenerateModal = () => {
  generateModal.open = false
  generateModal.loading = false
}

const handleGenerate = async () => {
  if (!activeNotebookId.value) {
    message.warning('请先选择一个笔记本')
    return
  }
  if (!generateModal.attachments.length) {
    message.warning('请至少选择一个资料')
    return
  }
  const countVal = Number(generateModal.count)
  const count = Number.isFinite(countVal) && countVal > 0 ? Math.floor(countVal) : undefined

  generateModal.loading = true
  generating.value = true
  try {
    const model = getModelFor('quiz')
    const result = await generateQuizForNotebook(activeNotebookId.value, {
      attachmentIds: generateModal.attachments,
      count,
      focus: generateModal.focus.trim() || undefined,
      model
    })
    generateModal.open = false
    folders.value = [result.folder, ...folders.value]
    quizQuestions.value = [...result.questions, ...quizQuestions.value]
  } catch (err) {
    console.error('Failed to generate quiz:', err)
    message.error(getErrorMessage(err))
  } finally {
    generateModal.loading = false
    generating.value = false
  }
}

const openEditFolderModal = (folder: QuizFolder) => {
  editFolderModal.target = folder
  editFolderModal.name = folder.name
  editFolderModal.open = true
}

const closeEditFolderModal = () => {
  editFolderModal.open = false
  editFolderModal.target = null
  editFolderModal.name = ''
}

const handleEditFolderSave = async () => {
  if (!editFolderModal.target) return
  if (!editFolderModal.name.trim()) {
    message.warning('请输入测验名称')
    return
  }

  editFolderModal.loading = true
  try {
    const updated = await updateQuizFolder(editFolderModal.target.id, {
      name: editFolderModal.name.trim(),
    })
    folders.value = folders.value.map(f =>
      f.id === updated.id ? updated : f
    )
    closeEditFolderModal()
  } catch (err) {
    console.error('Failed to rename quiz folder:', err)
    message.error(getErrorMessage(err))
  } finally {
    editFolderModal.loading = false
  }
}

const promptDeleteFolder = (folder: QuizFolder) => {
  deleteFolderModal.target = folder
  deleteFolderModal.open = true
}

const handleDeleteFolder = async () => {
  if (!deleteFolderModal.target) return

  try {
    await deleteQuizFolder(deleteFolderModal.target.id)
    folders.value = folders.value.filter(f => f.id !== deleteFolderModal.target!.id)
    if (selectedFolderId.value === deleteFolderModal.target.id) {
      selectedFolderId.value = null
    }
  } catch (err) {
    console.error('Failed to delete quiz folder:', err)
    message.error(getErrorMessage(err))
    throw err
  }
}
</script>

<style scoped>
.quiz-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-shell {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 16px;
}

.empty-panel {
  flex: 1;
  min-height: 0;
  border: 1px dashed rgba(0, 0, 0, 0.08);
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(250, 140, 22, 0.04), rgba(251, 191, 36, 0.03));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-align: center;
}

.empty-icon {
  width: 36px;
  height: 36px;
  color: #fa8c16;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.empty-desc {
  margin: 0;
  color: #64748b;
}

.list-view,
.quiz-view {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: auto;
}

.folders-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 2px 0 80px;
}

.folder-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.folder-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: linear-gradient(180deg, #fa8c16, #f59e0b);
  opacity: 0;
  transition: opacity 0.2s ease;
  pointer-events: none;
}

.folder-card:hover {
  transform: translateY(-2px);
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04);
  border-color: rgba(250, 140, 22, 0.15);
}

.folder-card:hover::before {
  opacity: 1;
}

.folder-card__head {
  display: flex;
  align-items: center;
  gap: 16px;
  position: relative;
}

.folder-info {
  flex: 1;
  min-width: 0;
}

.folder-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
}

.folder-title-text {
  font-size: 15px;
  letter-spacing: -0.01em;
  line-height: 1.5;
}

.folder-icon {
  width: 18px;
  height: 18px;
  color: #fa8c16;
  flex-shrink: 0;
}

.folder-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.meta-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 12px;
  color: #6b7280;
  font-size: 12px;
  font-weight: 500;
}

.folder-menu-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #64748b;
  opacity: 0;
  z-index: 2;
}

.folder-card:hover .folder-menu-btn {
  opacity: 1;
}

.folder-menu-btn:hover {
  background: rgba(0, 0, 0, 0.08);
  color: #334155;
}

.folder-menu-btn .menu-icon {
  width: 16px;
  height: 16px;
}

.generate-fab-center {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 26px;
  height: 48px;
  background: #1d77ec;
  border: none;
  font-size: 15px;
  font-weight: 700;
  transition: transform 0.22s ease, filter 0.22s ease;
}

.generate-fab-center:hover {
  transform: translateX(-50%) translateY(-2px) scale(1.02);
  filter: brightness(1.04);
}

.generate-fab-center:active {
  transform: translateX(-50%) translateY(0);
  filter: brightness(0.98);
}

.fab-icon {
  width: 18px;
  height: 18px;
}

.empty-inner {
  margin-top: 40px;
  text-align: center;
  color: #64748b;
}

.muted {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 13px;
}

/* Quiz View Styles */
.quiz-scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0;
}

.quiz-topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 0 16px;
}

.back-btn {
  border: none;
  background: transparent;
  padding: 8px;
  border-radius: 12px;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #334155;
}

.back-icon {
  width: 20px;
  height: 20px;
}

.quiz-head {
  min-width: 0;
  flex: 1;
}

.quiz-name {
  font-size: 19px;
  font-weight: 700;
  color: #0f172a;
}

.quiz-desc {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
}

.quiz-topbar .folder-menu-btn {
  position: static;
  opacity: 1;
}

.quiz-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 20px;
}

.progress-bar {
  height: 6px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #fa8c16, #f59e0b);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-text {
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
}

.question-card {
  background: #fff;
  border-radius: 20px;
  padding: 24px;
  border: 1px solid #fff;
  box-shadow: none;
}

.question-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.question-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 14px;
  background: linear-gradient(135deg, #fa8c16, #f59e0b);
  color: #fff;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 700;
}

.icon-btn {
  border: 1.5px solid rgba(0, 0, 0, 0.06);
  background: #fff;
  border-radius: 12px;
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.icon-btn:hover {
  border-color: #fa8c16;
  color: #fa8c16;
  background: rgba(250, 140, 22, 0.04);
}

.icon-btn.ghost {
  border-color: transparent;
  background: rgba(0, 0, 0, 0.03);
}

.icon-btn.is-favorite {
  color: #fa8c16;
  background: rgba(250, 140, 22, 0.1);
}

.icon {
  width: 16px;
  height: 16px;
}

.icon.filled {
  fill: currentColor;
}

.question-text {
  font-size: 17px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.6;
  margin-bottom: 24px;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-btn {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  background: #fafafa;
  border: 2px solid rgba(0, 0, 0, 0.06);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.option-btn:hover:not(:disabled) {
  background: #fff;
  border-color: #fa8c16;
}

.option-btn.selected {
  background: rgba(250, 140, 22, 0.08);
  border-color: #fa8c16;
}

.option-btn.correct {
  background: rgba(22, 163, 74, 0.08);
  border-color: #16a34a;
}

.option-btn.wrong {
  background: rgba(239, 68, 68, 0.08);
  border-color: #ef4444;
}

.option-btn:disabled {
  cursor: default;
}

.option-letter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  color: #64748b;
  flex-shrink: 0;
}

.option-btn.selected .option-letter {
  background: #fa8c16;
  color: #fff;
}

.option-btn.correct .option-letter {
  background: #16a34a;
  color: #fff;
}

.option-btn.wrong .option-letter {
  background: #ef4444;
  color: #fff;
}

.option-text {
  flex: 1;
  font-size: 15px;
  color: #334155;
  line-height: 1.5;
}

.option-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.option-icon.correct {
  color: #16a34a;
}

.option-icon.wrong {
  color: #ef4444;
}

.result-feedback {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feedback {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
}

.feedback.correct {
  background: rgba(22, 163, 74, 0.1);
  color: #16a34a;
}

.feedback.wrong {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.feedback-icon {
  width: 20px;
  height: 20px;
}

.hint-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 4px;
  background: transparent;
  border: none;
  color: #334155;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.hint-toggle-btn:hover {
  color: #0f172a;
}

.hint-toggle-btn--inline {
  padding: 8px 25px;
  border-radius: 12px;
  background: #fff;
  border: none;
  margin-left: 6px;
}

.hint-toggle-btn--inline:hover {
  background: rgba(0, 0, 0, 0.04);
}

.hint-toggle-icon {
  width: 16px;
  height: 16px;
}

.hint-content {
  margin-top: 4px;
  padding: 14px 18px;
  background: rgba(251, 191, 36, 0.18);
  border-radius: 12px;
  font-size: 14px;
  color: #92400e;
  line-height: 1.6;
}

.explanation-box {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(59, 130, 246, 0.08);
  border-radius: 12px;
  font-size: 16px;
  color: #1e40af;
  line-height: 1.6;
}

.explanation-icon {
  width: 18px;
  height: 18px;
  color: #3b82f6;
  flex-shrink: 0;
  margin-top: 2px;
}

.hint-box {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(250, 140, 22, 0.08);
  border-radius: 12px;
  font-size: 14px;
  color: #78350f;
  line-height: 1.5;
}

.hint-icon {
  width: 18px;
  height: 18px;
  color: #fa8c16;
  flex-shrink: 0;
  margin-top: 2px;
}

.quiz-footer {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.nav-group,
.action-group {
  display: inline-flex;
  gap: 8px;
  align-items: center;
}

.nav-group {
  margin-left: auto;
}

.pill-btn {
  border: 1.5px solid rgba(0, 0, 0, 0.08);
  background: #fff;
  padding: 9px 16px;
  border-radius: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 13px;
  color: #334155;
}

.pill-btn:hover:not(:disabled) {
  border-color: #fa8c16;
  color: #fa8c16;
  background: rgba(250, 140, 22, 0.04);
}

.pill-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pill-btn--primary {
  background: linear-gradient(135deg, #fa8c16, #f59e0b);
  color: #fff;
  border-color: transparent;
}

.pill-btn--primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #fff;
  border-color: transparent;
}


.panel-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(4px);
  display: grid;
  place-items: center;
  z-index: 20;
  border-radius: 16px;
}

/* Modal Styles */
.generate-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 8px 0;
}

.form-label {
  font-weight: 600;
  color: #0f172a;
  margin-top: 4px;
  font-size: 15px;
}

.dropdown-icon {
  width: 14px;
  height: 14px;
}

@media (max-width: 768px) {
  .panel-shell {
    padding: 12px;
  }
}
</style>

<style>
/* Global Modal Styles */
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
}

:deep(.quiz-actions-dropdown .ant-dropdown-menu-item) {
  padding: 10px 14px;
  line-height: 1.5;
  font-size: 14px;
}

:deep(.quiz-actions-dropdown .ant-dropdown-menu-item .ant-dropdown-menu-title-content) {
  display: flex;
  align-items: center;
}

:deep(.quiz-actions-dropdown .ant-dropdown-menu-item .anticon) {
  font-size: 14px;
  margin-right: 12px;
}

:deep(.quiz-actions-dropdown .delete-menu-item) {
  color: #ff4d4f;
}

:deep(.quiz-actions-dropdown .delete-menu-item:hover) {
  color: #ff4d4f;
  background-color: rgba(0, 0, 0, 0.04) !important;
}

:deep(.quiz-actions-dropdown .delete-menu-item .anticon) {
  color: #ff4d4f;
}

.item-name-box {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  border-radius: 8px;
  background: #f5f5f5;
  color: #1a1a1a;
  font-weight: 500;
}
</style>
