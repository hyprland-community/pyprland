<template>
  <div class="field-row">
    <div class="field-label">
      <div class="name">
        {{ field.name }}
        <span v-if="field.required" class="required" title="Required">*</span>
        <span v-else-if="field.recommended" class="recommended" title="Recommended">(rec)</span>
      </div>
      <div class="description">{{ field.description }}</div>
      <div class="type-badge">{{ field.type }}</div>
    </div>

    <div class="field-input">
      <!-- Boolean: toggle switch -->
      <div v-if="isBool" class="toggle-wrap">
        <label class="toggle">
          <input type="checkbox" :checked="boolValue" @change="emit('update:value', $event.target.checked)" />
          <span class="slider"></span>
        </label>
        <span class="toggle-label">{{ boolValue ? 'true' : 'false' }}</span>
      </div>

      <!-- Choices: dropdown select -->
      <select v-else-if="field.choices" :value="displayValue" @change="emitTyped($event.target.value)">
        <option v-if="!field.required" value="">-- default --</option>
        <option v-for="c in field.choices" :key="c" :value="c">{{ c || '(empty)' }}</option>
      </select>

      <!-- Number -->
      <input
        v-else-if="isNumeric"
        type="number"
        :value="displayValue"
        :placeholder="placeholderText"
        :step="isFloat ? '0.1' : '1'"
        @input="emitNumber($event.target.value)"
      />

      <!-- Dict without children schema: structured recursive editor -->
      <DictEditor
        v-else-if="isDict"
        :value="props.value || {}"
        @update:value="emit('update:value', $event)"
      />

      <!-- List of objects: JSON textarea -->
      <div v-else-if="isComplexList">
        <textarea
          class="json-textarea"
          :value="jsonDisplayValue"
          :placeholder="placeholderText || '[]'"
          @change="emitJson($event.target.value)"
          rows="6"
          spellcheck="false"
        ></textarea>
        <div class="field-hint">
          JSON format (list)
          <span v-if="jsonError" class="json-error">{{ jsonError }}</span>
        </div>
      </div>

      <!-- List of primitives (as comma-separated text) -->
      <div v-else-if="isList">
        <input
          type="text"
          :value="listDisplayValue"
          :placeholder="placeholderText"
          @input="emitList($event.target.value)"
        />
        <div class="field-hint">Comma-separated values</div>
      </div>

      <!-- String (default) -->
      <input
        v-else
        type="text"
        :value="displayValue"
        :placeholder="placeholderText"
        @input="emitTyped($event.target.value)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import DictEditor from './DictEditor.vue'

const props = defineProps({
  field: { type: Object, required: true },
  value: { default: undefined },
})

const emit = defineEmits(['update:value'])

const fieldType = computed(() => (props.field.type || 'str').toLowerCase())

const isBool = computed(() => fieldType.value === 'bool')
const isNumeric = computed(() => fieldType.value === 'int' || fieldType.value === 'float')
const isFloat = computed(() => fieldType.value === 'float')
const isList = computed(() => fieldType.value.startsWith('list'))

// Dict without a children schema — rendered with DictEditor
const isDict = computed(() => fieldType.value === 'dict' && !props.field.children?.length)

// List whose items are objects (not flat strings) — rendered as JSON textarea
const isComplexList = computed(() => {
  if (!isList.value) return false
  const check = (arr) => Array.isArray(arr) && arr.length > 0 && typeof arr[0] === 'object' && arr[0] !== null
  return check(props.value) || check(props.field.default)
})

const boolValue = computed(() => {
  if (props.value === undefined || props.value === null) return props.field.default ?? false
  return !!props.value
})

const displayValue = computed(() => {
  if (props.value === undefined || props.value === null) return ''
  return String(props.value)
})

const listDisplayValue = computed(() => {
  if (props.value === undefined || props.value === null) return ''
  if (Array.isArray(props.value)) return props.value.join(', ')
  return String(props.value)
})

const jsonDisplayValue = computed(() => {
  if (props.value === undefined || props.value === null) return ''
  return JSON.stringify(props.value, null, 2)
})

const jsonError = ref('')

const placeholderText = computed(() => {
  if (props.field.default !== undefined && props.field.default !== null) {
    const d = props.field.default
    if (typeof d === 'object') return JSON.stringify(d, null, 2)
    if (Array.isArray(d)) return d.length ? d.join(', ') : '(empty list)'
    return String(d)
  }
  return ''
})

function emitTyped(str) {
  emit('update:value', str === '' ? undefined : str)
}

function emitNumber(str) {
  if (str === '') { emit('update:value', undefined); return }
  const num = isFloat.value ? parseFloat(str) : parseInt(str, 10)
  if (!isNaN(num)) emit('update:value', num)
}

function emitList(str) {
  if (str === '') { emit('update:value', undefined); return }
  emit('update:value', str.split(',').map(s => s.trim()).filter(s => s !== ''))
}

function emitJson(str) {
  jsonError.value = ''
  if (str.trim() === '') { emit('update:value', undefined); return }
  try {
    emit('update:value', JSON.parse(str))
  } catch (e) {
    jsonError.value = e.message
  }
}
</script>
