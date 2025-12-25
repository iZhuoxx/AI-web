<template>
  <a-card class="mindmap-panel" :bordered="false" :body-style="{ height: '100%', padding: 0 }">
    <div class="panel-shell">
      <div v-if="!activeNotebookId" class="empty-panel">
        <MapIcon class="empty-icon" />
        <div class="empty-title">请选择一个笔记以查看思维导图</div>
        <p class="empty-desc">打开笔记本后即可浏览或生成思维导图。</p>
      </div>

      <template v-else>
        <div v-if="activeMindmap" class="mindmap-view">
          <div class="mindmap-topbar">
            <button class="back-btn" type="button" @click="goBackToList">
              <ArrowLeftIcon class="back-icon" />
            </button>
            <div class="mindmap-head">
              <div class="mindmap-title">{{ activeMindmap.title }}</div>
              <div v-if="activeMindmap.description" class="mindmap-sub">{{ activeMindmap.description }}</div>
            </div>
            <div class="mindmap-actions">
              <a-button class="ghost-btn" :disabled="loadingMap" @click="resetMindmap">
                重置
              </a-button>
              <a-button type="primary" :loading="saving" :disabled="!hasUnsavedChanges" @click="saveMindmap">
                {{ saving ? '保存中...' : '保存' }}
              </a-button>
            </div>
          </div>

          <div class="mindmap-canvas" ref="mindmapContainer"></div>
          <div v-if="loadingMap" class="canvas-overlay">
            <a-spin />
          </div>
        </div>

        <div v-else class="list-view">
          <div class="folders-grid">
            <div
              v-for="(item, index) in mindmaps"
              :key="item.id"
              class="folder-card"
              :class="`folder-card--color-${index % 6}`"
              @click="openMindmap(item.id)"
            >
              <div class="folder-card__head">
                <div class="folder-info">
                  <div class="folder-title">
                    <MapIcon class="folder-icon" />
                    <span class="folder-title-text">{{ item.title }}</span>
                  </div>
                  <div v-if="item.description" class="folder-desc">{{ item.description }}</div>
                  <div class="folder-materials">
                    <span class="material-tag">{{ formatDate(item.updatedAt) }} 更新</span>
                    <span class="material-tag">{{ getNodeCount(item) }} 节点</span>
                  </div>
                </div>
                <a-dropdown trigger="click" placement="bottomRight">
                  <button class="folder-menu-btn" type="button" @click.stop>
                    <MoreVerticalIcon class="menu-icon" />
                  </button>
                  <template #overlay>
                    <a-menu>
                      <a-menu-item @click.stop="promptDeleteMindmap(item)">
                        删除
                      </a-menu-item>
                    </a-menu>
                  </template>
                </a-dropdown>
              </div>
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
            AI生成
          </a-button>

          <div v-if="!mindmaps.length && !loading" class="empty-inner">
            <p>还没有思维导图</p>
            <p class="muted">点击“AI生成”创建你的第一张导图。</p>
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
    title="AI生成思维导图"
    :maskClosable="false"
    :width="560"
    centered
    destroy-on-close
    wrap-class-name="rounded-modal"
    @ok="handleGenerate"
    @cancel="closeGenerateModal"
  >
    <div class="generate-form">
      <label class="form-label">导图标题</label>
      <a-input v-model:value="generateModal.title" placeholder="自动根据笔记生成" />

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
        placeholder="让AI根据你的重点生成导图（可选）"
      />

      <label class="form-label">导图简介（可选）</label>
      <a-textarea
        v-model:value="generateModal.description"
        :auto-size="{ minRows: 2, maxRows: 3 }"
        placeholder="用一句话描述这张导图"
      />
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, shallowRef, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { ArrowLeftIcon, MapIcon, MoreVerticalIcon, SparklesIcon } from 'lucide-vue-next'
import type { MindElixirData, MindElixirInstance } from 'mind-elixir'
import type { MindMap } from '@/types/mindmaps'
import type { NoteAttachment } from '@/types/notes'
import { deleteMindMap, generateMindMapForNotebook, listMindMaps, updateMindMap } from '@/services/api'
import { useNotebookStore } from '@/composables/useNotes'
import { getModelFor } from '@/composables/setting'

const notebookStore = useNotebookStore()

const loading = ref(false)
const loadingMap = ref(false)
const generating = ref(false)
const saving = ref(false)
const mindmaps = ref<MindMap[]>([])
const activeMindmapId = ref<string | null>(null)
const hasUnsavedChanges = ref(false)

const generateModal = reactive({
  open: false,
  loading: false,
  attachments: [] as string[],
  focus: '',
  title: '',
  description: '',
})

const mindmapContainer = ref<HTMLElement | null>(null)
const mindInstance = shallowRef<MindElixirInstance | null>(null)

const activeNotebookId = computed(() => notebookStore.activeNotebook.value?.id ?? null)
const attachments = computed<NoteAttachment[]>(() => notebookStore.activeNotebook.value?.attachments ?? [])
const selectableAttachments = computed(() => attachments.value.filter(item => !!item.openaiFileId))

const activeMindmap = computed(() => mindmaps.value.find(item => item.id === activeMindmapId.value) ?? null)

const getErrorMessage = (err: unknown) => (err instanceof Error ? err.message : '请求失败')

const formatDate = (iso: string): string => {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString()
}

const getNodeCount = (mindmap: MindMap): number => {
  const walk = (node: any): number => {
    if (!node) return 0
    const children = Array.isArray(node.children) ? node.children : []
    return 1 + children.reduce((sum, child) => sum + walk(child), 0)
  }
  return walk((mindmap.data as any)?.nodeData)
}

const parseTime = (value: string): number => {
  const time = new Date(value || '').getTime()
  return Number.isNaN(time) ? 0 : time
}

const sortMindmaps = (items: MindMap[]): MindMap[] =>
  [...items].sort(
    (a, b) => parseTime(b.updatedAt) - parseTime(a.updatedAt),
  )

const buildFallbackData = (title: string): MindElixirData => ({
  nodeData: {
    id: `root-${Date.now()}`,
    topic: title || '思维导图',
    root: true,
    children: [],
  },
  linkData: {},
})

const loadMindmaps = async () => {
  if (!activeNotebookId.value) return
  loading.value = true
  try {
    mindmaps.value = sortMindmaps(await listMindMaps({ notebookId: activeNotebookId.value }))
  } catch (err) {
    message.error(getErrorMessage(err))
    mindmaps.value = []
  } finally {
    loading.value = false
  }
}

const renderMindmap = async () => {
  if (!activeMindmap.value || !mindmapContainer.value) return
  loadingMap.value = true
  try {
    const { default: MindElixir } = await import('mind-elixir')
    mindmapContainer.value.innerHTML = ''
    const direction = (MindElixir as any).SIDE ?? (MindElixir as any).RIGHT ?? 1
    const instance = new MindElixir({
      el: mindmapContainer.value,
      direction,
      draggable: true,
      editable: true,
      contextMenu: true,
      toolBar: true,
      nodeMenu: true,
      keypress: true,
    })
    const data = (activeMindmap.value.data as any)?.nodeData
      ? (activeMindmap.value.data as MindElixirData)
      : buildFallbackData(activeMindmap.value.title)
    instance.init(data)
    instance.bus?.addListener?.('operation', () => {
      hasUnsavedChanges.value = true
    })
    mindInstance.value = instance
    hasUnsavedChanges.value = false
  } catch (err) {
    message.error(getErrorMessage(err))
  } finally {
    loadingMap.value = false
  }
}

const openMindmap = async (id: string) => {
  activeMindmapId.value = id
  await nextTick()
  await renderMindmap()
}

const goBackToList = () => {
  if (hasUnsavedChanges.value) {
    Modal.confirm({
      title: '放弃未保存的修改？',
      content: '返回列表将不会保存当前导图的更改。',
      okText: '放弃修改',
      cancelText: '继续编辑',
      centered: true,
      onOk: () => {
        hasUnsavedChanges.value = false
        activeMindmapId.value = null
      },
    })
    return
  }
  activeMindmapId.value = null
}

const resetMindmap = async () => {
  if (!activeMindmap.value) return
  hasUnsavedChanges.value = false
  await nextTick()
  await renderMindmap()
}

const saveMindmap = async () => {
  if (!activeMindmap.value || !mindInstance.value) return
  saving.value = true
  try {
    const data = mindInstance.value.getAllData()
    const updated = await updateMindMap(activeMindmap.value.id, { data })
    mindmaps.value = sortMindmaps(mindmaps.value.map(item => (item.id === updated.id ? updated : item)))
    hasUnsavedChanges.value = false
    await nextTick()
    await renderMindmap()
    message.success('已保存思维导图')
  } catch (err) {
    message.error(getErrorMessage(err))
  } finally {
    saving.value = false
  }
}

const promptDeleteMindmap = (mindmap: MindMap) => {
  Modal.confirm({
    title: '',
    icon: null,
    content: `确定删除「${mindmap.title}」吗？`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    centered: true,
    onOk: async () => {
      try {
        await deleteMindMap(mindmap.id)
        mindmaps.value = sortMindmaps(mindmaps.value.filter(item => item.id !== mindmap.id))
        if (activeMindmapId.value === mindmap.id) {
          activeMindmapId.value = null
        }
        message.success('已删除思维导图')
      } catch (err) {
        message.error(getErrorMessage(err))
        throw err
      }
    },
  })
}

const openGenerateModal = () => {
  if (!activeNotebookId.value) {
    message.warning('请先选择一个笔记本')
    return
  }
  if (!selectableAttachments.value.length) {
    message.warning('请先上传并同步资料到 OpenAI 后再生成思维导图')
    return
  }
  generateModal.attachments = selectableAttachments.value.map(item => item.id)
  generateModal.focus = ''
  generateModal.title = notebookStore.activeNotebook.value?.title
    ? `${notebookStore.activeNotebook.value.title} 思维导图`
    : ''
  generateModal.description = ''
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
  generateModal.loading = true
  generating.value = true
  try {
    const model = getModelFor('mindmap')
    const mindmap = await generateMindMapForNotebook(activeNotebookId.value, {
      attachmentIds: generateModal.attachments,
      focus: generateModal.focus.trim() || undefined,
      title: generateModal.title.trim() || undefined,
      description: generateModal.description.trim() || undefined,
      model,
    })
    mindmaps.value = sortMindmaps([mindmap, ...mindmaps.value.filter(item => item.id !== mindmap.id)])
    generateModal.open = false
    activeMindmapId.value = mindmap.id
    await nextTick()
    await renderMindmap()
    message.success('已生成思维导图')
  } catch (err) {
    message.error(getErrorMessage(err))
  } finally {
    generateModal.loading = false
    generating.value = false
  }
}

watch(
  () => activeNotebookId.value,
  id => {
    activeMindmapId.value = null
    if (id) {
      loadMindmaps()
    } else {
      mindmaps.value = []
    }
  },
  { immediate: true },
)

watch(
  () => activeMindmapId.value,
  async id => {
    if (!id) {
      mindInstance.value = null
      return
    }
    await nextTick()
    await renderMindmap()
  },
)
</script>

<style scoped>
.mindmap-panel {
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
  background: linear-gradient(135deg, rgba(82, 196, 26, 0.05), rgba(59, 130, 246, 0.03));
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
  color: #16a34a;
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
.mindmap-view {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.folders-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 2px 0 80px;
  overflow: auto;
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

.folder-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.06);
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

.folder-card__head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.folder-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.folder-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: #0f172a;
}

.folder-title-text {
  font-size: 17px;
}

.folder-icon {
  width: 18px;
  height: 18px;
  color: #0f172a;
}

.folder-desc {
  color: #475569;
  font-size: 14px;
}

.folder-materials {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.material-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 12px;
  color: #475569;
  font-size: 12px;
}

.folder-menu-btn {
  border: none;
  background: rgba(255, 255, 255, 0.6);
  padding: 8px;
  border-radius: 12px;
  color: #475569;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
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

.mindmap-topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 0 12px;
  flex-wrap: wrap;
}

.mindmap-head {
  min-width: 0;
  flex: 1;
}

.mindmap-title {
  font-size: 19px;
  font-weight: 700;
  color: #0f172a;
}

.mindmap-sub {
  margin-top: 4px;
  color: #475569;
}

.mindmap-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
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

.ghost-btn:hover {
  border-color: #16a34a;
  color: #16a34a;
  background: rgba(22, 163, 74, 0.08);
}

.mindmap-canvas {
  flex: 1;
  min-height: 0;
  border-radius: 14px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #f8fafc;
  overflow: hidden;
  position: relative;
}

.canvas-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

.panel-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.generate-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-label {
  font-weight: 600;
  color: #475569;
  margin-top: 4px;
}
</style>
