// .vitepress/theme/index.js
import DefaultTheme from 'vitepress/theme'

import CommandList from '/components/CommandList.vue'
import ConfigBadges from '/components/ConfigBadges.vue'
import EngineDefaults from '/components/EngineDefaults.vue'
import PluginCommands from '/components/PluginCommands.vue'
import PluginConfig from '/components/PluginConfig.vue'
import './custom.css'

/** @type {import('vitepress').Theme} */
export default {
    extends: DefaultTheme,
    enhanceApp({ app }) {
        // global components
        app.component('CommandList', CommandList)
        app.component('ConfigBadges', ConfigBadges)
        app.component('EngineDefaults', EngineDefaults)
        app.component('PluginCommands', PluginCommands)
        app.component('PluginConfig', PluginConfig)
    }
}
