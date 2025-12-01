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
          <div class="header-content">
            <h2>我的笔记</h2>
            <p class="header-subtitle">{{ headerSubtitle }}</p>
          </div>
          
          <div class="header-actions">
            <div :class="['search-container', { 'is-expanded': searchExpanded }]">
              <button 
                v-if="!searchExpanded" 
                class="search-icon-btn" 
                @click="handleSearchExpand"
                type="button"
              >
                <SearchOutlined />
              </button>
              <a-input
                v-else
                ref="searchInputRef"
                v-model:value="searchQuery"
                size="large"
                allow-clear
                placeholder="搜索标题或摘要..."
                class="search-input"
                @blur="handleSearchBlur"
              >
                <template #prefix>
                  <SearchOutlined />
                </template>
              </a-input>
            </div>
          </div>
        </header>

        <div v-if="listLoading" class="notes-list-view__placeholder">
          <a-spin />
          <span>加载笔记列表...</span>
        </div>

        <div v-else>
          <div v-if="shouldShowCreateCard || notebooks.length" class="notes-list-view__grid">
            <div
              v-if="shouldShowCreateCard"
              key="create-card"
              :class="['notes-list-view__card', 'notes-list-view__card--create', { 'is-loading': creatingCard }]"
              role="button"
              tabindex="0"
              @click="!creatingCard && handleCreateNotebook()"
              @keydown.enter.prevent="!creatingCard && handleCreateNotebook()"
            >
              <div class="create-card__icon">
                <PlusOutlined />
              </div>
              <h3>新建笔记</h3>
              <p>开启属于你的知识库</p>
              <a-spin v-if="creatingCard" size="small" />
            </div>
            <div
              v-for="notebook in notebooks"
              :key="notebook.id"
              :class="['notes-list-view__card', `card-color--${notebook.color || 'yellow'}`, { 'is-active': notebook.id === activeNotebookId }]"
              @click="handleSelectNotebook(notebook.id)"
              @keydown.enter.prevent="handleSelectNotebook(notebook.id)"
              role="button"
              tabindex="0"
            >
              <div class="card-header">
                <div class="card-header__info">
                  <h3>{{ notebook.title || '未命名笔记' }}</h3>
                  <span>{{ formatDate(notebook.updatedAt) }}</span>
                </div>
                <a-dropdown :trigger="['click']" placement="bottomRight" overlay-class-name="note-card-menu">
                  <button class="card-menu" type="button" @click.stop>
                    <MoreOutlined />
                  </button>
                  <template #overlay>
                    <a-menu @click="onNotebookMenuClick(notebook, $event)">
                      <a-menu-item key="rename">
                        <EditOutlined />
                        <span>重命名</span>
                      </a-menu-item>
                      <a-menu-item key="color">
                        <BgColorsOutlined />
                        <span>更改颜色</span>
                      </a-menu-item>
                <a-menu-divider />
                <a-menu-item key="delete">
                  <DeleteOutlined />
                  <span>删除</span>
                </a-menu-item>
                    </a-menu>
                  </template>
                </a-dropdown>
              </div>
              <p class="card-summary">{{ notebook.summary || '暂无摘要，进入笔记继续完善内容～' }}</p>
            </div>
          </div>

          <div v-if="isSearching && !notebooks.length" class="notes-list-view__placeholder notes-list-view__placeholder--surface">
            <a-empty description="没有找到相关笔记，换个关键词试试？" />
          </div>

          <div v-else-if="!isSearching && !notebooks.length" class="notes-list-view__empty-hint">
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
          :maxlength="60"
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

    <a-modal
      v-model:visible="colorModal.open"
      :footer="null"
      :maskClosable="true"
      :width="320"
      centered
      destroy-on-close
      wrap-class-name="note-modal note-modal--color"
      @cancel="handleColorCancel"
      @afterClose="resetColorModal"
    >
      <div class="note-modal__body note-modal__body--color">
        <h3 class="color-modal__title">选择笔记颜色</h3>
        <div class="color-picker">
          <button
            v-for="color in noteColors"
            :key="color.value"
            :class="['color-picker__item', `color-picker__item--${color.value}`, { 'is-selected': (colorModal.note?.color || 'yellow') === color.value }]"
            @click="handleColorSelect(color.value)"
            type="button"
          >
            <CheckOutlined v-if="(colorModal.note?.color || 'yellow') === color.value" class="color-selected-icon" />
          </button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { message } from 'ant-design-vue'
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { BookOutlined, BgColorsOutlined, CheckOutlined, DeleteOutlined, EditOutlined, MoreOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons-vue'
import type { MenuInfo } from 'ant-design-vue/es/menu/src/interface'
import { useAuth } from '@/composables/useAuth'
import { useNotebookStore } from '@/composables/useNotes'
import type { NotebookSummary } from '@/types/notes'

const auth = useAuth()
const notebookStore = useNotebookStore()
const router = useRouter()

const {
  notebooksState,
  fetchNotebookList,
  createNotebookWithFirstNote,
  renameNotebook,
  removeNotebook,
  updateNotebookColor,
  clearActiveNotebook,
} = notebookStore

const listLoading = computed(() => notebooksState.listLoading)
const searchQuery = ref('')
const searchExpanded = ref(false)
const searchInputRef = ref<any>(null)
const creatingCard = ref(false)

const noteColors = [
  { value: 'yellow', label: '浅黄色' },
  { value: 'blue', label: '浅蓝色' },
  { value: 'green', label: '浅绿色' },
  { value: 'purple', label: '浅紫色' },
  { value: 'pink', label: '浅粉色' },
  { value: 'orange', label: '浅橙色' },
]

const sortedNotebooks = computed(() => [...notebooksState.list].sort((a, b) => (a.updatedAt > b.updatedAt ? -1 : 1)))
const filteredNotebooks = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return sortedNotebooks.value
  return sortedNotebooks.value.filter(notebook => {
    const inTitle = notebook.title?.toLowerCase().includes(query)
    const inSummary = notebook.summary?.toLowerCase().includes(query)
    return inTitle || inSummary
  })
})
const notebooks = computed<NotebookSummary[]>(() => filteredNotebooks.value)
const isSearching = computed(() => Boolean(searchQuery.value.trim()))
const shouldShowCreateCard = computed(() => !isSearching.value)
const totalCount = computed(() => notebooksState.list.length)
const activeNotebookId = computed(() => notebooksState.activeNotebook?.id ?? null)
const headerSubtitle = computed(() => {
  if (!isSearching.value) return `共 ${totalCount.value} 条记录`
  return `显示 ${notebooks.value.length} / ${totalCount.value} 条匹配结果`
})

type CardAction = 'rename' | 'delete' | 'color'

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

const colorModal = reactive({
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
        await fetchNotebookList()
      } catch (err) {
        // 错误在 store 内部已有提示
      }
    } else {
      clearActiveNotebook()
    }
  },
  { immediate: true },
)

const handleSearchExpand = () => {
  searchExpanded.value = true
  nextTick(() => {
    searchInputRef.value?.focus()
  })
}

const handleSearchBlur = () => {
  if (!searchQuery.value.trim()) {
    searchExpanded.value = false
  }
}

const handleSelectNotebook = (notebookId: string) => {
  router.push({ name: 'note-editor', params: { id: notebookId } })
}

const handleCreateNotebook = async () => {
  if (creatingCard.value) return
  creatingCard.value = true
  try {
    await createNotebookWithFirstNote()
    const active = notebooksState.activeNotebook
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

const handleCardMenuAction = (notebook: NotebookSummary, action: CardAction) => {
  if (action === 'rename') {
    openRenameModal(notebook)
  } else if (action === 'delete') {
    openDeleteModal(notebook)
  } else if (action === 'color') {
    openColorModal(notebook)
  }
}

const onNotebookMenuClick = (notebook: NotebookSummary, event: MenuInfo) => {
  const actionKey = String(event.key)
  if (actionKey === 'rename' || actionKey === 'delete' || actionKey === 'color') {
    handleCardMenuAction(notebook, actionKey as CardAction)
  }
}

const openRenameModal = (notebook: NotebookSummary) => {
  renameModal.note = notebook
  renameModal.value = notebook.title ?? ''
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
    await renameNotebook(renameModal.note.id, newTitle)
    await fetchNotebookList()
    renameModal.open = false
  } catch (err) {
    return
  } finally {
    renameModal.loading = false
  }
}

const openDeleteModal = (notebook: NotebookSummary) => {
  deleteModal.note = notebook
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
    await removeNotebook(deleteModal.note.id)
    deleteModal.open = false
  } finally {
    deleteModal.loading = false
  }
}

const openColorModal = (notebook: NotebookSummary) => {
  colorModal.note = notebook
  colorModal.open = true
}

const handleColorCancel = () => {
  colorModal.open = false
}

const resetColorModal = () => {
  colorModal.note = null
  colorModal.loading = false
}

const handleColorSelect = async (color: string) => {
  if (!colorModal.note) return
  colorModal.loading = true
  try {
    await updateNotebookColor(colorModal.note.id, color)
    colorModal.open = false
  } catch (err) {
    // error handled in store
  } finally {
    colorModal.loading = false
  }
}
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
  padding: 40px 60px;
  box-sizing: border-box;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.notes-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #5f6368;
  border-radius: 8px;
  padding: 24px;
}

.notes-placeholder--center {
  flex: 1;
  background: #fff;
  border: 1px solid #e8eaed;
}

.placeholder-text {
  font-size: 14px;
}

.notes-list-view {
  display: flex;
  flex-direction: column;
  gap: 32px;
  height: 100%;
}

/* Header Styles - Simple and Advanced */
.notes-list-view__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-bottom: 12px;
  border-bottom: 1px solid #e8eaed;
}

.header-content h2 {
  margin: 0;
  font-size: 32px;
  font-weight: 400;
  color: #202124;
  letter-spacing: -0.5px;
}

.header-subtitle {
  margin: 4px 0 0;
  color: #5f6368;
  font-size: 14px;
  font-weight: 400;
}

/* Compact Search Box */
.header-actions {
  display: flex;
  align-items: center;
  padding-bottom: 2px;
}

.search-container {
  width: 36px;
  height: 36px;
  transition: width 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
  position: relative;
}

.search-container.is-expanded {
  width: 280px;
}

.search-icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid #dadce0;
  background: #fff;
  color: #5f6368;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.search-icon-btn:hover {
  background: #f8f9fa;
  border-color: #c0c4cc;
}

.search-icon-btn:active {
  background: #f1f3f4;
}

.search-input {
  width: 100%;
  height: 100%;
  border-radius: 18px !important;
  border: 1px solid #dadce0 !important;
  background: #fff !important;
  transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.search-input:hover {
  border-color: #c0c4cc !important;
}

.search-input:focus-within {
  border-color: #1a73e8 !important;
  box-shadow: 0 1px 4px rgba(26, 115, 232, 0.25);
}

.search-input :deep(.ant-input-affix-wrapper) {
  border: none !important;
  background: transparent !important;
  padding: 0 12px !important;
  height: 100%;
}

.search-input :deep(.ant-input-prefix) {
  color: #5f6368;
  margin-right: 8px;
  font-size: 16px;
}

.search-input :deep(.ant-input) {
  background: transparent;
  font-size: 14px;
  color: #202124;
}

.search-input :deep(.ant-input::placeholder) {
  color: #80868b;
}

.search-input :deep(.ant-input-clear-icon) {
  color: #5f6368;
}

.notes-list-view__placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
  justify-content: center;
  border: 1px solid #e8eaed;
  border-radius: 8px;
  background: #fff;
  color: #5f6368;
}

.notes-list-view__placeholder--surface {
  background: #f8f9fa;
  border: 1px solid #e8eaed;
}

.notes-list-view__empty-hint {
  margin-top: 40px;
  text-align: center;
  color: #5f6368;
}

.notes-list-view__empty-hint h3 {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 400;
  color: #202124;
}

.notes-list-view__empty-hint p {
  margin: 0;
  font-size: 14px;
}

/* Constant Size Grid - Smaller notebooks */
.notes-list-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, 200px);
  gap: 16px;
  padding: 8px 0;
  overflow: auto;
}

/* Note Cards - Constant Size with Google-inspired Colors */
.notes-list-view__card {
  width: 200px;
  height: 200px;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px solid #e8eaed;
  transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
  cursor: pointer;
}

.notes-list-view__card:hover {
  border-color: #d0d3d7;
}

.notes-list-view__card:focus-visible {
  outline: 2px solid #1a73e8;
  outline-offset: 2px;
}

/* Color Variants - Google Keep Style */
.card-color--yellow {
  background: #fff8e1;
}

.card-color--blue {
  background: #e3f2fd;
}

.card-color--green {
  background: #e8f5e9;
}

.card-color--purple {
  background: #f3e5f5;
}

.card-color--pink {
  background: #fce4ec;
}

.card-color--orange {
  background: #ffe0b2;
}

/* Create Card */
.notes-list-view__card--create {
  background: #fff;
  border: 1px solid #e8eaed;
  align-items: center;
  text-align: center;
  gap: 12px;
  justify-content: center;
}

.notes-list-view__card--create:hover {
  border-color: #1a73e8;
  background: #f8f9fa;
}

.notes-list-view__card--create h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #202124;
}

.notes-list-view__card--create p {
  margin: 0;
  font-size: 13px;
  color: #5f6368;
}

.notes-list-view__card--create.is-loading {
  pointer-events: none;
  opacity: 0.6;
}

.create-card__icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f3f4;
  color: #5f6368;
}

.create-card__icon .anticon {
  font-size: 24px;
}

.notes-list-view__card.is-active {
  border-color: #1a73e8;
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: flex-start;
}

.card-header__info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #202124;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-header span {
  font-size: 12px;
  color: #5f6368;
}

.card-summary {
  margin: 0;
  color: #202124;
  font-size: 14px;
  line-height: 1.5;
  flex: 1;
  display: -webkit-box;
  line-clamp: 5;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-menu {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: #5f6368;
  cursor: pointer;
  transition: background 0.2s ease;
  flex-shrink: 0;
}

.card-menu:hover {
  background: rgba(0, 0, 0, 0.06);
}

.card-menu:active {
  background: rgba(0, 0, 0, 0.1);
}

/* Dropdown Menu */
:deep(.note-card-menu .ant-dropdown-menu) {
  border-radius: 8px;
  padding: 8px 0;
  background: #fff;
  box-shadow: 0 1px 2px 0 rgba(60, 64, 67, 0.3), 0 2px 6px 2px rgba(60, 64, 67, 0.15);
  border: none;
  min-width: 200px;
}

:deep(.note-card-menu .ant-dropdown-menu-item) {
  padding: 8px 16px;
  color: #202124;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
}

:deep(.note-card-menu .ant-dropdown-menu-item:hover) {
  background: #f1f3f4;
}

:deep(.note-card-menu .ant-dropdown-menu-item-group-title) {
  padding: 8px 16px;
  color: #5f6368;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

:deep(.note-card-menu .ant-dropdown-menu-item-divider) {
  background: #e8eaed;
  margin: 4px 0;
}

/* Color Picker Modal */
.note-modal--color :deep(.ant-modal-content) {
  padding: 24px;
}

.note-modal__body--color {
  gap: 20px;
}

.color-modal__title {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #202124;
  text-align: center;
}

.color-picker {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  width: 100%;
}

.color-picker__item {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 8px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.color-picker__item:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.color-picker__item.is-selected {
  border-color: #1a73e8;
  box-shadow: 0 0 0 1px #1a73e8;
}

.color-picker__item--yellow { background: #fff8e1; }
.color-picker__item--blue { background: #e3f2fd; }
.color-picker__item--green { background: #e8f5e9; }
.color-picker__item--purple { background: #f3e5f5; }
.color-picker__item--pink { background: #fce4ec; }
.color-picker__item--orange { background: #ffe0b2; }

.color-selected-icon {
  color: #1a73e8;
  font-size: 24px;
}

/* Modal Styles */
:deep(.note-modal.ant-modal) {
  border-radius: 8px;
}

:deep(.note-modal .ant-modal-content) {
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 3px 0 rgba(60, 64, 67, 0.3), 0 4px 8px 3px rgba(60, 64, 67, 0.15);
}

.note-modal__body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.note-modal__body--delete {
  gap: 24px;
}

.note-modal__avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a73e8;
  color: #fff;
  font-size: 36px;
}

.note-modal__label {
  font-size: 14px;
  font-weight: 500;
  color: #202124;
  align-self: flex-start;
}

.note-modal__input {
  width: 100%;
  border-radius: 4px;
  border: 1px solid #dadce0;
}

.note-modal__input :deep(.ant-input) {
  border: none;
  padding: 12px 16px;
  font-size: 14px;
  color: #202124;
}

.note-modal__input:focus-within {
  border-color: #1a73e8;
  box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
}

.note-modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  width: 100%;
}

.note-modal__btn {
  border-radius: 4px !important;
  font-weight: 500 !important;
  height: 36px !important;
  padding: 0 24px !important;
}

.note-modal__btn--ghost {
  background: transparent !important;
  border: none !important;
  color: #1a73e8 !important;
}

.note-modal__btn--ghost:hover {
  background: rgba(26, 115, 232, 0.08) !important;
}

.note-modal__btn--primary {
  background: #1a73e8 !important;
  border: none !important;
  color: #fff !important;
}

.note-modal__btn--primary:hover {
  background: #1765cc !important;
}

.note-modal__btn--danger {
  background: #d93025 !important;
  border: none !important;
  color: #fff !important;
}

.note-modal__btn--danger:hover {
  background: #c5221f !important;
}

.note-modal__delete-title {
  margin: 0;
  font-size: 16px;
  color: #202124;
  text-align: center;
  line-height: 1.5;
}

.note-modal__note-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f1f3f4;
  color: #202124;
  font-weight: 500;
}

@media (max-width: 768px) {
  .page-content {
    padding: 20px;
  }

  .notes-list-view__header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
  }

  .search-container.is-expanded {
    width: 100%;
  }

  .notes-list-view__grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }

  .notes-list-view__card {
    width: 100%;
  }
}
</style>
