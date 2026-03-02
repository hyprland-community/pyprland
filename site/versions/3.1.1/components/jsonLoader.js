/**
 * JSON loader with glob imports for version-aware plugin data.
 *
 * Uses Vite's import.meta.glob to pre-bundle all JSON files at build time,
 * enabling runtime selection based on version.
 */

// Pre-load all JSON files at build time
const currentJson = import.meta.glob('../generated/*.json', { eager: true })
const versionedJson = import.meta.glob('../versions/*/generated/*.json', { eager: true })

/**
 * Get plugin data from the appropriate JSON file.
 *
 * @param {string} name - JSON filename without extension (e.g., 'scratchpads', 'index', 'menu')
 * @param {string|null} version - Version string (e.g., '3.0.0') or null for current
 * @returns {object|null} - Parsed JSON data or null if not found
 */
export function getPluginData(name, version = null) {
  const filename = `${name}.json`

  if (version) {
    const key = `../versions/${version}/generated/${filename}`
    const data = versionedJson[key]
    return data?.default || data || null
  }

  const key = `../generated/${filename}`
  const data = currentJson[key]
  return data?.default || data || null
}
