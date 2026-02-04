<template>
  <!-- Grouped by category (only at top level, when categories exist) -->
  <div v-if="hasCategories && !isNested" class="config-categories">
    <details
      v-for="group in groupedItems"
      :key="group.category"
      :open="group.category === 'basic'"
      class="config-category"
    >
      <summary class="config-category-header">
        {{ getCategoryDisplayName(group.category) }}
        <span class="config-category-count">({{ group.items.length }})</span>
      </summary>
      <table class="config-table">
        <thead>
          <tr>
            <th>Option</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="item in group.items" :key="item.name">
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
                <Badge type="info">{{ getTypeIcon(item) }}{{ item.type }}</Badge>
                <Badge v-if="item.required" type="danger">required</Badge>
                <Badge v-else-if="item.recommended" type="warning">recommended</Badge>
                <div v-if="hasDefault(item.default)" type="tip">=<code>{{ formatDefault(item.default) }}</code></div>
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
    </details>
  </div>

  <!-- Flat table (for nested tables or when no categories) -->
  <table v-else :class="['config-table', { 'config-nested': isNested }]">
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
            <Badge v-if="item.required" type="danger">required</Badge>
            <Badge v-else-if="item.recommended" type="warning">recommended</Badge>
            <div v-if="hasDefault(item.default)" type="tip">=<code>{{ formatDefault(item.default) }}</code></div>
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

// Category display order and names
const CATEGORY_ORDER = ['basic', 'menu', 'appearance', 'positioning', 'behavior', 'external_commands', 'templating', 'placement', 'advanced', 'overrides', '']
const CATEGORY_NAMES = {
  'basic': 'Basic',
  'menu': 'Menu',
  'appearance': 'Appearance',
  'positioning': 'Positioning',
  'behavior': 'Behavior',
  'external_commands': 'External commands',
  'templating': 'Templating',
  'placement': 'Placement',
  'advanced': 'Advanced',
  'overrides': 'Overrides',
  '': 'Other'
}

export default {
  name: 'ConfigTable',
  props: {
    items: { type: Array, required: true },
    isNested: { type: Boolean, default: false },
    optionToAnchor: { type: Object, default: () => ({}) },
    parentName: { type: String, default: '' }
  },
  computed: {
    hasCategories() {
      // Only group if there are multiple distinct categories
      const categories = new Set(this.items.map(item => item.category || ''))
      return categories.size > 1
    },
    groupedItems() {
      // Group items by category
      const groups = {}
      for (const item of this.items) {
        const category = item.category || ''
        if (!groups[category]) {
          groups[category] = []
        }
        groups[category].push(item)
      }

      // Sort groups by CATEGORY_ORDER
      const result = []
      for (const cat of CATEGORY_ORDER) {
        if (groups[cat]) {
          result.push({ category: cat, items: groups[cat] })
          delete groups[cat]
        }
      }
      // Add any remaining categories not in the order list
      for (const cat of Object.keys(groups).sort()) {
        result.push({ category: cat, items: groups[cat] })
      }

      return result
    }
  },
  methods: {
    hasChildren,
    hasDefault,
    formatDefault,
    renderDescription,
    getTypeIcon(item) {
      const type = item.type || ''
      if (type.includes('Path')) {
        return item.is_directory ? '\u{1F4C1} ' : '\u{1F4C4} '
      }
      return ''
    },
    getCategoryDisplayName(category) {
      return CATEGORY_NAMES[category] || category.charAt(0).toUpperCase() + category.slice(1)
    },
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

<style scoped>
.config-categories {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.config-category {
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  overflow: hidden;
}

.config-category[open] {
  border-color: var(--vp-c-brand);
}

.config-category-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--vp-c-bg-soft);
  font-weight: 600;
  cursor: pointer;
  user-select: none;
}

.config-category-header:hover {
  background: var(--vp-c-bg-mute);
}

.config-category-count {
  font-weight: 400;
  color: var(--vp-c-text-2);
  font-size: 0.875em;
}

.config-category .config-table {
  margin: 0;
  border: none;
  border-radius: 0;
}

.config-category .config-table thead {
  background: var(--vp-c-bg-alt);
}
</style>
