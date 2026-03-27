import { ref, watch, nextTick } from 'vue'

/**
 * Two-way sync a local copy of an object prop with a guard to prevent
 * infinite watch cycles.
 *
 * @param {() => object} propGetter - getter that returns the prop value
 * @param {Function} emit - the component's emit function
 * @param {string} eventName - event to emit on local changes (e.g. 'update:value')
 * @returns {import('vue').Ref<object>} reactive local copy
 */
export function useLocalCopy(propGetter, emit, eventName) {
  const local = ref({ ...propGetter() })
  let updating = false

  watch(propGetter, (v) => {
    updating = true
    local.value = { ...v }
    nextTick(() => { updating = false })
  }, { deep: true })

  watch(local, (v) => {
    if (updating) return
    emit(eventName, { ...v })
  }, { deep: true })

  return local
}
