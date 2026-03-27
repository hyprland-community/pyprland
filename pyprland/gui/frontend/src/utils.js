/** Type-checking helpers */
export const isString = (v) => typeof v === 'string'
export const isArray = (v) => Array.isArray(v)
export const isObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v)

/**
 * Try to JSON.parse a string; return *fallback* on failure.
 * @param {string} raw
 * @param {*} [fallback] defaults to raw itself
 */
export function tryParseJson(raw, fallback) {
  try { return JSON.parse(raw) } catch { return fallback !== undefined ? fallback : raw }
}

/**
 * Format any value for display in a text input.
 * Objects are JSON-stringified, primitives become strings.
 */
export function formatValue(val) {
  if (val === undefined || val === null) return ''
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

/**
 * Group an array of field descriptor objects by their `category` property.
 * @param {Array<{category?: string}>} fields
 * @returns {Record<string, Array>}
 */
export function groupFields(fields) {
  const groups = {}
  for (const f of fields) {
    const cat = f.category || 'general'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(f)
  }
  return groups
}
