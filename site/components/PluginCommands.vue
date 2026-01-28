<template>
  <div v-if="loading">Loading commands...</div>
  <div v-else-if="error">{{ error }}</div>
  <ul v-else>
    <li v-for="command in commands" :key="command.name">
      <code>{{ command.name }}</code>
      <template v-for="(arg, idx) in command.args" :key="idx">
        &nbsp;<code>{{ formatArg(arg) }}</code>
      </template>
      &nbsp;<span v-html="renderDescription(command.short_description)" />
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

function formatArg(arg) {
  return arg.required ? arg.value : `[${arg.value}]`
}
</script>
