---
---

# toggle_special

Allows moving the focused window to a special workspace and back (based on the visibility status of that workspace).

It's a companion of the `togglespecialworkspace` Hyprland's command which toggles a special workspace's visibility.

You most likely will need to configure the two commands for a complete user experience, eg:

```lua
hl.bind(mainMod .. " + SHIFT + N", hl.dsp.workspace.toggle_special("stash")) --toggles "stash" special workspace visibility
hl.bind(mainMod .. " + N", hl.dsp.exec_cmd(pypr .. " toggle_special stash") --moves window to/from the "stash" workspace
```

No other configuration needed, here `MOD+SHIFT+N` will show every window in "stash" while `MOD+N` will move the focused window out of it/ to it.

## Commands

<PluginCommands plugin="toggle_special" />

## Configuration

<PluginConfig plugin="toggle_special" linkPrefix="config-" />

### `name` <ConfigBadges plugin="toggle_special" option="name" /> {#config-name}

Default special workspace name.
