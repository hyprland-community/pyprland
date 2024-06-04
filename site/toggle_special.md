---
commands:
    - name: toggle_special [name]
      description: moves the focused window to the special workspace <code>name</code>, or move it back to the active workspace
---

# toggle_special

Allows moving the focused window to a special workspace and back (based on the visibility status of that workspace).

It's a companion of `togglespecialworkspace` Hyprland's command which toggles a special workspace's visibility.

You most likely will need to configure the two commands for a complete user experience, eg:

```bash
bind = $mainMod SHIFT, N, togglespecialworkspace, stash # toggles "stash" special workspace visibility
bind = $mainMod, N, exec, pypr toggle_special stash # moves window to/from the "stash" workspace
```

No other configuration needed, here `MOD+SHIFT+N` will show every window in "stash" while `MOD+N` will move the focused window out of it/ to it.

## Command

<CommandList :commands="$frontmatter.commands" />
