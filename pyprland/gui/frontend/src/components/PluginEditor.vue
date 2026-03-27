<template>
  <div class="plugin-header">
    <h2>{{ plugin.name }}</h2>
    <p>{{ plugin.description }}</p>
    <div v-if="plugin.environments.length" class="plugin-envs">
      <span v-for="env in plugin.environments" :key="env" class="env-badge">{{ env }}</span>
    </div>
  </div>

  <!-- Top-level config fields (grouped by category) — excludes dict fields with children -->
  <div v-if="topLevelFields.length">
    <div v-for="(fields, cat) in groupedFields" :key="cat" class="category-group">
      <h3>{{ cat }}</h3>
      <FieldInput
        v-for="field in fields"
        :key="field.name"
        :field="field"
        :value="local[field.name]"
        @update:value="local[field.name] = $event"
      />
    </div>
  </div>

  <!-- Dict fields with children schema (e.g., monitors.placement) -->
  <div v-for="dictField in dictFieldsWithChildren" :key="dictField.name" class="child-entries">
    <h3 class="child-entries-title">{{ dictField.name }}</h3>
    <p v-if="dictField.description" class="child-entries-desc">{{ dictField.description }}</p>

    <div v-for="entryName in getDictEntryNames(dictField.name)" :key="dictField.name + '.' + entryName" class="dict-entry">
      <div class="collapsible-header" @click="toggle(dictField.name + '.' + entryName)">
        <span :class="['chevron', { open: opened[dictField.name + '.' + entryName] }]">&#9654;</span>
        <h4 style="font-size: 0.9rem; font-family: monospace;">{{ entryName }}</h4>
        <div class="dict-entry-actions">
          <button class="btn btn-secondary btn-xs" @click.stop="removeDictEntry(dictField.name, entryName)">Remove</button>
        </div>
      </div>
      <div v-if="opened[dictField.name + '.' + entryName]" class="dict-entry-body">
        <!-- Schema-defined fields -->
        <div v-for="(fields, cat) in groupFields(dictField.children)" :key="cat" class="category-group">
          <h3>{{ cat }}</h3>
          <FieldInput
            v-for="childField in fields"
            :key="childField.name"
            :field="childField"
            :value="getDictEntryValue(dictField.name, entryName, childField.name)"
            @update:value="setDictEntryValue(dictField.name, entryName, childField.name, $event)"
          />
        </div>
        <!-- Extra keys not in children schema — delegate to flat DictEditor -->
        <div v-if="dictField.children_allow_extra">
          <h3 class="category-group" style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid var(--border);">extra</h3>
          <DictEditor
            :value="getExtraEntries(dictField, entryName)"
            :flat="true"
            @update:value="setExtraEntries(dictField.name, entryName, $event)"
          />
        </div>
      </div>
    </div>

    <div class="add-row">
      <input v-model="newEntryNames[dictField.name]" type="text" :placeholder="'New ' + dictField.name + ' entry...'" @keyup.enter="addDictEntry(dictField.name)" />
      <button class="btn btn-secondary btn-xs" @click="addDictEntry(dictField.name)" :disabled="!(newEntryNames[dictField.name] || '').trim()">Add</button>
    </div>
  </div>

  <!-- Plugin-level child entries (e.g., scratchpads named entries) -->
  <div v-if="plugin.child_schema" class="child-entries">
    <h3 class="child-entries-title">Entries</h3>

    <div v-for="name in childNames" :key="name" class="dict-entry">
      <div class="collapsible-header" @click="toggle(name)">
        <span :class="['chevron', { open: opened[name] }]">&#9654;</span>
        <h4 style="font-size: 0.9rem; font-family: monospace;">{{ name }}</h4>
        <div class="dict-entry-actions">
          <button class="btn btn-secondary btn-xs" @click.stop="removeChild(name)">Remove</button>
        </div>
      </div>
      <div v-if="opened[name]" class="dict-entry-body">
        <div v-for="(fields, cat) in groupFields(plugin.child_schema)" :key="cat" class="category-group">
          <h3>{{ cat }}</h3>
          <FieldInput
            v-for="field in fields"
            :key="field.name"
            :field="field"
            :value="local[name]?.[field.name]"
            @update:value="setChildValue(name, field.name, $event)"
          />
        </div>
      </div>
    </div>

    <div class="add-row">
      <input v-model="newChildName" type="text" placeholder="New entry name..." @keyup.enter="addChild" />
      <button class="btn btn-secondary btn-xs" @click="addChild" :disabled="!newChildName.trim()">Add</button>
    </div>
  </div>

  <!-- Empty config state -->
  <div v-if="!topLevelFields.length && !plugin.child_schema && !dictFieldsWithChildren.length" class="empty-state">
    <p>This plugin has no configurable options.</p>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import FieldInput from './FieldInput.vue'
import DictEditor from './DictEditor.vue'
import { useLocalCopy } from '../composables/useLocalCopy.js'
import { useToggleMap } from '../composables/useToggleMap.js'
import { isObject, groupFields } from '../utils.js'

const props = defineProps({
  plugin: { type: Object, required: true },
  config: { type: Object, required: true },
})

const emit = defineEmits(['update:config'])

const local = useLocalCopy(() => props.config, emit, 'update:config')
const { state: opened, toggle } = useToggleMap()

// ---------------------------------------------------------------------------
//  Top-level fields (excludes dict-with-children — they get their own section)
// ---------------------------------------------------------------------------

const dictFieldsWithChildren = computed(() =>
  (props.plugin.config_schema || []).filter(f => f.type === 'dict' && f.children?.length)
)

const dictWithChildrenNames = computed(() =>
  new Set(dictFieldsWithChildren.value.map(f => f.name))
)

const topLevelFields = computed(() =>
  (props.plugin.config_schema || []).filter(f => !dictWithChildrenNames.value.has(f.name))
)

const groupedFields = computed(() => groupFields(topLevelFields.value))

// ---------------------------------------------------------------------------
//  Dict fields with children schema (e.g., monitors.placement)
// ---------------------------------------------------------------------------

const newEntryNames = reactive({})

function getDictEntryNames(fieldName) {
  const val = local.value[fieldName]
  if (!val || !isObject(val)) return []
  return Object.keys(val).filter(k => isObject(val[k]))
}

function getDictEntryValue(fieldName, entryName, childFieldName) {
  return local.value[fieldName]?.[entryName]?.[childFieldName]
}

function setDictEntryValue(fieldName, entryName, childFieldName, value) {
  if (!local.value[fieldName]) local.value[fieldName] = {}
  if (!local.value[fieldName][entryName]) local.value[fieldName][entryName] = {}
  local.value[fieldName][entryName][childFieldName] = value
}

function removeDictEntry(fieldName, entryName) {
  if (local.value[fieldName]) {
    delete local.value[fieldName][entryName]
    local.value[fieldName] = { ...local.value[fieldName] }
  }
  delete opened[fieldName + '.' + entryName]
}

function addDictEntry(fieldName) {
  const name = (newEntryNames[fieldName] || '').trim()
  if (!name) return
  if (!local.value[fieldName]) local.value[fieldName] = {}
  if (!local.value[fieldName][name]) {
    local.value[fieldName][name] = {}
  }
  opened[fieldName + '.' + name] = true
  newEntryNames[fieldName] = ''
}

/** Return only keys in this entry that are NOT in the children schema. */
function getExtraEntries(dictField, entryName) {
  const entry = local.value[dictField.name]?.[entryName]
  if (!entry || !isObject(entry)) return {}
  const schemaNames = new Set((dictField.children || []).map(f => f.name))
  const result = {}
  for (const [k, v] of Object.entries(entry)) {
    if (!schemaNames.has(k)) result[k] = v
  }
  return result
}

/** Replace extra keys in an entry (merge with schema-defined keys). */
function setExtraEntries(fieldName, entryName, extraData) {
  const entry = local.value[fieldName]?.[entryName]
  if (!entry) return
  const dictField = dictFieldsWithChildren.value.find(f => f.name === fieldName)
  const schemaNames = new Set((dictField?.children || []).map(f => f.name))
  // Keep only schema-defined keys, then merge in the new extra data
  const kept = {}
  for (const [k, v] of Object.entries(entry)) {
    if (schemaNames.has(k)) kept[k] = v
  }
  local.value[fieldName][entryName] = { ...kept, ...extraData }
}

// ---------------------------------------------------------------------------
//  Plugin-level child entries (scratchpads etc.)
// ---------------------------------------------------------------------------

const newChildName = ref('')

const childNames = computed(() => {
  if (!props.plugin.child_schema) return []
  const topNames = new Set((props.plugin.config_schema || []).map(f => f.name))
  return Object.keys(local.value).filter(k =>
    isObject(local.value[k]) && !topNames.has(k)
  )
})

function setChildValue(childName, fieldName, value) {
  if (!local.value[childName]) {
    local.value[childName] = {}
  }
  local.value[childName][fieldName] = value
}

function addChild() {
  const name = newChildName.value.trim()
  if (!name) return
  if (!local.value[name]) {
    local.value[name] = {}
  }
  opened[name] = true
  newChildName.value = ''
}

function removeChild(name) {
  delete local.value[name]
  delete opened[name]
}
</script>
