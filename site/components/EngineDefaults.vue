<template>
  <div v-if="loading" class="engine-loading">Loading engine defaults...</div>
  <div v-else-if="error" class="engine-error">{{ error }}</div>
  <table v-else class="engine-table">
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

<style scoped>
.engine-table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}

.engine-table th,
.engine-table td {
  border: 1px solid var(--vp-c-divider);
  padding: 0.5rem 0.75rem;
  text-align: left;
}

.engine-table th {
  background-color: var(--vp-c-bg-soft);
  font-weight: 600;
}

.engine-table tr:hover {
  background-color: var(--vp-c-bg-soft);
}

.engine-table code {
  font-size: 0.875em;
}

.engine-loading,
.engine-error {
  padding: 1rem;
  color: var(--vp-c-text-2);
}

.engine-error {
  color: var(--vp-c-danger-1);
}
</style>
