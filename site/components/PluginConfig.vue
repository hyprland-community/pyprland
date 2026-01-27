<template>
  <div v-if="loading" class="config-loading">Loading configuration...</div>
  <div v-else-if="error" class="config-error">{{ error }}</div>
  <div v-else-if="filteredConfig.length === 0" class="config-empty">No configuration options available.</div>
  <config-table
    v-else
    :items="filteredConfig"
    :option-to-anchor="optionToAnchor"
  />
</template>

<script>
import ConfigTable from './ConfigTable.vue'

export default {
  components: {
    ConfigTable
  },
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
  }
}
</script>
