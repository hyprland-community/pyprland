---
---

# toggle_special

Allows moving the focused window to a special workspace and back (based on the visibility status of that workspace).

It's a companion of the `togglespecialworkspace` Hyprland's command which toggles a special workspace's visibility.

You most likely will need to configure the two commands for a complete user experience, eg:

```bash
bind = $mainMod SHIFT, N, togglespecialworkspace, stash # toggles "stash" special workspace visibility
bind = $mainMod, N, exec, pypr toggle_special stash # moves window to/from the "stash" workspace
```

No other configuration needed, here `MOD+SHIFT+N` will show every window in "stash" while `MOD+N` will move the focused window out of it/ to it.

## Commands

| Command | Description |
|---------|-------------|
| `toggle_special [name]` | Toggles switching the focused window to the special workspace "name" (default: minimized). |


## Configuration

| Option | Description |
|--------|-------------|
| `name` · *str* · =`"minimized"` | Default special workspace name |


### `name` *str* · =`"minimized"` {#config-name}

Default special workspace name.
