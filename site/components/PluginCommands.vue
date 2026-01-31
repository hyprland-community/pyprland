<template>
  <div v-if="loading" class="command-loading">Loading commands...</div>
  <div v-else-if="error" class="command-error">{{ error }}</div>
  <div v-else class="command-box">
    <ul class="command-list">
      <li v-for="command in commands" :key="command.name" class="command-item">
        <code class="command-name">{{ command.name }}</code>
        <template v-for="(arg, idx) in command.args" :key="idx">
          <code class="command-arg">{{ formatArg(arg) }}</code>
        </template>
        <span class="command-desc" v-html="renderDescription(command.short_description)" />
      </li>
    </ul>
  </div>
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
