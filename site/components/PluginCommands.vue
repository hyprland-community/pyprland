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

<script setup>
import { renderDescription } from './configHelpers.js'
import { usePluginData } from './usePluginData.js'

const props = defineProps({
  plugin: {
    type: String,
    required: true
  }
})

const { data: commands, loading, error } = usePluginData(async () => {
  const module = await import(`../generated/${props.plugin}.json`)
  return module.commands || []
})

function formatSignature(sig) {
  return sig.replace(/[ ]*$/, '').replace(/ +/g, '&ensp;')
}
</script>
