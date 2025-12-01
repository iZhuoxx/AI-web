<template>
  <a-card
    class="materials-panel"
    :bordered="false"
    :body-style="{ height: '100%', padding: '0' }"
  >
    <div class="materials-body">
      <template v-if="!previewingAttachment">
        <div class="materials-scroll">
          <div v-if="!sortedAttachments.length" class="empty">
            <UploadIcon class="icon-large" />
            <p>当前还没有上传资料</p>
            <p class="tip">支持 PDF / 图片 / 音视频 / 其他文件类型</p>
          </div>
          <div v-else class="materials-list">
            <div
              v-for="item in sortedAttachments"
              :key="item.id"
              class="material-item"
              :class="{ 'material-item--active': item.id === previewingId }"
              @click="openPreview(item)"
            >
              <div class="material-info">
                <component :is="resolveFileIcon(item)" class="item-icon" />
                <div class="name">{{ resolveName(item) }}</div>
              </div>
              <div class="material-actions">
                <a-dropdown
                  :trigger="['click']"
                  placement="bottomRight"
                  overlay-class-name="materials-actions-dropdown"
                >
                  <button class="more-btn" type="button" @click.stop>
                    <MoreVerticalIcon class="more-icon" />
                  </button>
                  <template #overlay>
                    <a-menu @click="onMenuClick(item, $event)">
                      <a-menu-item key="rename">
                        <PencilIcon class="menu-icon" />
                        <span>重命名</span>
                      </a-menu-item>
                      <a-menu-item key="delete">
                        <Trash2Icon class="menu-icon" />
                        <span>移除</span>
                      </a-menu-item>
                      <a-menu-divider />
                      <a-menu-item key="download" :disabled="downloading === item.id">
                        <DownloadIcon class="menu-icon" />
                        <span>下载</span>
                      </a-menu-item>
                    </a-menu>
                  </template>
                </a-dropdown>
              </div>
            </div>
          </div>
        </div>
      </template>
      <template v-else>
        <div class="preview-panel" :class="{ 'preview-panel--pdf': isPdf(previewingAttachment) }">
          <div v-if="!isPdf(previewingAttachment)" class="preview-header">
            <button class="back-btn" type="button" @click="exitPreview">
              <ArrowLeftIcon class="back-icon" />
              返回
            </button>
            <div class="preview-title">
              <component :is="resolveFileIcon(previewingAttachment)" class="header-icon" />
              <div class="preview-text">
                <div class="preview-name">{{ resolveName(previewingAttachment) }}</div>
                <div class="preview-meta">
                  {{ resolveMimeLabel(previewingAttachment.mime) }}
                  <template v-if="previewingAttachment.bytes"
                    >&nbsp;· {{ formatBytes(previewingAttachment.bytes) }}</template
                  >
                  <template v-if="previewingAttachment.createdAt"
                    >&nbsp;· {{ formatDate(previewingAttachment.createdAt) }}</template
                  >
                </div>
              </div>
            </div>
            <div class="preview-actions">
              <a-button
                size="small"
                :loading="downloading === previewingAttachment.id"
                @click="handleDownload(previewingAttachment.id)"
              >
                <DownloadIcon class="action-icon" />
                下载
              </a-button>
            </div>
          </div>
          <div class="preview-body">
            <div v-if="previewLoading" class="preview-loading">
              <a-spin />
            </div>
            <div v-else-if="previewError" class="preview-error">{{ previewError }}</div>
            <template v-else-if="previewUrl && previewingAttachment">
              <AttachmentPdfViewer
                v-if="isPdf(previewingAttachment)"
                :source="previewUrl"
                :focus-text="focusText || null"
                :focus-trigger="focusTrigger"
                show-back
                @download="handleDownload(previewingAttachment.id)"
                @back="exitPreview"
              />
              <AttachmentDocViewer
                v-else-if="isWordDocument(previewingAttachment)"
                :source="previewUrl"
              />
              <div v-else-if="isImage(previewingAttachment)" class="preview-content image">
                <img :src="previewUrl" :alt="resolveName(previewingAttachment)" />
              </div>
              <div v-else-if="isVideo(previewingAttachment)" class="preview-content video">
                <video :src="previewUrl" controls />
              </div>
              <div v-else-if="isAudio(previewingAttachment)" class="preview-content audio">
                <audio :src="previewUrl" controls />
              </div>
              <div v-else class="preview-frame">
                <iframe :src="previewUrl" />
              </div>
            </template>
            <div v-else class="preview-placeholder">选择一个附件查看预览</div>
          </div>
        </div>
      </template>

      <div v-if="!previewingAttachment" class="upload-floating">
        <a-button
          type="primary"
          size="large"
          class="upload-btn"
          :loading="uploading"
          @click="handleUploadClick"
        >
          <UploadIcon class="icon" />
          上传资料
        </a-button>
        <input ref="fileInput" type="file" class="file-input" @change="handleFileChange" />
      </div>

      <div v-if="loading || uploading" class="spin-overlay">
        <a-spin />
      </div>
    </div>
  </a-card>

  <a-modal
    v-model:visible="renameModal.open"
    :footer="null"
    :maskClosable="false"
    :width="420"
    centered
    destroy-on-close
    wrap-class-name="rename-modal"
    @cancel="handleRenameCancel"
    @afterClose="resetRenameModal"
  >
    <div class="rename-modal__body">
      <p class="rename-modal__title">要重命名“{{ renameModal.target ? resolveName(renameModal.target) : '' }}”吗？</p>
      <label class="rename-modal__label" for="rename-input">来源名称 *</label>
      <a-input
        id="rename-input"
        v-model:value="renameModal.value"
        :maxlength="255"
        placeholder="请输入新的文件名"
      />
      <div class="modal-actions">
        <a-button class="modal-btn" @click="handleRenameCancel">取消</a-button>
        <a-button
          type="primary"
          class="modal-btn modal-btn--primary"
          :loading="renameModal.loading"
          @click="handleRenameConfirm"
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
    :width="460"
    centered
    destroy-on-close
    wrap-class-name="delete-modal"
    @cancel="handleDeleteCancel"
    @afterClose="resetDeleteModal"
  >
    <div class="delete-modal__body">
      <p class="delete-modal__title">要删除“{{ deleteModal.target ? resolveName(deleteModal.target) : '' }}”吗？</p>
      <div class="modal-actions">
        <a-button class="modal-btn" @click="handleDeleteCancel">取消</a-button>
        <a-button
          type="primary"
          danger
          class="modal-btn modal-btn--danger"
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
import { message } from 'ant-design-vue'
import { computed, reactive, ref, watch } from 'vue'
import {
  ArrowLeftIcon,
  DownloadIcon,
  FileArchiveIcon,
  FileAudioIcon,
  FileCodeIcon,
  FileIcon,
  FileImageIcon,
  FileSpreadsheetIcon,
  FileTextIcon,
  FileTypeIcon,
  FileVideoIcon,
  MoreVerticalIcon,
  PencilIcon,
  UploadIcon,
  Trash2Icon,
} from 'lucide-vue-next'
import AttachmentDocViewer from './AttachmentDocViewer.vue'
import AttachmentPdfViewer from './AttachmentPdfViewer.vue'
import type { NoteAttachment } from '@/types/notes'
import {
  deleteAttachment,
  getAttachmentDownloadUrl,
  linkAttachmentToOpenAI,
  presignAttachmentUpload,
  updateAttachment,
  uploadOpenAIFile,
} from '@/services/api'

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
const renameModal = reactive({
  open: false,
  loading: false,
  target: null as NoteAttachment | null,
  value: '',
})
const deleteModal = reactive({
  open: false,
  loading: false,
  target: null as NoteAttachment | null,
})
const previewingId = ref<string | null>(null)
const previewUrl = ref<string | null>(null)
const previewLoading = ref(false)
const previewError = ref<string | null>(null)
const focusText = ref('')
const focusTrigger = ref(0)

const loading = computed(() => props.loading === true)
const previewingAttachment = computed(
  () => props.attachments.find(item => item.id === previewingId.value) ?? null,
)
const sortedAttachments = computed(() => {
  return [...props.attachments].sort((a, b) => {
    const aTime = new Date(a.createdAt || '').getTime()
    const bTime = new Date(b.createdAt || '').getTime()
    if (Number.isNaN(aTime) || Number.isNaN(bTime)) return 0
    return bTime - aTime
  })
})

watch(
  () => props.attachments,
  newList => {
    if (previewingId.value && !newList.some(item => item.id === previewingId.value)) {
      exitPreview()
    }
  },
)

const handleUploadClick = () => {
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

    const openAIFile = await uploadOpenAIFile(file, {
      purpose: 'assistants',
      expiresAfterAnchor: 'created_at',
      expiresAfterSeconds: 2_592_000,
    })
    if (!openAIFile?.id) {
      throw new Error('未能获取 OpenAI 文件 ID')
    }
    await linkAttachmentToOpenAI(response.attachmentId, openAIFile.id)
    message.success('资料上传成功并同步至 OpenAI资料库')
    emit('updated')
  } catch (err: any) {
    const error = err?.message || '上传失败，请稍后再试'
    message.error(error)
  } finally {
    uploading.value = false
    if (target) target.value = ''
  }
}

const onMenuClick = (item: NoteAttachment, event: { key: string | number; domEvent?: Event }) => {
  event?.domEvent?.stopPropagation?.()
  if (event.key === 'rename') {
    openRenameModal(item)
  } else if (event.key === 'delete') {
    openDeleteModal(item)
  } else if (event.key === 'download') {
    handleDownload(item.id)
  }
}

const openRenameModal = (item: NoteAttachment) => {
  renameModal.target = item
  renameModal.value = resolveName(item)
  renameModal.open = true
}

const handleRenameCancel = () => {
  renameModal.open = false
}

const resetRenameModal = () => {
  renameModal.loading = false
  renameModal.target = null
  renameModal.value = ''
}

const handleRenameConfirm = async () => {
  if (!renameModal.target) return
  const filename = renameModal.value.trim()
  if (!filename) {
    message.warning('请输入新的文件名')
    return
  }
  renameModal.loading = true
  try {
    await updateAttachment(renameModal.target.id, { filename })
    message.success('文件名已更新')
    renameModal.open = false
    emit('updated')
  } catch (err: any) {
    const error = err?.message || '重命名失败'
    message.error(error)
  } finally {
    renameModal.loading = false
  }
}

const openDeleteModal = (item: NoteAttachment) => {
  deleteModal.target = item
  deleteModal.open = true
}

const handleDeleteCancel = () => {
  deleteModal.open = false
}

const resetDeleteModal = () => {
  deleteModal.loading = false
  deleteModal.target = null
}

const handleDeleteConfirm = async () => {
  if (!deleteModal.target) return
  deleteModal.loading = true
  try {
    await deleteAttachment(deleteModal.target.id)
    message.success('附件已删除')
    if (previewingId.value === deleteModal.target.id) {
      exitPreview()
    }
    deleteModal.open = false
    emit('updated')
  } catch (err: any) {
    const error = err?.message || '删除失败'
    message.error(error)
  } finally {
    deleteModal.loading = false
  }
}

const applyFocusText = (text?: string | null) => {
  focusText.value = text?.trim() || ''
  focusTrigger.value += 1
}

const openPreview = async (item: NoteAttachment, options?: { focusText?: string | null }) => {
  applyFocusText(options?.focusText)
  if (previewingId.value === item.id && previewUrl.value && !previewError.value) return
  previewingId.value = item.id
  previewLoading.value = true
  previewError.value = null
  previewUrl.value = null
  try {
    previewUrl.value = await resolvePreviewUrl(item)
  } catch (err: any) {
    const error = err?.message || '预览加载失败'
    previewError.value = error
    message.error(error)
  } finally {
    previewLoading.value = false
  }
}

const resolvePreviewUrl = async (item: NoteAttachment) => {
  if (item.externalUrl && item.externalUrl.trim()) return item.externalUrl
  if (item.s3Url && item.s3Url.trim()) return item.s3Url
  const { url } = await getAttachmentDownloadUrl(item.id)
  return url
}

const exitPreview = () => {
  previewingId.value = null
  previewUrl.value = null
  previewError.value = null
  previewLoading.value = false
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
    if (downloading.value === id) downloading.value = null
  }
}

type FileCategory =
  | 'pdf'
  | 'image'
  | 'audio'
  | 'video'
  | 'archive'
  | 'sheet'
  | 'doc'
  | 'text'
  | 'code'
  | 'other'

const resolveMimeLabel = (mime: string | null) => {
  if (typeof mime === 'string' && mime.trim()) return mime
  return '文件'
}

const resolveName = (item: NoteAttachment) => {
  if (item.filename && item.filename.trim()) return item.filename
  if (item.meta && typeof item.meta === 'object' && 'filename' in item.meta) {
    const name = (item.meta as Record<string, any>).filename
    if (typeof name === 'string' && name.trim()) return name
  }
  const key = item.s3ObjectKey || ''
  const parts = key.split('/')
  return parts[parts.length - 1] || '未命名文件'
}

const formatBytes = (value: number | null) => {
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

const getExtension = (name: string) => {
  const parts = name.split('.')
  if (parts.length <= 1) return ''
  return parts.pop()?.toLowerCase() ?? ''
}

const resolveFileCategory = (item: NoteAttachment): FileCategory => {
  const mime = item.mime?.toLowerCase() ?? ''
  const ext = getExtension(resolveName(item)).toLowerCase()

  if (mime.includes('pdf') || ext === 'pdf') return 'pdf'
  if (mime.startsWith('image/') || ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'svg', 'webp', 'avif', 'heic'].includes(ext))
    return 'image'
  if (
    mime.startsWith('video/') ||
    ['mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v'].includes(ext)
  )
    return 'video'
  if (
    mime.startsWith('audio/') ||
    ['mp3', 'aac', 'wav', 'flac', 'ogg', 'm4a', 'wma'].includes(ext)
  )
    return 'audio'
  if (
    mime.includes('spreadsheet') ||
    mime.includes('excel') ||
    ['xls', 'xlsx', 'csv'].includes(ext)
  )
    return 'sheet'
  if (
    mime.includes('presentation') ||
    ['ppt', 'pptx', 'key', 'odp'].includes(ext)
  )
    return 'doc'
  if (mime.includes('word') || ['doc', 'docx', 'pages', 'odt'].includes(ext)) return 'doc'
  if (['zip', 'rar', '7z', 'gz', 'tar', 'bz2'].includes(ext)) return 'archive'
  if (mime.startsWith('text/') || ['txt', 'md', 'rtf'].includes(ext)) return 'text'
  if (
    mime.includes('json') ||
    ['js', 'ts', 'tsx', 'jsx', 'json', 'py', 'java', 'c', 'cpp', 'cs', 'go', 'rb', 'php', 'sh', 'rs', 'html', 'css'].includes(
      ext,
    )
  )
    return 'code'
  return 'other'
}

const fileIconMap: Record<FileCategory, any> = {
  pdf: FileTypeIcon,
  image: FileImageIcon,
  audio: FileAudioIcon,
  video: FileVideoIcon,
  archive: FileArchiveIcon,
  sheet: FileSpreadsheetIcon,
  doc: FileTextIcon,
  text: FileTextIcon,
  code: FileCodeIcon,
  other: FileIcon,
}

const resolveFileIcon = (item: NoteAttachment): any => fileIconMap[resolveFileCategory(item)] || FileIcon

const isPdf = (item: NoteAttachment | null) => !!item && resolveFileCategory(item) === 'pdf'
const isWordDocument = (item: NoteAttachment | null) => {
  if (!item) return false
  const mime = item.mime?.toLowerCase() ?? ''
  const ext = getExtension(resolveName(item)).toLowerCase()
  return mime.includes('word') || ['doc', 'docx', 'odt'].includes(ext)
}
const isImage = (item: NoteAttachment | null) => !!item && resolveFileCategory(item) === 'image'
const isVideo = (item: NoteAttachment | null) => !!item && resolveFileCategory(item) === 'video'
const isAudio = (item: NoteAttachment | null) => !!item && resolveFileCategory(item) === 'audio'

const focusAttachmentByCitation = async (payload: { fileId: string; quote?: string | null }) => {
  const target = props.attachments.find(
    item => item.openaiFileId === payload.fileId || item.id === payload.fileId,
  )
  if (!target) return false
  await openPreview(target, { focusText: payload.quote })
  return true
}

defineExpose({ focusAttachmentByCitation })
</script>

<style scoped>
.materials-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 22px;
  overflow: hidden;
  background: #fff;
}

.materials-panel :deep(.ant-card-body) {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 12px 12px 20px;
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
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.materials-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
  padding-bottom: 72px; /* 留空间给悬浮上传按钮 */
}

.materials-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
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
  align-items: center;
  gap: 12px;
  padding: 10px 10px;
  border-radius: 12px;
  border: 1px solid transparent;
  transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
  cursor: pointer;
}

.material-item:hover {
  background: #f7f9fc;
  border-color: rgba(0, 0, 0, 0.04);
}

.material-item--active {
  background: #eef4ff;
  border-color: rgba(22, 119, 255, 0.18);
  box-shadow: 0 8px 18px rgba(22, 119, 255, 0.08);
}

.material-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.item-icon {
  width: 24px;
  height: 24px;
  color: #1677ff;
  margin-top: 2px;
  flex-shrink: 0;
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
  font-size: 15px;
  line-height: 1;
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
  align-self: center;
}

.more-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.more-btn:hover {
  background: rgba(22, 119, 255, 0.08);
  color: #1677ff;
}

.more-btn:focus-visible {
  outline: 2px solid rgba(22, 119, 255, 0.35);
  outline-offset: 2px;
}

.more-icon {
  width: 18px;
  height: 18px;
  color: rgba(0, 0, 0, 0.55);
}

:deep(.materials-actions-dropdown .ant-dropdown-menu) {
  min-width: 160px;
  padding: 6px 0;
}

:deep(.materials-actions-dropdown .ant-dropdown-menu-item) {
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.materials-actions-dropdown .menu-icon) {
  width: 16px;
  height: 16px;
  color: rgba(0, 0, 0, 0.55);
}

:deep(.materials-actions-dropdown .ant-dropdown-menu-item-disabled .menu-icon) {
  color: rgba(0, 0, 0, 0.35);
}

.action-icon {
  width: 14px;
  height: 14px;
  margin-right: 4px;
}

.preview-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.preview-panel--pdf {
  gap: 0;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 4px 6px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: rgba(0, 0, 0, 0.04);
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  color: rgba(0, 0, 0, 0.65);
  transition: background-color 0.2s ease, color 0.2s ease;
}

.back-btn:hover {
  background: rgba(22, 119, 255, 0.1);
  color: #1677ff;
}

.back-icon {
  width: 16px;
  height: 16px;
}

.preview-title {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.header-icon {
  width: 22px;
  height: 22px;
  color: #1677ff;
  flex-shrink: 0;
}

.preview-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.preview-name {
  font-weight: 600;
  font-size: 15px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preview-meta {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}

.preview-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spin-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
}

.preview-body {
  position: relative;
  flex: 1;
  min-height: 0;
  background: #fff;
  border: 1px solid #e6eaf3;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.preview-content {
  width: 100%;
  height: 100%;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
}

.preview-content.image img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 14px;
  box-shadow: 0 6px 12px rgba(15, 23, 42, 0.08);
  background: #fff;
  padding: 12px;
}

.preview-content.video video,
.preview-content.audio audio {
  width: 100%;
  max-height: 100%;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 6px 12px rgba(15, 23, 42, 0.06);
}

.preview-frame {
  width: 100%;
  height: 100%;
  padding: 12px;
  box-sizing: border-box;
}

.preview-frame iframe {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 12px;
  background: #fff;
}

.preview-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  flex: 1;
}

.preview-error,
.preview-placeholder {
  text-align: center;
  color: rgba(0, 0, 0, 0.55);
  line-height: 1.6;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
  flex: 1;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
}

.modal-btn {
  border-radius: 999px;
  padding: 6px 16px;
}

.modal-btn--primary,
.modal-btn--danger {
  box-shadow: none;
}

.upload-floating {
  position: absolute;
  left: 50%;
  bottom: 16px;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3;
}

.upload-btn {
  min-width: 140px;
  border-radius: 999px;
  box-shadow: none;
  height: 38px;
  font-weight: 600;
  gap: 6px;
}

.rename-modal__body,
.delete-modal__body {
  padding: 6px 2px;
}

.rename-modal__title,
.delete-modal__title {
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 12px;
  line-height: 1.5;
}

.rename-modal__label {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.6);
  margin-bottom: 6px;
  display: block;
}

:deep(.rename-modal .ant-modal-content),
:deep(.delete-modal .ant-modal-content) {
  border-radius: 16px;
  padding: 22px 24px;
}

:deep(.rename-modal .ant-modal-body),
:deep(.delete-modal .ant-modal-body) {
  padding: 0;
}
</style>
