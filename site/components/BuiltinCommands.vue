<template>
  <div v-if="loading">Loading commands...</div>
  <div v-else-if="error">{{ error }}</div>
  <table v-else class="commands-table">
    <thead>
      <tr>
        <th>Command</th>
        <th>Description</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="command in commands" :key="command.name">
        <td>
          <a v-if="isDocumented(command.name)" :href="'#' + commandToAnchor[command.name]" class="command-link" title="More details below">
            <code>{{ command.name }}</code>
            <span class="command-info-icon">i</span>
          </a>
          <code v-else>{{ command.name }}</code>
        </td>
        <td v-html="renderDescription(command.short_description)" />
      </tr>
    </tbody>
  </table>
</template>

<script>
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: true, linkify: true })

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

<style scoped>
.commands-table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}

.commands-table th,
.commands-table td {
  border: 1px solid var(--vp-c-divider);
  padding: 0.5rem 0.75rem;
  text-align: left;
}

.commands-table th {
  background-color: var(--vp-c-bg-soft);
  font-weight: 600;
}

.commands-table tr:hover {
  background-color: var(--vp-c-bg-soft);
}

.commands-table code {
  font-size: 0.875em;
}

.command-link {
  text-decoration: none;
  color: inherit;
}

.command-link:hover {
  text-decoration: underline;
  color: var(--vp-c-brand-1);
}

.command-link:hover code {
  color: var(--vp-c-brand-1);
}

.command-info-icon {
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

.command-link:hover .command-info-icon {
  opacity: 1;
}
</style>
