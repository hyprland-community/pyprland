<template>
  <div class="dict-editor" :class="{ nested: depth > 0 }">
    <div v-for="key in sortedKeys" :key="key" class="dict-entry">
      <div class="collapsible-header" @click="toggle(key)">
        <span :class="['chevron', { open: opened[key] }]">&#9654;</span>
        <span class="dict-entry-name">{{ key }}</span>
        <template v-if="!flat">
          <span class="dict-entry-type">{{ entryTypeLabel(local[key]) }}</span>
          <span v-if="isString(local[key]) && !local[key].includes('\n')" class="dict-entry-preview">{{ local[key] }}</span>
        </template>
        <div class="dict-entry-actions">
          <button class="btn btn-secondary btn-xs" @click.stop="removeEntry(key)">Remove</button>
        </div>
      </div>

      <div v-if="opened[key]" class="dict-entry-body">
        <!-- Flat mode: always a simple text input -->
        <input
          v-if="flat"
          type="text"
          :value="formatValue(local[key])"
          @input="updateValue(key, $event.target.value)"
        />

        <!-- String value -->
        <template v-else-if="isString(local[key])">
          <textarea
            v-if="local[key].includes('\n') || local[key].length > 100"
            class="dict-value-input"
            :value="local[key]"
            @change="updateValue(key, $event.target.value)"
            rows="4"
            spellcheck="false"
          ></textarea>
          <input
            v-else
            type="text"
            :value="local[key]"
            @input="updateValue(key, $event.target.value)"
          />
        </template>

        <!-- Array value -->
        <div v-else-if="isArray(local[key])" class="dict-array-editor">
          <div v-for="(item, idx) in local[key]" :key="idx" class="dict-array-item">
            <!-- Array item is an object -->
            <div v-if="isObject(item)" class="dict-array-object">
              <div class="dict-array-object-header">
                <span class="dict-entry-type">object</span>
                <button class="btn btn-secondary btn-xs" @click="removeArrayItem(key, idx)">Remove</button>
              </div>
              <div v-for="(val, okey) in item" :key="okey" class="dict-array-object-field">
                <label class="dict-array-field-label">{{ okey }}</label>
                <input
                  v-if="isString(val) || typeof val === 'number'"
                  type="text"
                  :value="String(val)"
                  @input="updateArrayObjectField(key, idx, okey, $event.target.value)"
                />
                <textarea
                  v-else-if="isArray(val)"
                  class="dict-value-input"
                  :value="JSON.stringify(val, null, 2)"
                  @change="updateArrayObjectFieldJson(key, idx, okey, $event.target.value)"
                  rows="2"
                  spellcheck="false"
                ></textarea>
              </div>
              <!-- Add field to array object -->
              <div class="add-row">
                <input v-model="newArrayObjKey[key + '.' + idx]" type="text" placeholder="key" class="add-row-key" @keyup.enter="addArrayObjectField(key, idx)" />
                <input v-model="newArrayObjVal[key + '.' + idx]" type="text" placeholder="value" class="add-row-val" @keyup.enter="addArrayObjectField(key, idx)" />
                <button class="btn btn-secondary btn-xs" @click="addArrayObjectField(key, idx)" :disabled="!(newArrayObjKey[key + '.' + idx] || '').trim()">+</button>
              </div>
            </div>
            <!-- Array item is a string -->
            <div v-else class="dict-array-string">
              <textarea
                v-if="isString(item) && (item.includes('\n') || item.length > 80)"
                class="dict-value-input"
                :value="item"
                @change="updateArrayItem(key, idx, $event.target.value)"
                rows="3"
                spellcheck="false"
              ></textarea>
              <input
                v-else
                type="text"
                :value="String(item)"
                @input="updateArrayItem(key, idx, $event.target.value)"
              />
              <button class="btn btn-secondary btn-xs" @click="removeArrayItem(key, idx)">x</button>
            </div>
          </div>
          <!-- Add array item -->
          <div class="add-row">
            <select v-model="newArrayItemType[key]" class="add-row-type">
              <option value="string">string</option>
              <option value="object">object</option>
            </select>
            <input v-if="newArrayItemType[key] !== 'object'" v-model="newArrayItemVal[key]" type="text" placeholder="New item..." class="add-row-val" @keyup.enter="addArrayItem(key)" />
            <button class="btn btn-secondary btn-xs" @click="addArrayItem(key)">+ item</button>
          </div>
        </div>

        <!-- Nested dict (submenu) — recurse -->
        <DictEditor
          v-else-if="isObject(local[key])"
          :value="local[key]"
          :depth="depth + 1"
          @update:value="updateValue(key, $event)"
        />

        <!-- Fallback: show as JSON -->
        <input v-else type="text" :value="JSON.stringify(local[key])" @change="updateValueJson(key, $event.target.value)" />

        <!-- Rename (hidden in flat mode) -->
        <div v-if="!flat" class="dict-entry-rename">
          <span class="dict-rename-label">key:</span>
          <input type="text" :value="key" @change="renameEntry(key, $event.target.value)" class="dict-rename-input" />
        </div>
      </div>
    </div>

    <!-- Add new entry -->
    <div class="add-row">
      <input v-model="newKey" type="text" placeholder="New key..." class="add-row-key" @keyup.enter="addEntry" />
      <select v-if="!flat" v-model="newType" class="add-row-type">
        <option value="string">string</option>
        <option value="array">array</option>
        <option value="dict">submenu</option>
      </select>
      <button class="btn btn-secondary btn-xs" @click="addEntry" :disabled="!newKey.trim()">Add</button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useLocalCopy } from '../composables/useLocalCopy.js'
import { useToggleMap } from '../composables/useToggleMap.js'
import { isString, isArray, isObject, tryParseJson, formatValue } from '../utils.js'

const props = defineProps({
  value: { type: Object, default: () => ({}) },
  depth: { type: Number, default: 0 },
  flat: { type: Boolean, default: false },
})

const emit = defineEmits(['update:value'])

const local = useLocalCopy(() => props.value, emit, 'update:value')
const { state: opened, toggle } = useToggleMap()

const newKey = ref('')
const newType = ref('string')
const newArrayItemType = reactive({})
const newArrayItemVal = reactive({})
const newArrayObjKey = reactive({})
const newArrayObjVal = reactive({})

const sortedKeys = computed(() => Object.keys(local.value))

function entryTypeLabel(v) {
  if (isString(v)) return 'str'
  if (isArray(v)) return `list(${v.length})`
  if (isObject(v)) return `{${Object.keys(v).length}}`
  return typeof v
}

function updateValue(key, val) {
  local.value[key] = val
}

function updateValueJson(key, raw) {
  const parsed = tryParseJson(raw)
  if (parsed !== raw) local.value[key] = parsed
}

function removeEntry(key) {
  delete local.value[key]
  local.value = { ...local.value }
}

function renameEntry(oldKey, newName) {
  const trimmed = newName.trim()
  if (!trimmed || trimmed === oldKey) return
  const rebuilt = {}
  for (const [k, v] of Object.entries(local.value)) {
    rebuilt[k === oldKey ? trimmed : k] = v
  }
  local.value = rebuilt
  if (opened[oldKey]) {
    delete opened[oldKey]
    opened[trimmed] = true
  }
}

function addEntry() {
  const k = newKey.value.trim()
  if (!k || local.value[k] !== undefined) return
  if (props.flat || newType.value === 'string') {
    local.value[k] = ''
  } else if (newType.value === 'array') {
    local.value[k] = []
  } else {
    local.value[k] = {}
  }
  opened[k] = true
  newKey.value = ''
}

// --- Array item operations ---

function updateArrayItem(key, idx, val) {
  const arr = [...local.value[key]]
  arr[idx] = val
  local.value[key] = arr
}

function removeArrayItem(key, idx) {
  const arr = [...local.value[key]]
  arr.splice(idx, 1)
  local.value[key] = arr
}

function addArrayItem(key) {
  const arr = [...(local.value[key] || [])]
  const type = newArrayItemType[key] || 'string'
  if (type === 'object') {
    arr.push({})
  } else {
    arr.push(newArrayItemVal[key] || '')
    newArrayItemVal[key] = ''
  }
  local.value[key] = arr
}

function updateArrayObjectField(key, idx, okey, val) {
  const arr = [...local.value[key]]
  arr[idx] = { ...arr[idx], [okey]: val }
  local.value[key] = arr
}

function updateArrayObjectFieldJson(key, idx, okey, raw) {
  updateArrayObjectField(key, idx, okey, tryParseJson(raw))
}

function addArrayObjectField(key, idx) {
  const compKey = key + '.' + idx
  const k = (newArrayObjKey[compKey] || '').trim()
  if (!k) return
  updateArrayObjectField(key, idx, k, tryParseJson(newArrayObjVal[compKey] || ''))
  newArrayObjKey[compKey] = ''
  newArrayObjVal[compKey] = ''
}
</script>
