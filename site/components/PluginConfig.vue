<template>
  <div v-if="loading" class="config-loading">Loading configuration...</div>
  <div v-else-if="error" class="config-error">{{ error }}</div>
  <div v-else-if="filteredConfig.length === 0" class="config-empty">No configuration options available.</div>
  <table v-else class="config-table">
    <thead>
      <tr>
        <th>Option</th>
        <th>Type</th>
        <th>Default</th>
        <th>Description</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="item in filteredConfig" :key="item.name">
        <td>
          <a v-if="isDocumented(item.name)" :href="'#' + getAnchor(item.name)" class="config-link" title="More details below">
            <code>{{ item.name }}</code>
            <span class="config-info-icon">i</span>
          </a>
          <code v-else>{{ item.name }}</code>
          <span v-if="item.required" class="config-badge config-required">required</span>
          <span v-else-if="item.recommended" class="config-badge config-recommended">recommended</span>
        </td>
        <td><code>{{ item.type }}</code></td>
        <td>
          <code v-if="hasDefault(item.default)">{{ formatDefault(item.default) }}</code>
          <span v-else class="config-none">-</span>
        </td>
        <td class="config-description" v-html="renderDescription(item.description)" />
      </tr>
    </tbody>
  </table>
</template>

<script>
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: true, linkify: true })

export default {
  props: {
    plugin: {
      type: String,
      required: true
    },
    linkPrefix: {
      type: String,
      default: ''
    },
    filter: {
      type: Array,
      default: null
    }
  },
  data() {
    return {
      config: [],
      loading: true,
      error: null,
      optionToAnchor: {}
    }
  },
  computed: {
    filteredConfig() {
      if (!this.filter || this.filter.length === 0) {
        return this.config
      }
      return this.config.filter(item => {
        const baseName = item.name.replace(/^\[.*?\]\./, '')
        return this.filter.includes(baseName)
      })
    }
  },
  async mounted() {
    try {
      const data = await import(`../generated/${this.plugin}.json`)
      this.config = data.config || []
    } catch (e) {
      this.error = `Failed to load configuration for plugin: ${this.plugin}`
      console.error(e)
    } finally {
      this.loading = false
    }
    
    // Scan page for documented option anchors and build option->anchor mapping
    if (this.linkPrefix) {
      const anchors = document.querySelectorAll(`h3[id^="${this.linkPrefix}"]`)
      const mapping = {}
      anchors.forEach(h3 => {
        // Extract option names from <code> elements in heading
        const codes = h3.querySelectorAll('code')
        codes.forEach(code => {
          mapping[code.textContent] = h3.id
        })
      })
      this.optionToAnchor = mapping
    }
  },
  methods: {
    hasDefault(value) {
      if (value === null || value === undefined) return false
      if (value === '') return false
      if (Array.isArray(value) && value.length === 0) return false
      if (typeof value === 'object' && Object.keys(value).length === 0) return false
      return true
    },
    formatDefault(value) {
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
    },
    renderDescription(text) {
      if (!text) return ''
      // Transform <opt1|opt2|...> patterns to styled inline code blocks
      text = text.replace(/<([^>|]+(?:\|[^>|]+)+)>/g, (match, choices) => {
        return choices.split('|').map(c => `\`${c}\``).join(' | ')
      })
      // Use render() to support links, then strip wrapping <p> tags
      const html = md.render(text)
      return html.replace(/^<p>/, '').replace(/<\/p>\n?$/, '')
    },
    slugify(name) {
      // Convert option name to anchor-friendly slug
      // e.g., "[scratchpad].max_size" -> "scratchpad-max-size"
      return name.replace(/[\[\]\._]/g, '-').replace(/^-+|-+$/g, '').replace(/-+/g, '-')
    },
    isDocumented(name) {
      if (!this.linkPrefix || Object.keys(this.optionToAnchor).length === 0) return false
      // Get base name (e.g., "command" from "[scratchpad].command")
      const baseName = name.replace(/^\[.*?\]\./, '')
      return baseName in this.optionToAnchor
    },
    getAnchor(name) {
      const baseName = name.replace(/^\[.*?\]\./, '')
      return this.optionToAnchor[baseName] || ''
    }
  }
}
</script>

<style scoped>
.config-table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}

.config-table th,
.config-table td {
  border: 1px solid var(--vp-c-divider);
  padding: 0.5rem 0.75rem;
  text-align: left;
}

.config-table th {
  background-color: var(--vp-c-bg-soft);
  font-weight: 600;
}

.config-table tr:hover {
  background-color: var(--vp-c-bg-soft);
}

.config-table code {
  font-size: 0.875em;
}

.config-none {
  color: var(--vp-c-text-3);
}

.config-description a {
  color: var(--vp-c-brand-1);
  text-decoration: none;
}

.config-description a:hover {
  text-decoration: underline;
}

.config-description code {
  background-color: var(--vp-c-bg-soft);
  padding: 0.15em 0.3em;
  border-radius: 3px;
}

.config-loading,
.config-error,
.config-empty {
  padding: 1rem;
  color: var(--vp-c-text-2);
}

.config-error {
  color: var(--vp-c-danger-1);
}

.config-badge {
  font-size: 0.7em;
  padding: 0.15em 0.4em;
  border-radius: 3px;
  margin-left: 0.5em;
  font-weight: 500;
  vertical-align: middle;
}

.config-required {
  background-color: var(--vp-c-danger-soft);
  color: var(--vp-c-danger-1);
}

.config-recommended {
  background-color: var(--vp-c-warning-soft);
  color: var(--vp-c-warning-1);
}

.config-link {
  text-decoration: none;
  color: inherit;
}

.config-link:hover {
  text-decoration: underline;
  color: var(--vp-c-brand-1);
}

.config-link:hover code {
  color: var(--vp-c-brand-1);
}

.config-info-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.1em;
  height: 1.1em;
  margin-left: 0.4em;
  font-size: 0.75em;
  font-weight: 600;
  font-style: italic;
  font-family: serif;
  color: var(--vp-c-brand-1);
  border: 1px solid var(--vp-c-brand-1);
  border-radius: 50%;
  opacity: 0.7;
  transition: opacity 0.2s;
  vertical-align: middle;
}

.config-link:hover .config-info-icon {
  opacity: 1;
}
</style>
