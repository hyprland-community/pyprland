<template>
  <table :class="['config-table', { 'config-nested': isNested }]">
    <thead>
      <tr>
        <th>Option</th>
        <th>Description</th>
      </tr>
    </thead>
    <tbody>
      <template v-for="item in items" :key="item.name">
        <tr>
          <td class="config-option-cell">
            <a v-if="isDocumented(item.name)" :href="'#' + getAnchor(item.name)" class="config-link" title="More details below">
              <span v-if="hasChildren(item)" class="config-has-children" title="Has child options">+</span>
              <code>{{ item.name }}</code>
              <span class="config-info-icon">i</span>
            </a>
            <template v-else>
              <span v-if="hasChildren(item)" class="config-has-children" title="Has child options">+</span>
              <code>{{ item.name }}</code>
            </template>
            <Badge type="info">{{ item.type }}</Badge>
            <Badge v-if="hasDefault(item.default)" type="tip">=<code>{{ formatDefault(item.default) }}</code></Badge>
            <Badge v-if="item.required" type="danger">required</Badge>
            <Badge v-else-if="item.recommended" type="warning">recommended</Badge>
          </td>
          <td class="config-description" v-html="renderDescription(item.description)" />
        </tr>
        <!-- Children row (recursive) -->
        <tr v-if="hasChildren(item)" class="config-children-row">
          <td colspan="2" class="config-children-cell">
            <details class="config-children-details">
              <summary><code>{{ item.name }}</code> options</summary>
              <config-table
                :items="item.children"
                :is-nested="true"
                :option-to-anchor="optionToAnchor"
                :parent-name="getQualifiedName(item.name)"
              />
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
    items: { type: Array, required: true },
    isNested: { type: Boolean, default: false },
    optionToAnchor: { type: Object, default: () => ({}) },
    parentName: { type: String, default: '' }
  },
  methods: {
    hasChildren,
    hasDefault,
    formatDefault,
    renderDescription,
    getQualifiedName(name) {
      const baseName = name.replace(/^\[.*?\]\./, '')
      return this.parentName ? `${this.parentName}.${baseName}` : baseName
    },
    isDocumented(name) {
      if (Object.keys(this.optionToAnchor).length === 0) return false
      const qualifiedName = this.getQualifiedName(name)
      const anchorKey = qualifiedName.replace(/\./g, '-')
      return anchorKey in this.optionToAnchor || qualifiedName in this.optionToAnchor
    },
    getAnchor(name) {
      const qualifiedName = this.getQualifiedName(name)
      const anchorKey = qualifiedName.replace(/\./g, '-')
      return this.optionToAnchor[anchorKey] || this.optionToAnchor[qualifiedName] || ''
    }
  }
}
</script>
