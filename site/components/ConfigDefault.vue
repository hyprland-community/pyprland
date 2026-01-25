<template>
    <div v-if="hasDefault" class="config-default">
        <strong>Default:</strong> <code>{{ formattedDefault }}</code>
        <span class="rightaligned">
        <badge v-if="defaultItem?.recommended" type="warning">recommended</badge>
        <badge v-else-if="defaultItem?.required" type="danger">required</badge>
        </span>
    </div>
    <div v-else-if="loaded" class="config-default config-default-none">
        <strong>Default:</strong> <em>none</em>
        <span class="rightaligned">
        <badge v-if="defaultItem?.recommended" type="warning">recommended</badge>
        <badge v-else-if="defaultItem?.required" type="danger">required</badge>
        </span>
    </div>
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
            defaultValue: null,
            defaultItem: null,
            loaded: false
        }
    },
    async mounted() {
        try {
            const data = await import(`../generated/${this.plugin}.json`)
            const config = data.config || []
            // Find the option - handle both "option" and "[prefix].option" formats
            const item = config.find(c => {
                const baseName = c.name.replace(/^\[.*?\]\./, '')
                return baseName === this.option || c.name === this.option
            })
            if (item) {
                this.defaultValue = item.default
                this.defaultItem = item
            }
        } catch (e) {
            console.error(`Failed to load config for plugin: ${this.plugin}`, e)
        } finally {
            this.loaded = true
        }
    },
    computed: {
        hasDefault() {
            if (this.defaultValue === null || this.defaultValue === undefined) return false
            if (this.defaultValue === '') return false
            if (Array.isArray(this.defaultValue) && this.defaultValue.length === 0) return false
            if (typeof this.defaultValue === 'object' && Object.keys(this.defaultValue).length === 0) return false
            return true
        },
        formattedDefault() {
            const value = this.defaultValue
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

.config-default .rightaligned {
    float: right;
}
.config-default {
    background-color: var(--vp-c-default-soft);
    border-left: 4px solid var(--vp-c-brand-1);
    padding: 0.5rem 1rem;
    margin: 0.5rem 0 1rem 0;
    border-radius: 0 4px 4px 0;
}

.config-default code {
    background-color: var(--vp-c-bg-soft);
    padding: 0.15em 0.4em;
    border-radius: 3px;
    font-size: 0.9em;
}

.config-default-none em {
    color: var(--vp-c-text-2);
}
</style>
