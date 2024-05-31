import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "Pyprland web",
  base: "/pyprland/",
  description: "The official Pyprland website",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config

    socialLinks: [
      { icon: 'github', link: 'https://github.com/fdev31/pyprland' }
    ]
  }
})
