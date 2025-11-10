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

      <div v-else class="notes-list-view">
        <header class="notes-list-view__header">
          <div class="header-text">
            <h2>我的笔记</h2>
            <p>{{ headerSubtitle }}</p>
          </div>
        </header>

        <div class="notes-toolbar">
          <div class="notes-search">
            <a-input
              v-model:value="searchQuery"
              size="large"
              allow-clear
              placeholder="搜索标题、摘要或标签..."
              class="notes-search__input"
            >
              <template #prefix>
                <SearchOutlined />
              </template>
            </a-input>
          </div>
        </div>

        <div v-if="listLoading" class="notes-list-view__placeholder">
          <a-spin />
          <span>加载笔记列表...</span>
        </div>

        <div v-else>
          <div v-if="shouldShowCreateCard || notes.length" class="notes-list-view__grid">
            <div
              v-if="shouldShowCreateCard"
              key="create-card"
              :class="['notes-list-view__card', 'notes-list-view__card--create', { 'is-loading': creatingCard }]"
              role="button"
              tabindex="0"
              @click="!creatingCard && handleCreateNote()"
              @keydown.enter.prevent="!creatingCard && handleCreateNote()"
            >
              <div class="create-card__badge">
                <PlusOutlined />
              </div>
              <h3>新建笔记</h3>
              <p>开启属于你的知识库。</p>
              <a-spin v-if="creatingCard" size="small" />
            </div>
            <div
              v-for="note in notes"
              :key="note.id"
              :class="['notes-list-view__card', { 'is-active': note.id === activeNoteId }]"
              @click="handleSelectNote(note.id)"
              @keydown.enter.prevent="handleSelectNote(note.id)"
              role="button"
              tabindex="0"
            >
              <div class="card-header">
                <div class="card-header__info">
                  <h3>{{ note.title }}</h3>
                  <span>{{ formatDate(note.updatedAt) }}</span>
                </div>
                <a-dropdown :trigger="['click']" placement="bottomRight" overlay-class-name="note-card-menu">
                  <button class="card-menu" type="button" @click.stop>
                    <MoreOutlined />
                  </button>
                  <template #overlay>
                    <a-menu @click="onNoteMenuClick(note, $event)">
                      <a-menu-item key="rename">
                        <EditOutlined />
                        <span>重命名</span>
                      </a-menu-item>
                      <a-menu-item key="delete">
                        <DeleteOutlined />
                        <span>删除</span>
                      </a-menu-item>
                    </a-menu>
                  </template>
                </a-dropdown>
              </div>
              <p class="card-summary">{{ note.summary || '暂无摘要，进入笔记继续完善内容～' }}</p>
              <div class="card-tags">
                <a-tag v-for="tag in note.tags" :key="`${note.id}-${tag}`" bordered>{{ tag }}</a-tag>
              </div>
            </div>
          </div>

          <div v-if="isSearching && !notes.length" class="notes-list-view__placeholder notes-list-view__placeholder--surface">
            <a-empty description="没有找到相关笔记，换个关键词试试？" />
          </div>

          <div v-else-if="!isSearching && !notes.length" class="notes-list-view__empty-hint">
            <h3>还没有笔记</h3>
            <p>点击上方的卡片立即创建第一篇笔记吧。</p>
          </div>
        </div>
      </div>
    </div>
    <a-modal
      v-model:visible="renameModal.open"
      :footer="null"
      :maskClosable="false"
      :width="420"
      centered
      destroy-on-close
      wrap-class-name="note-modal note-modal--rename"
      @cancel="handleRenameCancel"
      @afterClose="resetRenameModal"
    >
      <div class="note-modal__body">
        <div class="note-modal__avatar">
          <BookOutlined />
        </div>
        <label class="note-modal__label" for="note-rename-input">笔记本名称*</label>
        <a-input
          id="note-rename-input"
          ref="renameInputRef"
          v-model:value="renameModal.value"
          allow-clear
          maxlength="60"
          size="large"
          placeholder="输入新的笔记名称"
          autofocus
          class="note-modal__input"
        />
        <div class="note-modal__actions">
          <a-button class="note-modal__btn note-modal__btn--ghost" @click="handleRenameCancel">取消</a-button>
          <a-button
            class="note-modal__btn note-modal__btn--primary"
            type="primary"
            :loading="renameModal.loading"
            @click="handleRenameSubmit"
          >
            保存
          </a-button>
        </div>
      </div>
    </a-modal>

    <a-modal
      v-model:visible="deleteModal.open"
      :footer="null"
      :maskClosable="false"
      :width="360"
      centered
      destroy-on-close
      wrap-class-name="note-modal note-modal--delete"
      @cancel="handleDeleteCancel"
      @afterClose="resetDeleteModal"
    >
      <div class="note-modal__body note-modal__body--delete">
        <p class="note-modal__delete-title">
          要删除
          <span class="note-modal__note-title">
            <BookOutlined />
            <span>{{ deleteModal.note?.title || '未命名笔记' }}</span>
          </span>
          吗?
        </p>
        <div class="note-modal__actions">
          <a-button class="note-modal__btn note-modal__btn--ghost" @click="handleDeleteCancel">取消</a-button>
          <a-button
            class="note-modal__btn note-modal__btn--danger"
            type="primary"
            :loading="deleteModal.loading"
            @click="handleDeleteConfirm"
          >
            删除
          </a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { message } from 'ant-design-vue'
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { BookOutlined, DeleteOutlined, EditOutlined, MoreOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons-vue'
import { useAuth } from '@/composables/useAuth'
import { useNotes } from '@/composables/useNotes'
import type { NotebookSummary } from '@/types/notes'

const auth = useAuth()
const notesStore = useNotes()
const router = useRouter()

const { state, fetchList, createNewNote, renameNote, removeNote, clearActiveNote } = notesStore

const listLoading = computed(() => state.listLoading)
const searchQuery = ref('')
const creatingCard = ref(false)
const sortedNotes = computed(() => [...state.list].sort((a, b) => (a.updatedAt > b.updatedAt ? -1 : 1)))
const filteredNotes = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return sortedNotes.value
  return sortedNotes.value.filter(note => {
    const inTitle = note.title?.toLowerCase().includes(query)
    const inSummary = note.summary?.toLowerCase().includes(query)
    const inTags = note.tags?.some(tag => tag.toLowerCase().includes(query))
    return inTitle || inSummary || inTags
  })
})
const notes = computed<NotebookSummary[]>(() =>
  filteredNotes.value.map(note => ({
    ...note,
    tags: [...note.tags],
  }))
)
const isSearching = computed(() => Boolean(searchQuery.value.trim()))
const shouldShowCreateCard = computed(() => !isSearching.value)
const totalCount = computed(() => state.list.length)
const activeNoteId = computed(() => state.active?.id ?? null)
const headerSubtitle = computed(() => {
  if (!isSearching.value) return `共 ${totalCount.value} 条记录，随时同步到云端`
  return `共 ${totalCount.value} 条记录，当前显示 ${notes.value.length} 条匹配结果`
})

type CardAction = 'rename' | 'delete'

const renameModal = reactive({
  open: false,
  loading: false,
  value: '',
  note: null as NotebookSummary | null,
})

const deleteModal = reactive({
  open: false,
  loading: false,
  note: null as NotebookSummary | null,
})

const renameInputRef = ref<{ focus?: () => void } | null>(null)

watch(
  () => ({ ready: auth.state.ready, authed: auth.isAuthenticated.value }),
  async ({ ready, authed }) => {
    if (!ready) return
    if (authed) {
      try {
        await fetchList()
      } catch (err) {
        // 错误在 store 内部已有提示
      }
    } else {
      clearActiveNote()
    }
  },
  { immediate: true },
)

const handleSelectNote = (noteId: string) => {
  router.push({ name: 'note-editor', params: { id: noteId } })
}

const handleCreateNote = async () => {
  if (creatingCard.value) return
  creatingCard.value = true
  try {
    await createNewNote()
    const active = state.active
    if (active?.id) {
      router.push({ name: 'note-editor', params: { id: active.id } })
    }
  } catch (err) {
    // 错误已在 store 内提示
  } finally {
    creatingCard.value = false
  }
}

const formatDate = (value?: string | null) => {
  if (!value) return '刚刚'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

const handleCardMenuAction = (note: NotebookSummary, action: CardAction) => {
  if (action === 'rename') {
    openRenameModal(note)
  } else if (action === 'delete') {
    openDeleteModal(note)
  }
}

interface MenuClickEvent {
  key: string
}

const onNoteMenuClick = (note: NotebookSummary, event: MenuClickEvent) => {
  handleCardMenuAction(note, event.key as CardAction)
}

const openRenameModal = (note: NotebookSummary) => {
  renameModal.note = note
  renameModal.value = note.title ?? ''
  renameModal.open = true
  nextTick(() => {
    renameInputRef.value?.focus?.()
  })
}

const handleRenameCancel = () => {
  renameModal.open = false
}

const resetRenameModal = () => {
  renameModal.loading = false
  renameModal.value = ''
  renameModal.note = null
  renameInputRef.value = null
}

const handleRenameSubmit = async () => {
  if (!renameModal.note) return
  const newTitle = renameModal.value.trim()
  if (!newTitle) {
    message.warning('标题不能为空')
    return
  }
  if (newTitle === renameModal.note.title) {
    renameModal.open = false
    return
  }
  renameModal.loading = true
  try {
    await renameNote(renameModal.note.id, newTitle)
    await fetchList()
    renameModal.open = false
  } catch (err) {
    return
  } finally {
    renameModal.loading = false
  }
}

const openDeleteModal = (note: NotebookSummary) => {
  deleteModal.note = note
  deleteModal.open = true
}

const handleDeleteCancel = () => {
  deleteModal.open = false
}

const resetDeleteModal = () => {
  deleteModal.loading = false
  deleteModal.note = null
}

const handleDeleteConfirm = async () => {
  if (!deleteModal.note) return
  deleteModal.loading = true
  try {
    await removeNote(deleteModal.note.id)
    deleteModal.open = false
  } finally {
    deleteModal.loading = false
  }
}
</script>

<style scoped>
.notes-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f7fb;
}

.page-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 20px;
  box-sizing: border-box;
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
  border: 1px dashed rgba(37, 99, 235, 0.16);
}

.placeholder-text {
  font-size: 13px;
}

.notes-list-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.notes-list-view__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(79, 137, 255, 0.12), rgba(134, 179, 255, 0.25));
  box-shadow: 0 16px 32px rgba(79, 137, 255, 0.12);
}

.header-text h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #111827;
}

.header-text p {
  margin: 6px 0 0;
  color: rgba(17, 24, 39, 0.72);
  font-size: 14px;
}

.notes-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 0 4px;
  margin-bottom: 12px;
  margin-top: 10px;
}

.notes-search {
  flex: 1;
  --search-radius: 28px;
}

.notes-search__input {
  width: 100%;
  position: relative;
  border-radius: var(--search-radius);
  padding: 2px;
  background: #fff;
  border: 1px solid rgba(86, 100, 132, 0.18);
  transition:
    border-color 0.2s ease,
    transform 0.2s ease;
}

.notes-search__input:focus-within {
  border-color: rgba(79, 109, 255, 0.42);
  transform: translateY(-1px);
}

.notes-search__input :deep(.ant-input-affix-wrapper) {
  position: relative;
  border-radius: calc(var(--search-radius) - 6px);
  border: none;
  background: transparent;
  padding: 12px 26px 12px 34px;
  transition:
    transform 0.24s ease;
}

.notes-search__input :deep(.ant-input-prefix) {
  margin-right: 16px;
  color: rgba(71, 96, 255, 0.8);
  font-size: 18px;
}

.notes-search__input :deep(.ant-input-clear-icon) {
  color: rgba(71, 96, 255, 0.65);
  transition: color 0.2s ease;
}

.notes-search__input :deep(.ant-input-clear-icon:hover) {
  color: rgba(71, 96, 255, 0.95);
}

.notes-search__input :deep(.ant-input) {
  background: transparent;
  font-size: 15px;
  color: #1f2937;
  padding-left: 6px;
}

.notes-search__input :deep(.ant-input::placeholder) {
  color: rgba(31, 41, 55, 0.58);
}

.notes-list-view__placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
  justify-content: center;
  border: 1px dashed rgba(37, 99, 235, 0.2);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.6);
  color: #4b5563;
}

.notes-list-view__placeholder--surface {
  background: rgba(248, 250, 255, 0.72);
  border: 1px solid rgba(121, 145, 255, 0.18);
}

.notes-list-view__empty-hint {
  margin-top: 20px;
  text-align: center;
  color: rgba(55, 65, 81, 0.78);
}

.notes-list-view__empty-hint h3 {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 600;
  color: #3b4bff;
}

.notes-list-view__empty-hint p {
  margin: 0;
  font-size: 14px;
}

.notes-list-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  justify-content: center;
  gap: 14px;
  padding: 6px 0 12px;
  overflow: auto;
  margin-top: 14px;
}

.notes-list-view__card {
  position: relative;
  border-radius: 18px;
  padding: 16px;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: linear-gradient(150deg, #fff8d8, #ffe6ad);
  transition:
    transform 0.2s ease,
    background 0.2s ease;
  cursor: pointer;
  min-height: 180px;
}

.notes-list-view__card--create {
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  align-items: center;
  text-align: center;
  gap: 14px;
  justify-content: center;
  padding: 28px 16px 26px;
  transition:
    transform 0.2s ease,
    border-color 0.2s ease;
}

.notes-list-view__card--create:hover {
  transform: translateY(-4px);
  border-color: rgba(79, 109, 255, 0.35);
}

.notes-list-view__card--create h3 {
  margin: 6px 0 0;
  font-size: 16px;
  font-weight: 600;
  color: #273469;
}

.notes-list-view__card--create p {
  margin: 4px 0 0;
  font-size: 13px;
  color: rgba(39, 52, 105, 0.6);
}

.notes-list-view__card--create.is-loading {
  pointer-events: none;
  opacity: 0.7;
}

.notes-list-view__card--create :deep(.ant-spin) {
  margin-top: 6px;
}

.create-card__badge {
  width: 68px;
  height: 68px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(86, 115, 255, 0.12);
  color: #4058ff;
}

.create-card__badge .anticon {
  font-size: 20px;
}

.notes-list-view__card:focus-visible {
  outline: 2px solid rgba(255, 175, 45, 0.45);
  outline-offset: 3px;
}

.notes-list-view__card.is-active {
  background: linear-gradient(150deg, #fff8d8, #ffe6ad);
  transform: none;
}

.notes-list-view__card:hover {
  transform: translateY(-3px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.card-header__info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #8a5800;
}

.card-header span {
  font-size: 12px;
  color: rgba(138, 88, 0, 0.7);
}

.card-summary {
  margin: 0;
  color: #5f3c00;
  font-size: 14px;
  line-height: 1.6;
  min-height: 42px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.card-tags :deep(.ant-tag) {
  background: rgba(255, 255, 255, 0.6);
  border: none;
  color: #b05d00;
  border-radius: 999px;
  font-weight: 500;
}

.card-menu {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 12px;
  border: none;
  background: transparent;
  color: rgba(138, 88, 0, 0.55);
  cursor: pointer;
  transition:
    background 0.2s ease,
    color 0.2s ease;
}

.card-menu:hover {
  background: rgba(255, 196, 72, 0.22);
  color: #8a5800;
}

.card-menu:active {
  background: rgba(255, 196, 72, 0.3);
}

:deep(.note-card-menu .ant-dropdown-menu) {
  border-radius: 14px;
  padding: 8px;
  background: rgba(255, 253, 240, 0.96);
  box-shadow:
    0 18px 36px rgba(79, 137, 255, 0.14),
    0 6px 16px rgba(189, 156, 58, 0.18);
  border: 1px solid rgba(255, 199, 96, 0.2);
  backdrop-filter: blur(8px);
}

:deep(.note-card-menu .ant-dropdown-menu-item) {
  border-radius: 10px;
  color: #8a5800;
  font-weight: 500;
}

:deep(.note-card-menu .ant-dropdown-menu-item:hover) {
  background: rgba(255, 209, 120, 0.3);
  color: #5f3c00;
}

:deep(.note-modal.ant-modal) {
  border-radius: 32px;
  overflow: hidden;
}

:deep(.note-modal .ant-modal-content) {
  border-radius: 30px;
  padding: 36px 34px 32px;
  background: rgba(248, 250, 255, 0.96);
  box-shadow:
    0 28px 64px rgba(71, 99, 255, 0.22),
    0 12px 32px rgba(71, 99, 255, 0.12);
  backdrop-filter: blur(12px);
}

.note-modal__body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.note-modal__body--delete {
  gap: 28px;
}

.note-modal__avatar {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 35% 30%, rgba(255, 255, 255, 0.9), rgba(83, 106, 255, 0.95));
  color: #fff;
  font-size: 44px;
}

.note-modal__label {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: rgba(55, 65, 81, 0.86);
  align-self: flex-start;
}

.note-modal__input {
  width: 100%;
  border-radius: 18px;
  border: 1px solid rgba(123, 145, 255, 0.35);
  padding: 0;
  overflow: hidden;
  transition:
    border-color 0.22s ease,
    box-shadow 0.22s ease,
    background 0.22s ease;
}

.note-modal__input :deep(.ant-input) {
  border: none;
  padding: 12px 16px;
  font-size: 14px;
  background: transparent;
  color: #1f2937;
}

.note-modal__input :deep(.ant-input::placeholder) {
  color: rgba(31, 41, 55, 0.55);
}

.note-modal__input :deep(.ant-input-clear-icon) {
  color: rgba(79, 101, 255, 0.65);
}

.note-modal__input:focus-within {
  border-color: rgba(79, 137, 255, 0.65);
  box-shadow: 0 0 0 3px rgba(79, 137, 255, 0.18);
  background: rgba(255, 255, 255, 0.98);
}

.note-modal__actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  width: 100%;
}

.note-modal__btn {
  border-radius: 999px !important;
  font-weight: 600 !important;
}

.note-modal__btn--ghost,
.note-modal__btn--primary {
  height: 40px !important;
  padding: 0 28px !important;
  min-width: 102px;
}

.note-modal__btn--ghost {
  background: rgba(122, 146, 255, 0.12) !important;
  border: none !important;
  color: #6175ff !important;
}

.note-modal__btn--ghost:hover {
  background: rgba(122, 146, 255, 0.22) !important;
  color: #4252d8 !important;
}

.note-modal__btn--primary {
  background: linear-gradient(135deg, #547bff, #7f5bff) !important;
  border: none !important;
  color: #fff !important;
}

.note-modal__btn--primary:hover {
  filter: brightness(1.05);
}

.note-modal__btn--danger {
  background: linear-gradient(135deg, #7a6bff, #5f57ff) !important;
  border: none !important;
  color: #fff !important;
  box-shadow: 0 8px 18px rgba(91, 86, 255, 0.32) !important;
  height: 40px !important;
  padding: 0 28px !important;
  min-width: 102px;
}

.note-modal__btn--danger:hover {
  filter: brightness(1.05);
}

.note-modal__delete-title {
  margin: 0;
  font-size: 16px;
  color: rgba(31, 41, 55, 0.88);
  text-align: center;
  line-height: 1.6;
}

.note-modal__note-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(226, 234, 255, 0.56);
  color: #4051c0;
  font-weight: 600;
}

@media (max-width: 768px) {
  .page-content {
    padding: 12px;
  }

  .notes-list-view__header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }

  .notes-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
