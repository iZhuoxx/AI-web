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
                <h3 class="card-title">{{ notebook.title || '未命名笔记' }}</h3>
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
              <span class="card-time">{{ formatDate(notebook.updatedAt) }}</span>
            </div>
          </div>

          <div v-if="isSearching && !notebooks.length" class="notes-list-view__placeholder notes-list-view__placeholder--empty">
            <a-empty description="没有找到相关笔记，换个关键词试试?" />
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
      :closable="false"
      :width="420"
      centered
      destroy-on-close
      wrap-class-name="note-modal note-modal--rename"
      @cancel="handleRenameCancel"
      @afterClose="resetRenameModal"
    >
      <div class="note-modal__body">
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
      :closable="false"
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
/* ==================== 基础布局 ==================== */
.notes-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #ffffff;
}

.page-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 48px 80px;
  box-sizing: border-box;
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
}

/* ==================== 加载和占位状态 ==================== */
.notes-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #5f6368;
  border-radius: 12px;
  padding: 48px 24px;
}

.notes-placeholder--center {
  flex: 1;
  background: #ffffff;
  border: 1px solid #e8eaed;
}

.placeholder-text {
  font-size: 15px;
  font-weight: 400;
  letter-spacing: 0.2px;
}

/* ==================== 笔记列表视图 ==================== */
.notes-list-view {
  display: flex;
  flex-direction: column;
  gap: 40px;
  height: 100%;
}

/* ==================== 头部样式 ==================== */
.notes-list-view__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-bottom: 20px;
  border-bottom: 2px solid #f0f0f0;
}

.header-content h2 {
  margin: 0;
  font-size: 36px;
  font-weight: 300;
  color: #1a1a1a;
  letter-spacing: -0.8px;
}

.header-subtitle {
  margin: 8px 0 0;
  color: #666666;
  font-size: 14px;
  font-weight: 400;
  letter-spacing: 0.3px;
}

/* ==================== 搜索框 ==================== */
.header-actions {
  display: flex;
  align-items: center;
  padding-bottom: 4px;
}

.search-container {
  width: 40px;
  height: 40px;
  transition: width 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
  position: relative;
}

.search-container.is-expanded {
  width: 320px;
}

.search-icon-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid #e0e0e0;
  background: #ffffff;
  color: #666666;
  font-size: 17px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0.0, 0.2, 1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.search-icon-btn:hover {
  background: #fafafa;
  border-color: #d0d0d0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
  transform: translateY(-1px);
}

.search-icon-btn:active {
  background: #f5f5f5;
  transform: translateY(0);
}

.search-input {
  width: 100%;
  height: 100%;
  border-radius: 20px !important;
  border: 1px solid #e0e0e0 !important;
  background: #ffffff !important;
  transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.search-input:hover {
  border-color: #d0d0d0 !important;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.search-input:focus-within {
  border-color: #1a73e8 !important;
  box-shadow: 0 2px 8px rgba(26, 115, 232, 0.25);
}

.search-input :deep(.ant-input-affix-wrapper) {
  border: none !important;
  background: transparent !important;
  padding: 0 16px !important;
  height: 100%;
}

.search-input :deep(.ant-input-prefix) {
  color: #666666;
  margin-right: 10px;
  font-size: 17px;
}

.search-input :deep(.ant-input) {
  background: transparent;
  font-size: 15px;
  color: #1a1a1a;
  font-weight: 400;
}

.search-input :deep(.ant-input::placeholder) {
  color: #999999;
}

.search-input :deep(.ant-input-clear-icon) {
  color: #666666;
}

/* ==================== 占位符和空状态 ==================== */
.notes-list-view__placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
  justify-content: center;
  border: 1px solid #f0f0f0;
  border-radius: 16px;
  background: #ffffff;
  color: #666666;
  min-height: 400px;
}

.notes-list-view__placeholder--empty {
  background: #fafafa;
  border: 1px solid #f0f0f0;
}

.notes-list-view__empty-hint {
  margin-top: 60px;
  text-align: center;
  color: #666666;
}

.notes-list-view__empty-hint h3 {
  margin: 0 0 12px;
  font-size: 22px;
  font-weight: 400;
  color: #1a1a1a;
  letter-spacing: -0.3px;
}

.notes-list-view__empty-hint p {
  margin: 0;
  font-size: 15px;
  color: #666666;
}

/* ==================== 笔记网格 ==================== */
.notes-list-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, 220px);
  gap: 20px;
  padding: 12px 0;
  overflow: auto;
}

/* ==================== 笔记卡片 ==================== */
.notes-list-view__card {
  width: 220px;
  height: 220px;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e8e8e8;
  transition: all 0.25s cubic-bezier(0.4, 0.0, 0.2, 1);
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  position: relative;
  overflow: hidden;
}

.notes-list-view__card:hover {
  border-color: #d0d0d0;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  transform: translateY(-4px);
}

.notes-list-view__card:focus-visible {
  outline: 2px solid #1a73e8;
  outline-offset: 2px;
}

/* ==================== 卡片颜色变体 ==================== */
.card-color--yellow {
  background: #fff8e1;
  border-color: #f5e6b3;
}

.card-color--blue {
  background: #e3f2fd;
  border-color: #b3d9ff;
}

.card-color--green {
  background: #e8f5e9;
  border-color: #b3e6b8;
}

.card-color--purple {
  background: #f3e5f5;
  border-color: #e0b3f0;
}

.card-color--pink {
  background: #fce4ec;
  border-color: #ffb3c9;
}

.card-color--orange {
  background: #ffe0b2;
  border-color: #ffcc80;
}

.card-color--yellow:hover { border-color: #e6d199; }
.card-color--blue:hover { border-color: #99c7ff; }
.card-color--green:hover { border-color: #99d99e; }
.card-color--purple:hover { border-color: #cc99e0; }
.card-color--pink:hover { border-color: #ff99b8; }
.card-color--orange:hover { border-color: #ffb366; }

/* ==================== 创建卡片 ==================== */
.notes-list-view__card--create {
  background: #ffffff;
  border: 2px dashed #d0d0d0;
  align-items: center;
  text-align: center;
  gap: 16px;
  justify-content: center;
  box-shadow: none;
}

.notes-list-view__card--create:hover {
  border-color: #1a73e8;
  border-style: solid;
  background: #f0f7ff;
  box-shadow: 0 4px 16px rgba(26, 115, 232, 0.15);
}

.notes-list-view__card--create h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 500;
  color: #1a1a1a;
  letter-spacing: -0.2px;
}

.notes-list-view__card--create p {
  margin: 0;
  font-size: 14px;
  color: #666666;
}

.notes-list-view__card--create.is-loading {
  pointer-events: none;
  opacity: 0.6;
}

.create-card__icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f0f0;
  color: #666666;
  transition: all 0.25s ease;
}

.notes-list-view__card--create:hover .create-card__icon {
  background: #1a73e8;
  color: #ffffff;
  transform: scale(1.1);
}

.create-card__icon .anticon {
  font-size: 28px;
}

/* ==================== 激活状态 ==================== */
.notes-list-view__card.is-active {
  border-color: #1a73e8;
  box-shadow: 0 4px 16px rgba(26, 115, 232, 0.25);
}

/* ==================== 卡片头部 ==================== */
.card-header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
  flex: 1;
}

.card-title {
  margin: 0;
  font-size: 17px;
  font-weight: 500;
  color: #1a1a1a;
  line-height: 1.5;
  letter-spacing: -0.2px;
  flex: 1;
  min-width: 0;
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 7;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ==================== 卡片时间 ==================== */
.card-time {
  font-size: 12px;
  color: #999999;
  font-weight: 400;
  margin-top: auto;
  padding-top: 8px;
}

/* ==================== 卡片菜单按钮 ==================== */
.card-menu {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: #666666;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.card-menu:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #1a1a1a;
}

.card-menu:active {
  background: rgba(0, 0, 0, 0.1);
}

/* ==================== 下拉菜单 ==================== */
:deep(.note-card-menu .ant-dropdown-menu) {
  border-radius: 12px;
  padding: 8px;
  background: #ffffff;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  border: 1px solid #e8e8e8;
  min-width: 200px;
}

:deep(.note-card-menu .ant-dropdown-menu-item) {
  padding: 10px 16px;
  color: #1a1a1a;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 8px;
  transition: all 0.2s ease;
}

:deep(.note-card-menu .ant-dropdown-menu-item:hover) {
  background: #f5f5f5;
}

:deep(.note-card-menu .ant-dropdown-menu-item-divider) {
  background: #f0f0f0;
  margin: 8px 0;
}

/* ==================== 模态框样式 ==================== */
:deep(.ant-modal-wrap.note-modal .ant-modal) {
  border-radius: 16px !important;
  overflow: hidden;
}

:deep(.ant-modal-wrap.note-modal .ant-modal-content) {
  border-radius: 16px !important;
  padding: 32px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
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
  width: 88px;
  height: 88px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a73e8;
  color: #ffffff;
  font-size: 40px;
  box-shadow: 0 4px 16px rgba(26, 115, 232, 0.25);
}

.note-modal__label {
  font-size: 15px;
  font-weight: 500;
  color: #1a1a1a;
  align-self: flex-start;
  letter-spacing: 0.1px;
}

.note-modal__input {
  width: 100%;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  transition: all 0.3s ease;
}

.note-modal__input :deep(.ant-input) {
  border: none;
  padding: 14px 16px;
  font-size: 15px;
  color: #1a1a1a;
}

.note-modal__input:hover {
  border-color: #d0d0d0;
}

.note-modal__input:focus-within {
  border-color: #1a73e8;
  box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.15);
}

.note-modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  width: 100%;
}

.note-modal__btn {
  border-radius: 8px !important;
  font-weight: 500 !important;
  height: 36px !important;
  padding: 0 20px !important;
  font-size: 14px !important;
  transition: all 0.2s ease !important;
  box-shadow: none !important;
  border: none !important;
}

.note-modal__btn--ghost {
  background: #f5f5f5 !important;
  color: #5f6368 !important;
}

.note-modal__btn--ghost:hover {
  background: #e8e8e8 !important;
  color: #3c4043 !important;
}

.note-modal__btn--primary {
  background: #1a73e8 !important;
  color: #ffffff !important;
}

.note-modal__btn--primary:hover {
  background: #1557b0 !important;
}

.note-modal__btn--danger {
  background: #d93025 !important;
  color: #ffffff !important;
}

.note-modal__btn--danger:hover {
  background: #c5221f !important;
}

.note-modal__delete-title {
  margin: 0;
  font-size: 17px;
  color: #1a1a1a;
  text-align: center;
  line-height: 1.6;
  font-weight: 400;
}

.note-modal__note-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  border-radius: 8px;
  background: #f5f5f5;
  color: #1a1a1a;
  font-weight: 500;
}

/* ==================== 颜色选择器模态框 ==================== */
.note-modal--color :deep(.ant-modal-content) {
  padding: 28px;
  border-radius: 16px;
}

.note-modal__body--color {
  gap: 24px;
}

.color-modal__title {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
  color: #1a1a1a;
  text-align: center;
  letter-spacing: -0.2px;
}

.color-picker {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  width: 100%;
}

.color-picker__item {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 12px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0.0, 0.2, 1);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.color-picker__item:hover {
  transform: scale(1.08);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.color-picker__item.is-selected {
  border-color: #1a73e8;
  box-shadow: 0 4px 16px rgba(26, 115, 232, 0.3);
}

.color-picker__item--yellow { background: #fff8e1; }
.color-picker__item--blue { background: #e3f2fd; }
.color-picker__item--green { background: #e8f5e9; }
.color-picker__item--purple { background: #f3e5f5; }
.color-picker__item--pink { background: #fce4ec; }
.color-picker__item--orange { background: #ffe0b2; }

.color-selected-icon {
  color: #1a73e8;
  font-size: 28px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 1200px) {
  .page-content {
    padding: 40px 60px;
  }
}

@media (max-width: 768px) {
  .page-content {
    padding: 24px;
  }

  .notes-list-view__header {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }

  .header-content h2 {
    font-size: 28px;
  }

  .header-actions {
    width: 100%;
  }

  .search-container.is-expanded {
    width: 100%;
  }

  .notes-list-view__grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
  }

  .notes-list-view__card {
    width: 100%;
  }
}
</style>

<style>
/* Modal 全局样式 - 确保圆角生效 */
.ant-modal-wrap.note-modal .ant-modal {
  border-radius: 16px !important;
  overflow: hidden !important;
}

.ant-modal-wrap.note-modal .ant-modal-content {
  border-radius: 16px !important;
}
</style>
