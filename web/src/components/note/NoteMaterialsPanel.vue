<template>
  <a-card
    class="materials-panel"
    :bordered="false"
    :body-style="{ height: '100%', padding: '0 16px 16px' }"
  >
    <template #title>
      <div class="panel-title">
        <div>
          <div class="heading">资料库</div>
          <div class="subheading">已同步至数据库的课件、作业与阅读材料</div>
        </div>
      </div>
    </template>
    <template #extra>
      <a-button type="primary" size="small" :loading="uploading" @click="handleUploadClick">
        <UploadIcon class="icon" />
        上传资料
      </a-button>
      <input ref="fileInput" type="file" class="file-input" @change="handleFileChange" />
    </template>
    <a-spin :spinning="loading || uploading">
      <div class="materials-body">
        <div v-if="!attachments.length" class="empty">
          <UploadIcon class="icon-large" />
          <p>当前还没有上传资料</p>
          <p class="tip">支持 PDF / 图片 / 音视频 / 其他文件类型</p>
        </div>
        <div v-else class="materials-list">
          <div
            v-for="item in attachments"
            :key="item.id"
            class="material-item"
          >
            <div class="material-info">
              <component :is="resolveIcon(item.kind)" class="item-icon" />
              <div class="text">
                <div class="name">{{ resolveName(item) }}</div>
                <div class="meta">
                  {{ resolveKindLabel(item.kind) }}
                  <template v-if="item.bytes">&nbsp;· {{ formatBytes(item.bytes) }}</template>
                  <template v-if="item.createdAt">&nbsp;· {{ formatDate(item.createdAt) }}</template>
                </div>
                <div v-if="item.summary" class="summary">{{ item.summary }}</div>
              </div>
            </div>
            <div class="material-actions">
              <a-button
                type="text"
                size="small"
                :loading="downloading === item.id"
                @click="handleDownload(item.id)"
              >
                <DownloadIcon class="action-icon" />
                下载
              </a-button>
            </div>
          </div>
        </div>
      </div>
    </a-spin>
  </a-card>
</template>

<script setup lang="ts">
import { message } from 'ant-design-vue'
import { computed, ref } from 'vue'
import {
  AudioLinesIcon,
  DownloadIcon,
  FileIcon,
  FileTextIcon,
  ImageIcon,
  UploadIcon,
  VideoIcon,
} from 'lucide-vue-next'
import type { NoteAttachment } from '@/types/notes'
import { getAttachmentDownloadUrl, presignAttachmentUpload } from '@/services/api'

const props = defineProps<{
  attachments: ReadonlyArray<NoteAttachment>
  notebookId: string | null
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'updated'): void
}>()

const uploading = ref(false)
const downloading = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

const loading = computed(() => props.loading === true)

const handleUploadClick = () => {
  if (!props.notebookId) {
    message.warning('请先选择一个笔记本，再上传资料')
    return
  }
  fileInput.value?.click()
}

const handleFileChange = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  if (!props.notebookId) {
    message.warning('请先选择一个笔记本，再上传资料')
    target.value = ''
    return
  }

  uploading.value = true
  try {
    const response = await presignAttachmentUpload({
      notebookId: props.notebookId,
      filename: file.name,
      contentType: file.type || undefined,
      bytes: file.size,
    })
    const formData = new FormData()
    Object.entries(response.upload.fields ?? {}).forEach(([key, value]) => {
      formData.append(key, value as string)
    })
    formData.append('file', file)
    const uploadResult = await fetch(response.upload.url, {
      method: 'POST',
      body: formData,
    })
    if (!uploadResult.ok) throw new Error('上传文件到对象存储失败')
    message.success('资料上传成功')
    emit('updated')
  } catch (err: any) {
    const error = err?.message || '上传失败，请稍后再试'
    message.error(error)
  } finally {
    uploading.value = false
    if (target) target.value = ''
  }
}

const handleDownload = async (id: string) => {
  downloading.value = id
  try {
    const { url } = await getAttachmentDownloadUrl(id)
    window.open(url, '_blank', 'noopener')
  } catch (err: any) {
    const error = err?.message || '获取下载链接失败'
    message.error(error)
  } finally {
    downloading.value = downloading.value === id ? null : downloading.value
  }
}

const resolveIcon = (kind: string) => {
  switch (kind) {
    case 'pdf':
      return FileTextIcon
    case 'image':
      return ImageIcon
    case 'audio':
      return AudioLinesIcon
    case 'video':
      return VideoIcon
    default:
      return FileIcon
  }
}

const resolveKindLabel = (kind: string) => {
  switch (kind) {
    case 'pdf':
      return 'PDF'
    case 'image':
      return '图像'
    case 'audio':
      return '音频'
    case 'video':
      return '视频'
    case 'file':
      return '文件'
    default:
      return '其他'
  }
}

const resolveName = (item: NoteAttachment) => {
  if (item.meta && typeof item.meta === 'object' && 'filename' in item.meta) {
    const name = (item.meta as Record<string, any>).filename
    if (typeof name === 'string' && name.trim()) return name
  }
  const key = item.objectKey || ''
  const parts = key.split('/')
  return parts[parts.length - 1] || '未命名文件'
}

const formatBytes = (value: number) => {
  if (!value) return ''
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = value
  let index = 0
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024
    index += 1
  }
  return `${size.toFixed(size < 10 && index > 0 ? 1 : 0)} ${units[index]}`
}

const formatDate = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.materials-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 22px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.heading {
  font-weight: 600;
}

.subheading {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}

.icon {
  width: 14px;
  height: 14px;
  margin-right: 6px;
}

.file-input {
  display: none;
}

.materials-body {
  flex: 1;
  overflow-y: auto;
}

.materials-list {
  display: flex;
  flex-direction: column;
}

.empty {
  height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: rgba(0, 0, 0, 0.45);
  text-align: center;
}

.tip {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.35);
}

.icon-large {
  width: 28px;
  height: 28px;
  opacity: 0.4;
}

.material-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.material-info {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex: 1;
}

.item-icon {
  width: 24px;
  height: 24px;
  color: #1677ff;
  margin-top: 2px;
}

.text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.name {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.meta {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}

.summary {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.55);
  line-height: 1.5;
}

.material-actions {
  display: flex;
  align-items: center;
}

.action-icon {
  width: 14px;
  height: 14px;
  margin-right: 4px;
}
</style>
