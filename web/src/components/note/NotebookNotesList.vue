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
          新增笔记
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
          <div class="item-top">
            <FileTextIcon class="item-icon" />
            <div class="item-text">
              <div class="item-title">{{ resolveTitle(note.title) }}</div>
              <div class="item-preview">{{ buildPreview(note.content) }}</div>
            </div>
          </div>
          <ChevronRightIcon class="chevron" />
        </li>
      </ul>
    </a-spin>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BotIcon, ChevronRightIcon, FileTextIcon, PlusIcon } from 'lucide-vue-next'
import type { NoteItem } from '@/types/notes'

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

const loading = computed(() => props.loading === true)

const stripHtml = (value: string) => {
  const doc = new DOMParser().parseFromString(value, 'text/html')
  return doc.body.textContent || ''
}

const buildPreview = (value: string) => {
  const plain = stripHtml(value)
  return plain.length > 54 ? `${plain.slice(0, 54)}…` : plain || '暂无内容'
}

const resolveTitle = (value: string) => value?.trim() || '未命名笔记'
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
  padding: 0;
  margin: 0;
  flex: 1;
  overflow-y: auto;
}

.note-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  border-bottom: 1px solid rgba(5, 5, 5, 0.06);
}

.note-item:last-child {
  border-bottom: none;
}

.note-item:hover {
  background: rgba(37, 99, 235, 0.08);
}

.note-item.active {
  background: rgba(37, 99, 235, 0.12);
  border-left: 3px solid #2563eb;
  padding-left: 13px;
}

.item-top {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex: 1;
}

.item-icon {
  width: 18px;
  height: 18px;
  margin-top: 2px;
  color: #2563eb;
  flex-shrink: 0;
}

.item-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.item-title {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-preview {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  line-height: 1.4;
  max-height: 2.8em;
  overflow: hidden;
}

.chevron {
  width: 16px;
  height: 16px;
  color: rgba(0, 0, 0, 0.3);
  flex-shrink: 0;
}
</style>
