import type { MindElixirData } from 'mind-elixir'

export type MindMap = {
  id: string
  notebookId: string
  title: string
  description: string | null
  data: MindElixirData
  createdAt: string
  updatedAt: string
}
