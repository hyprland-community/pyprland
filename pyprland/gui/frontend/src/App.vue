<template>
  <div v-if="loading" class="loading">Loading...</div>
  <template v-else>
    <header class="app-header">
      <h1><img src="/icon.png" alt="" class="header-icon" />pypr-gui</h1>
      <div class="action-bar">
        <span v-if="statusMsg" :class="['status-message', statusType]">{{ statusMsg }}</span>
        <button class="btn btn-secondary" @click="handleValidate" :disabled="saving">Validate</button>
        <button class="btn btn-primary" @click="handleSave" :disabled="saving">Save</button>
        <button class="btn btn-success" @click="handleApply" :disabled="saving">Apply</button>
      </div>
    </header>

    <div class="app-body">
      <aside class="sidebar">
        <div class="sidebar-section">
          <h3>Config</h3>
          <div style="padding: 0 8px; font-size: 0.75rem; color: var(--text-muted); font-family: monospace; word-break: break-all;">
            {{ configPath }}
          </div>
        </div>

        <div class="sidebar-section">
          <h3>Plugins</h3>
          <div
            v-for="plugin in allPlugins"
            :key="plugin.name"
            :class="['plugin-item', { active: activeView === plugin.name, disabled: !isEnabled(plugin.name) }]"
            @click="selectPlugin(plugin.name)"
          >
            <input
              type="checkbox"
              :checked="isEnabled(plugin.name)"
              @click.stop
              @change="togglePlugin(plugin.name)"
            />
            <span class="plugin-name">{{ plugin.name }}</span>
          </div>
        </div>

        <div v-if="hasVariables" class="sidebar-section">
          <h3>Misc</h3>
          <div
            :class="['plugin-item', { active: activeView === '_variables' }]"
            @click="activeView = '_variables'"
          >
            <span class="plugin-name">variables</span>
          </div>
        </div>
      </aside>

      <main class="main-content">
        <!-- Variables editor (flat DictEditor) -->
        <template v-if="activeView === '_variables'">
          <div class="plugin-header">
            <h2>Variables</h2>
            <p>Template variables available in plugin configs via <code>[var_name]</code> syntax.</p>
          </div>
          <DictEditor
            :value="variables"
            :flat="true"
            @update:value="variables = $event"
          />
        </template>

        <!-- Plugin editor -->
        <template v-else-if="activeView && currentPluginInfo">
          <PluginEditor
            :plugin="currentPluginInfo"
            :config="getPluginConfig(activeView)"
            @update:config="setPluginConfig(activeView, $event)"
          />
        </template>

        <div v-else class="empty-state">
          <h3>Select a plugin</h3>
          <p>Choose a plugin from the sidebar to configure it. Check the checkbox to enable it.</p>
        </div>
      </main>
    </div>

    <ul v-if="errors.length" class="error-list" style="margin: 0 24px 12px;">
      <li v-for="(err, i) in errors" :key="i">{{ err }}</li>
    </ul>
  </template>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import PluginEditor from './components/PluginEditor.vue'
import DictEditor from './components/DictEditor.vue'

const loading = ref(true)
const saving = ref(false)
const statusMsg = ref('')
const statusType = ref('success')
const errors = ref([])

const allPlugins = ref([])
const config = ref({})
const configPath = ref('')
const variables = ref({})

onMounted(async () => {
  try {
    const [pluginsRes, configRes] = await Promise.all([
      fetch('/api/plugins').then(r => r.json()),
      fetch('/api/config').then(r => r.json()),
    ])
    allPlugins.value = pluginsRes
    config.value = configRes.config || {}
    configPath.value = configRes.path || ''

    // Ensure pyprland section exists
    if (!config.value.pyprland) {
      config.value.pyprland = { plugins: [] }
    }
    if (!config.value.pyprland.plugins) {
      config.value.pyprland.plugins = []
    }
    // Deduplicate plugins (merge() list concatenation can cause dupes)
    config.value.pyprland.plugins = [...new Set(config.value.pyprland.plugins)]

    // Extract variables into a separate ref (they live under pyprland.variables)
    variables.value = config.value.pyprland.variables || {}
  } catch (e) {
    statusMsg.value = 'Failed to load: ' + e.message
    statusType.value = 'error'
  } finally {
    loading.value = false
  }
})

// activeView is either a plugin name or '_variables'
const activeView = ref(null)

const enabledPlugins = computed(() => [...new Set(config.value.pyprland?.plugins || [])])

const hasVariables = computed(() => Object.keys(variables.value).length > 0)

const currentPluginInfo = computed(() => {
  if (!activeView.value || activeView.value === '_variables') return null
  return allPlugins.value.find(p => p.name === activeView.value) || null
})

function isEnabled(name) {
  return enabledPlugins.value.includes(name)
}

function selectPlugin(name) {
  activeView.value = name
}

function togglePlugin(name) {
  const plugins = config.value.pyprland.plugins
  if (plugins.includes(name)) {
    // Remove all occurrences (merge() can cause duplicates)
    config.value.pyprland.plugins = plugins.filter(p => p !== name)
    delete config.value[name]
  } else {
    plugins.push(name)
    // Deduplicate and sort
    config.value.pyprland.plugins = [...new Set(plugins)].sort()
    if (!config.value[name]) {
      config.value[name] = {}
    }
  }
}

function getPluginConfig(name) {
  // Return the same reactive object each time so the PluginEditor prop
  // reference stays stable and doesn't trigger unnecessary deep-watch cycles.
  if (!config.value[name]) {
    config.value[name] = {}
  }
  return config.value[name]
}

function setPluginConfig(name, newConf) {
  config.value[name] = newConf
}

/** Merge variables back into the config before sending to the API. */
function buildSavePayload() {
  const payload = { ...config.value }
  payload.pyprland = { ...payload.pyprland }
  if (Object.keys(variables.value).length > 0) {
    payload.pyprland.variables = { ...variables.value }
  } else {
    delete payload.pyprland.variables
  }
  return payload
}

function showStatus(msg, type, duration = 4000) {
  statusMsg.value = msg
  statusType.value = type
  errors.value = []
  if (duration) setTimeout(() => { statusMsg.value = '' }, duration)
}

/** Shared POST-to-API helper. */
async function apiAction(endpoint, onSuccess) {
  saving.value = true
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config: buildSavePayload() }),
    })
    const data = await res.json()
    errors.value = data.errors || []
    onSuccess(data)
  } catch (e) {
    showStatus(`${endpoint.split('/').pop()} failed: ${e.message}`, 'error')
  } finally {
    saving.value = false
  }
}

function handleValidate() {
  apiAction('/api/validate', (data) => {
    if (data.ok) showStatus('Valid', 'success')
    else showStatus(`${data.errors.length} issue(s) found`, 'warning', 0)
  })
}

function handleSave() {
  apiAction('/api/save', (data) => {
    showStatus(data.backup ? `Saved (backup: ${data.backup})` : 'Saved', 'success')
  })
}

function handleApply() {
  apiAction('/api/apply', (data) => {
    if (data.daemon_reloaded) showStatus('Saved & reloaded', 'success')
    else showStatus('Saved (daemon not running)', 'warning')
  })
}
</script>
