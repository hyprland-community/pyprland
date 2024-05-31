import { defineConfig } from 'vitepress'

const menu = [
  { text: 'Getting started', link: '/Getting-started' },
  { text: 'Plugins', link: '/Plugins' },
  { text: 'Troubleshooting', link: '/Troubleshooting' },
  { text: 'Development', link: '/Development' },
]

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "Pyprland web",
  base: "/pyprland/",
  description: "The official Pyprland website",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: menu,

    sidebar: [
      {
        text: 'Navigation',
        items: menu
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/fdev31/pyprland' }
    ]
  }
})
