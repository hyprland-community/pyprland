<template>
    <span v-if="loaded && item" class="config-badges">
        <Badge type="info">{{ item.type }}</Badge>
        <Badge v-if="hasDefault" type="tip">=<code>{{ formattedDefault }}</code></Badge>
        <Badge v-if="item.required" type="danger">required</Badge>
        <Badge v-else-if="item.recommended" type="warning">recommended</Badge>
    </span>
</template>

<script>
export default {
    props: {
        plugin: {
            type: String,
            required: true
        },
        option: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            item: null,
            loaded: false
        }
    },
    async mounted() {
        try {
            const data = await import(`../generated/${this.plugin}.json`)
            const config = data.config || []
            // Find the option - handle both "option" and "[prefix].option" formats
            this.item = config.find(c => {
                const baseName = c.name.replace(/^\[.*?\]\./, '')
                return baseName === this.option || c.name === this.option
            })
        } catch (e) {
            console.error(`Failed to load config for plugin: ${this.plugin}`, e)
        } finally {
            this.loaded = true
        }
    },
    computed: {
        hasDefault() {
            if (!this.item) return false
            const value = this.item.default
            if (value === null || value === undefined) return false
            if (value === '') return false
            if (Array.isArray(value) && value.length === 0) return false
            if (typeof value === 'object' && Object.keys(value).length === 0) return false
            return true
        },
        formattedDefault() {
            if (!this.item) return ''
            const value = this.item.default
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
        }
    }
}
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
