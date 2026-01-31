<template>
  <div v-if="loading" class="command-loading">Loading commands...</div>
  <div v-else-if="error" class="command-error">{{ error }}</div>
  <div v-else-if="filteredCommands.length === 0" class="command-empty">
    No commands are provided by this plugin.
  </div>
  <div v-else class="command-box">
    <ul class="command-list">
      <li v-for="command in filteredCommands" :key="command.name" class="command-item">
        <a v-if="isDocumented(command.name)" :href="'#' + getAnchor(command.name)" class="command-link" title="More details below">
          <code class="command-name">{{ command.name }}</code>
          <span class="command-info-icon">i</span>
        </a>
        <code v-else class="command-name">{{ command.name }}</code>
        <template v-for="(arg, idx) in command.args" :key="idx">
          <code class="command-arg">{{ formatArg(arg) }}</code>
        </template>
        <span class="command-desc" v-html="renderDescription(command.short_description)" />
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { renderDescription } from './configHelpers.js'
import { usePluginData } from './usePluginData.js'

const props = defineProps({
  plugin: {
    type: String,
    required: true
  },
  filter: {
    type: Array,
    default: null
  },
  linkPrefix: {
    type: String,
    default: ''
  }
})

const commandToAnchor = ref({})

const { data: commands, loading, error } = usePluginData(async () => {
  const module = await import(`../generated/${props.plugin}.json`)
  return module.commands || []
})

const filteredCommands = computed(() => {
  if (!props.filter || props.filter.length === 0) {
    return commands.value
  }
  return commands.value.filter(cmd => props.filter.includes(cmd.name))
})

onMounted(() => {
  if (props.linkPrefix) {
    const anchors = document.querySelectorAll('h3[id], h4[id], h5[id]')
    const mapping = {}
    anchors.forEach(heading => {
      mapping[heading.id] = heading.id
      // Also extract command names from <code> elements
      const codes = heading.querySelectorAll('code')
      codes.forEach(code => {
        mapping[code.textContent] = heading.id
      })
    })
    commandToAnchor.value = mapping
  }
})

function isDocumented(name) {
  if (Object.keys(commandToAnchor.value).length === 0) return false
  const anchorKey = `${props.linkPrefix}${name}`
  return anchorKey in commandToAnchor.value || name in commandToAnchor.value
}

function getAnchor(name) {
  const anchorKey = `${props.linkPrefix}${name}`
  return commandToAnchor.value[anchorKey] || commandToAnchor.value[name] || ''
}

function formatArg(arg) {
  return arg.required ? arg.value : `[${arg.value}]`
}
</script>
