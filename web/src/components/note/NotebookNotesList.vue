<template>
  <a-card
    class="note-list-panel"
    :bordered="false"
    :body-style="{ padding: 0, height: '100%' }"
  >
    <template #title>
      <div class="panel-header">
        <button class="new-note-btn" type="button" @click="$emit('ai-report')">
          <BotIcon class="icon" />
          AI 报告
        </button>
        <button class="new-note-btn" type="button" @click="$emit('create')">
          <PlusIcon class="icon" />
          添加笔记
        </button>
      </div>
    </template>
    <a-spin :spinning="loading">
      <div v-if="!notes.length" class="empty-state">
        <FileTextIcon class="empty-icon" />
        <p>笔记本中还没有笔记</p>
        <p class="hint">点击右上角「新增笔记」开始创建</p>
      </div>
      <ul v-else class="notes-list">
        <li
          v-for="note in notes"
          :key="note.id"
          :class="['note-item', { active: note.id === selectedId }]"
          @click="$emit('select', note.id)"
        >
          <div class="item-main">
            <FileTextIcon class="item-icon" />
            <div class="item-title">{{ resolveTitle(note.title) }}</div>
          </div>
          <div class="item-actions">
            <a-dropdown :trigger="['click']" placement="bottomRight" overlay-class-name="note-actions-dropdown">
              <button class="more-btn" type="button" @click.stop>
                <MoreVerticalIcon class="more-icon" />
              </button>
              <template #overlay>
                <a-menu @click="onMenuClick(note, $event)">
                  <a-menu-item key="delete">
                    <Trash2Icon class="menu-icon" />
                    <span>删除</span>
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </div>
        </li>
      </ul>
    </a-spin>
  </a-card>
  <a-modal
    v-model:visible="deleteModal.open"
    :footer="null"
    :maskClosable="false"
    :width="360"
    centered
    destroy-on-close
    wrap-class-name="note-delete-modal"
    @cancel="handleDeleteCancel"
    @afterClose="resetDeleteModal"
  >
    <div class="delete-modal__body">
      <p class="delete-modal__title">
        要删除
        <span class="delete-modal__note">
          <FileTextIcon class="delete-modal__note-icon" />
          <span>{{ resolveTitle(deleteModal.note?.title || '') }}</span>
        </span>
        吗？
      </p>
      <div class="delete-modal__actions">
        <a-button class="delete-modal__btn" @click="handleDeleteCancel">取消</a-button>
        <a-button
          type="primary"
          danger
          class="delete-modal__btn delete-modal__btn--danger"
          :loading="deleteModal.loading"
          @click="handleDeleteConfirm"
        >
          删除
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { BotIcon, FileTextIcon, MoreVerticalIcon, PlusIcon, Trash2Icon } from 'lucide-vue-next'
import type { MenuInfo } from 'ant-design-vue/es/menu/src/interface'
import type { NoteItem } from '@/types/notes'
import { useNotebookStore } from '@/composables/useNotes'

const props = defineProps<{
  notes: ReadonlyArray<NoteItem>
  selectedId: string | null
  notebookTitle?: string | null
  loading?: boolean
}>()

defineEmits<{
  (e: 'select', noteId: string): void
  (e: 'create'): void
  (e: 'ai-report'): void
}>()

const notebookStore = useNotebookStore()
const loading = computed(() => props.loading === true)

const resolveTitle = (value: string) => value?.trim() || '未命名笔记'

const deleteModal = reactive({
  open: false,
  loading: false,
  note: null as NoteItem | null,
})

const onMenuClick = (note: NoteItem, event: MenuInfo) => {
  if (String(event.key) === 'delete') {
    deleteModal.note = note
    deleteModal.open = true
  }
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
    await notebookStore.removeNoteFromActiveNotebook(deleteModal.note.id)
    deleteModal.open = false
  } catch (err) {
    // 错误提示由 store 统一处理
  } finally {
    deleteModal.loading = false
  }
}
</script>

<style scoped>
.note-list-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 22px;
  overflow: hidden;
  background: #fff;
  border: none;
  box-shadow: none;
}

.note-list-panel :deep(.ant-spin-nested-loading),
.note-list-panel :deep(.ant-spin-container) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  width: 100%;
}

.header-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.heading {
  font-weight: 600;
  font-size: 16px;
}

.subheading {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}

.new-note-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.6);
  background: #fff;
  color: #1f2937;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: color 0.2s ease, background 0.2s ease, border-color 0.2s ease, transform 0.15s ease;
}

.new-note-btn:hover {
  transform: translateY(-1px);
  background: rgba(37, 99, 235, 0.14);
  color: #1d4ed8;
  border-color: rgba(37, 99, 235, 0.4);
}

.new-note-btn:active {
  transform: translateY(0);
  background: rgba(37, 99, 235, 0.25);
  color: #1d4ed8;
}

.icon {
  width: 14px;
  height: 14px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: rgba(0, 0, 0, 0.45);
  text-align: center;
  padding: 0 16px;
}

.empty-icon {
  width: 32px;
  height: 32px;
  opacity: 0.35;
}

.hint {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.35);
}

.notes-list {
  list-style: none;
  padding: 8px;
  margin: 0;
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.note-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
  border-radius: 12px;
  transition: background-color 0.2s ease, box-shadow 0.2s ease;
}

.note-item:hover {
  background: rgba(37, 99, 235, 0.08);
}

.note-item.active {
  background: rgba(37, 99, 235, 0.12);
}

.item-main {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.item-icon {
  width: 16px;
  height: 16px;
  margin-top: 1px;
  color: #2563eb;
  flex-shrink: 0;
}

.item-title {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.more-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  padding: 0;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.more-btn:hover {
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
}

.more-icon {
  width: 16px;
  height: 16px;
}

:deep(.note-actions-dropdown .ant-dropdown-menu) {
  padding: 6px 0;
  border-radius: 10px;
}

:deep(.note-actions-dropdown .ant-dropdown-menu-item) {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
}

.menu-icon {
  width: 16px;
  height: 16px;
  color: #dc2626;
}

:deep(.note-delete-modal .ant-modal-content) {
  border-radius: 10px;
  padding: 20px;
}

.delete-modal__body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
}

.delete-modal__title {
  margin: 0;
  text-align: center;
  color: #111827;
  line-height: 1.5;
}

.delete-modal__note {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 6px;
  background: #f3f4f6;
  color: #111827;
  font-weight: 600;
}

.delete-modal__note-icon {
  width: 16px;
  height: 16px;
  color: #2563eb;
}

.delete-modal__actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  width: 100%;
}

.delete-modal__btn {
  min-width: 80px;
}

.delete-modal__btn--danger {
  background: #dc2626;
  border-color: #dc2626;
}

.delete-modal__btn--danger:hover {
  background: #b91c1c;
  border-color: #b91c1c;
}
</style>
