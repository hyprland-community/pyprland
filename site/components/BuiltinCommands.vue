<template>
  <div v-if="loading" class="data-loading">Loading commands...</div>
  <div v-else-if="error" class="data-error">{{ error }}</div>
  <table v-else class="data-table">
    <thead>
      <tr>
        <th>Command</th>
        <th>Description</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="command in commands" :key="command.name">
        <td>
          <a v-if="isDocumented(command.name)" :href="'#' + commandToAnchor[command.name]" class="config-link" title="More details below">
            <code>{{ command.name }}</code>
            <span class="config-info-icon">i</span>
          </a>
          <code v-else>{{ command.name }}</code>
        </td>
        <td v-html="renderDescription(command.short_description)" />
      </tr>
    </tbody>
  </table>
</template>

<script>
import { renderDescription } from './configHelpers.js'

export default {
  data() {
    return {
      commands: [],
      loading: true,
      error: null,
      commandToAnchor: {}
    }
  },
  async mounted() {
    try {
      const data = await import('../generated/builtins.json')
      this.commands = data.commands || []
    } catch (e) {
      this.error = 'Failed to load built-in commands'
      console.error(e)
    } finally {
      this.loading = false
    }

    // Scan page for documented command anchors (e.g., id="command-compgen")
    this.$nextTick(() => {
      const anchors = document.querySelectorAll('[id^="command-"]')
      const mapping = {}
      anchors.forEach(el => {
        // Extract command name from anchor: "command-compgen" -> "compgen"
        const commandName = el.id.replace(/^command-/, '')
        mapping[commandName] = el.id
      })
      this.commandToAnchor = mapping
    })
  },
  methods: {
    isDocumented(name) {
      return name in this.commandToAnchor
    },
    renderDescription
  }
}
</script>
