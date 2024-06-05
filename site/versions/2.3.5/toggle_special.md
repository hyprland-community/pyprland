# toggle_special

Allows moving the focused window to a special workspace and back (based on the visibility status of that workspace).

It's a companion of the `togglespecialworkspace` Hyprland's command which toggles a special workspace's visibility.

You most likely will need to configure the two commands for a complete user experience, eg:

```bash
bind = $mainMod SHIFT, N, togglespecialworkspace, stash # toggles "stash" special workspace visibility
bind = $mainMod, N, exec, pypr toggle_special stash # moves window to/from the "stash" workspace
```

No other configuration needed, here `MOD+SHIFT+N` will show every window in "stash" while `MOD+N` will move the focused window out of it/ to it.

> _Added in version 1.8.0_

## Commands

- `toggle_special [name]`: moves the focused window to the special workspace `name`, or move it back to the active workspace.
    If none set, "minimized" will be used.

