// .vitepress/theme/index.js
import DefaultTheme from 'vitepress/theme'

import CommandList from '/components/CommandList.vue'
import './custom.css'

/** @type {import('vitepress').Theme} */
export default {
    extends: DefaultTheme,
    enhanceApp({ app }) {
        // global components
        app.component('CommandList', CommandList)
    }
}
