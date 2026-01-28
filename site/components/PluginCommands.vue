<template>
  <div v-if="loading">Loading commands...</div>
  <div v-else-if="error">{{ error }}</div>
  <ul v-else v-for="command in commands" :key="command.name">
    <li>
      <code v-html="formatSignature(command.signature)" />&nbsp;
      <span v-html="renderDescription(command.short_description)" />
    </li>
  </ul>
</template>

<script>
import { renderDescription } from './configHelpers.js'

export default {
  props: {
    plugin: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      commands: [],
      loading: true,
      error: null
    }
  },
  async mounted() {
    try {
      const data = await import(`../generated/${this.plugin}.json`)
      this.commands = data.commands || []
    } catch (e) {
      this.error = `Failed to load commands for plugin: ${this.plugin}`
      console.error(e)
    } finally {
      this.loading = false
    }
  },
  methods: {
    formatSignature(sig) {
      return sig.replace(/[ ]*$/, '').replace(/ +/g, '&ensp;')
    },
    renderDescription
  }
}
</script>
