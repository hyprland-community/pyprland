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
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: true, linkify: true })

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
    renderDescription(text) {
      // Transform <opt1|opt2|...> patterns to styled inline code blocks
      text = text.replace(/<([^>|]+(?:\|[^>|]+)+)>/g, (match, choices) => {
        return choices.split('|').map(c => `\`${c}\``).join(' | ')
      })
      return md.renderInline(text)
    }
  }
}
</script>
