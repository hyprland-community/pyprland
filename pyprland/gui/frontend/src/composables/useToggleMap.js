import { reactive } from 'vue'

/**
 * A reactive map of boolean toggle states, keyed by string.
 *
 * @returns {{ state: Record<string, boolean>, toggle: (key: string) => void }}
 */
export function useToggleMap() {
  const state = reactive({})
  const toggle = (key) => { state[key] = !state[key] }
  return { state, toggle }
}
