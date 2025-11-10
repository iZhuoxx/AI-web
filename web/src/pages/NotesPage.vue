<template>
  <div class="notes-page">
    <div class="page-content">
      <div v-if="isNotesFullscreen" class="fullscreen-editor">
        <NoteEditorPanel
          :notes="notes"
          :isGenerating="isGeneratingNotes"
          :isFullscreen="true"
          :showSyncButton="!shouldAutoSyncNotes"
          @toggle-fullscreen="isNotesFullscreen = false"
          @user-edit="handleNoteEdited"
          @request-sync="restoreAutoSync"
        />
      </div>
      <div v-else class="workspace" ref="gridRef" :style="workspaceStyles">
        <section class="left-pane">
          <NoteEditorPanel
            :notes="notes"
            :isGenerating="isGeneratingNotes"
            :isFullscreen="false"
            :showSyncButton="!shouldAutoSyncNotes"
            @toggle-fullscreen="isNotesFullscreen = true"
            @user-edit="handleNoteEdited"
            @request-sync="restoreAutoSync"
          />
        </section>

        <div class="vertical-handle" :class="{ active: verticalDragging }" @mousedown="startVerticalDrag" />

        <section class="right-pane">
          <NoteRecordingPanel
            :canRecord="canRecord"
            :isConnected="isConnected"
            :connectionReady="connectionReady"
            :isRecording="isRecording"
            :isPaused="isPaused"
            :duration="duration"
            :segments="transcriptSegments"
            :liveText="liveText"
            :audioLevel="audioLevel"
            :errorMessage="recordingError || undefined"
            @start="handleStartRecording"
            @stop="handleStopRecording"
            @pause="handlePauseRecording"
            @resume="handleResumeRecording"
          />
          <div class="tabs-wrapper">
            <a-tabs v-model:activeKey="activeTab" class="tabs">
              <a-tab-pane key="chat" tab="AI 对话">
                <NoteChatPanel />
              </a-tab-pane>
              <a-tab-pane key="realtime" tab="实时字幕">
                <NoteTranscriptionPanel :segments="transcriptSegments" :live-text="liveText" :isRecording="isRecording" />
              </a-tab-pane>
              <a-tab-pane key="keywords" tab="重点分析">
                <NoteKeywordsPanel :keywords="keywords" @keyword-selected="handleKeywordSelected" />
              </a-tab-pane>
              <a-tab-pane key="learning" tab="学习路径">
                <NoteLearningPathPanel :materials="materialsForLearning" :keywords="keywords" :isLoading="isLoadingMaterials" />
              </a-tab-pane>
              <a-tab-pane key="materials" tab="资料库">
                <NoteMaterialsPanel />
              </a-tab-pane>
            </a-tabs>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import NoteEditorPanel from '@/components/note/NoteEditorPanel.vue'
import NoteRecordingPanel from '@/components/note/NoteRecordingPanel.vue'
import NoteChatPanel from '@/components/note/NoteChatPanel.vue'
import NoteKeywordsPanel from '@/components/note/NoteKeywordsPanel.vue'
import NoteLearningPathPanel from '@/components/note/NoteLearningPathPanel.vue'
import NoteMaterialsPanel from '@/components/note/NoteMaterialsPanel.vue'
import NoteTranscriptionPanel from '@/components/note/NoteTranscriptionPanel.vue'
import { useRealtimeTranscription } from '@/composables/useRealtimeTranscription'
import type { KeywordItem, LearningMaterial, NoteItem, TranscriptSegment } from '@/types/notes'

const { canRecord, isConnected, connectionReady, isRecording, isPaused, duration, audioLevel, segments, liveText, transcriptText, errorMessage, startRecording, stopRecording, pauseRecording, resumeRecording, cancelRecording } = useRealtimeTranscription()

const transcriptSegments = computed<TranscriptSegment[]>(() => segments.value)
const recordingError = computed(() => errorMessage.value)
const isGeneratingNotes = computed(() => isRecording.value && !isPaused.value)

const notes = ref<NoteItem[]>([])
const shouldAutoSyncNotes = ref(true)

const extractSegmentsAsNote = () => {
  const text = transcriptText.value.trim()
  if (!text) { notes.value = []; return }
  notes.value = [{ id: 'transcript-note', title: '实时记录', content: text }]
}

watch(transcriptText, () => { if (!shouldAutoSyncNotes.value) return; extractSegmentsAsNote() }, { immediate: true })
watch(isRecording, v => { if (v) { shouldAutoSyncNotes.value = true; extractSegmentsAsNote() } })
watch(recordingError, v => { if (v) message.error(v) })

const handleNoteEdited = () => { shouldAutoSyncNotes.value = false }
const restoreAutoSync = () => { shouldAutoSyncNotes.value = true; extractSegmentsAsNote(); message.success('已根据实时转写内容同步笔记') }

// ----- keywords & materials (保持你的原逻辑) -----
const STOPWORDS = new Set(['the','and','you','are','for','with','that','have','this','from','your','just','will','they','我们','你们','他们','这个','那个','的是','以及','还有','而且','但是','或者','因此','那么','一个','或者','以及','的','了','呢','吧','啊','吗','是','在','和','到','就','还','也','很','让','能'])
const isChineseToken = (w: string) => /[\u4e00-\u9fa5]/.test(w)
const segmentText = (text: string) => {
  const list: string[] = []
  const trySeg = (locale: string) => {
    try { const S: any = (Intl as any).Segmenter; if (!S) return; const seg = new S(locale, { granularity: 'word' }); for (const it of seg.segment(text)) if (it.isWordLike) list.push(it.segment) } catch {}
  }
  trySeg('zh-Hans'); trySeg('en');
  if (!list.length) list.push(...text.split(/[\s,.;:，。！？、]+/g))
  return list
}
const extractKeywords = (text: string, limit = 12) => {
  const t = text.trim(); if (!t) return [] as KeywordItem[]
  const map = new Map<string, { text: string; score: number }>()
  const add = (w: string) => { const raw = w.trim(); if (!raw) return; const low = raw.toLowerCase(); if (STOPWORDS.has(low) || STOPWORDS.has(raw)) return; if (/^\d+(\.\d+)?$/.test(raw)) return; if (low.length < 2 && !isChineseToken(raw)) return; const k = low; const e = map.get(k); if (e) e.score += 1; else map.set(k, { text: raw, score: 1 }) }
  for (const tk of segmentText(t)) add(tk)
  return Array.from(map.values()).sort((a,b)=>b.score-a.score).slice(0, limit).map((e, i)=>({ id: `${e.text}-${i}`, text: e.text, relevance: e.score }))
}
const keywords = computed<KeywordItem[]>(() => extractKeywords(transcriptText.value))
const materialsForLearning = ref<LearningMaterial[]>([])
const isLoadingMaterials = ref(false)
let materialsTimer: number | null = null
const materialTypes: LearningMaterial['type'][] = ['article','video','document']
const scheduleMaterialsUpdate = () => {
  if (materialsTimer !== null) { window.clearTimeout(materialsTimer); materialsTimer = null }
  if (keywords.value.length < 3) { materialsForLearning.value = []; isLoadingMaterials.value = false; return }
  isLoadingMaterials.value = true
  const snapshot = keywords.value.slice(0, 6)
  materialsTimer = window.setTimeout(() => {
    materialsForLearning.value = snapshot.map((k, i) => {
      const type = materialTypes[i % materialTypes.length]
      return { id: `material-${k.id}-${i}`, title: `${k.text} ${type==='video'?'讲解':type==='document'?'文档':'进阶指南'}`, description: `结合「${k.text}」主题的精选${type==='video'?'视频':type==='document'?'文档资料':'文章与教程'}，帮助你快速巩固知识点。`, type, url: `https://www.google.com/search?q=${encodeURIComponent(k.text)}`, relevance: k.relevance, keywords: snapshot.map(x=>x.text) }
    })
    isLoadingMaterials.value = false
  }, 800)
}
watch(keywords, scheduleMaterialsUpdate, { deep: true, immediate: true })

// ----- layout state -----
const isNotesFullscreen = ref(false)
const activeTab = ref('chat')

const leftPaneWidth = ref(45)

const gridRef = ref<HTMLElement | null>(null)
const verticalDragging = ref(false)

const workspaceStyles = computed(() => {
  const left = Math.min(72, Math.max(28, leftPaneWidth.value))
  const right = Math.max(28, 100 - left)
  return { gridTemplateColumns: `${left}fr 12px ${right}fr` }
})

const handleStartRecording = async () => { try { await startRecording() } catch (err: any) { message.error(err?.message || '无法开始录音') } }
const handleStopRecording = async () => { await stopRecording() }
const handlePauseRecording = async () => { await pauseRecording() }
const handleResumeRecording = async () => { await resumeRecording() }

const handleKeywordSelected = (keyword: string) => { message.info(`已选择关键词：${keyword}`) }

const startVerticalDrag = (e: MouseEvent) => { e.preventDefault(); verticalDragging.value = true }
const stopDragging = () => { verticalDragging.value = false }
const handleMouseMove = (e: MouseEvent) => {
  if (verticalDragging.value && gridRef.value) {
    const rect = gridRef.value.getBoundingClientRect();
    const relative = ((e.clientX - rect.left) / rect.width) * 100;
    leftPaneWidth.value = Math.min(72, Math.max(28, relative))
  }
}

onMounted(() => { window.addEventListener('mousemove', handleMouseMove); window.addEventListener('mouseup', stopDragging) })
onBeforeUnmount(() => { window.removeEventListener('mousemove', handleMouseMove); window.removeEventListener('mouseup', stopDragging); if (materialsTimer !== null) { window.clearTimeout(materialsTimer); materialsTimer = null } void cancelRecording() })
</script>

<style scoped>
.notes-page { display:flex; flex-direction:column; height:100%; background:#f5f7fb; }
.page-content { flex:1; display:flex; flex-direction:column; padding:20px; overflow:hidden; }
.fullscreen-editor { flex:1; background:white; border-radius:16px; padding:20px; box-shadow:0 16px 40px rgba(15,23,42,.08); }

.workspace { flex:1; display:grid; grid-template-rows:1fr; grid-template-columns:45fr 12px 55fr; gap:0; background:white; border-radius:16px; box-shadow:0 16px 40px rgba(15,23,42,.08); overflow:hidden; min-height:0; min-width:0; }
.left-pane { height:100%; padding:20px; overflow-y:auto; background:white; display:flex; flex-direction:column; gap:16px; min-height:0; min-width:0; }

.right-pane { display:flex; flex-direction:column; padding:20px; gap:16px; overflow:hidden; background:white; min-height:0; min-width:0; }

.vertical-handle { width:12px; cursor:col-resize; background:rgba(15,23,42,.04); transition:background-color .2s ease; position:relative; }
.vertical-handle::after { content:''; position:absolute; top:16px; bottom:16px; left:50%; width:4px; transform:translateX(-50%); border-radius:999px; background:rgba(15,23,42,.12); transition:background-color .2s ease; }
.vertical-handle:hover,.vertical-handle.active { background:rgba(22,119,255,.1); }
.vertical-handle:hover::after,.vertical-handle.active::after { background:#1677ff; }

.tabs-wrapper { min-height:0; display:flex; flex:1; overflow:hidden; }
.tabs { flex:1; display:flex; flex-direction:column; }
.tabs :deep(.ant-tabs-content) { flex:1; display:flex; min-height:0; }
.tabs :deep(.ant-tabs-tabpane) { height:100%; display:flex; flex-direction:column; min-height:0; overflow:hidden; }
.tabs :deep(.ant-tabs-tabpane > *) { height:100%; flex:1; }

/* === 关键补丁：打通 Tabs → Card → Body 的高度链，启用内部滚动 === */
.tabs :deep(.ant-tabs-content-holder) { flex:1; display:flex; min-height:0; }
.tabs :deep(.ant-tabs-tabpane > .ant-card) { height:100%; display:flex; flex-direction:column; min-height:0; }
.tabs :deep(.ant-tabs-tabpane > .ant-card .ant-card-body) { flex:1; display:flex; flex-direction:column; min-height:0; }
</style>
