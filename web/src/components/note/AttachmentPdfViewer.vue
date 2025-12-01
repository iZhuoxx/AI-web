<template>
  <div ref="viewerEl" class="pdf-viewer">
    <div class="pdf-toolbar">
      <div class="toolbar-section">
        <button
          v-if="props.showBack"
          class="toolbar-btn"
          type="button"
          @click="emit('back')"
        >
          <ArrowLeftIcon class="toolbar-icon" />
        </button>
        <button class="toolbar-btn" type="button" :class="{ active: showThumbs }" @click="toggleThumbs">
          <PanelLeftOpenIcon class="toolbar-icon" />
        </button>
        <button class="toolbar-btn" type="button" :class="{ active: showSearch }" @click="toggleSearch">
          <SearchIcon class="toolbar-icon" />
        </button>
      </div>

      <div class="toolbar-section toolbar-section--center">
        <div class="pager">
          <div class="page-input-wrap">
            <input
              class="page-input"
              :value="page"
              type="number"
              min="1"
              :max="total"
              @input="onPageInput"
            />
            <span class="page-total">/ {{ total }}</span>
          </div>
        </div>
        <div class="scale-control">
          <div ref="scaleDropdownEl" class="scale-dropdown">
            <button class="toolbar-btn scale-toggle" type="button" @click="toggleScaleMenu">
              <span>{{ scaleMode === 'fit-width' ? 'Page fit' : `${Math.round(currentScale * 100)}%` }}</span>
              <ChevronDownIcon class="toolbar-icon" />
            </button>
            <div v-if="showScaleMenu" class="scale-menu">
              <div class="scale-menu__header">
                <span class="scale-menu__value">{{ Math.round(currentScale * 100) }}%</span>
                <div class="scale-menu__steps">
                  <button class="scale-step" type="button" @click="stepScale(-0.1)">-</button>
                  <button class="scale-step" type="button" @click="stepScale(0.1)">+</button>
                </div>
              </div>
              <button
                type="button"
                class="scale-menu__item"
                :class="{ active: scaleMode === 'fit-width' }"
                @click="setFitWidth"
              >
                Page width
              </button>
              <button
                v-for="option in scaleOptions"
                :key="option"
                type="button"
                class="scale-menu__item"
                :class="{ active: scaleMode === 'custom' && isScaleActive(option) }"
                @click="selectScale(option)"
              >
                {{ Math.round(option * 100) }}%
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="toolbar-section toolbar-section--right">
        <button class="toolbar-btn" type="button" @click="rotateClockwise">
          <RotateCwIcon class="toolbar-icon" />
        </button>
        <button class="toolbar-btn" type="button" @click="emit('download')">
          <DownloadIcon class="toolbar-icon" />
        </button>
        <button class="toolbar-btn" type="button" @click="toggleFullscreen">
          <Maximize2Icon class="toolbar-icon" />
        </button>
      </div>
    </div>

    <div class="pdf-body">
      <aside v-if="showThumbs" class="thumbs-panel">
        <div
          v-for="pageNumber in thumbnails"
          :key="pageNumber"
          class="thumb-item"
          :class="{ active: pageNumber === page }"
          @click="setPage(pageNumber)"
        >
          <VuePdfEmbed
            :source="documentSource"
            :page="pageNumber"
            :scale="0.3"
            :rotation="rotation"
            class="thumb-canvas"
            @error="onError"
          />
          <span class="thumb-label">Page {{ pageNumber }}</span>
        </div>
      </aside>

      <aside v-if="showSearch" class="search-panel">
        <div class="search-box">
          <SearchIcon class="search-box__icon" />
          <input
            v-model="searchQuery"
            class="search-input"
            type="text"
            placeholder="搜索文档内容..."
            @keyup.enter="runSearch"
          />
          <button class="toolbar-btn" type="button" :disabled="searching || !searchQuery.trim()" @click="runSearch">
            <SearchIcon class="toolbar-icon" />
          </button>
        </div>
        <div class="search-results">
          <div v-if="searching" class="searching">
            <a-spin size="small" />
            <span>搜索中...</span>
          </div>
          <div v-else-if="!searchResults.length" class="empty">
            {{ searchQuery.trim() ? '暂无搜索结果' : '输入关键字后按回车开始搜索' }}
          </div>
          <button
            v-else
            v-for="result in searchResults"
            :key="result.id"
            class="search-result"
            type="button"
            @click="jumpTo(result.page)"
          >
            <span class="result-page">Page {{ result.page }}</span>
            <span class="result-text">{{ result.snippet }}</span>
          </button>
        </div>
      </aside>

      <div ref="mainEl" class="pdf-main" @click="activateWheelControl">
        <div v-if="error" class="viewer-error">{{ error }}</div>
        <VuePdfEmbed
          v-else
          :key="renderKey"
          ref="pdfEmbedRef"
          class="pdf-canvas"
          :id="viewerId"
          :source="documentSource"
          :page="thumbnails"
          :scale="1"
          :width="displayWidth"
          :rotation="rotation"
          text-layer
          @loaded="onLoaded"
          @rendered="onRendered"
          @error="onError"
        />
        <div v-if="loading" class="viewer-overlay">
          <a-spin />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { message } from 'ant-design-vue'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  ChevronDownIcon,
  DownloadIcon,
  Maximize2Icon,
  PanelLeftOpenIcon,
  RotateCwIcon,
  SearchIcon,
  ArrowLeftIcon,
} from 'lucide-vue-next'
import VuePdfEmbed from 'vue-pdf-embed'
import * as pdfjsLib from 'pdfjs-dist'
import 'vue-pdf-embed/dist/styles/textLayer.css'

type PdfPageProxy = {
  getViewport: (params: { scale: number; rotation?: number }) => { width: number; height: number }
  getTextContent: (params?: any) => Promise<{ items: Array<{ str?: string }> }>
}

type PdfDocumentLike = {
  numPages: number
  getPage: (pageNumber: number) => Promise<PdfPageProxy>
  destroy?: () => Promise<void> | void
}

type PdfDocumentLoadingTaskLike = {
  promise: Promise<PdfDocumentLike>
  destroy?: () => Promise<void> | void
}

type PdfEmbedInstance = InstanceType<typeof VuePdfEmbed> & { document?: PdfDocumentLike }

type ViewerPDFDocumentProxy = Parameters<
  NonNullable<InstanceType<typeof VuePdfEmbed>['$props']['onLoaded']>
>[0]

// 修复: 设置 worker 路径
if (typeof pdfjsLib.GlobalWorkerOptions !== 'undefined') {
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url
  ).toString()
}

const props = defineProps<{
  source: string
  showBack?: boolean
  focusText?: string | null
  focusTrigger?: number
}>()

const emit = defineEmits<{
  (e: 'download'): void
  (e: 'back'): void
}>()

const resolveDocumentSource = () => ({
  url: props.source,
  withCredentials: true,
})
const documentSource = computed(resolveDocumentSource)

const page = ref(1)
const total = ref(1)
const scale = ref(1)
const fitScale = ref<number | null>(null)
const scaleMode = ref<'custom' | 'fit-width'>('custom')
const rotation = ref(0)
const viewerId = 'pdf-viewer'
const loading = ref(true)
const error = ref<string | null>(null)
const pdfEmbedRef = ref<PdfEmbedInstance | null>(null)
// 修复: 使用与 VuePdfEmbed 事件一致的 PDF 类型
const pdfDoc = ref<ViewerPDFDocumentProxy | PdfDocumentLike | null>(null)
const showThumbs = ref(false)
const showSearch = ref(false)
const viewerEl = ref<HTMLElement | null>(null)
const mainEl = ref<HTMLElement | null>(null)
const scaleDropdownEl = ref<HTMLElement | null>(null)
const showScaleMenu = ref(false)
const containerWidth = ref(800)
const wheelActive = ref(false)
const searchQuery = ref('')
const searchResults = ref<{ page: number; snippet: string; id: string }[]>([])
const searching = ref(false)
const textCache = ref<Record<number, string>>({})
const searchDoc = ref<PdfDocumentLike | null>(null)
const searchLoadingTask = ref<PdfDocumentLoadingTaskLike | null>(null)
const scaleOptions = [0.5, 0.75, 1, 1.25, 1.5, 2, 3]
// 修复: 添加独立的 render key 来强制重新渲染
const renderKey = ref(0)

const thumbnails = computed(() => Array.from({ length: total.value }, (_, idx) => idx + 1))
const currentScale = computed(() => (scaleMode.value === 'fit-width' ? fitScale.value ?? scale.value : scale.value))
const baseWidth = computed(() => Math.max(containerWidth.value, 100))
const displayWidth = computed(() =>
  scaleMode.value === 'fit-width' ? baseWidth.value : Math.max(baseWidth.value * scale.value, 50),
)

const clampScale = (value: number) => {
  const next = Math.min(Math.max(value, 0.5), 3)
  return parseFloat(next.toFixed(3))
}

const cleanupSearchDoc = async () => {
  const loadingTask = searchLoadingTask.value
  const doc = searchDoc.value

  try {
    if (loadingTask?.destroy) {
      await loadingTask.destroy()
    }
  } catch (err) {
    console.error('Failed to destroy search loading task:', err)
  } finally {
    searchLoadingTask.value = null
  }

  try {
    if (doc?.destroy) {
      await doc.destroy()
    }
  } catch (err) {
    console.error('Failed to destroy search document:', err)
  } finally {
    searchDoc.value = null
  }
}

const loadSearchDocument = async (): Promise<PdfDocumentLike | null> => {
  // Prefer the actual pdf.js document from the viewer ref
  if (pdfEmbedRef.value?.document) {
    return pdfEmbedRef.value.document
  }

  if (searchDoc.value) return searchDoc.value
  if (searchLoadingTask.value) return searchLoadingTask.value.promise

  try {
    const task = pdfjsLib.getDocument(resolveDocumentSource()) as PdfDocumentLoadingTaskLike
    searchLoadingTask.value = task
    const doc = await task.promise
    searchDoc.value = doc
    total.value = doc.numPages || total.value
    return doc
  } catch (err) {
    console.error('Failed to load PDF for search:', err)
    return null
  }
}

const resetState = () => {
  void cleanupSearchDoc()
  page.value = 1
  total.value = 1
  scale.value = 1
  fitScale.value = null
  scaleMode.value = 'custom'
  rotation.value = 0
  loading.value = true
  error.value = null
  pdfDoc.value = null
  searchQuery.value = ''
  searchResults.value = []
  searching.value = false
  textCache.value = {}
  showScaleMenu.value = false
  renderKey.value = 0
}

const updateContainerWidth = () => {
  containerWidth.value = Math.max(mainEl.value?.clientWidth ?? 0, 100)
  renderKey.value++
}

const activateWheelControl = () => {
  wheelActive.value = true
}

const handleWheel = (event: WheelEvent) => {
  if (!wheelActive.value) return
  if (!event.ctrlKey) return
  event.preventDefault()
  const delta = event.deltaY > 0 ? -0.1 : 0.1
  scaleMode.value = 'custom'
  setScale(currentScale.value + delta)
}

watch(
  () => props.source,
  () => {
    resetState()
    nextTick(() => {
      updateContainerWidth()
    })
  },
  { immediate: true },
)

watch(
  () => [props.focusText, props.focusTrigger],
  async ([text]) => {
    const query = (text ?? '').toString().trim()
    if (!query) return
    searchQuery.value = query
    showSearch.value = true
    await nextTick()
    await runSearch({ autoJump: true })
  },
)

// 修复: 监听 scale 变化并强制重新渲染
watch([() => scale.value, () => fitScale.value, () => scaleMode.value], () => {
  renderKey.value++
})

watch(
  () => page.value,
  () => {
    if (scaleMode.value === 'fit-width') {
      nextTick(() => {
        updateContainerWidth()
        updateFitScale()
      })
    }
  },
)

const onLoaded = (pdf: ViewerPDFDocumentProxy) => {
  pdfDoc.value = pdf
  total.value = pdf?.numPages || 1
  loading.value = false
  if (scaleMode.value === 'fit-width') {
    nextTick(() => updateFitScale())
  }
}

// 修复: 添加 rendered 事件处理
const onRendered = () => {
  loading.value = false
}

const onError = (err: any) => {
  const errorMsg = err?.message || 'PDF 预览失败'
  error.value = errorMsg
  loading.value = false
  message.error(errorMsg)
}

const setPage = (value: number) => {
  if (!value) return
  page.value = Math.min(Math.max(Math.round(value), 1), total.value || 1)
  scrollToPage(page.value)
}

const onPageInput = (event: Event) => {
  const value = Number((event.target as HTMLInputElement)?.value ?? 1)
  if (Number.isFinite(value)) setPage(value)
}

const setScale = (value: number) => {
  const next = clampScale(Number(value) || 1)
  scaleMode.value = 'custom'
  scale.value = next
  fitScale.value = null
}

const selectScale = (value: number) => {
  setScale(value)
  showScaleMenu.value = false
}

const stepScale = (delta: number) => {
  setScale(currentScale.value + delta)
}

const updateFitScale = async () => {
  if (!pdfDoc.value || !mainEl.value) return
  try {
    const containerWidthValue = Math.max(mainEl.value?.clientWidth ?? 0, 100)
    containerWidth.value = containerWidthValue
    const pdfPage = await pdfDoc.value.getPage(page.value)
    const viewport = pdfPage.getViewport({ scale: 1, rotation: rotation.value })
    const next = clampScale(containerWidthValue / viewport.width)
    fitScale.value = next
  } catch (err) {
    console.error('Failed to calculate fit scale:', err)
  }
}

const setFitWidth = () => {
  scaleMode.value = 'fit-width'
  nextTick(() => {
    updateContainerWidth()
    updateFitScale()
  })
  showScaleMenu.value = false
}

const toggleScaleMenu = () => {
  showScaleMenu.value = !showScaleMenu.value
}

const isScaleActive = (value: number) => Math.abs(currentScale.value - value) < 0.001

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as Node
  if (mainEl.value && !mainEl.value.contains(target)) {
    wheelActive.value = false
  }
  if (!showScaleMenu.value) return
  if (scaleDropdownEl.value && !scaleDropdownEl.value.contains(target)) {
    showScaleMenu.value = false
  }
}

const rotateClockwise = () => {
  rotation.value = (rotation.value + 90) % 360
  renderKey.value++
  if (scaleMode.value === 'fit-width') {
    nextTick(() => updateFitScale())
  }
}

const toggleThumbs = () => {
  showThumbs.value = !showThumbs.value
  if (scaleMode.value === 'fit-width') {
    nextTick(() => {
      updateContainerWidth()
      updateFitScale()
    })
  }
}

const toggleSearch = () => {
  showSearch.value = !showSearch.value
  if (scaleMode.value === 'fit-width') {
    nextTick(() => {
      updateContainerWidth()
      updateFitScale()
    })
  }
}

const toggleFullscreen = async () => {
  if (!viewerEl.value) return
  if (document.fullscreenElement) {
    await document.exitFullscreen()
  } else {
    await viewerEl.value.requestFullscreen()
  }
}

const scrollToPage = (targetPage: number) => {
  const el = document.getElementById(`${viewerId}-${targetPage}`)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// 修复: 使用正确的 pdfjs API 获取页面文本
const getPageText = async (pageNumber: number, doc?: PdfDocumentLike | null): Promise<string> => {
  if (textCache.value[pageNumber]) return textCache.value[pageNumber]
  const targetDoc = doc ?? (await loadSearchDocument())
  if (!targetDoc) return ''

  try {
    const page = await targetDoc.getPage(pageNumber)
    const textContent = await page.getTextContent({
      includeMarkedContent: true,
      normalizeWhitespace: true,
    })
    const strings = textContent.items
      .map((item: { str?: string }) => item.str || '')
      .filter(Boolean)
    const text = strings.join(' ')
    textCache.value[pageNumber] = text
    return text
  } catch (err) {
    console.error(`Failed to extract text from page ${pageNumber}:`, err)
    return ''
  }
}

type RunSearchOptions = { autoJump?: boolean }

const resolveRunSearchOptions = (payload?: RunSearchOptions | Event): RunSearchOptions | undefined => {
  if (payload && typeof payload === 'object' && 'autoJump' in (payload as any)) {
    return payload as RunSearchOptions
  }
  return undefined
}

const runSearch = async (payload?: RunSearchOptions | Event) => {
  const options = resolveRunSearchOptions(payload)
  const query = searchQuery.value.trim()
  if (!query) return

  searching.value = true
  searchResults.value = []
  const keyword = query.toLowerCase()
  const results: { page: number; snippet: string; id: string }[] = []

  try {
    const doc = await loadSearchDocument()
    if (!doc) {
      message.warning('PDF 尚未加载完成')
      return
    }

    const pageCount = doc.numPages || total.value
    total.value = pageCount

    for (let i = 1; i <= pageCount; i += 1) {
      try {
        const originalText = await getPageText(i, doc)
        const text = originalText.toLowerCase()
        let searchStart = 0

        while (true) {
          const index = text.indexOf(keyword, searchStart)
          if (index === -1) break

          const start = Math.max(0, index - 32)
          const end = Math.min(originalText.length, index + keyword.length + 32)
          const snippet = originalText.substring(start, end).trim()
          results.push({
            page: i,
            snippet: snippet || originalText.substring(index, index + keyword.length),
            id: `${i}-${index}`,
          })

          searchStart = index + keyword.length
        }
      } catch (err) {
        console.error(`Error searching page ${i}:`, err)
      }
    }

    searchResults.value = results

    if (!results.length) {
      if (!options?.autoJump) {
        message.info('未找到匹配内容')
      }
    } else {
      if (!options?.autoJump) {
        message.success(`找到 ${results.length} 处匹配`)
      }
      if (options?.autoJump) {
        jumpTo(results[0].page)
      }
    }
  } finally {
    searching.value = false
  }
}

const jumpTo = (targetPage: number) => {
  setPage(targetPage)
}

const handleResize = () => {
  updateContainerWidth()
  if (scaleMode.value === 'fit-width') {
    updateFitScale()
  }
}

const handleKeydown = (event: KeyboardEvent) => {
  if (!document.fullscreenElement) return
  if (event.key === 'Escape') {
    document.exitFullscreen()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  window.addEventListener('resize', handleResize)
  document.addEventListener('click', handleClickOutside)
  nextTick(() => {
    if (mainEl.value) {
      mainEl.value.addEventListener('wheel', handleWheel, { passive: false })
    }
  })
  nextTick(() => {
    updateContainerWidth()
    if (scaleMode.value === 'fit-width') {
      updateFitScale()
    }
  })
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('click', handleClickOutside)
  if (mainEl.value) {
    mainEl.value.removeEventListener('wheel', handleWheel)
  }
  void cleanupSearchDoc()
})
</script>

<style scoped>
.pdf-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
}

.pdf-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid #edf0f5;
  background: #fff;
}

.toolbar-section {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.toolbar-section--center {
  flex: 1;
  justify-content: center;
  gap: 10px;
}

.toolbar-section--right {
  margin-left: auto;
}

.toolbar-btn {
  height: 28px;
  min-width: 28px;
  padding: 0 8px;
  border-radius: 8px;
  border: 1px solid #e6eaf3;
  background: #fff;
  color: #1f2937;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toolbar-btn.active {
  background: #eef4ff;
  border-color: #d7e5ff;
  color: #1677ff;
}

.toolbar-btn:hover {
  background: #eef4ff;
  color: #1677ff;
  border-color: #d7e5ff;
}

.toolbar-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.toolbar-icon {
  width: 14px;
  height: 14px;
}

.pager {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
}

.page-input-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.page-input {
  width: 36px;
  height: 28px;
  border: 1px solid #e6eaf3;
  border-radius: 8px;
  background: #fff;
  text-align: center;
  outline: none;
  font-weight: 600;
  color: #0f172a;
  font-size: 13px;
}

.page-input::-webkit-inner-spin-button,
.page-input::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.page-total {
  color: rgba(17, 24, 39, 0.55);
  font-size: 12px;
}

.scale-control {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
}

.scale-dropdown {
  position: relative;
}

.scale-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  height: 32px;
}

.scale-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  min-width: 170px;
  background: #fff;
  border: 1px solid #e6eaf3;
  border-radius: 12px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
  padding: 10px;
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.scale-menu__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.scale-menu__value {
  font-weight: 700;
  color: #0f172a;
}

.scale-menu__steps {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.scale-step {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 1px solid #e6eaf3;
  background: #f8fafc;
  font-weight: 700;
  color: #0f172a;
  cursor: pointer;
  transition: all 0.2s ease;
}

.scale-step:hover {
  background: #eef4ff;
  border-color: #d7e5ff;
}

.scale-menu__item {
  width: 100%;
  text-align: left;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 8px 10px;
  background: #fff;
  color: #0f172a;
  cursor: pointer;
  transition: all 0.2s ease;
}

.scale-menu__item:hover {
  border-color: #d7e5ff;
  background: #f6f9ff;
}

.scale-menu__item.active {
  background: #eef4ff;
  border-color: #d7e5ff;
  color: #1677ff;
}

.pdf-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 0;
  background: #fff;
  padding: 0;
}

.thumbs-panel {
  width: 160px;
  background: #fff;
  border: 1px solid #e6eaf3;
  border-radius: 8px;
  padding: 6px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.thumb-item {
  border: 1px solid #e6eaf3;
  border-radius: 8px;
  padding: 4px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.thumb-item.active {
  border-color: #1677ff;
  box-shadow: 0 6px 12px rgba(22, 119, 255, 0.1);
}

.thumb-canvas {
  width: 100%;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
}

.thumb-label {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: rgba(17, 24, 39, 0.65);
  text-align: center;
}

.pdf-main {
  position: relative;
  flex: 1;
  min-width: 0;
  background: #fff;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow: auto;
  padding: 0;
}

.pdf-canvas {
  display: inline-block;
  flex-shrink: 0;
  width: fit-content;
  height: fit-content;
  background: #fff;
}

/* outer wrapper */
.pdf-canvas :deep(.vue-pdf-embed) {
  display: inline-block;
  width: fit-content;
}

/* page wrapper */
.pdf-canvas :deep(.vue-pdf-embed__page) {
  width: fit-content;
  height: fit-content;
}

/* Allow zoom to visually resize the canvas instead of being capped by max-width */
.pdf-canvas :deep(canvas) {
  max-width: none !important;
  height: auto !important;
}

.pdf-canvas :deep(.textLayer span) {
  color: transparent !important;
  -webkit-text-fill-color: transparent;
  text-shadow: none;
}

.pdf-canvas :deep(.textLayer span::selection),
.pdf-canvas :deep(.textLayer ::selection) {
  color: transparent !important;
  -webkit-text-fill-color: transparent;
  text-shadow: none;
}

.viewer-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.8);
  z-index: 2;
}

.viewer-error {
  color: #b91c1c;
  font-weight: 600;
}

.search-panel {
  width: 220px;
  background: #fff;
  border: 1px solid #e6eaf3;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  padding: 8px;
  gap: 8px;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border: 1px solid #e6eaf3;
  border-radius: 8px;
  background: #fff;
}

.search-box__icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 14px;
  height: 14px;
  color: #94a3b8;
  pointer-events: none;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 14px;
  padding-left: 26px;
}

.search-results {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.search-result {
  text-align: left;
  border: 1px solid #e6eaf3;
  border-radius: 8px;
  padding: 8px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.search-result:hover {
  border-color: #1677ff;
  box-shadow: 0 8px 16px rgba(22, 119, 255, 0.08);
}

.result-page {
  display: block;
  font-weight: 700;
  color: #0f172a;
}

.result-text {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.7);
  word-break: break-word;
}

.searching {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(17, 24, 39, 0.65);
  font-size: 13px;
}

.empty {
  color: rgba(17, 24, 39, 0.55);
  text-align: center;
  font-size: 13px;
}
</style>
