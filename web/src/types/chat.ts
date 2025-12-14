export type TFileInMessage = {
  name: string
  type: string
  text?: string
  truncated?: boolean
  fileId?: string
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

export type UiPhase = 'waiting' | 'streaming' | 'finished'

export interface ResponseUIState {
  phase: UiPhase
  statusKey: string | null
  statusText: string | null
  hasTextStarted: boolean
}
