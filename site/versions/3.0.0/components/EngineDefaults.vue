<template>
  <div v-if="loading" class="data-loading">Loading engine defaults...</div>
  <div v-else-if="error" class="data-error">{{ error }}</div>
  <table v-else class="data-table">
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
import { usePluginData } from './usePluginData.js'

const { data: engineDefaults, loading, error } = usePluginData(async () => {
  const module = await import('../generated/menu.json')
  return module.engine_defaults || {}
})
</script>
