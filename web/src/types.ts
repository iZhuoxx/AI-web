// src/types.ts
export type TFileInMessage = {
  name: string
  type: string
  text?: string
  truncated?: boolean
  fileId?: string
  purpose?: 'vision' | 'assistants'
  viewUrl?: string
}

export type TMessage = {
  username: string
  msg: string
  type: 0 | 1
  time: string
  images: string[]
  files: TFileInMessage[]
  meta: Record<string, any>
}
