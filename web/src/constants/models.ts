export const MODEL_OPTIONS = Object.freeze([
  'gpt-4.1',
  'gpt-4o-mini',
  'gpt-4.1-mini',
  'gpt-5',
]) as readonly string[]

export type ModelOption = (typeof MODEL_OPTIONS)[number]
