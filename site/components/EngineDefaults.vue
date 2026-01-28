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

<script>
export default {
  data() {
    return {
      engineDefaults: {},
      loading: true,
      error: null
    }
  },
  async mounted() {
    try {
      const data = await import('../generated/menu.json')
      this.engineDefaults = data.engine_defaults || {}
    } catch (e) {
      this.error = 'Failed to load engine defaults'
      console.error(e)
    } finally {
      this.loading = false
    }
  }
}
</script>
