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

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { renderDescription } from './configHelpers.js'
import { usePluginData } from './usePluginData.js'

const { data: commands, loading, error } = usePluginData(async () => {
  const module = await import('../generated/builtins.json')
  return module.commands || []
})

const commandToAnchor = ref({})

onMounted(async () => {
  // Wait for data to load and render
  await nextTick()

  // Scan page for documented command anchors (e.g., id="command-compgen")
  const anchors = document.querySelectorAll('[id^="command-"]')
  const mapping = {}
  anchors.forEach(el => {
    // Extract command name from anchor: "command-compgen" -> "compgen"
    const commandName = el.id.replace(/^command-/, '')
    mapping[commandName] = el.id
  })
  commandToAnchor.value = mapping
})

function isDocumented(name) {
  return name in commandToAnchor.value
}
</script>
