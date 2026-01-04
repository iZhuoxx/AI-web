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
            </div>
          </div>

          <div class="mindmap-canvas" :id="mindmapElementId" ref="mindmapContainer"></div>

          <div class="canvas-actions">
            <button
              class="canvas-action-btn"
              type="button"
              :data-label="allExpanded ? '收起全部' : '展开全部'"
              @click="toggleExpandAll"
            >
              <ChevronsUpDownIcon class="action-icon" />
            </button>
            <button
              class="canvas-action-btn"
              type="button"
              :data-label="isFullscreen ? '退出全屏' : '全屏画布'"
              @click="toggleFullscreen"
            >
              <component :is="fullscreenIcon" class="action-icon" />
            </button>
            <button class="canvas-action-btn" type="button" data-label="导出图片" @click="exportMindmap">
              <DownloadIcon class="action-icon" />
            </button>
          </div>
          
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
                <div class="folder-materials">
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
            <p class="muted">点击"AI生成"创建你的第一张导图。</p>
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
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, shallowRef, toRaw, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  ArrowLeftIcon,
  ChevronsUpDownIcon,
  DownloadIcon,
  MapIcon,
  Maximize2Icon,
  Minimize2Icon,
  MoreVerticalIcon,
  SparklesIcon,
} from 'lucide-vue-next'
import type { MindElixirData, MindElixirInstance } from 'mind-elixir'
import type { MindMap } from '@/types/mindmaps'
import type { NoteAttachment } from '@/types/notes'
import { deleteMindMap, generateMindMapForNotebook, listMindMaps } from '@/services/api'
import { useNotebookStore } from '@/composables/useNotes'
import { getModelFor } from '@/composables/setting'



interface MindmapNodeData {
  id: string
  topic: string
  root?: boolean
  expanded?: boolean
  direction?: number
  note?: string
  children?: MindmapNodeData[]
}

interface WheelZoomTarget {
  targetScale: number
  worldX: number
  worldY: number
  pointerX: number
  pointerY: number
}

const notebookStore = useNotebookStore()

const loading = ref(false)
const loadingMap = ref(false)
const generating = ref(false)
const mindmaps = ref<MindMap[]>([])
const activeMindmapId = ref<string | null>(null)
const hasUnsavedChanges = ref(false)
const allExpanded = ref(false)
const isFullscreen = ref(false)
const fullscreenIcon = computed(() => (isFullscreen.value ? Minimize2Icon : Maximize2Icon))
// 放宽缩放范围并与内置 toolbar 保持可用
const MIN_SCALE = 0.5
const MAX_SCALE = 2
const ZOOM_SENSITIVITY = 0.0013
const MAX_WHEEL_DELTA = 180
const ZOOM_EASING = 0.28

const generateModal = reactive({
  open: false,
  loading: false,
  attachments: [] as string[],
  focus: '',
  title: '',
})

const mindmapContainer = ref<HTMLElement | null>(null)
const mindInstance = shallowRef<MindElixirInstance | null>(null)
const mindmapElementId = `mindmap-canvas-${Math.random().toString(36).slice(2)}`

const activeNotebookId = computed(() => notebookStore.activeNotebook.value?.id ?? null)
const attachments = computed<NoteAttachment[]>(() => notebookStore.activeNotebook.value?.attachments ?? [])
const selectableAttachments = computed(() => attachments.value.filter(item => !!item.openaiFileId))

const activeMindmap = computed(() => mindmaps.value.find(item => item.id === activeMindmapId.value) ?? null)

const getErrorMessage = (err: unknown) => (err instanceof Error ? err.message : '请求失败')

const clampScale = (value: number) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, value))
const normalizeWheelDelta = (evt: WheelEvent) => {
  const base = evt.deltaMode === 1 ? evt.deltaY * 16 : evt.deltaMode === 2 ? evt.deltaY * 120 : evt.deltaY
  // 限制过大的滚轮 delta，避免一次滚动跳跃过多
  const eased = Math.tanh(base / MAX_WHEEL_DELTA) * MAX_WHEEL_DELTA
  return eased
}

// 深度克隆函数 - 完全移除 Vue 响应式
const deepClone = (obj: any): any => {
  if (obj === null || obj === undefined) return obj
  if (typeof obj !== 'object') return obj
  if (Array.isArray(obj)) return obj.map(item => deepClone(item))
  
  const cloned: any = {}
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      cloned[key] = deepClone(obj[key])
    }
  }
  return cloned
}

// 安全的节点计数
const getNodeCount = (mindmap: MindMap): number => {
  const walk = (node: any): number => {
    if (!node || typeof node !== 'object') return 0
    const children = Array.isArray(node.children) ? node.children : []
    return 1 + children.reduce((sum: number, child: any) => sum + walk(child), 0)
  }
  
  try {
    const data = mindmap?.data
    if (!data || typeof data !== 'object') return 0
    const nodeData = (data as any).nodeData
    if (!nodeData || typeof nodeData !== 'object') return 0
    return walk(nodeData)
  } catch (err) {
    return 0
  }
}

const parseTime = (value: string): number => {
  const time = new Date(value || '').getTime()
  return Number.isNaN(time) ? 0 : time
}

const sortMindmaps = (items: MindMap[]): MindMap[] =>
  [...items].sort((a, b) => parseTime(b.updatedAt) - parseTime(a.updatedAt))

// ✅ 只展开根节点，显示一级节点
const ensureNode = (node: any, isRoot = false, depth = 0): MindmapNodeData | null => {
  if (!node || typeof node !== 'object') return null

  const normalized: MindmapNodeData = {
    id: String(node.id || `node-${Date.now()}-${Math.random().toString(16).slice(2)}`),
    topic: typeof node.topic === 'string' && node.topic.trim() ? node.topic.trim() : '未命名节点',
    root: isRoot ? true : node.root === true ? true : undefined,
    // ✅ 只展开根节点（depth === 0），其他都收起
    expanded: depth === 0,
    note: typeof node.note === 'string' ? node.note : undefined,
  }

  if (!isRoot && typeof node.direction === 'number') {
    normalized.direction = node.direction
  }

  const children = Array.isArray(node.children) ? node.children : []
  const normalizedChildren = children
    .map((child: any) => ensureNode(child, false, depth + 1))
    .filter((child: MindmapNodeData | null): child is MindmapNodeData => !!child)

  if (normalizedChildren.length) {
    normalized.children = normalizedChildren
  }

  return normalized
}

const loadMindmaps = async () => {
  if (!activeNotebookId.value) return
  loading.value = true
  try {
    const result = await listMindMaps({ notebookId: activeNotebookId.value })
    mindmaps.value = sortMindmaps(result)
  } catch (err) {
    console.error('加载思维导图失败:', err)
    message.error(getErrorMessage(err))
    mindmaps.value = []
  } finally {
    loading.value = false
  }
}

// 准备思维导图数据的辅助函数
const prepareMindmapData = (mindmap: MindMap): MindElixirData => {
  const fallbackData: MindElixirData = {
    nodeData: {
      id: `root-${Date.now()}`,
      topic: mindmap.title || '思维导图',
      root: true,
      expanded: true,
      children: [],
    },
    linkData: {},
  }
  
  try {
    let rawData = toRaw(mindmap.data)
    
    if (typeof rawData === 'string') {
      rawData = JSON.parse(rawData)
    }
    
    if (!rawData || typeof rawData !== 'object') {
      return fallbackData
    }
    
    const rawNodeData = (rawData as any).nodeData
    
    if (!rawNodeData || typeof rawNodeData !== 'object' || !rawNodeData.id || !rawNodeData.topic) {
      return fallbackData
    }
    
    const clonedNodeData = deepClone(rawNodeData)
    const clonedLinkData = deepClone((rawData as any).linkData || {})
    
    const normalizedNode = ensureNode(clonedNodeData, true, 0)
    
    if (!normalizedNode) {
      return fallbackData
    }
    
    return {
      nodeData: normalizedNode,
      linkData: clonedLinkData,
    }
  } catch (error) {
    console.error('prepareMindmapData 失败:', error)
    return fallbackData
  }
}

// 等待容器尺寸稳定，避免 panel 切换时 0 宽高导致渲染异常
const waitForContainerReady = async (maxTries = 5): Promise<boolean> => {
  for (let i = 0; i < maxTries; i++) {
    await nextTick()
    await new Promise(resolve => requestAnimationFrame(resolve))
    const rect = mindmapContainer.value?.getBoundingClientRect()
    if (rect && rect.width > 12 && rect.height > 12) return true
    await new Promise(resolve => setTimeout(resolve, 60))
  }
  return false
}

// ✅ 简化的居中和自适应 - 使用 MindElixir 内置方法
const fitToView = async (payload?: MouseEvent | MindElixirInstance | null) => {
  const instance = (payload && (payload as any)?.init ? (payload as MindElixirInstance) : mindInstance.value) as any

  if (!instance) {
    return
  }

  // 等待DOM渲染完成
  await nextTick()
  await new Promise(resolve => requestAnimationFrame(resolve))

  try {
    // 重置缩放并居中
    instance.scale(1)

    // ✅ 使用 MindElixir 内置的 toCenter 方法
    if (instance.toCenter) {
      instance.toCenter()
    }
  } catch (error) {
    console.error('fitToView 执行失败:', error)
  }
}

const stopWheelZoomAnimation = () => {
  if (wheelZoomFrame) {
    cancelAnimationFrame(wheelZoomFrame)
    wheelZoomFrame = null
  }
  wheelZoomTarget = null
}

// 绑定带缓动的滚轮缩放
const bindSmoothWheelZoom = (instance: MindElixirInstance) => {
  const container = (instance as any)?.container as HTMLElement | null
  const mapEl = (instance as any)?.map as HTMLElement | null

  if (!container || !mapEl || typeof (instance as any).scale !== 'function') {
    console.warn('bindSmoothWheelZoom: 缺少 container 或 map 元素')
    return null
  }

  const clampScroll = (value: number, max: number, view: number) =>
    Math.min(Math.max(value, 0), Math.max(0, max - view))

  const applyScaleAtPoint = (targetScale: number, worldX: number, worldY: number, pointerX: number, pointerY: number) => {
    const originX = mapEl.clientWidth / 2
    const originY = mapEl.clientHeight / 2
    const xVis = targetScale * worldX + originX * (1 - targetScale)
    const yVis = targetScale * worldY + originY * (1 - targetScale)

    ;(instance as any).scale(targetScale)
    container.scrollTo({
      left: clampScroll(xVis - pointerX, container.scrollWidth, container.clientWidth),
      top: clampScroll(yVis - pointerY, container.scrollHeight, container.clientHeight),
    })
  }

  const stepZoom = () => {
    if (!wheelZoomTarget) {
      wheelZoomFrame = null
      return
    }

    const { targetScale, worldX, worldY, pointerX, pointerY } = wheelZoomTarget
    const currentScale = clampScale((instance as any).scaleVal || 1)
    const diff = targetScale - currentScale
    const nextScale = Math.abs(diff) < 0.001 ? targetScale : currentScale + diff * ZOOM_EASING

    applyScaleAtPoint(nextScale, worldX, worldY, pointerX, pointerY)

    if (Math.abs(diff) < 0.001) {
      wheelZoomTarget = null
      wheelZoomFrame = null
      return
    }

    wheelZoomFrame = requestAnimationFrame(stepZoom)
  }

  const onWheel = (evt: WheelEvent) => {
    if (!mapEl.clientWidth || !mapEl.clientHeight) return

    // 支持触控板缩放（ctrlKey）并防止页面滚动
    evt.preventDefault()

    const delta = normalizeWheelDelta(evt)
    if (!delta) return

    const rect = container.getBoundingClientRect()
    if (!rect.width || !rect.height) return

    const pointerX = evt.clientX - rect.left
    const pointerY = evt.clientY - rect.top

    const currentScale = clampScale((instance as any).scaleVal || 1)
    const targetScale = clampScale(currentScale * (1 - delta * ZOOM_SENSITIVITY))
    if (targetScale === currentScale) return

    const originX = mapEl.clientWidth / 2
    const originY = mapEl.clientHeight / 2
    const worldX = (container.scrollLeft + pointerX - originX * (1 - currentScale)) / currentScale
    const worldY = (container.scrollTop + pointerY - originY * (1 - currentScale)) / currentScale

    stopWheelZoomAnimation()
    wheelZoomTarget = {
      targetScale,
      worldX,
      worldY,
      pointerX,
      pointerY,
    }
    wheelZoomFrame = requestAnimationFrame(stepZoom)
  }

  container.addEventListener('wheel', onWheel, { passive: false })

  return () => {
    stopWheelZoomAnimation()
    container.removeEventListener('wheel', onWheel)
  }
}

// ✅ 展开/收起所有节点
const toggleExpandAll = async () => {
  if (!mindInstance.value) return

  const instance = mindInstance.value as any
  const shouldExpand = !allExpanded.value

  // 直接修改数据模型的 expanded 状态，避免依赖 DOM
  const toggleNode = (node: any) => {
    if (!node) return
    if (node.children && Array.isArray(node.children) && node.children.length) {
      node.expanded = shouldExpand
      node.children.forEach((child: any) => toggleNode(child))
    }
  }

  const data = instance.getData?.() || instance.nodeData
  const rootNode = data?.nodeData || data
  if (rootNode) {
    // 确保根节点保持展开
    rootNode.expanded = true
    toggleNode(rootNode)
    // 重新布局更新展开状态
    if (instance.layout && instance.linkDiv) {
      instance.layout()
      instance.linkDiv()
    }
  }

  allExpanded.value = shouldExpand
  hasUnsavedChanges.value = true

  // ✅ 展开/收缩后自动居中
  await nextTick()
  await fitToView()
}

const handleFullscreenChange = async () => {
  isFullscreen.value = !!document.fullscreenElement
  if (isFullscreen.value && mindInstance.value) {
    await nextTick()
    await fitToView()
  }
}

const toggleFullscreen = async () => {
  if (!mindmapContainer.value) return
  try {
    if (!document.fullscreenElement && mindmapContainer.value.requestFullscreen) {
      await mindmapContainer.value.requestFullscreen()
    } else if (document.exitFullscreen) {
      await document.exitFullscreen()
    }
  } catch (err) {
    console.error('切换全屏失败:', err)
    message.error('切换全屏失败，请重试')
  }
}

const exportMindmap = async () => {
  if (!mindInstance.value) {
    message.warning('请先打开思维导图')
    return
  }
  try {
    const painterModule = await import('mind-elixir/dist/painter')
    const painter = (painterModule as any).default || painterModule
    painter.exportPng(mindInstance.value, activeMindmap.value?.title || '思维导图')
  } catch (err) {
    console.error('导出思维导图失败:', err)
    message.error('导出失败，请稍后重试')
  }
}

const exitFullscreenIfNeeded = async () => {
  if (document.fullscreenElement && document.exitFullscreen) {
    try {
      await document.exitFullscreen()
    } catch (err) {
      console.warn('退出全屏失败:', err)
    }
  }
}

// ✅ 优化后的渲染函数
const renderMindmap = async () => {
  if (!activeMindmap.value) {
    console.error('无法渲染：activeMindmap 为空')
    return
  }
  
  if (!mindmapContainer.value) {
    console.error('无法渲染：mindmapContainer 为空')
    return
  }
  
  loadingMap.value = true
  
  try {
    const { default: MindElixir } = await import('mind-elixir')
    const isContainerReady = await waitForContainerReady()
    if (!isContainerReady) {
      console.warn('思维导图容器未准备好，跳过渲染')
      return
    }
    
    mindmapContainer.value.innerHTML = ''
    
    const mindElixirData = prepareMindmapData(activeMindmap.value)
    
    const rawData = toRaw(activeMindmap.value.data)
    const direction =
      typeof (rawData as any)?.direction === 'number'
        ? (rawData as any).direction
        : (MindElixir as any).SIDE ?? (MindElixir as any).RIGHT ?? 1
    
    // ✅ 优化的配置：清晰简洁的只读思维导图查看器
    const instance = new (MindElixir as any)({
      el: `#${mindmapElementId}`,
      direction,
      // 交互设置
      draggable: true,              // 允许拖动画布以便浏览
      editable: false,              // 禁止编辑节点内容
      contextMenu: false,           // 无右键菜单
      toolBar: false,               // 无工具栏（使用自定义工具栏）
      nodeMenu: false,              // 无节点菜单
      keypress: false,              // 无键盘快捷键
      mouseSelectionButton: 0,      // 左键选择节点
      // 视图设置
      alignment: 'nodes',           // 以整个思维导图为中心对齐
      overflowHidden: false,        // 允许画布移动
      // 缩放设置
      scaleSensitivity: 0.3,       // 滚轮缩放灵敏度（更平滑）
      // 布局设置
      primaryLinkStyle: 2,          // 连线样式：贝塞尔曲线
      primaryNodeHorizontalGap: 42, // 水平间距
      primaryNodeVerticalGap: 18,   // 垂直间距
      // 本地化
      locale: 'zh_CN',
      data: mindElixirData,
    })
    
    instance.init()

    // 等待渲染完成
    await nextTick()
    await new Promise(resolve => requestAnimationFrame(resolve))

    // 移除旧的滚轮缩放监听
    if (wheelCleanup) {
      wheelCleanup()
      wheelCleanup = null
    }

    mindInstance.value = instance

    // ✅ 自动居中显示
    await fitToView(instance)
    
    // ✅ 添加双击展开/收缩功能
    const canvas = mindmapContainer.value.querySelector('.map-canvas')
    if (canvas) {
      canvas.addEventListener('dblclick', (e: any) => {
        const target = e.target
        const nodeElement = target.closest('.node-container')
        if (nodeElement) {
          const nodeId = nodeElement.getAttribute('data-nodeid')
          if (nodeId && instance.selectNode) {
            const node = instance.getNodeById(nodeId)
            if (node && node.children && node.children.length > 0) {
              const isExpanded = node.expanded !== false
              instance.expandNode(node, !isExpanded)
              hasUnsavedChanges.value = true
            }
          }
        }
      })
    }
    
    // 鼠标滚轮缩放，保持指针附近位置（平滑缓动）
    const wheelRelease = bindSmoothWheelZoom(instance)
    if (wheelRelease) {
      wheelCleanup = wheelRelease
    }
    
    hasUnsavedChanges.value = false
    allExpanded.value = false
    
    console.log('思维导图渲染成功！')
  } catch (err) {
    console.error('渲染思维导图失败:', err)
    console.error('错误堆栈:', (err as Error).stack)
  } finally {
    loadingMap.value = false
  }
}

const openMindmap = async (id: string) => {
  activeMindmapId.value = id
  await nextTick()
  await renderMindmap()
}

const goBackToList = async () => {
  activeMindmapId.value = null
  if (mindInstance.value) {
    mindInstance.value = null
  }
  if (wheelCleanup) {
    wheelCleanup()
    wheelCleanup = null
  }
  await exitFullscreenIfNeeded()
  isFullscreen.value = false
}

const resetMindmap = async () => {
  if (!activeMindmap.value) return
  hasUnsavedChanges.value = false
  allExpanded.value = false
  await nextTick()
  await renderMindmap()
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
      model,
    })
    
    mindmaps.value = sortMindmaps([mindmap, ...mindmaps.value.filter(item => item.id !== mindmap.id)])
    generateModal.open = false
    activeMindmapId.value = mindmap.id
    await nextTick()
    await renderMindmap()
    message.success('已生成思维导图')
  } catch (err) {
    console.error('生成思维导图失败:', err)
    message.error(getErrorMessage(err))
  } finally {
    generateModal.loading = false
    generating.value = false
  }
}

let resizeObserver: ResizeObserver | null = null
let wheelCleanup: (() => void) | null = null
let wheelZoomFrame: number | null = null
let wheelZoomTarget: WheelZoomTarget | null = null

onMounted(() => {
  document.addEventListener('fullscreenchange', handleFullscreenChange)
})

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  if (wheelCleanup) {
    wheelCleanup()
    wheelCleanup = null
  }
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  exitFullscreenIfNeeded()
})

watch(
  () => activeNotebookId.value,
  id => {
    activeMindmapId.value = null
    if (mindInstance.value) {
      mindInstance.value = null
    }
    if (wheelCleanup) {
      wheelCleanup()
      wheelCleanup = null
    }
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
      if (mindInstance.value) {
        mindInstance.value = null
      }
      if (wheelCleanup) {
        wheelCleanup()
        wheelCleanup = null
      }
      if (resizeObserver) {
        resizeObserver.disconnect()
        resizeObserver = null
      }
      await exitFullscreenIfNeeded()
      isFullscreen.value = false
      return
    }
    await nextTick()
    await renderMindmap()
    
    // ✅ 监听容器大小变化，自动重新居中（带防抖）
    if (mindmapContainer.value && typeof ResizeObserver !== 'undefined') {
      let resizeTimer: number | null = null
      resizeObserver = new ResizeObserver(() => {
        if (resizeTimer) clearTimeout(resizeTimer)
        resizeTimer = window.setTimeout(() => {
          if (mindInstance.value) {
            fitToView()
          }
        }, 150)
      })
      resizeObserver.observe(mindmapContainer.value)
    }
  },
)
</script>

<style scoped>
.mindmap-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.panel-shell {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  padding: 16px;
  overflow: hidden;
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
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: auto;
  width: 100%;
  position: relative;
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

.folder-materials {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.material-tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 10px;
  color: #475569;
  font-size: 11px;
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
  flex-shrink: 0;
}

.mindmap-head {
  min-width: 0;
  flex: 1;
}

.mindmap-title {
  font-size: 19px;
  font-weight: 700;
  color: #0f172a;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.mindmap-sub {
  margin-top: 4px;
  color: #475569;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.mindmap-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  flex-wrap: wrap;
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
  flex-shrink: 0;
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
  white-space: nowrap;
}

.ghost-btn:hover {
  border-color: #16a34a;
  color: #16a34a;
  background: rgba(22, 163, 74, 0.08);
}

/* ✅ 优化：移除滚动条，让 MindElixir 自带的工具栏可见 */
.mindmap-canvas {
  flex: 1;
  min-height: 400px;
  min-width: 0;
  width: 100%;
  max-width: 100%;
  border-radius: 14px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #f9fafb;
  overflow: hidden;
  position: relative;
  box-sizing: border-box;
}

.canvas-actions {
  position: fixed;
  right: 58px;
  bottom: 48px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 4;
}

.canvas-action-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  width: 38px;
  height: 38px;
  padding: 0;
  border-radius: 12px;
  border: 1px solid transparent;
  background: #f9fafb;
  box-shadow: none;
  color: #0f172a;
  cursor: pointer;
  transition: all 0.2s ease;
}

.canvas-action-btn:hover {
  transform: translateY(-1px) scale(1.02);
  border-color: rgba(15, 23, 42, 0.12);
  background: #f1f5f9;
}

.action-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.canvas-action-btn::after {
  content: attr(data-label);
  position: absolute;
  left: 50%;
  bottom: 100%;
  transform: translate(-50%, -10px);
  padding: 4px 8px;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.16s ease, transform 0.16s ease;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18);
}

.canvas-action-btn:hover::after {
  opacity: 1;
  transform: translate(-50%, -14px);
}

/* ✅ MindElixir 容器样式优化 */
:deep(.mind-elixir) {
  height: 100%;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  border-radius: 14px;
  overflow: hidden;
  box-sizing: border-box;
  --me-primary: #2563eb;
  --me-primary-soft: #dbeafe;
  --me-secondary: #f97316;
  --me-leaf: #22c55e;
  --me-muted: #94a3b8;
}

:deep(.mind-elixir .map-container) {
  height: 100%;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow: hidden !important;
  border-radius: inherit;
  background: transparent;
  box-sizing: border-box;
}

:deep(.mind-elixir .map-canvas) {
  position: relative;
  background: transparent;
  cursor: grab;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

:deep(.mind-elixir .map-canvas:active) {
  cursor: grabbing;
}

/* 线条风格：更接近官方示例的平滑圆角 */
:deep(.mind-elixir .map-container line),
:deep(.mind-elixir .map-container path) {
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke: var(--me-muted);
  stroke-width: 2px;
  fill: none;
}

:deep(.mind-elixir .map-container .svg2nd line) {
  stroke: var(--me-primary);
  stroke-width: 2.4px;
  opacity: 0.92;
}

:deep(.mind-elixir .map-container .svg3rd line) {
  stroke: var(--me-secondary);
  stroke-width: 2.1px;
  opacity: 0.8;
}

:deep(.mind-elixir .topiclinks path) {
  stroke: #ef4444;
  stroke-width: 2.2px;
  opacity: 0.85;
}

/* ✅ 优化工具栏样式 - 保持原生风格但稍作美化 */
:deep(.mind-elixir .toolbar) {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  flex-wrap: wrap;
  max-width: calc(100% - 40px);
  margin: 12px 20px;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 10;
}

:deep(.mind-elixir .toolbar button) {
  padding: 6px 12px;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #475569;
  font-size: 13px;
  white-space: nowrap;
  min-width: 36px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
}

:deep(.mind-elixir .toolbar button:hover) {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

:deep(.mind-elixir .toolbar button:active) {
  background: rgba(59, 130, 246, 0.15);
}

:deep(.mind-elixir .toolbar button svg) {
  width: 18px;
  height: 18px;
}

/* ✅ 大幅优化节点展开/收缩按钮样式 - 更大、更醒目、完美居中 */
:deep(.mind-elixir me-epd),
:deep(.mind-elixir [class*="epd"]) {
  width: 28px !important;
  height: 28px !important;
  min-width: 28px !important;
  min-height: 28px !important;
  border-radius: 50% !important;
  background: var(--me-primary) !important;
  border: 3px solid #fff !important;
  box-shadow: 0 3px 10px rgba(59, 130, 246, 0.35) !important;
  cursor: pointer !important;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-size: 18px !important;
  font-weight: bold !important;
  color: #fff !important;
  line-height: 1 !important;
  z-index: 10 !important;
  position: absolute !important;
}

/* ✅ 确保加号/减号完美居中 */
:deep(.mind-elixir me-epd::before),
:deep(.mind-elixir [class*="epd"]::before) {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 100% !important;
  height: 100% !important;
  line-height: 1 !important;
}

:deep(.mind-elixir me-epd:hover),
:deep(.mind-elixir [class*="epd"]:hover) {
  background: #1d4ed8 !important;
  transform: scale(1.15) !important;
  box-shadow: 0 5px 16px rgba(37, 99, 235, 0.45) !important;
}

:deep(.mind-elixir me-epd:active),
:deep(.mind-elixir [class*="epd"]:active) {
  transform: scale(1.05) !important;
}

/* ✅ 主节点的展开/收缩按钮位置优化 */
:deep(.mind-elixir me-main > me-wrapper > me-parent > me-epd) {
  top: 50% !important;
  transform: translateY(-50%) !important;
}

/* ✅ 子节点的展开/收缩按钮位置 */
:deep(.mind-elixir me-epd) {
  top: 100% !important;
  transform: translateY(-50%) !important;
}

/* ✅ 左侧节点的展开/收缩按钮 */
:deep(.mind-elixir .lhs > me-wrapper > me-parent > me-epd) {
  left: -14px !important;
}

:deep(.mind-elixir .lhs me-epd) {
  left: 8px !important;
}

/* ✅ 右侧节点的展开/收缩按钮 */
:deep(.mind-elixir .rhs > me-wrapper > me-parent > me-epd) {
  right: -14px !important;
}

:deep(.mind-elixir .rhs me-epd) {
  right: 8px !important;
}

/* ✅ 节点主题更贴近官方示例，带柔和阴影与配色 */
:deep(.mind-elixir root tpc) {
  background: var(--me-primary);
  color: #fff;
  border-radius: 14px;
  padding: 12px 18px;
  font-weight: 800;
}

:deep(.mind-elixir .box > grp > t > tpc) {
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 12px;
  padding: 10px 14px;
  color: #0f172a;
}

:deep(.mind-elixir .box > grp.rhs > t > tpc) {
  border-left: 3px solid var(--me-primary);
}

:deep(.mind-elixir .box > grp.lhs > t > tpc) {
  border-right: 3px solid var(--me-leaf);
}

:deep(.mind-elixir tpc .tags span) {
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
}

:deep(.mind-elixir .map-canvas .selected) {
  outline: 2px solid var(--me-primary);
}

/* ✅ 节点样式优化 - 添加悬停效果和交互提示 */
:deep(.mind-elixir .node-container) {
  cursor: pointer !important;
  transition: all 0.2s ease !important;
  position: relative !important;
}

:deep(.mind-elixir .node-container:hover) {
  transform: translateY(-1px) !important;
}

/* ✅ 节点悬停边框效果 */
:deep(.mind-elixir .node-container::after) {
  content: '' !important;
  position: absolute !important;
  top: -2px !important;
  left: -2px !important;
  right: -2px !important;
  bottom: -2px !important;
  pointer-events: none !important;
  border: 2px solid transparent !important;
  border-radius: 6px !important;
  transition: border-color 0.2s ease !important;
}

:deep(.mind-elixir .node-container:hover::after) {
  border-color: rgba(59, 130, 246, 0.4) !important;
}

.canvas-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  border-radius: 14px;
}

.panel-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border-radius: 20px;
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
