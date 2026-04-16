<template>
    <ul v-if="loaded && choices && choices.length > 0" class="config-choices">
        <li v-for="choice in choices" :key="choiceName(choice)">
            <code>{{ choiceName(choice) }}</code>
            <span v-if="choiceDesc(choice)"> — {{ choiceDesc(choice) }}</span>
        </li>
    </ul>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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

const choices = ref(null)
const loaded = ref(false)

function choiceName(choice) {
    return typeof choice === 'object' ? choice.name : choice
}

function choiceDesc(choice) {
    return typeof choice === 'object' ? choice.desc : ''
}

/**
 * Find a config item by option name, supporting dot-separated paths
 * for nested children (e.g., "placement.transform").
 */
function findItem(config, option) {
    const parts = option.split('.')
    if (parts.length === 1) {
        // Top-level lookup
        return config.find(c => {
            const baseName = c.name.replace(/^\[.*?\]\./, '')
            return baseName === option || c.name === option
        })
    }
    // Nested lookup: walk parent.child.grandchild...
    let items = config
    for (let i = 0; i < parts.length; i++) {
        const part = parts[i]
        const match = items.find(c => {
            const baseName = c.name.replace(/^\[.*?\]\./, '')
            return baseName === part || c.name === part
        })
        if (!match) return null
        if (i === parts.length - 1) return match
        items = match.children || []
    }
    return null
}

onMounted(() => {
    try {
        const data = getPluginData(props.plugin, props.version)
        if (data) {
            const item = findItem(data.config || [], props.option)
            if (item) {
                choices.value = item.choices
            }
        }
    } catch (e) {
        console.error(`Failed to load choices for ${props.plugin}.${props.option}`, e)
    } finally {
        loaded.value = true
    }
})
</script>

<style scoped>
.config-choices {
    margin: 0.5em 0;
    padding-left: 1.5em;
}

.config-choices li {
    margin: 0.25em 0;
}

.config-choices code {
    font-weight: 600;
}
</style>
