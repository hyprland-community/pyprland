<template>
    <div>
        <h1>Built-in plugins</h1>
        <div v-if="loading">Loading plugins...</div>
        <div v-else-if="error">{{ error }}</div>
        <div v-else v-for="plugin in sortedPlugins" :key="plugin.name" class="plugin-item">
            <div class="plugin-info">
                <h3>
                    <a :href="plugin.name + '.html'">{{ plugin.name }}</a>
                    <span v-html="'&nbsp;' + getStars(plugin.stars)"></span>
                    <span v-if="plugin.multimon">
                        <Badge type="tip" text="multi-monitor" />
                    </span>
                    <span v-if="plugin.environments && plugin.environments.length">
                        <Badge v-for="env in plugin.environments" :key="env" type="tip" :text="env" style="margin-left: 5px;" />
                    </span>
                </h3>
                <p v-html="plugin.description" />
            </div>
            <a v-if="plugin.demoVideoId" :href="'https://www.youtube.com/watch?v=' + plugin.demoVideoId"
                class="plugin-video">
                <img :src="'https://img.youtube.com/vi/' + plugin.demoVideoId + '/1.jpg'" alt="Demo video thumbnail" />
            </a>
        </div>
    </div>
</template>

<style scoped>
.plugin-item {
    display: flex;
    align-items: flex-start;
    margin-bottom: 1.5rem;
}

.plugin-info {
    flex: 1;
}

.plugin-video {
    margin-left: 1rem;
}

.plugin-video img {
    max-width: 200px;
    /* Adjust as needed */
    height: auto;
}
</style>


<script>
import pluginIndex from '../generated/index.json'

export default {
    computed: {
        sortedPlugins() {
            if (!this.plugins.length) return []
            if (this.sortByStars) {
                return this.plugins.slice().sort((a, b) => {
                    if (b.stars === a.stars) {
                        return a.name.localeCompare(b.name);
                    }
                    return b.stars - a.stars;
                });
            } else {
                return this.plugins.slice().sort((a, b) => a.name.localeCompare(b.name));
            }
        }
    },
    data() {
        return {
            sortByStars: false,
            plugins: [],
            loading: true,
            error: null
        }
    },
    mounted() {
        try {
            // Filter out internal plugins like 'pyprland'
            this.plugins = pluginIndex.plugins.filter(p => p.name !== 'pyprland')
        } catch (e) {
            this.error = 'Failed to load plugin list'
            console.error(e)
        } finally {
            this.loading = false
        }
    },
    methods: {
        getStars(count) {
            return count > 0 ? '&#11088;'.repeat(count) : ''
        }
    }
}
</script>
