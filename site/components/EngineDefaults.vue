<template>
  <div v-if="error" class="data-error">{{ error }}</div>
  <table v-else-if="engineDefaults" class="data-table">
    <thead>
      <tr>
        <th>Engine</th>
        <th>Default Parameters</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(params, engine) in engineDefaults" :key="engine">
        <td><code>{{ engine }}</code></td>
        <td><code>{{ params || '-' }}</code></td>
      </tr>
    </tbody>
  </table>
</template>

<script setup>
import { computed } from 'vue'
import { getPluginData } from './jsonLoader.js'

const props = defineProps({
  version: {
    type: String,
    default: null
  }
})

const data = computed(() => {
  try {
    return getPluginData('menu', props.version)
  } catch (e) {
    console.error('Failed to load menu data:', e)
    return null
  }
})

const engineDefaults = computed(() => data.value?.engine_defaults || null)
const error = computed(() => data.value === null ? 'Failed to load engine defaults' : null)
</script>
