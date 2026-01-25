<script setup>
import PluginList from '/components/PluginList.vue'
</script>

This page lists every plugin provided by Pyprland out of the box, more can be enabled if you install the matching package.

"🌟" indicates some maturity & reliability level of the plugin, considering age, attention paid and complexity - from 0 to 3.

A badge such as <Badge type="tip">multi-monitor</Badge> indicates a requirement.

Some plugins require an external **graphical menu system**, such as *rofi*.
Each plugin can use a different menu system but the [configuration is unified](Menu). In case no [engine](Menu#engine) is provided some auto-detection of installed applications will happen.

<PluginList/>
