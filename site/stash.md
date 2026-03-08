---
---

# stash

Stash and show windows in named groups using special workspaces.

Unlike `toggle_special` which uses a single special workspace, `stash` supports multiple named stash groups. Windows can be quickly stashed away and retrieved later, appearing on whichever workspace you are currently on.

## Usage

```bash
bind = $mainMod, S, exec, pypr stash          # toggle stash the focused window
bind = $mainMod SHIFT, S, exec, pypr stash_show # peek at stashed windows
```

For multiple stash groups:

```bash
bind = $mainMod, S, exec, pypr stash default
bind = $mainMod, W, exec, pypr stash work
bind = $mainMod SHIFT, S, exec, pypr stash_show default
bind = $mainMod SHIFT, W, exec, pypr stash_show work
```

## Commands

<PluginCommands plugin="stash" />

## Configuration

This plugin has no configuration options.
