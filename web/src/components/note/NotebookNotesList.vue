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
      <Draggable
        v-else
        v-model="workingNotes"
        tag="ul"
        class="notes-list"
        item-key="id"
        :animation="220"
        :ghost-class="'note-item--ghost'"
        :chosen-class="'note-item--chosen'"
        :drag-class="'note-item--dragging'"
        :handle="'.drag-handle'"
        :fallback-on-body="true"
        :force-fallback="true"
        :fallback-class="'note-item--fallback'"
        :swap-threshold="0.55"
        :move="handleMove"
        @start="onDragStart"
        @change="onListChange"
        @end="onDragEnd"
      >
        <template #item="{ element }">
          <li
            :key="element.id"
            :data-id="element.id"
            :class="['note-item', { active: element.id === selectedId, pending: element.isPlaceholder }]"
            @click="!element.isPlaceholder && $emit('select', element.id)"
          >
            <div class="item-main">
              <button
                v-if="!element.isPlaceholder"
                class="drag-handle"
                type="button"
                title="拖拽调整排序"
                @click.stop
              >
                <GripVerticalIcon class="drag-icon" />
              </button>
              <Loader2Icon v-if="element.isPlaceholder" class="item-icon spin" />
              <FileTextIcon v-else class="item-icon" />
              <div class="item-title">{{ resolveTitle(element.title) }}</div>
            </div>
            <div v-if="!element.isPlaceholder" class="item-actions">
              <a-dropdown :trigger="['click']" placement="bottomRight" overlay-class-name="rounded-dropdown note-actions-dropdown">
                <button class="more-btn" type="button" @click.stop>
                  <MoreVerticalIcon class="more-icon" />
                </button>
                <template #overlay>
                  <a-menu @click="onMenuClick(element, $event)">
                    <a-menu-item key="delete" class="delete-menu-item">
                      <template #icon>
                        <DeleteOutlined />
                      </template>
                      删除
                    </a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
            </div>
          </li>
        </template>
      </Draggable>
    </a-spin>
  </a-card>
  <ConfirmModal
    v-model="deleteModal.open"
    variant="danger"
    confirm-text="删除"
    cancel-text="取消"
    :on-confirm="handleDeleteConfirm"
  >
    <template v-if="deleteModal.note">
      要删除
      <span class="item-name-box">
        <FileTextIcon class="delete-modal__note-icon" />
        <span>{{ resolveTitle(deleteModal.note.title || '') }}</span>
      </span>
      吗？
    </template>
  </ConfirmModal>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch, defineComponent, type SlotsType } from 'vue'
import { BotIcon, FileTextIcon, GripVerticalIcon, Loader2Icon, MoreVerticalIcon, PlusIcon } from 'lucide-vue-next'
import { DeleteOutlined } from '@ant-design/icons-vue'
import type { MenuInfo } from 'ant-design-vue/es/menu/src/interface'
import DraggableComponent from 'vuedraggable'
import type { SortableEvent } from 'sortablejs'
import ConfirmModal from '@/components/common/ConfirmModal.vue'
import type { NoteItem } from '@/types/notes'
import { useNotebookStore } from '@/composables/useNotes'

const Draggable = DraggableComponent as unknown as any

const props = defineProps<{
  notes: ReadonlyArray<NoteItem>
  selectedId: string | null
  notebookTitle?: string | null
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'select', noteId: string): void
  (e: 'create'): void
  (e: 'ai-report'): void
  (e: 'reorder', orderedIds: string[]): void
  (e: 'reorder-preview', orderedIds: string[] | null): void
}>()

const notebookStore = useNotebookStore()
const loading = computed(() => props.loading === true)
const draggingId = ref<string | null>(null)
const dragStartOrder = ref<string[]>([])
const workingNotes = ref<NoteItem[]>([])

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
  await notebookStore.removeNoteFromActiveNotebook(deleteModal.note.id)
}

const syncWorkingNotes = (next: ReadonlyArray<NoteItem>) => {
  workingNotes.value = [...next]
}

watch(
  () => props.notes,
  (next) => syncWorkingNotes(next),
  { immediate: true, deep: true },
)

const collectOrderedIds = (source: ReadonlyArray<NoteItem> = workingNotes.value) =>
  source.filter(note => !note.isPlaceholder).map(note => note.id)

type DragMoveEvent = {
  draggedContext?: { element?: NoteItem }
  relatedContext?: { element?: NoteItem }
}

type DragStartEvent = Partial<SortableEvent> & { item?: HTMLElement | null } & Record<string, any>

const handleMove = (event: DragMoveEvent) => {
  const dragged: NoteItem | undefined = event?.draggedContext?.element
  const related: NoteItem | undefined = event?.relatedContext?.element
  if (dragged?.isPlaceholder || related?.isPlaceholder) return false
  return true
}

const onDragStart = (event: DragStartEvent) => {
  const rawId = event.item?.dataset?.id
  draggingId.value = rawId ?? null
  dragStartOrder.value = collectOrderedIds(props.notes)
}

const onListChange = () => {
  if (!draggingId.value) return
  const orderedIds = collectOrderedIds()
  emit('reorder-preview', orderedIds)
}

const onDragEnd = () => {
  const orderedIds = collectOrderedIds()
  const initialOrder = dragStartOrder.value
  draggingId.value = null
  dragStartOrder.value = []
  if (!orderedIds.length) {
    emit('reorder-preview', null)
    return
  }
  if (orderedIds.join('|') === initialOrder.join('|')) {
    emit('reorder-preview', null)
    return
  }
  emit('reorder', orderedIds)
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
  transition: background-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
  user-select: none;
}

.note-item:hover {
  background: rgba(37, 99, 235, 0.08);
}

.note-item.active {
  background: rgba(37, 99, 235, 0.12);
}

.note-item.pending {
  cursor: default;
  background: #f8fafc;
}

.note-item.pending .item-title {
  color: #1d4ed8;
}

.note-item.pending .item-icon {
  color: #1d4ed8;
}

.note-item--ghost {
  opacity: 0.45;
  background: rgba(37, 99, 235, 0.08);
  border: 1px dashed rgba(37, 99, 235, 0.35);
}

.note-item--dragging {
  cursor: grabbing !important;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
}

.note-item--chosen {
  transform: scale(1.01);
}

:global(.note-item--fallback) {
  opacity: 0 !important;
  visibility: hidden !important;
  pointer-events: none !important;
}

.item-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.drag-handle {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  cursor: grab;
  border-radius: 8px;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: background-color 0.18s ease, color 0.18s ease, opacity 0.16s ease, visibility 0.16s ease;
}

.drag-handle:active {
  cursor: grabbing;
}

.drag-handle:hover {
  background: rgba(37, 99, 235, 0.08);
}

.drag-icon {
  width: 18px;
  height: 18px;
  color: #9ca3af;
}

.item-icon {
  width: 18px;
  height: 18px;
  margin-top: 1px;
  color: #2563eb;
  flex-shrink: 0;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.item-title {
  font-weight: 500;
  font-size: 15px;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 0.16s ease, visibility 0.16s ease;
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

.note-item:hover .drag-handle,
.note-item:focus-within .drag-handle,
.note-item--dragging .drag-handle {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}

.note-item:hover .item-actions,
.note-item:focus-within .item-actions,
.note-item--dragging .item-actions {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}

/* Dropdown menu container */
:deep(.note-actions-dropdown .ant-dropdown-menu) {
  min-width: 170px;
  padding: 6px 0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
}

/* Menu item base styles */
:deep(.note-actions-dropdown .ant-dropdown-menu-item) {
  padding: 10px 14px;
  line-height: 1.5;
  font-size: 14px;
}

:deep(.note-actions-dropdown .ant-dropdown-menu-item .ant-dropdown-menu-title-content) {
  display: flex;
  align-items: center;
}

/* Icon styles */
:deep(.note-actions-dropdown .ant-dropdown-menu-item .anticon) {
  font-size: 14px;
  margin-right: 12px;
}

/* Delete option styles */
:deep(.note-actions-dropdown .delete-menu-item) {
  color: #ff4d4f;
}

:deep(.note-actions-dropdown .delete-menu-item:hover) {
  color: #ff4d4f;
  background-color: rgba(0, 0, 0, 0.04) !important;
}

:deep(.note-actions-dropdown .delete-menu-item .anticon) {
  color: #ff4d4f;
}

:deep(.note-delete-modal .ant-modal-content) {
  border-radius: 10px;
  padding: 20px;
}

.delete-modal__note-icon {
  width: 16px;
  height: 16px;
  color: #2563eb;
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
</style>
