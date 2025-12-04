declare module 'vuedraggable' {
  import type { DefineComponent } from 'vue'
  import type { SortableEvent, SortableOptions } from 'sortablejs'

  // Minimal component typing to satisfy TS while keeping options accessible.
  const Draggable: DefineComponent<Record<string, any>, Record<string, any>, any>
  export default Draggable
  export type { SortableEvent, SortableOptions }
}

declare module 'sortablejs' {
  // Slim SortableEvent surface used in NotebookNotesList
  export interface SortableEvent {
    item: HTMLElement
    oldIndex?: number
    newIndex?: number
    [key: string]: any
  }

  const Sortable: any
  export default Sortable
}
