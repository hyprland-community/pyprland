/**
 * Composable for loading plugin data with loading/error states.
 *
 * Provides a standardized pattern for async data loading in Vue components.
 */

import { ref, onMounted } from 'vue'

/**
 * Load data asynchronously with loading and error state management.
 *
 * @param {Function} loader - Async function that returns the data
 * @returns {Object} - { data, loading, error } refs
 *
 * @example
 * // Load commands from a plugin JSON file
 * const { data: commands, loading, error } = usePluginData(async () => {
 *   const module = await import(`../generated/${props.plugin}.json`)
 *   return module.commands || []
 * })
 *
 * @example
 * // Load with default value
 * const { data: config, loading, error } = usePluginData(
 *   async () => {
 *     const module = await import('../generated/menu.json')
 *     return module.engine_defaults || {}
 *   }
 * )
 */
export function usePluginData(loader) {
  const data = ref(null)
  const loading = ref(true)
  const error = ref(null)

  onMounted(async () => {
    try {
      data.value = await loader()
    } catch (e) {
      error.value = e.message || 'Failed to load data'
      console.error(e)
    } finally {
      loading.value = false
    }
  })

  return { data, loading, error }
}
