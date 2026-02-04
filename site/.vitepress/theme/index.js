// .vitepress/theme/index.js
import DefaultTheme from 'vitepress/theme'

import CommandList from "/components/CommandList.vue";
import ConfigBadges from "/components/ConfigBadges.vue";
import EngineDefaults from "/components/EngineDefaults.vue";
import EngineList from "/components/EngineList.vue";
import PluginCommands from '/components/PluginCommands.vue'
import PluginConfig from '/components/PluginConfig.vue'
import PluginList from '/components/PluginList.vue'
import './custom.css'

/** @type {import('vitepress').Theme} */
export default {
    extends: DefaultTheme,
    enhanceApp({ app, router }) {
        // global components
        app.component('CommandList', CommandList)
        app.component('PluginCommands', PluginCommands)
        app.component("PluginConfig", PluginConfig);
        app.component("PluginList", PluginList);
        app.component("ConfigBadges", ConfigBadges);
        app.component("EngineDefaults", EngineDefaults);
        app.component("EngineList", EngineList);

        // Version switcher: preserve current page when changing versions
        router.onBeforeRouteChange = (to) => {
            // Don't intercept if we're leaving a 404 page
            if (router.route.data.isNotFound) {
                return
            }

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
        router.onAfterRouteChanged = (to) => {
            if (router.route.data.isNotFound) {
                const versionMatch = to.match(/^\/pyprland\/versions\/([^/]+)\//)
                if (versionMatch) {
                    const target = `/pyprland/versions/${versionMatch[1]}/`
                    // Replace current history entry so back button skips the 404
                    history.replaceState(null, '', target)
                    router.go(target)
                }
            }
        }
    }
}
