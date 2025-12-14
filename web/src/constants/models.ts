export const MODEL_OPTIONS = Object.freeze([
  'gpt-4.1',
  'gpt-5',
  'gpt-5.1',
]) as readonly string[]

export type ModelOption = (typeof MODEL_OPTIONS)[number]
