// .vitepress/theme/index.js
import DefaultTheme from 'vitepress/theme'
import { nextTick } from 'vue'

import ConfigBadges from '/components/ConfigBadges.vue'
import EngineDefaults from '/components/EngineDefaults.vue'
import PluginCommands from '/components/PluginCommands.vue'
import PluginConfig from '/components/PluginConfig.vue'
import PluginList from '/components/PluginList.vue'
import './custom.css'

/** @type {import('vitepress').Theme} */
export default {
    extends: DefaultTheme,
    enhanceApp({ app, router }) {
        // global components
        app.component('ConfigBadges', ConfigBadges)
        app.component('EngineDefaults', EngineDefaults)
        app.component('PluginCommands', PluginCommands)
        app.component('PluginConfig', PluginConfig)
        app.component('PluginList', PluginList)

        // Version switcher: preserve current page when changing versions
        router.onBeforeRouteChange = (to) => {
            // Switching to a specific version
            const versionRootMatch = to.match(/^\/pyprland\/versions\/([^/]+)\/$/)
            if (versionRootMatch) {
                const currentPage = router.route.path
                    .replace(/^\/pyprland\/versions\/[^/]+\//, '')
                    .replace(/^\/pyprland\//, '')
                if (currentPage && currentPage !== '' && currentPage !== 'index.html') {
                    router.go(`/pyprland/versions/${versionRootMatch[1]}/${currentPage}`)
                    return false
                }
            }

            // Switching to current version (from a versioned page)
            if (to === '/pyprland/' || to === '/pyprland/index.html') {
                const versionedPageMatch = router.route.path.match(/^\/pyprland\/versions\/[^/]+\/(.+)$/)
                if (versionedPageMatch && versionedPageMatch[1] !== 'index.html') {
                    router.go(`/pyprland/${versionedPageMatch[1]}`)
                    return false
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
