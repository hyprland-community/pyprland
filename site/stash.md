---
---

# stash

Stash and show windows in named groups using special workspaces.

Unlike `toggle_special` which uses a single special workspace, `stash` supports multiple named stash groups. Windows can be quickly stashed away and retrieved later, appearing on whichever workspace you are currently on.

## Usage

```bash
bind = $mainMod, S, exec, pypr stash          # toggle stash the focused window
bind = $mainMod SHIFT, S, exec, pypr stash_toggle # show/hide stashed windows
```

For multiple stash groups:

```bash
bind = $mainMod, S, exec, pypr stash default
bind = $mainMod, W, exec, pypr stash work
bind = $mainMod SHIFT, S, exec, pypr stash_toggle default
bind = $mainMod SHIFT, W, exec, pypr stash_toggle work
```

## Commands

<PluginCommands plugin="stash" />

## Configuration

<PluginConfig plugin="stash" />

### Example

```toml
[stash]
style = [
    "border_color rgb(ec8800)",
    "border_size 3",
]
```

When `style` is set, shown stash windows are tagged with `stash` and the listed [window rules](https://wiki.hyprland.org/Configuring/Window-Rules/) are applied.
The tag is removed when windows are hidden or removed from the stash.

### Overlay mode

By default, `stash_toggle` restores windows to their original floating/tiled state (e.g. a tiled window will return as tiled). Set `restore_floating` to `false` to keep shown windows floating as overlays instead:

```toml
[stash]
restore_floating = false
```
