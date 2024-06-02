<template>
    <div>
        <h1>Built-in plugins</h1>
        <div v-for="plugin in sortedPlugins" :key="plugin.name" class="plugin-item">
            <div class="plugin-info">
                <h3>
                    <a :href="plugin.name + '.html'">{{ plugin.name }}</a>
                    <span>&nbsp;{{ '🌟'.repeat(plugin.stars) }}</span>
                    <span>{{ plugin.multimon ? ' (multi-monitor)' : '' }}</span>
                </h3>
                <p v-html="plugin.description" />
            </div>
            <a v-if="plugin.demoVideoId" :href="'https://www.youtube.com/watch?v=' + plugin.demoVideoId"
                class="plugin-video">
                <img :src="'https://img.youtube.com/vi/' + plugin.demoVideoId + '/1.jpg'" alt="Demo video thumbnail" />
            </a>
        </div>
    </div>
</template>

<style scoped>
.plugin-item {
    display: flex;
    align-items: flex-start;
    margin-bottom: 1.5rem;
}

.plugin-info {
    flex: 1;
}

.plugin-video {
    margin-left: 1rem;
}

.plugin-video img {
    max-width: 200px;
    /* Adjust as needed */
    height: auto;
}
</style>


<script>

export default {
    computed: {
        sortedPlugins() {
            if (this.sortByStars) {
                return this.plugins.slice().sort((a, b) => {
                    if (b.stars === a.stars) {
                        return a.name.localeCompare(b.name);
                    }
                    return b.stars - a.stars;
                });
            } else {
                return this.plugins.slice().sort((a, b) => a.name.localeCompare(b.name));
            }
        }
    },
    data() {
        return {
            sortByStars: false,
            plugins: [
                {
                    name: 'scratchpads',
                    stars: 3,
                    description: 'makes your applications dropdowns & togglable poppups',
                    demoVideoId: 'ZOhv59VYqkc'
                },
                {
                    name: 'magnify',
                    stars: 3,
                    description: 'toggles zooming of viewport or sets a specific scaling factor',
                    demoVideoId: 'yN-mhh9aDuo'

                },
                {
                    name: 'toggle_special',
                    stars: 3,
                    description: 'moves windows from/to special workspaces',
                    demoVideoId: 'BNZCMqkwTOo'
                },
                {
                    name: 'shortcuts_menu',
                    stars: 3,
                    description: 'a flexible way to make your own shortcuts menus & launchers',
                    demoVideoId: 'UCuS417BZK8'
                },
                {
                    name: 'fetch_client_menu',
                    stars: 3,
                    description: 'select a window to be moved to your active workspace (using rofi, dmenu, etc...)',
                },
                {
                    name: 'layout_center',
                    stars: 3,
                    description: 'a workspace layout where one client window is almost maximized and others seat in the background',
                    demoVideoId: 'vEr9eeSJYDc'
                },
                {
                    name: 'system_notifier',
                    stars: 3,
                    description: 'open streams (eg: journal logs) and trigger notifications',
                },
                {
                    name: 'wallpapers',
                    stars: 3,
                    description: 'handles random wallpapers at regular interval (from a folder)'
                },
                {
                    name: 'gbar',
                    stars: 3,
                    description: 'improves multi-monitor handling of the status bar - only <tt>gBar</tt> is supported at the moment'
                },
                {
                    name: 'expose',
                    stars: 2,
                    description: 'exposes all the windows for a quick "jump to" feature',
                    demoVideoId: 'ce5HQZ3na8M'
                },
                {
                    name: 'lost_windows',
                    stars: 1,
                    description: 'brings lost floating windows (which are out of reach) to the current workspace'
                },
                {
                    name: 'toggle_dpms',
                    stars: 0,
                    description: 'toggles the DPMS status of every plugged monitor'
                },
                {
                    name: 'workspaces_follow_focus',
                    multimon: true,
                    stars: 3,
                    description: 'makes non visible workspaces available on the currently focused screen.<br/> If you think the multi-screen behavior of Hyprland is not usable or broken/unexpected, this is probably for you.'

                },
                {
                    name: 'shift_monitors',
                    multimon: true,
                    stars: 3,
                    description: 'moves workspaces from monitor to monitor (caroussel)'
                },
                {
                    name: 'monitors',
                    stars: 3,
                    description: 'allows relative placement and configuration of monitors'
                }
            ]
        }
    }
}
</script>
