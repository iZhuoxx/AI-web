declare module 'mind-elixir' {
  export type MindElixirData = {
    nodeData: any
    linkData?: Record<string, unknown>
    template?: string
    direction?: any
    theme?: string
    meta?: Record<string, unknown>
  }

  export interface MindElixirOptions {
    el: HTMLElement | string
    direction?: any
    draggable?: boolean
    editable?: boolean
    contextMenu?: boolean | Record<string, unknown>
    toolBar?: boolean
    nodeMenu?: boolean
    keypress?: boolean
    allowUndo?: boolean
  }

  export interface MindElixirInstance {
    init(data: MindElixirData): void
    getAllData(): MindElixirData
    refresh(data?: MindElixirData): void
    focusNode?: (id: string) => void
    addChild?: (node: unknown) => void
    addSibling?: (node: unknown) => void
    removeNode?: (node: unknown) => void
    bus?: { addListener: (event: string, fn: (...args: any[]) => void) => void }
    mindElixirBox?: HTMLElement
  }

  interface MindElixirConstructor {
    new (options: MindElixirOptions): MindElixirInstance
    LEFT: any
    RIGHT: any
    SIDE: any
  }

  const MindElixir: MindElixirConstructor
  export const E: any
  export default MindElixir
}
