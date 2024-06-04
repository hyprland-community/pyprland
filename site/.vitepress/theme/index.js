// .vitepress/theme/index.js
import DefaultTheme from 'vitepress/theme'

import CommandList from '/components/CommandList.vue'

/** @type {import('vitepress').Theme} */
export default {
    extends: DefaultTheme,
    enhanceApp({ app }) {
        // global components
        app.component('CommandList', CommandList)
    }
}
