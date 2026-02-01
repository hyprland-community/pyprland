/**
 * VitePress configuration with dynamic version discovery.
 *
 * Sidebar configurations are loaded from sidebar.json files:
 * - site/sidebar.json for current version
 * - site/versions/<version>/sidebar.json for archived versions
 *
 * Versions are automatically discovered by scanning the versions/ folder.
 */

import { readdirSync, readFileSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

const __dirname = dirname(fileURLToPath(import.meta.url))
const siteDir = join(__dirname, '..')

/**
 * Load sidebar configuration from a sidebar.json file.
 * @param {string} dir - Directory containing sidebar.json
 * @returns {Array|null} - Sidebar items array or null if not found
 */
function loadSidebar(dir) {
  const sidebarPath = join(dir, 'sidebar.json')
  if (!existsSync(sidebarPath)) {
    console.warn(`Warning: sidebar.json not found in ${dir}`)
    return null
  }

  try {
    const config = JSON.parse(readFileSync(sidebarPath, 'utf-8'))
    return [...config.main, config.plugins]
  } catch (e) {
    console.error(`Error loading sidebar from ${sidebarPath}:`, e.message)
    return null
  }
}

/**
 * Discover all versions and build sidebar + nav configuration.
 * @returns {{ sidebar: Object, nav: Array }}
 */
function buildVersionedConfig() {
  const sidebar = {}
  const versionItems = [{ text: 'Current', link: '/' }]

  // Load current version sidebar
  const currentSidebar = loadSidebar(siteDir)
  if (currentSidebar) {
    sidebar['/'] = currentSidebar
  }

  // Discover and load archived versions
  const versionsDir = join(siteDir, 'versions')
  if (existsSync(versionsDir)) {
    const versions = readdirSync(versionsDir, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => d.name)
      // Sort versions: newest first (descending)
      .sort((a, b) => {
        // Extract numeric parts for comparison
        const aParts = a.replace(/[^0-9.]/g, '').split('.').map(Number)
        const bParts = b.replace(/[^0-9.]/g, '').split('.').map(Number)
        for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
          const aVal = aParts[i] || 0
          const bVal = bParts[i] || 0
          if (bVal !== aVal) return bVal - aVal
        }
        return 0
      })

    for (const version of versions) {
      const versionDir = join(versionsDir, version)
      const versionSidebar = loadSidebar(versionDir)

      if (versionSidebar) {
        sidebar[`/versions/${version}/`] = [
          ...versionSidebar,
          { text: 'Return to latest version', link: '/' }
        ]
      }

      versionItems.push({ text: version, link: `/versions/${version}/` })
    }
  }

  const nav = [{ text: 'Versions', items: [{ items: versionItems }] }]

  return { sidebar, nav }
}

const { sidebar, nav } = buildVersionedConfig()

export default withMermaid(defineConfig({
  title: 'Pyprland web',
  base: '/pyprland/',
  description: 'The official Pyprland website',
  themeConfig: {
    nav,
    logo: '/icon.png',
    search: {
      provider: 'local',
      options: {
        _render(src, env, md) {
          const html = md.render(src, env)
          // Exclude versioned pages from search index
          if (env.relativePath.startsWith('versions/')) return ''
          // Also respect frontmatter search: false
          if (env.frontmatter?.search === false) return ''
          return html
        }
      }
    },
    outline: { level: [2, 3] },
    sidebar,
    socialLinks: [
      { icon: 'github', link: 'https://github.com/fdev31/pyprland' },
      { icon: 'discord', link: 'https://discord.com/channels/1055990214411169892/1230972154330218526' }
    ]
  },
  mermaid: {},
  mermaidPlugin: { class: 'mermaid' }
}))
