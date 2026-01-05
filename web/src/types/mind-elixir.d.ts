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
    data?: MindElixirData
    direction?: any
    locale?: string
    draggable?: boolean
    editable?: boolean
    contextMenu?: boolean | Record<string, unknown>
    toolBar?: boolean
    nodeMenu?: boolean
    keypress?: boolean
    allowUndo?: boolean
    before?: Record<string, unknown>
    newTopicName?: string
    primaryLinkStyle?: number
    overflowHidden?: boolean
    primaryNodeHorizontalGap?: number
    primaryNodeVerticalGap?: number
    mobileMenu?: boolean
  }

  export interface MindElixirInstance {
    init(data?: MindElixirData): void
    getAllData(): MindElixirData
    refresh(data?: MindElixirData): void
    toCenter?: () => void
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

declare module 'mind-elixir/dist/painter' {
  import type { MindElixirInstance } from 'mind-elixir'

  export interface MindElixirPainter {
    exportSvg(instance: MindElixirInstance, fileName?: string): void
    exportPng(instance: MindElixirInstance, fileName?: string): Promise<void>
  }

  export const exportSvg: MindElixirPainter['exportSvg']
  export const exportPng: MindElixirPainter['exportPng']
  const painter: MindElixirPainter
  export default painter
}