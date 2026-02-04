<template>
  <div v-if="error" class="data-error">{{ error }}</div>
  <ul v-else class="engine-list">
    <li></li>
    <li v-for="engine in engines" :key="engine">
            <code>{{ engine }}</code>
    </li>
  </ul>
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

const engineDefaults = computed(() => data.value?.engine_defaults ?? {})
const engines = computed(() => Object.keys(engineDefaults.value))
const error = computed(() => (data.value === null ? 'Failed to load engine defaults' : null))
</script>

<style scoped>
.engine-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

.engine-list li {
  float: left;
  margin-right: 0.75rem;
}
</style>
