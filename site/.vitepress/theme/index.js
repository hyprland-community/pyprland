// .vitepress/theme/index.js
import DefaultTheme from 'vitepress/theme'
import { nextTick } from 'vue'

import CommandList from '/components/CommandList.vue'
import ConfigBadges from '/components/ConfigBadges.vue'
import EngineDefaults from '/components/EngineDefaults.vue'
import PluginCommands from '/components/PluginCommands.vue'
import PluginConfig from '/components/PluginConfig.vue'
import './custom.css'

/** @type {import('vitepress').Theme} */
export default {
    extends: DefaultTheme,
    enhanceApp({ app, router }) {
        // global components
        app.component('CommandList', CommandList)
        app.component('ConfigBadges', ConfigBadges)
        app.component('EngineDefaults', EngineDefaults)
        app.component('PluginCommands', PluginCommands)
        app.component('PluginConfig', PluginConfig)

        // Version switcher: preserve current page when changing versions
        router.onBeforeRouteChange = (to) => {
            const versionRootMatch = to.match(/^\/pyprland\/versions\/([^/]+)\/$/)
            if (versionRootMatch) {
                const currentPage = router.route.path
                    .replace(/^\/pyprland\/versions\/[^/]+\//, '')
                    .replace(/^\/pyprland\//, '')
                if (currentPage && currentPage !== '' && currentPage !== 'index.html') {
                    return `/pyprland/versions/${versionRootMatch[1]}/${currentPage}`
                }
            }
        }

        // Fallback: if page doesn't exist (404), redirect to version root
        if (typeof window !== 'undefined') {
            router.onAfterRouteChanged = (to) => {
                nextTick(() => {
                    if (document.querySelector('.NotFound')) {
                        const versionMatch = to.match(/^\/pyprland\/versions\/([^/]+)\//)
                        if (versionMatch) {
                            router.go(`/pyprland/versions/${versionMatch[1]}/`)
                        }
                    }
                })
            }
        }
    }
}
