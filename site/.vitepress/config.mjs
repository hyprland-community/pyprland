const enableVersions = true;
import { defineConfig } from 'vitepress'

const version_names = ['2.3.5']

const extra_versions = {
  items: [
    {
      text: 'Latest',
      link: '/'
    }
  ]
}


for (const version of version_names) {
  extra_versions.items.push({
    text: version,
    link: `/versions/${version}/`
  })
}


const menu = [
  { text: 'Getting started', link: './Getting-started' },
  { text: 'Plugins', link: './Plugins' },
  { text: 'Troubleshooting', link: './Troubleshooting' },
  { text: 'Development', link: './Development' },
]

const plugin_list = {
  text: 'Featured plugins',
  collapsible: true,
  collapsed: false,
  items: [
    { text: "Expose", link: "./expose" },
    { text: "Fetch client menu", link: "./fetch_client_menu" },
    { text: "Gbar", link: "./gbar" },
    { text: "Layout center", link: "./layout_center" },
    { text: "Lost windows", link: "./lost_windows" },
    { text: "Magnify", link: "./magnify" },
    { text: "Monitors", link: "./monitors" },
    {
      text: "Scratchpads", link: "./scratchpads",
      items: [
        { text: "Advanced", link: "./scratchpads_advanced" },
        { text: "Special cases", link: "./scratchpads_nonstandard" }

      ]
    },
    { text: "Shift monitors", link: "./shift_monitors" },
    { text: "Shortcuts menu", link: "./shortcuts_menu" },
    { text: "System notifier", link: "./system_notifier" },
    { text: "Toggle dpms", link: "./toggle_dpms" },
    { text: "Toggle special", link: "./toggle_special" },
    { text: "Wallpapers", link: "./wallpapers" },
    { text: "Workspaces follow focus", link: "./workspaces_follow_focus" },
  ]
}

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "Pyprland web",
  base: "/pyprland/",
  description: "The official Pyprland website",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: menu,
    logo: '/icon.png',
    search: {
      provider: 'local'
    },
    outline: {
      level: [2, 3],
    },
    sidebar: {
      collapsible: true,
      collapsed: true,
      '/versions': [
        plugin_list,
        {
          text: 'Return to latest version',
          link: '/'
        }
      ],
      '/': [
        plugin_list,
        {
          text: 'Versions',
          items: [extra_versions],
        }
      ]
    },
    socialLinks: [
      { icon: 'github', link: 'https://github.com/fdev31/pyprland' },
      { icon: 'discord', link: 'https://discord.com/channels/1055990214411169892/1230972154330218526' }
    ]
  }
})
