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

interface NotesState {
  list: NotebookSummary[]
  active: NotebookDetail | null
  listLoading: boolean
  noteLoading: boolean
  saving: boolean
}

const state = reactive<NotesState>({
  list: [],
  active: null,
  listLoading: false,
  noteLoading: false,
  saving: false,
})

const editorNotes = ref<NoteItem[]>([])
const drafts = useStorage<Record<string, { title: string; content: string }>>('notes-editor-drafts', {})

const sortNotebookNotes = (notes: NotebookNote[]): NotebookNote[] =>
  [...notes].sort((a, b) => a.seq - b.seq)

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
  editorNotes.value = toEditorNotes(state.active)
}

const buildNotesPayload = (items: NoteItem[]): NotebookPayload['notes'] =>
  items.map((item, index) => ({
    title: item.title,
    content: item.content,
    seq: index,
  }))

const fetchList = async () => {
  state.listLoading = true
  try {
    state.list = await listNotebooks()
  } catch (err) {
    const msg = err instanceof Error ? err.message : '加载笔记失败'
    message.error(msg)
    state.list = []
    throw err
  } finally {
    state.listLoading = false
  }
}

const openNote = async (id: string) => {
  state.noteLoading = true
  try {
    state.active = await getNotebook(id)
    refreshEditorNotes()
  } catch (err) {
    const msg = err instanceof Error ? err.message : '加载笔记详情失败'
    message.error(msg)
    throw err
  } finally {
    state.noteLoading = false
  }
}

const createNewNote = async (payload?: NotebookPayload) => {
  state.noteLoading = true
  try {
    const defaultPayload: NotebookPayload = {
      title: '未命名笔记',
      summary: '',
      tags: [],
      notes: [{ title: '未命名笔记', content: '', seq: 0 }],
      ...payload,
    }
    state.active = await createNotebook(defaultPayload)
    await fetchList()
    refreshEditorNotes()
  } catch (err) {
    const msg = err instanceof Error ? err.message : '创建笔记失败'
    message.error(msg)
    throw err
  } finally {
    state.noteLoading = false
  }
}

const saveActiveNote = async (
  payload: { title?: string | null; content?: string | null; summary?: string | null; tags?: string[]; isArchived?: boolean },
  options: { noteId?: string | null } = {},
) => {
  if (!state.active) return null
  state.saving = true
  try {
    const ordered = sortNotebookNotes(state.active.notes ?? [])
    const items = ordered.map(note => ({
      id: note.id,
      title: note.title ?? '未命名笔记',
      content: note.content ?? '',
    }))

    let targetIndex = 0
    if (options.noteId) {
      const found = items.findIndex(note => note.id === options.noteId)
      if (found >= 0) {
        targetIndex = found
      } else {
        targetIndex = items.length
        items.push({
          id: options.noteId,
          title: payload.title ?? '未命名笔记',
          content: payload.content ?? '',
        })
      }
    } else if (!items.length) {
      items.push({
        id: state.active.id,
        title: payload.title ?? '未命名笔记',
        content: payload.content ?? '',
      })
      targetIndex = 0
    }

    if (items[targetIndex]) {
      items[targetIndex] = {
        ...items[targetIndex],
        title: payload.title ?? items[targetIndex].title,
        content: payload.content ?? items[targetIndex].content,
      }
    }

    const updated = await updateNotebook(state.active.id, {
      title: state.active.title,
      summary: payload.summary ?? state.active.summary,
      tags: payload.tags ?? state.active.tags,
      is_archived: payload.isArchived ?? state.active.isArchived,
      notes: buildNotesPayload(items),
    })
    state.active = updated
    await fetchList()
    refreshEditorNotes()
    message.success('笔记已保存')
    return updated.notes?.find(note => note.seq === targetIndex) ?? null
  } catch (err) {
    const msg = err instanceof Error ? err.message : '保存笔记失败'
    message.error(msg)
    throw err
  } finally {
    state.saving = false
  }
}

const addNoteToActive = async (payload?: { title?: string | null; content?: string | null }) => {
  if (!state.active) return null
  state.saving = true
  try {
    const ordered = sortNotebookNotes(state.active.notes ?? [])
    const items = ordered.map(note => ({
      id: note.id,
      title: note.title ?? '未命名笔记',
      content: note.content ?? '',
    }))
    const nextIndex = items.length
    items.push({
      id: `temp-${Date.now()}`,
      title: payload?.title ?? '新建笔记',
      content: payload?.content ?? '',
    })

    const updated = await updateNotebook(state.active.id, {
      title: state.active.title,
      summary: state.active.summary,
      tags: state.active.tags,
      is_archived: state.active.isArchived,
      notes: buildNotesPayload(items),
    })
    state.active = updated
    await fetchList()
    refreshEditorNotes()
    message.success('已创建新的笔记页')
    return updated.notes?.find(note => note.seq === nextIndex) ?? null
  } catch (err) {
    const msg = err instanceof Error ? err.message : '创建新笔记页失败'
    message.error(msg)
    throw err
  } finally {
    state.saving = false
  }
}

const updateActiveNotebookTitle = async (title: string) => {
  if (!state.active) return
  state.saving = true
  try {
    const ordered = sortNotebookNotes(state.active.notes ?? [])
    const items = ordered.map(note => ({
      id: note.id,
      title: note.title ?? '未命名笔记',
      content: note.content ?? '',
    }))
    const updated = await updateNotebook(state.active.id, {
      title,
      summary: state.active.summary,
      tags: state.active.tags,
      is_archived: state.active.isArchived,
      notes: buildNotesPayload(items),
    })
    state.active = updated
    await fetchList()
    refreshEditorNotes()
    message.success('笔记本标题已更新')
  } catch (err) {
    const msg = err instanceof Error ? err.message : '更新笔记本标题失败'
    message.error(msg)
    throw err
  } finally {
    state.saving = false
  }
}

const renameNote = async (noteId: string, title: string) => {
  state.noteLoading = true
  try {
    const updated = await updateNotebook(noteId, { title })
    state.list = state.list.map(note =>
      note.id === noteId
        ? {
            ...note,
            title: updated.title,
            summary: updated.summary,
            updatedAt: updated.updatedAt,
            isArchived: updated.isArchived,
            tags: updated.tags,
          }
        : note,
    )
    if (state.active?.id === noteId) {
      state.active = {
        ...state.active,
        title: updated.title,
        summary: updated.summary,
        updatedAt: updated.updatedAt,
        isArchived: updated.isArchived,
        tags: updated.tags,
      }
      refreshEditorNotes()
    }
    const draft = drafts.value?.[noteId]
    if (draft) {
      drafts.value = {
        ...drafts.value,
        [noteId]: { ...draft, title: updated.title },
      }
    }
    message.success('笔记标题已更新')
  } catch (err) {
    const msg = err instanceof Error ? err.message : '重命名笔记失败'
    message.error(msg)
    throw err
  } finally {
    state.noteLoading = false
  }
}

const removeNote = async (noteId: string) => {
  state.noteLoading = true
  try {
    await deleteNotebookRequest(noteId)
    state.list = state.list.filter(note => note.id !== noteId)
    if (state.active?.id === noteId) {
      state.active = null
      refreshEditorNotes()
    }
    clearDraft(noteId)
    await fetchList()
    message.success('笔记已删除')
  } catch (err) {
    const msg = err instanceof Error ? err.message : '删除笔记失败'
    message.error(msg)
    throw err
  } finally {
    state.noteLoading = false
  }
}

const clearActiveNote = () => {
  state.active = null
  refreshEditorNotes()
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

export const useNotes = () => {
  const list = computed(() => state.list)
  const active = computed(() => state.active)

  return {
    state: readonly(state),
    notesForEditor: readonly(editorNotes),
    list,
    active,
    fetchList,
    openNote,
    createNewNote,
    saveActiveNote,
    addNoteToActive,
    updateActiveNotebookTitle,
    renameNote,
    removeNote,
    clearActiveNote,
    refreshEditorNotes,
    getDraft,
    setDraft,
    clearDraft,
  }
}
