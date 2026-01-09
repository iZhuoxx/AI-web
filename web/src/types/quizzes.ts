export type QuizQuestion = {
  id: string
  notebookId: string
  question: string
  options: string[]
  correctIndex: number
  hint: string | null
  meta: Record<string, unknown> | null
  isFavorite: boolean
  folderIds: string[]
  createdAt: string
  updatedAt: string
}

export type QuizFolder = {
  id: string
  notebookId: string
  name: string
  description: string | null
  questionIds: string[]
  createdAt: string
  updatedAt: string
}
