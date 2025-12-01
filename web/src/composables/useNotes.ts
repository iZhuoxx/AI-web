import { computed, reactive, readonly, ref } from 'vue'
import { useStorage } from '@vueuse/core'
import { message } from 'ant-design-vue'
import {
  createNotebook,
  deleteNotebook as deleteNotebookRequest,
  getNotebook,
  listNotebooks,
  updateNotebook,
  type NotebookPayload,
} from '@/services/api'
import type { NotebookDetail, NotebookSummary, NotebookNote, NoteItem } from '@/types/notes'

interface NotebooksState {
  list: NotebookSummary[]
  activeNotebook: NotebookDetail | null
  listLoading: boolean
  activeLoading: boolean
  saving: boolean
}

const notebooksState = reactive<NotebooksState>({
  list: [],
  activeNotebook: null,
  listLoading: false,
  activeLoading: false,
  saving: false,
})

const editorNotes = ref<NoteItem[]>([])
const drafts = useStorage<Record<string, { title: string; content: string }>>('notes-editor-drafts', {})

const sortNotebookNotes = (notes: NotebookNote[]): NotebookNote[] =>
  [...notes].sort((a, b) => a.seq - b.seq)

const getNotebookSnapshot = (id: string): NotebookDetail | NotebookSummary | null => {
  if (notebooksState.activeNotebook?.id === id) return notebooksState.activeNotebook
  return notebooksState.list.find(item => item.id === id) ?? null
}

const toEditorNotes = (notebook: NotebookDetail | null): NoteItem[] => {
  if (!notebook) return []
  const ordered = sortNotebookNotes(notebook.notes ?? [])
  if (!ordered.length) {
    return [
      {
        id: notebook.id,
        title: notebook.title ?? '未命名笔记',
        content: '',
      },
    ]
  }
  return ordered.map(note => ({
    id: note.id,
    title: note.title ?? '未命名笔记',
    content: note.content ?? '',
  }))
}

const refreshEditorNotes = () => {
  editorNotes.value = toEditorNotes(notebooksState.activeNotebook)
}

type NoteDraft = { id?: string | null; title: string; content: string; seq: number }

const buildNotesPayload = (items: NoteDraft[]): NotebookPayload['notes'] =>
  items.map(item => ({
    id: item.id ?? undefined,
    title: item.title,
    content: item.content,
    seq: item.seq,
  }))

const getNextSeq = (notes: NotebookNote[]): number =>
  notes.reduce((max, note) => Math.max(max, note.seq), -1) + 1

const fetchNotebookList = async () => {
  notebooksState.listLoading = true
  try {
    notebooksState.list = await listNotebooks()
  } catch (err) {
    const msg = err instanceof Error ? err.message : '加载笔记失败'
    message.error(msg)
    notebooksState.list = []
    throw err
  } finally {
    notebooksState.listLoading = false
  }
}

const openNotebook = async (id: string) => {
  notebooksState.activeLoading = true
  try {
    notebooksState.activeNotebook = await getNotebook(id)
    refreshEditorNotes()
  } catch (err) {
    const msg = err instanceof Error ? err.message : '加载笔记详情失败'
    message.error(msg)
    throw err
  } finally {
    notebooksState.activeLoading = false
  }
}

const createNotebookWithFirstNote = async (payload?: NotebookPayload) => {
  notebooksState.activeLoading = true
  try {
    const defaultPayload: NotebookPayload = {
      title: '未命名笔记',
      summary: '',
      notes: [{ title: '未命名笔记', content: '', seq: 0 }],
      ...payload,
    }
    notebooksState.activeNotebook = await createNotebook(defaultPayload)
    await fetchNotebookList()
    refreshEditorNotes()
  } catch (err) {
    const msg = err instanceof Error ? err.message : '创建笔记失败'
    message.error(msg)
    throw err
  } finally {
    notebooksState.activeLoading = false
  }
}

const saveNoteInActiveNotebook = async (
  payload: { title?: string | null; content?: string | null; summary?: string | null; isArchived?: boolean },
  options: { noteId?: string | null } = {},
) => {
  if (!notebooksState.activeNotebook) return null
  notebooksState.saving = true
  try {
    const ordered = sortNotebookNotes(notebooksState.activeNotebook.notes ?? [])
    const items: NoteDraft[] = ordered.map(note => ({
      id: note.id,
      title: note.title ?? '未命名笔记',
      content: note.content ?? '',
      seq: note.seq,
    }))

    let targetIndex = 0
    let targetSeq = items[0]?.seq ?? 0
    if (options.noteId) {
      const found = items.findIndex(note => note.id === options.noteId)
      if (found >= 0) {
        targetIndex = found
        targetSeq = items[found].seq
      } else {
        const nextSeq = getNextSeq(ordered)
        targetIndex = items.length
        items.push({
          id: options.noteId ?? undefined,
          title: payload.title ?? '未命名笔记',
          content: payload.content ?? '',
          seq: nextSeq,
        })
        targetSeq = nextSeq
      }
    } else if (!items.length) {
      items.push({
        id: undefined,
        title: payload.title ?? '未命名笔记',
        content: payload.content ?? '',
        seq: 0,
      })
      targetIndex = 0
      targetSeq = 0
    }

    if (items[targetIndex]) {
      items[targetIndex] = {
        ...items[targetIndex],
        title: payload.title ?? items[targetIndex].title,
        content: payload.content ?? items[targetIndex].content,
      }
    }

    const updated = await updateNotebook(notebooksState.activeNotebook.id, {
      title: notebooksState.activeNotebook.title,
      summary: payload.summary ?? notebooksState.activeNotebook.summary,
      is_archived: payload.isArchived ?? notebooksState.activeNotebook.isArchived,
      color: notebooksState.activeNotebook.color,
      openai_vector_store_id: notebooksState.activeNotebook.openaiVectorStoreId,
      vector_store_expires_at: notebooksState.activeNotebook.vectorStoreExpiresAt,
      notes: buildNotesPayload(items),
    })
    notebooksState.activeNotebook = updated
    await fetchNotebookList()
    refreshEditorNotes()
    message.success('笔记已保存')
    const targetId = items[targetIndex]?.id
    return updated.notes?.find(note => (targetId ? note.id === targetId : note.seq === targetSeq)) ?? null
  } catch (err) {
    const msg = err instanceof Error ? err.message : '保存笔记失败'
    message.error(msg)
    throw err
  } finally {
    notebooksState.saving = false
  }
}

const addNoteToActiveNotebook = async (payload?: { title?: string | null; content?: string | null }) => {
  if (!notebooksState.activeNotebook) return null
  notebooksState.saving = true
  try {
    const ordered = sortNotebookNotes(notebooksState.activeNotebook.notes ?? [])
    const items: NoteDraft[] = ordered.map(note => ({
      id: note.id,
      title: note.title ?? '未命名笔记',
      content: note.content ?? '',
      seq: note.seq,
    }))
    const nextSeq = getNextSeq(ordered)
    items.push({
      id: undefined,
      title: payload?.title ?? '新建笔记',
      content: payload?.content ?? '',
      seq: nextSeq,
    })

    const updated = await updateNotebook(notebooksState.activeNotebook.id, {
      title: notebooksState.activeNotebook.title,
      summary: notebooksState.activeNotebook.summary,
      is_archived: notebooksState.activeNotebook.isArchived,
      color: notebooksState.activeNotebook.color,
      openai_vector_store_id: notebooksState.activeNotebook.openaiVectorStoreId,
      vector_store_expires_at: notebooksState.activeNotebook.vectorStoreExpiresAt,
      notes: buildNotesPayload(items),
    })
    notebooksState.activeNotebook = updated
    await fetchNotebookList()
    refreshEditorNotes()
    message.success('已创建新的笔记页')
    return updated.notes?.find(note => note.seq === nextSeq) ?? null
  } catch (err) {
    const msg = err instanceof Error ? err.message : '创建新笔记页失败'
    message.error(msg)
    throw err
  } finally {
    notebooksState.saving = false
  }
}

const removeNoteFromActiveNotebook = async (noteId: string) => {
  if (!notebooksState.activeNotebook) return
  if (!notebooksState.activeNotebook.notes?.some(note => note.id === noteId)) return
  notebooksState.saving = true
  try {
    const ordered = sortNotebookNotes(notebooksState.activeNotebook.notes ?? [])
    const items: NoteDraft[] = ordered
      .filter(note => note.id !== noteId)
      .map(note => ({
        id: note.id,
        title: note.title ?? '未命名笔记',
        content: note.content ?? '',
        seq: note.seq,
      }))

    const updated = await updateNotebook(notebooksState.activeNotebook.id, {
      title: notebooksState.activeNotebook.title,
      summary: notebooksState.activeNotebook.summary,
      is_archived: notebooksState.activeNotebook.isArchived,
      color: notebooksState.activeNotebook.color,
      openai_vector_store_id: notebooksState.activeNotebook.openaiVectorStoreId,
      vector_store_expires_at: notebooksState.activeNotebook.vectorStoreExpiresAt,
      notes: buildNotesPayload(items),
    })
    notebooksState.activeNotebook = updated
    await fetchNotebookList()
    refreshEditorNotes()
    clearDraft(noteId)
    message.success('笔记已删除')
  } catch (err) {
    const msg = err instanceof Error ? err.message : '删除笔记失败'
    message.error(msg)
    throw err
  } finally {
    notebooksState.saving = false
  }
}

const updateActiveNotebookTitle = async (title: string) => {
  if (!notebooksState.activeNotebook) return
  notebooksState.saving = true
  try {
    const ordered = sortNotebookNotes(notebooksState.activeNotebook.notes ?? [])
    const items: NoteDraft[] = ordered.map(note => ({
      id: note.id,
      title: note.title ?? '未命名笔记',
      content: note.content ?? '',
      seq: note.seq,
    }))
    const updated = await updateNotebook(notebooksState.activeNotebook.id, {
      title,
      summary: notebooksState.activeNotebook.summary,
      is_archived: notebooksState.activeNotebook.isArchived,
      color: notebooksState.activeNotebook.color,
      openai_vector_store_id: notebooksState.activeNotebook.openaiVectorStoreId,
      vector_store_expires_at: notebooksState.activeNotebook.vectorStoreExpiresAt,
      notes: buildNotesPayload(items),
    })
    notebooksState.activeNotebook = updated
    await fetchNotebookList()
    refreshEditorNotes()
    message.success('笔记本标题已更新')
  } catch (err) {
    const msg = err instanceof Error ? err.message : '更新笔记本标题失败'
    message.error(msg)
    throw err
  } finally {
    notebooksState.saving = false
  }
}

const renameNotebook = async (noteId: string, title: string) => {
  notebooksState.activeLoading = true
  try {
    const existing = notebooksState.list.find(note => note.id === noteId)
    const source = existing ?? notebooksState.activeNotebook
    const updated = await updateNotebook(noteId, {
      title,
      summary: source?.summary ?? null,
      is_archived: source?.isArchived,
      color: source?.color ?? null,
      openai_vector_store_id: source?.openaiVectorStoreId ?? null,
      vector_store_expires_at: source?.vectorStoreExpiresAt ?? null,
    })
    notebooksState.list = notebooksState.list.map(note =>
      note.id === noteId
        ? {
            ...note,
            title: updated.title,
            summary: updated.summary,
            updatedAt: updated.updatedAt,
            isArchived: updated.isArchived,
            color: updated.color,
            openaiVectorStoreId: updated.openaiVectorStoreId,
            vectorStoreExpiresAt: updated.vectorStoreExpiresAt,
        }
        : note,
    )
    if (notebooksState.activeNotebook?.id === noteId) {
      notebooksState.activeNotebook = {
        ...notebooksState.activeNotebook,
        title: updated.title,
        summary: updated.summary,
        updatedAt: updated.updatedAt,
        isArchived: updated.isArchived,
        color: updated.color,
        openaiVectorStoreId: updated.openaiVectorStoreId,
        vectorStoreExpiresAt: updated.vectorStoreExpiresAt,
      }
      refreshEditorNotes()
    }
    const draft = drafts.value?.[noteId]
    if (draft) {
      drafts.value = {
        ...drafts.value,
        [noteId]: { ...draft, title: updated.title ?? '' },
      }
    }
    message.success('笔记标题已更新')
  } catch (err) {
    const msg = err instanceof Error ? err.message : '重命名笔记失败'
    message.error(msg)
    throw err
  } finally {
    notebooksState.activeLoading = false
  }
}

const removeNotebook = async (noteId: string) => {
  notebooksState.activeLoading = true
  try {
    await deleteNotebookRequest(noteId)
    notebooksState.list = notebooksState.list.filter(note => note.id !== noteId)
    if (notebooksState.activeNotebook?.id === noteId) {
      notebooksState.activeNotebook = null
      refreshEditorNotes()
    }
    clearDraft(noteId)
    await fetchNotebookList()
    message.success('笔记已删除')
  } catch (err) {
    const msg = err instanceof Error ? err.message : '删除笔记失败'
    message.error(msg)
    throw err
  } finally {
    notebooksState.activeLoading = false
  }
}

const updateNotebookColor = async (noteId: string, color: string) => {
  notebooksState.activeLoading = true
  try {
    const snapshot = getNotebookSnapshot(noteId)
    const payload: NotebookPayload = {
      title: snapshot?.title ?? null,
      summary: snapshot?.summary ?? null,
      is_archived: snapshot?.isArchived ?? false,
      color,
      openai_vector_store_id: snapshot?.openaiVectorStoreId ?? null,
      vector_store_expires_at: snapshot?.vectorStoreExpiresAt ?? null,
    }
    const updated = await updateNotebook(noteId, payload)
    notebooksState.list = notebooksState.list.map(note =>
      note.id === noteId
        ? {
            ...note,
            title: updated.title,
            summary: updated.summary,
            updatedAt: updated.updatedAt,
            isArchived: updated.isArchived,
            color: updated.color,
            openaiVectorStoreId: updated.openaiVectorStoreId,
            vectorStoreExpiresAt: updated.vectorStoreExpiresAt,
        }
        : note,
    )
    if (notebooksState.activeNotebook?.id === noteId) {
      notebooksState.activeNotebook = updated
      refreshEditorNotes()
    }
    message.success('笔记颜色已更新')
    return updated
  } catch (err) {
    const msg = err instanceof Error ? err.message : '更新笔记颜色失败'
    message.error(msg)
    throw err
  } finally {
    notebooksState.activeLoading = false
  }
}

const clearActiveNotebook = () => {
  notebooksState.activeNotebook = null
  refreshEditorNotes()
}

const reloadActiveNotebook = async () => {
  if (!notebooksState.activeNotebook?.id) return null
  notebooksState.activeLoading = true
  try {
    const id = notebooksState.activeNotebook.id
    const updated = await getNotebook(id)
    notebooksState.activeNotebook = updated
    await fetchNotebookList()
    refreshEditorNotes()
    return updated
  } catch (err) {
    const msg = err instanceof Error ? err.message : '刷新笔记失败'
    message.error(msg)
    throw err
  } finally {
    notebooksState.activeLoading = false
  }
}

const getDraft = (noteId: string) => drafts.value?.[noteId] ?? null
const setDraft = (noteId: string, payload: { title: string; content: string }) => {
  drafts.value = { ...drafts.value, [noteId]: payload }
}
const clearDraft = (noteId: string) => {
  if (!drafts.value?.[noteId]) return
  const next = { ...drafts.value }
  delete next[noteId]
  drafts.value = next
}

export const useNotebookStore = () => {
  const list = computed(() => notebooksState.list)
  const active = computed(() => notebooksState.activeNotebook)

  return {
    // 状态
    notebooksState: readonly(notebooksState),
    notesForEditor: readonly(editorNotes),
    notebookList: list,
    activeNotebook: active,

    // Notebook 相关（新命名）
    fetchNotebookList,
    openNotebook,
    createNotebookWithFirstNote,
    renameNotebook,
    removeNotebook,
    clearActiveNotebook,
    reloadActiveNotebook,
    updateActiveNotebookTitle,

    // Note 相关（新命名）
    saveNoteInActiveNotebook,
    addNoteToActiveNotebook,
    removeNoteFromActiveNotebook,
    updateNotebookColor,

    // 草稿相关
    getDraft,
    setDraft,
    clearDraft,
  }
}
