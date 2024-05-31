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
      },
      {
        text: 'standard plugins',
        items: [
          { text: "Expose", link: "expose" },
          { text: "Fetch_client_menu", link: "fetch_client_menu" },
          { text: "Gbar", link: "gbar" },
          { text: "Layout center", link: "layout_center" },
          { text: "Lost_windows", link: "lost_windows" },
          { text: "Magnify", link: "magnify" },
          { text: "Monitors", link: "monitors" },
          { text: "Scratchpads", link: "scratchpads" },
          { text: "Shortcuts menu", link: "shortcuts_menu" },
          { text: "System notifier", link: "system_notifier" },
          { text: "Toggle dpms", link: "toggle_dpms" },
          { text: "Toggle special", link: "toggle_special" },
          { text: "Wallpapers", link: "wallpapers" },
        ]
      }, {
        text: 'multi-monitor plugins',
        items: [
          { text: "Monitors", link: "monitors" },
          { text: "Shift monitors", link: "shift_monitors" },
          { text: "Workspaces_follow focus", link: "workspaces_follow_focus" },
        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/fdev31/pyprland' }
    ]
  }
})
