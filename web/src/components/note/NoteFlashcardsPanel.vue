<template>
  <a-card class="flashcards-panel" :bordered="false" :body-style="{ height: '100%', padding: 0 }">
    <div class="panel-shell">
      <div v-if="!activeNotebookId" class="empty-panel">
        <SparklesIcon class="empty-icon" />
        <div class="empty-title">请选择一个笔记以生成闪卡</div>
        <p class="empty-desc">打开任意笔记本后即可查看或生成闪卡。</p>
      </div>

      <template v-else>
        <div v-if="selectedFolder" class="folder-view">
          <div class="folder-scroll">
            <div class="folder-topbar">
              <button class="back-btn" type="button" @click="goBackToList">
                <ArrowLeftIcon class="back-icon" />
              </button>
              <div class="folder-head">
                <div class="folder-name">{{ selectedFolder.name }}</div>
              </div>
            </div>

            <div class="mode-switch-wrapper">
              <div class="mode-switch">
                <button
                  class="mode-btn"
                  :class="{ 'mode-btn--active': reviewMode === 'spaced' }"
                  type="button"
                  @click="setMode('spaced')"
                >
                  浏览模式
                </button>
                <button
                  class="mode-btn"
                  :class="{ 'mode-btn--active': reviewMode === 'fast' }"
                  type="button"
                  @click="setMode('fast')"
                >
                  快速复习
                </button>
              </div>
            </div>

            <div v-if="reviewMode === 'spaced'" class="toolbar">
              <div class="toolbar-left">
                <span class="toolbar-title">Flashcards</span>
                <span class="toolbar-count">({{ activeFolderCards.length }})</span>
              </div>
              <div class="toolbar-right">
                <button class="toolbar-btn" type="button" @click="openAddCardModal">
                  <PlusIcon class="btn-icon" />
                  添加
                </button>
                <button
                  class="toolbar-btn toolbar-btn--primary"
                  type="button"
                  :disabled="folderGenerating"
                  @click="openGenerateInFolderModal"
                >
                  <a-spin v-if="folderGenerating" size="small" class="btn-spin" />
                  <SparklesIcon v-else class="btn-icon" />
                  {{ folderGenerating ? '生成中...' : 'AI生成' }}
                </button>
                <button class="toolbar-btn" type="button" @click="exportFlashcards">
                  <DownloadIcon class="btn-icon" />
                  导出
                </button>
              </div>
            </div>

            <template v-if="reviewMode === 'spaced'">
              <section class="card-list">
                <div v-if="!activeFolderCards.length" class="empty-inner">
                  <p>当前合集还没有闪卡</p>
                </div>
                <div v-else>
                  <div v-for="card in activeFolderCards" :key="card.id" class="card-row">
                    <div class="qa">
                      <div class="question">{{ card.question }}</div>
                      <div class="divider"></div>
                      <div class="answer">{{ card.answer }}</div>
                    </div>
                    <!-- 右上角删除按钮 -->
                    <a-dropdown trigger="click" placement="bottomRight">
                      <button class="card-menu-btn" type="button" @click.stop>
                        <MoreVerticalIcon class="menu-icon" />
                      </button>
                      <template #overlay>
                        <a-menu>
                          <a-menu-item @click.stop="promptDeleteCard(card)">
                            删除
                          </a-menu-item>
                        </a-menu>
                      </template>
                    </a-dropdown>
                    <!-- 右下角编辑按钮 -->
                    <button class="card-edit-btn" type="button" @click.stop="openEdit(card)">
                      <Edit3Icon class="edit-icon" />
                    </button>
                  </div>
                </div>
              </section>
            </template>

            <template v-else>
              <div v-if="currentReviewCard" class="fast-review">
                <div 
                  class="fast-card" 
                  :class="{ 'fast-card--flipped': revealAnswer }"
                  @click="toggleReveal"
                >
                  <div class="fast-card__inner">
                    <div class="fast-card__front">
                      <div class="fast-card__header">
                        <span class="pill pill--soft">问题</span>
                        <button class="icon-btn ghost" type="button" @click.stop="openEdit(currentReviewCard)">
                          <Edit3Icon class="icon" />
                        </button>
                      </div>
                      <div class="fast-card__body">
                        <p class="fast-text">{{ currentReviewCard.question }}</p>
                      </div>
                    </div>
                    <div class="fast-card__back">
                      <div class="fast-card__header">
                        <span class="pill pill--answer">答案</span>
                        <button class="icon-btn ghost" type="button" @click.stop="openEdit(currentReviewCard)">
                          <Edit3Icon class="icon" />
                        </button>
                      </div>
                      <div class="fast-card__body">
                        <p class="fast-text">{{ currentReviewCard.answer }}</p>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="flip-hint">点击卡片翻面</div>
                <div class="fast-footer">
                  <div class="nav-group">
                    <button class="pill-btn" type="button" :disabled="reviewIndex === 0" @click="prevCard">
                      上一张
                    </button>
                    <button
                      class="pill-btn"
                      type="button"
                      :disabled="reviewIndex >= reviewQueue.length - 1"
                      @click="nextCard"
                    >
                      下一张
                    </button>
                  </div>
                  <div class="counter">{{ reviewIndex + 1 }} / {{ reviewQueue.length }}</div>
                  <div class="action-group">
                    <button class="ghost-btn" type="button" @click="toggleShuffle">
                      <ShuffleIcon class="btn-icon" />
                      {{ shuffleEnabled ? '顺序播放' : 'Shuffle' }}
                    </button>
                  </div>
                </div>
              </div>
              <div v-else class="empty-inner">
                <p>暂无闪卡可复习</p>
              </div>
            </template>
          </div>
        </div>

        <div v-else class="list-view">
          <div class="folders-grid">
            <div
              v-for="(folder, index) in folders"
              :key="folder.id"
              class="folder-card"
              :class="`folder-card--color-${index % 6}`"
              @click="openFolder(folder.id)"
            >
              <div class="folder-card__head">
                <div class="folder-info">
                  <div class="folder-title">{{ folder.name }}</div>
                  <div v-if="folder.description" class="folder-desc">{{ folder.description }}</div>
                  <div class="folder-materials">
                    <template v-if="resolveMaterials(folder).length">
                      <span
                        v-for="(material, idx) in resolveMaterials(folder).slice(0, 2)"
                        :key="`${material}-${idx}`"
                        class="material-tag"
                      >
                        {{ material }}
                      </span>
                      <span v-if="resolveMaterials(folder).length > 2" class="material-more">
                        +{{ resolveMaterials(folder).length - 2 }}
                      </span>
                    </template>
                    <span v-else class="material-tag">课堂资料</span>
                  </div>
                </div>
                <!-- 卡片数量徽章 - 移到垂直居中 -->
                <span class="folder-badge">{{ getCardsForFolder(folder).length || folder.flashcardIds.length }} 张</span>
              </div>
              <!-- 右上角菜单按钮 -->
              <a-dropdown trigger="click" placement="bottomRight">
                <button class="folder-menu-btn" type="button" @click.stop>
                  <MoreVerticalIcon class="menu-icon" />
                </button>
                <template #overlay>
                  <a-menu>
                    <a-menu-item @click.stop="promptDeleteFolder(folder)">
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
            生成闪卡
          </a-button>

          <div v-if="!folders.length && !loading" class="empty-inner">
            <p>还没有闪卡合集</p>
            <p class="muted">点击"生成闪卡"试试看。</p>
          </div>
        </div>
      </template>

      <div v-if="loading" class="panel-overlay">
        <a-spin />
      </div>
    </div>
  </a-card>

  <a-modal
    v-model:visible="generateModal.open"
    :confirm-loading="generateModal.loading"
    title="生成闪卡"
    :maskClosable="false"
    :width="560"
    centered
    destroy-on-close
    wrap-class-name="rounded-modal"
    @ok="handleGenerate"
    @cancel="closeGenerateModal"
  >
    <div class="generate-form">
      <label class="form-label">闪卡数量</label>
      <a-input
        v-model:value="generateModal.count"
        type="number"
        min="1"
        placeholder="自动"
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
        placeholder="让AI根据你的重点和偏好来定制化闪卡"
      />
    </div>
  </a-modal>

  <a-modal
    v-model:visible="editModal.open"
    :footer="null"
    :maskClosable="false"
    :width="520"
    centered
    destroy-on-close
    wrap-class-name="rounded-modal flashcard-edit-modal"
  >
    <div class="edit-modal__body">
      <div class="edit-modal__title">编辑闪卡</div>
      <label class="edit-label">问题</label>
      <a-textarea v-model:value="editModal.question" :auto-size="{ minRows: 2, maxRows: 6 }" placeholder="更新问题" />
      <label class="edit-label">答案</label>
      <a-textarea v-model:value="editModal.answer" :auto-size="{ minRows: 2, maxRows: 6 }" placeholder="更新答案" />
      <div class="modal-actions">
        <a-button @click="closeEdit">取消</a-button>
        <a-button type="primary" :loading="editModal.loading" @click="handleEditSave">保存</a-button>
      </div>
    </div>
  </a-modal>

  <a-modal
    v-model:visible="addCardModal.open"
    :footer="null"
    :maskClosable="false"
    :width="520"
    centered
    destroy-on-close
    wrap-class-name="rounded-modal flashcard-edit-modal"
  >
    <div class="edit-modal__body">
      <div class="edit-modal__title">添加闪卡</div>
      <label class="edit-label">问题</label>
      <a-textarea v-model:value="addCardModal.question" :auto-size="{ minRows: 2, maxRows: 6 }" placeholder="输入问题" />
      <label class="edit-label">答案</label>
      <a-textarea v-model:value="addCardModal.answer" :auto-size="{ minRows: 2, maxRows: 6 }" placeholder="输入答案" />
      <div class="modal-actions">
        <a-button @click="closeAddCardModal">取消</a-button>
        <a-button type="primary" :loading="addCardModal.loading" @click="handleAddCard">添加</a-button>
      </div>
    </div>
  </a-modal>


</template>

<script setup lang="ts">
import { computed, reactive, ref, watch, h } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { ArrowLeftIcon, Edit3Icon, ShuffleIcon, SparklesIcon, PlusIcon, DownloadIcon, MoreVerticalIcon } from 'lucide-vue-next'
import type { Flashcard, FlashcardFolder } from '@/types/flashcards'
import type { NoteAttachment } from '@/types/notes'
import {
  createFlashcard,
  generateFlashcardsForNotebook,
  listFlashcardFolders,
  listFlashcards,
  updateFlashcard,
  deleteFlashcardFolder,
  deleteFlashcard,
} from '@/services/api'
import { useNotebookStore } from '@/composables/useNotes'
import { getModelFor } from '@/composables/setting'

const notebookStore = useNotebookStore()

const loading = ref(false)
const generating = ref(false)
const folderGenerating = ref(false)
const folders = ref<FlashcardFolder[]>([])
const flashcards = ref<Flashcard[]>([])
const selectedFolderId = ref<string | null>(null)
const reviewMode = ref<'spaced' | 'fast'>('spaced')
const shuffleEnabled = ref(false)
const reviewQueue = ref<Flashcard[]>([])
const reviewIndex = ref(0)
const revealAnswer = ref(false)

const generateModal = reactive({
  open: false,
  loading: false,
  attachments: [] as string[],
  count: '',
  focus: '',
})
const generateTargetFolderId = ref<string | null>(null)

const editModal = reactive({
  open: false,
  loading: false,
  question: '',
  answer: '',
  target: null as Flashcard | null,
})

const addCardModal = reactive({
  open: false,
  loading: false,
  question: '',
  answer: '',
})

const deleteFolderModal = reactive({
  open: false,
  loading: false,
  targetId: '' as string | null,
  targetName: '',
})

const deletingCardId = ref<string | null>(null)

const activeNotebookId = computed(() => notebookStore.activeNotebook.value?.id ?? null)
const attachments = computed<NoteAttachment[]>(() => notebookStore.activeNotebook.value?.attachments ?? [])
const selectableAttachments = computed(() =>
  attachments.value.filter(item => !!item.openaiFileId),
)

const cardsByFolderMap = computed(() => {
  const map = new Map<string, Flashcard[]>()
  folders.value.forEach(folder => map.set(folder.id, []))

  flashcards.value.forEach(card => {
    const candidateFolderIds = new Set<string>(card.folderIds)
    folders.value.forEach(folder => {
      if (folder.flashcardIds.includes(card.id)) {
        candidateFolderIds.add(folder.id)
      }
    })
    candidateFolderIds.forEach(folderId => {
      const list = map.get(folderId) ?? []
      list.push(card)
      map.set(folderId, list)
    })
  })

  return map
})

const selectedFolder = computed(() =>
  selectedFolderId.value ? folders.value.find(folder => folder.id === selectedFolderId.value) ?? null : null,
)

const activeFolderCards = computed(() => {
  const folder = selectedFolder.value
  if (!folder) return []
  const base = cardsByFolderMap.value.get(folder.id) ?? []
  const orderMap = new Map<string, number>()
  folder.flashcardIds.forEach((id, idx) => orderMap.set(id, idx))
  return [...base].sort((a, b) => (orderMap.get(b.id) ?? -1) - (orderMap.get(a.id) ?? -1))
})

const folderMaterials = computed(() => (selectedFolder.value ? resolveMaterials(selectedFolder.value) : []))

const currentReviewCard = computed(() => reviewQueue.value[reviewIndex.value] ?? null)

const getErrorMessage = (err: unknown) => (err instanceof Error ? err.message : '请求失败')

const extractMaterialNames = (meta: Record<string, unknown> | null): string[] => {
  if (!meta) return []
  const sources =
    (meta as any).sources ??
    (meta as any).materials ??
    (meta as any).attachments ??
    (meta as any).files ??
    (meta as any).source

  const list = Array.isArray(sources) ? sources : sources ? [sources] : []
  return list
    .map(item => {
      if (!item) return ''
      if (typeof item === 'string') return item
      if (typeof item === 'object') {
        const obj = item as Record<string, any>
        return obj.title || obj.name || obj.filename || obj.file || ''
      }
      return ''
    })
    .filter(Boolean)
}

const resolveMaterials = (folder: FlashcardFolder): string[] => {
  const cards = cardsByFolderMap.value.get(folder.id) ?? []
  const names = new Set<string>()
  cards.forEach(card => {
    extractMaterialNames(card.meta).forEach(name => names.add(name))
  })
  if (!names.size && attachments.value.length) {
    attachments.value.slice(0, 2).forEach(att => names.add(att.filename || att.s3ObjectKey || '课堂资料'))
  }
  return Array.from(names)
}

const shuffleCards = <T,>(input: T[]): T[] => {
  const arr = [...input]
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr
}

const rebuildReviewQueue = () => {
  if (!selectedFolder.value) {
    reviewQueue.value = []
    reviewIndex.value = 0
    revealAnswer.value = false
    return
  }
  const base = activeFolderCards.value
  reviewQueue.value = shuffleEnabled.value ? shuffleCards(base) : [...base]
  reviewIndex.value = 0
  revealAnswer.value = false
}

const loadFlashcards = async () => {
  if (!activeNotebookId.value) return
  loading.value = true
  try {
    const [folderList, cardList] = await Promise.all([
      listFlashcardFolders({ notebookId: activeNotebookId.value }),
      listFlashcards({ notebookId: activeNotebookId.value }),
    ])
    folders.value = folderList
    flashcards.value = cardList
  } catch (err) {
    message.error(getErrorMessage(err))
    folders.value = []
    flashcards.value = []
  } finally {
    loading.value = false
    rebuildReviewQueue()
  }
}

watch(
  () => activeNotebookId.value,
  id => {
    selectedFolderId.value = null
    if (id) {
      loadFlashcards()
    } else {
      folders.value = []
      flashcards.value = []
    }
  },
  { immediate: true },
)

watch(
  () => [selectedFolderId.value, activeFolderCards.value.length, shuffleEnabled.value],
  () => rebuildReviewQueue(),
)

const openFolder = (folderId: string) => {
  selectedFolderId.value = folderId
  reviewMode.value = 'spaced'
  shuffleEnabled.value = false
  rebuildReviewQueue()
}

const goBackToList = () => {
  selectedFolderId.value = null
  reviewMode.value = 'spaced'
  reviewIndex.value = 0
  revealAnswer.value = false
}

const setMode = (mode: 'spaced' | 'fast') => {
  reviewMode.value = mode
  revealAnswer.value = false
}

const toggleShuffle = () => {
  shuffleEnabled.value = !shuffleEnabled.value
  rebuildReviewQueue()
}

const toggleReveal = () => {
  revealAnswer.value = !revealAnswer.value
}

const nextCard = () => {
  if (reviewIndex.value < reviewQueue.value.length - 1) {
    reviewIndex.value += 1
    revealAnswer.value = false
  }
}

const prevCard = () => {
  if (reviewIndex.value > 0) {
    reviewIndex.value -= 1
    revealAnswer.value = false
  }
}

const openGenerateModal = () => {
  if (!activeNotebookId.value) {
    message.warning('请先选择一个笔记本')
    return
  }
  if (!selectableAttachments.value.length) {
    message.warning('请先上传并同步资料到 OpenAI 后再生成闪卡')
    return
  }
  generateTargetFolderId.value = null
  generateModal.attachments = selectableAttachments.value.map(item => item.id)
  generateModal.count = ''
  generateModal.focus = ''
  generateModal.open = true
}

const closeGenerateModal = () => {
  generateModal.open = false
  generateModal.loading = false
  generateTargetFolderId.value = null
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
  const targetFolderId = generateTargetFolderId.value

  generateModal.loading = true
  if (targetFolderId) {
    folderGenerating.value = true
  } else {
    generating.value = true
  }
  try {
    const model = getModelFor('flashcard')
    await generateFlashcardsForNotebook(activeNotebookId.value, {
      attachmentIds: generateModal.attachments,
      count,
      focus: generateModal.focus.trim() || undefined,
      model,
      folderId: targetFolderId ?? undefined,
    })
    generateModal.open = false
    generateTargetFolderId.value = null
    await loadFlashcards()
    message.success(targetFolderId ? '已为当前合集生成闪卡' : '已提交生成请求')
  } catch (err) {
    message.error(getErrorMessage(err))
  } finally {
    generateModal.loading = false
    generating.value = false
    folderGenerating.value = false
  }
}

const openEdit = (card: Flashcard) => {
  editModal.target = card
  editModal.question = card.question
  editModal.answer = card.answer
  editModal.open = true
}

const closeEdit = () => {
  editModal.open = false
  editModal.target = null
  editModal.question = ''
  editModal.answer = ''
}

const handleEditSave = async () => {
  if (!editModal.target) return
  editModal.loading = true
  try {
    const updated = await updateFlashcard(editModal.target.id, {
      question: editModal.question,
      answer: editModal.answer,
    })
    flashcards.value = flashcards.value.map(card => (card.id === updated.id ? updated : card))
    message.success('已更新闪卡')
    closeEdit()
  } catch (err) {
    message.error(getErrorMessage(err))
  } finally {
    editModal.loading = false
  }
}

const getCardsForFolder = (folder: FlashcardFolder): Flashcard[] => {
  return cardsByFolderMap.value.get(folder.id) ?? []
}

const openAddCardModal = () => {
  addCardModal.question = ''
  addCardModal.answer = ''
  addCardModal.open = true
}

const closeAddCardModal = () => {
  addCardModal.open = false
  addCardModal.loading = false
  addCardModal.question = ''
  addCardModal.answer = ''
}

const handleAddCard = async () => {
  if (!addCardModal.question.trim() || !addCardModal.answer.trim()) {
    message.warning('请填写问题和答案')
    return
  }
  if (!activeNotebookId.value) {
    message.warning('请先选择一个笔记本')
    return
  }
  if (!selectedFolderId.value) {
    message.warning('请先选择一个合集')
    return
  }
  
  addCardModal.loading = true
  try {
    const newCard = await createFlashcard({
      notebookId: activeNotebookId.value,
      question: addCardModal.question.trim(),
      answer: addCardModal.answer.trim(),
      folderIds: [selectedFolderId.value],
    })
    flashcards.value = [...flashcards.value, newCard]
    const folderIndex = folders.value.findIndex(folder => folder.id === selectedFolderId.value)
    if (folderIndex >= 0) {
      const folder = folders.value[folderIndex]
      folders.value.splice(folderIndex, 1, { ...folder, flashcardIds: [...folder.flashcardIds, newCard.id] })
    }
    message.success('闪卡已添加')
    closeAddCardModal()
  } catch (err) {
    message.error(getErrorMessage(err))
  } finally {
    addCardModal.loading = false
  }
}

const promptDeleteCard = (card: Flashcard) => {
  Modal.confirm({
    title: '删除闪卡',
    icon: null,
    content: h('div', [
      '确定要删除闪卡 ',
      h('span', { 
        class: 'delete-modal-name-tag'
      }, card.question),
      ' 吗？'
    ]),
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    centered: true,
    wrapClassName: 'custom-delete-modal',
    onOk: async () => {
      deletingCardId.value = card.id
      try {
        await deleteFlashcard(card.id)
        flashcards.value = flashcards.value.filter(item => item.id !== card.id)
        folders.value = folders.value.map(folder =>
          folder.flashcardIds.includes(card.id)
            ? { ...folder, flashcardIds: folder.flashcardIds.filter(id => id !== card.id) }
            : folder,
        )
        message.success('已删除闪卡')
      } catch (err) {
        message.error(getErrorMessage(err))
        throw err
      } finally {
        deletingCardId.value = null
      }
    },
  })
}

const promptDeleteFolder = (folder: FlashcardFolder) => {
  deleteFolderModal.targetId = folder.id
  deleteFolderModal.targetName = folder.name
  Modal.confirm({
    title: '',
    icon: null,
    content: h('div', [
      '确定删除 ',
      h('span', { 
        class: 'delete-modal-name-tag'
      }, folder.name),
      ' 吗？'
    ]),
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    centered: true,
    wrapClassName: 'custom-delete-modal',
    onOk: async () => {
      deleteFolderModal.loading = true
      try {
        await deleteFlashcardFolder(folder.id)
        folders.value = folders.value.filter(item => item.id !== folder.id)
        if (selectedFolderId.value === folder.id) {
          selectedFolderId.value = null
        }
        message.success('已删除闪卡合集')
      } catch (err) {
        message.error(getErrorMessage(err))
        throw err
      } finally {
        deleteFolderModal.loading = false
      }
    },
  })
}

const openGenerateInFolderModal = () => {
  if (!activeNotebookId.value) {
    message.warning('请先选择一个笔记本')
    return
  }
  if (!selectedFolder.value) {
    message.warning('请先选择一个合集')
    return
  }
  if (!selectableAttachments.value.length) {
    message.warning('请先上传并同步资料到 OpenAI 后再生成闪卡')
    return
  }
  generateTargetFolderId.value = selectedFolder.value.id
  generateModal.attachments = selectableAttachments.value.map(item => item.id)
  generateModal.count = ''
  generateModal.focus = ''
  generateModal.open = true
}

const exportFlashcards = () => {
  if (!activeFolderCards.value.length) {
    message.warning('当前合集没有闪卡可导出')
    return
  }
  
  // 创建CSV格式的数据
  const csvContent = [
    ['问题', '答案'],
    ...activeFolderCards.value.map(card => [card.question, card.answer])
  ].map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(',')).join('\n')
  
  // 创建Blob并下载
  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `${selectedFolder.value?.name || 'flashcards'}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  message.success('闪卡已导出')
}
</script>

<style scoped>
.flashcards-panel {
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
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.04), rgba(59, 130, 246, 0.03));
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
  color: #6366f1;
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
.folder-view {
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
  background: #fff;
  border-radius: 20px;
  padding: 18px 20px;
  border: 1.5px solid rgba(0, 0, 0, 0.05);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.folder-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  opacity: 0;
  transition: opacity 0.25s ease;
  pointer-events: none;
}

.folder-card--color-0 {
  background: linear-gradient(135deg, #fef3c7 0%, #fef9e7 100%);
  border-color: rgba(251, 191, 36, 0.2);
}

.folder-card--color-1 {
  background: linear-gradient(135deg, #dbeafe 0%, #eff6ff 100%);
  border-color: rgba(59, 130, 246, 0.2);
}

.folder-card--color-2 {
  background: linear-gradient(135deg, #fce7f3 0%, #fdf2f8 100%);
  border-color: rgba(236, 72, 153, 0.2);
}

.folder-card--color-3 {
  background: linear-gradient(135deg, #dcfce7 0%, #f0fdf4 100%);
  border-color: rgba(34, 197, 94, 0.2);
}

.folder-card--color-4 {
  background: linear-gradient(135deg, #e0e7ff 0%, #eef2ff 100%);
  border-color: rgba(99, 102, 241, 0.2);
}

.folder-card--color-5 {
  background: linear-gradient(135deg, #ffedd5 0%, #fff7ed 100%);
  border-color: rgba(249, 115, 22, 0.2);
}

.folder-card:hover {
  transform: translateY(-3px);
}

.folder-card--color-0:hover {
  border-color: rgba(251, 191, 36, 0.4);
}

.folder-card--color-1:hover {
  border-color: rgba(59, 130, 246, 0.4);
}

.folder-card--color-2:hover {
  border-color: rgba(236, 72, 153, 0.4);
}

.folder-card--color-3:hover {
  border-color: rgba(34, 197, 94, 0.4);
}

.folder-card--color-4:hover {
  border-color: rgba(99, 102, 241, 0.4);
}

.folder-card--color-5:hover {
  border-color: rgba(249, 115, 22, 0.4);
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
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 6px;
}

.folder-desc {
  font-size: 13px;
  color: #475569;
  margin-bottom: 10px;
}

.folder-materials {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.material-tag {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 11px;
  color: #475569;
  font-weight: 600;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.material-more {
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
}

/* 文件夹卡片数量徽章 - 移到垂直居中 */
.folder-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 42px;
  padding: 6px 10px;
  border-radius: 10px;
  background: rgba(99, 102, 241, 0.12);
  color: #4338ca;
  font-weight: 700;
  font-size: 13px;
  white-space: nowrap;
  flex-shrink: 0;
}

/* 文件夹菜单按钮 - 右上角悬浮 */
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

.pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
  padding: 8px 14px;
  border-radius: 12px;
  background: rgba(99, 102, 241, 0.08);
  color: #4f46e5;
  font-weight: 700;
  font-size: 13px;
  white-space: nowrap;
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
  background: linear-gradient(135deg, #3b82f6, #2563eb);
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

.folder-topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 0 16px;
  flex-wrap: wrap;
}

.folder-actions {
  margin-left: auto;
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

.ghost-btn {
  border: 1.5px solid rgba(0, 0, 0, 0.08);
  background: #fff;
  padding: 9px 14px;
  border-radius: 14px;
  color: #334155;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 600;
}

.ghost .icon.small {
  color: #94a3b8;
}

.ghost-btn:hover {
  border-color: #6366f1;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.04);
}

.btn-icon {
  width: 14px;
  height: 14px;
}

.btn-spin {
  width: 14px;
  height: 14px;
}

.folder-head {
  min-width: 0;
  flex: 1;
}

.folder-name {
  font-size: 19px;
  font-weight: 700;
  color: #0f172a;
}

.mode-switch-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.mode-switch {
  display: inline-flex;
  align-items: center;
  padding: 5px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 16px;
  gap: 4px;
}

.mode-btn {
  border: none;
  background: transparent;
  padding: 9px 16px;
  border-radius: 12px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 13px;
}

.mode-btn--active {
  background: #fff;
  color: #0f172a;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0 16px;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.toolbar-count {
  font-size: 14px;
  color: #94a3b8;
  font-weight: 500;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-btn {
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #fff;
  padding: 6px 12px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 12px;
  color: #475569;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toolbar-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.04);
}

.toolbar-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.toolbar-btn--primary {
  background: #3b82f6;
  color: #fff;
  border-color: #3b82f6;
}

.toolbar-btn--primary:hover {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.toolbar-btn--primary:disabled {
  background: #93c5fd;
  border-color: #93c5fd;
  color: #fff;
}

.folder-scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0;
}

.card-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 20px;
}

.card-row {
  background: #fff;
  border-radius: 16px;
  border: 1.5px solid rgba(0, 0, 0, 0.04);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  transition: all 0.2s ease;
  position: relative;
}

.card-row:hover {
  border-color: rgba(99, 102, 241, 0.2);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.qa {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 20px;
  align-items: flex-start;
  padding-right: 50px;
}

.question {
  font-weight: 600;
  color: #0f172a;
  font-size: 14px;
  line-height: 1.6;
}

.divider {
  width: 1.5px;
  height: 100%;
  background: linear-gradient(to bottom, transparent, rgba(0, 0, 0, 0.1), transparent);
}

.answer {
  color: #475569;
  font-size: 14px;
  line-height: 1.6;
}

/* 卡片菜单按钮 - 右上角悬浮 */
.card-menu-btn {
  position: absolute;
  top: 8px;
  right: 8px;
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
  color: #94a3b8;
  opacity: 0;
  z-index: 2;
}

.card-row:hover .card-menu-btn {
  opacity: 1;
}

.card-menu-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #475569;
}

.card-menu-btn .menu-icon {
  width: 16px;
  height: 16px;
}

/* 卡片编辑按钮 - 右下角悬浮 */
.card-edit-btn {
  position: absolute;
  bottom: 8px;
  right: 8px;
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
  color: #94a3b8;
  opacity: 0;
  z-index: 2;
}

.card-row:hover .card-edit-btn {
  opacity: 1;
}

.card-edit-btn:hover {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.card-edit-btn .edit-icon {
  width: 14px;
  height: 14px;
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
  border-color: #6366f1;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.04);
}

.icon-btn.ghost {
  border-color: transparent;
  background: rgba(0, 0, 0, 0.03);
}

.icon {
  width: 16px;
  height: 16px;
}

.icon.small {
  width: 14px;
  height: 14px;
}

.icon-btn.small {
  padding: 6px;
}

.card-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.fast-review {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
  padding-bottom: 20px;
}

.fast-card {
  width: 100%;
  max-width: 600px;
  perspective: 1000px;
  cursor: pointer;
  min-height: 280px;
}

.fast-card__inner {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 280px;
  transition: transform 0.6s;
  transform-style: preserve-3d;
}

.fast-card--flipped .fast-card__inner {
  transform: rotateY(180deg);
}

.fast-card__front,
.fast-card__back {
  position: absolute;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
  background: #fff;
  border-radius: 20px;
  padding: 20px;
  border: 1.5px solid rgba(0, 0, 0, 0.04);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
}

.fast-card__back {
  transform: rotateY(180deg);
}

.fast-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.pill--soft {
  background: rgba(0, 0, 0, 0.04);
  color: #0f172a;
  padding: 7px 13px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.pill--answer {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  padding: 7px 13px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.fast-card__body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 10px;
}

.fast-text {
  margin: 0;
  font-size: 18px;
  line-height: 1.7;
  color: #0f172a;
  text-align: center;
}

.flip-hint {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
  margin-top: -4px;
}

.fast-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  width: 100%;
  max-width: 600px;
  margin-top: 8px;
}

.nav-group,
.action-group {
  display: inline-flex;
  gap: 8px;
  align-items: center;
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
  border-color: #6366f1;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.04);
}

.pill-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.counter {
  font-weight: 700;
  color: #0f172a;
  flex: 1;
  text-align: center;
  font-size: 14px;
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

.edit-modal__body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0;
}

.edit-modal__title {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 4px;
}

.edit-label {
  font-size: 13px;
  color: #475569;
  font-weight: 600;
  margin-top: 4px;
}

.modal-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

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
  font-size: 14px;
}

@media (max-width: 768px) {
  .panel-shell {
    padding: 12px;
  }

  .qa {
    grid-template-columns: 1fr;
    gap: 12px;
    padding-right: 0;
  }

  .divider {
    display: none;
  }

  .fast-footer {
    flex-direction: column;
    gap: 12px;
  }

  .counter {
    order: -1;
  }
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
}

.flashcard-edit-modal .ant-modal-footer {
  display: none;
}

/* 自定义删除确认弹窗样式 */
.custom-delete-modal .ant-modal-content {
  border-radius: 24px !important;
  overflow: hidden;
  background: #fff;
}

.custom-delete-modal .ant-modal-header {
  border-radius: 24px 24px 0 0 !important;
  padding: 32px 28px 0;
  border-bottom: none;
  background: transparent;
}

.custom-delete-modal .ant-modal-title {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}

.custom-delete-modal .ant-modal-body {
  padding: 20px 28px 28px;
  font-size: 16px;
  line-height: 1.7;
  color: #475569;
}

.custom-delete-modal .ant-modal-footer {
  border-radius: 0 0 24px 24px !important;
  padding: 16px 28px 28px;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
  background: transparent;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.custom-delete-modal .ant-btn {
  border-radius: 10px !important;
  padding: 8px 14px;
  height: auto;
  font-weight: 600;
  font-size: 13px;
  transition: all 0.2s ease;
  border: 1px solid;
  box-shadow: none;
}

.custom-delete-modal .ant-btn-default {
  background: #fff;
  border-color: #d4d8df;
  color: #334155;
}

.custom-delete-modal .ant-btn-default:hover {
  background: #f6f7fb;
  border-color: #c8ced8;
  color: #1f2937;
}

.custom-delete-modal .ant-btn-dangerous {
  background: #ef4444;
  border-color: #ef4444;
  color: #fff;
  box-shadow: none;
}

.custom-delete-modal .ant-btn-dangerous:hover {
  background: #dc2626;
  border-color: #dc2626;
  box-shadow: none;
  transform: translateY(-1px);
}

.custom-delete-modal .ant-modal-close {
  top: 20px;
  right: 20px;
}

.custom-delete-modal .ant-modal-close-x {
  width: 40px;
  height: 40px;
  line-height: 40px;
  border-radius: 12px;
  transition: all 0.2s ease;
  color: #94a3b8;
}

.custom-delete-modal .ant-modal-close:hover .ant-modal-close-x {
  background: rgba(0, 0, 0, 0.04);
  color: #475569;
}

/* 删除弹窗中的名称标签样式 */
.delete-modal-name-tag {
  display: inline-block;
  background: rgba(0, 0, 0, 0.04);
  color: #0f172a;
  padding: 4px 10px;
  border-radius: 6px;
  font-weight: 600;
  font-size: 15px;
  margin: 0 2px;
}
</style>
