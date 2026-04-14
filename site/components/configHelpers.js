/**
 * Shared helper functions for config table components.
 */

import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: true, linkify: true })

/**
 * Check if a config item has children.
 * @param {Object} item - Config item
 * @returns {boolean}
 */
export function hasChildren(item) {
  return item.children && item.children.length > 0
}

/**
 * Check if a value represents a meaningful default (not empty/null).
 * @param {*} value - Default value to check
 * @returns {boolean}
 */
export function hasDefault(value) {
  if (value === null || value === undefined) return false
  if (value === '') return false
  if (Array.isArray(value) && value.length === 0) return false
  if (typeof value === 'object' && Object.keys(value).length === 0) return false
  return true
}

/**
 * Format a default value for display.
 * @param {*} value - Value to format
 * @returns {string}
 */
export function formatDefault(value) {
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }
  if (typeof value === 'string') {
    return `"${value}"`
  }
  if (Array.isArray(value)) {
    return JSON.stringify(value)
  }
  return String(value)
}

/**
 * Render description text with markdown support.
 * Transforms <opt1|opt2|...> patterns to styled inline code blocks.
 * When choices are provided, appends them as inline code after the description.
 * @param {string} text - Description text
 * @param {Array|null} choices - Optional list of valid values
 * @returns {string} - HTML string
 */
export function renderDescription(text, choices) {
  if (!text) return ''
  // Transform <opt1|opt2|...> patterns to styled inline code blocks
  text = text.replace(/<([^>|]+(?:\|[^>|]+)+)>/g, (match, opts) => {
    return opts.split('|').map(c => `\`${c}\``).join(' | ')
  })
  // Append choices from schema if available
  if (choices && choices.length > 0) {
    const choiceStr = choices.map(c => `\`${c}\``).join(', ')
    text += `. Values: ${choiceStr}`
  }
  // Use render() to support links, then strip wrapping <p> tags
  const html = md.render(text)
  return html.replace(/^<p>/, '').replace(/<\/p>\n?$/, '')
}
