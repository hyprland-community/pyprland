<template>
  <table :class="['config-table', { 'config-nested': isNested }]">
    <thead>
      <tr>
        <th>Option</th>
        <th>Type</th>
        <th>Default</th>
        <th>Description</th>
      </tr>
    </thead>
    <tbody>
      <template v-for="item in items" :key="item.name">
        <tr>
          <td>
            <a v-if="isDocumented(item.name)" :href="'#' + getAnchor(item.name)" class="config-link" title="More details below">
              <span v-if="hasChildren(item)" class="config-has-children" title="Has child options">+</span>
              <code>{{ item.name }}</code>
              <span class="config-info-icon">i</span>
            </a>
            <template v-else>
              <span v-if="hasChildren(item)" class="config-has-children" title="Has child options">+</span>
              <code>{{ item.name }}</code>
            </template>
            <span v-if="item.required" class="config-badge config-required">required</span>
            <span v-else-if="item.recommended" class="config-badge config-recommended">recommended</span>
          </td>
          <td><code>{{ item.type }}</code></td>
          <td>
            <code v-if="hasDefault(item.default)">{{ formatDefault(item.default) }}</code>
            <span v-else class="config-none">-</span>
          </td>
          <td class="config-description" v-html="renderDescription(item.description)" />
        </tr>
        <!-- Children row (recursive) -->
        <tr v-if="hasChildren(item)" class="config-children-row">
          <td colspan="4" class="config-children-cell">
            <details class="config-children-details">
              <summary>Child options for <code>{{ item.name }}</code></summary>
              <config-table :items="item.children" :is-nested="true" />
            </details>
          </td>
        </tr>
      </template>
    </tbody>
  </table>
</template>

<script>
import { hasChildren, hasDefault, formatDefault, renderDescription } from './configHelpers.js'

export default {
  name: 'ConfigTable',
  props: {
    items: {
      type: Array,
      required: true
    },
    isNested: {
      type: Boolean,
      default: false
    },
    optionToAnchor: {
      type: Object,
      default: () => ({})
    }
  },
  methods: {
    hasChildren,
    hasDefault,
    formatDefault,
    renderDescription,
    isDocumented(name) {
      if (Object.keys(this.optionToAnchor).length === 0) return false
      const baseName = name.replace(/^\[.*?\]\./, '')
      return baseName in this.optionToAnchor
    },
    getAnchor(name) {
      const baseName = name.replace(/^\[.*?\]\./, '')
      return this.optionToAnchor[baseName] || ''
    }
  }
}
</script>
