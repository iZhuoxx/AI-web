export type Flashcard = {
  id: string
  notebookId: string
  question: string
  answer: string
  meta: Record<string, unknown> | null
  folderIds: string[]
}

export type FlashcardFolder = {
  id: string
  notebookId: string
  name: string
  description: string | null
  flashcardIds: string[]
  createdAt: string
  updatedAt: string
}
