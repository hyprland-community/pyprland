<template>
    <span v-if="loaded && item" class="config-badges">
        <Badge type="info">{{ typeIcon }}{{ item.type }}</Badge>
        <Badge v-if="hasDefault" type="tip">=<code>{{ formattedDefault }}</code></Badge>
        <Badge v-if="item.required" type="danger">required</Badge>
        <Badge v-else-if="item.recommended" type="warning">recommended</Badge>
    </span>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getPluginData } from './jsonLoader.js'

const props = defineProps({
    plugin: {
        type: String,
        required: true
    },
    option: {
        type: String,
        required: true
    },
    version: {
        type: String,
        default: null
    }
})

const item = ref(null)
const loaded = ref(false)

onMounted(() => {
    try {
        const data = getPluginData(props.plugin, props.version)
        if (data) {
            const config = data.config || []
            // Find the option - handle both "option" and "[prefix].option" formats
            item.value = config.find(c => {
                const baseName = c.name.replace(/^\[.*?\]\./, '')
                return baseName === props.option || c.name === props.option
            })
        }
    } catch (e) {
        console.error(`Failed to load config for plugin: ${props.plugin}`, e)
    } finally {
        loaded.value = true
    }
})

const typeIcon = computed(() => {
    if (!item.value) return ''
    const type = item.value.type || ''
    if (type.includes('Path')) {
        return item.value.is_directory ? '\u{1F4C1} ' : '\u{1F4C4} '
    }
    return ''
})

const hasDefault = computed(() => {
    if (!item.value) return false
    const value = item.value.default
    if (value === null || value === undefined) return false
    if (value === '') return false
    if (Array.isArray(value) && value.length === 0) return false
    if (typeof value === 'object' && Object.keys(value).length === 0) return false
    return true
})

const formattedDefault = computed(() => {
    if (!item.value) return ''
    const value = item.value.default
    if (typeof value === 'boolean') {
        return value ? 'true' : 'false'
    }
    if (typeof value === 'string') {
        return `"${value}"`
    }
    if (Array.isArray(value)) {
        return JSON.stringify(value)
    }
    return String(value)
})
</script>

<style scoped>
.config-badges {
    margin-left: 0.5em;
}

.config-badges code {
    background: transparent;
    font-size: 0.9em;
}
</style>
