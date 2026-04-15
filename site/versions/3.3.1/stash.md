---
---

# stash

Store single-window overlays in named stashes.

Each stash name is a single slot. A stashed window can be shown as a pinned overlay on top of your current workspace and stays visible while you switch workspaces, including special workspaces.

## Usage

```bash
bind = $mainMod,       S, exec, pypr stash_toggle S
bind = $mainMod SHIFT, S, exec, pypr stash_send   S
bind = $mainMod,       C, exec, pypr stash_toggle C
bind = $mainMod SHIFT, C, exec, pypr stash_send   C
```

`stash_send <name>`:

- sends the focused window into stash `<name>`
- if `<name>` is already occupied, releases the old window to the current workspace and replaces it
- if the focused window is already the shown stash window, releases it back to the current workspace

`stash_toggle <name>`:

- shows the named stash as a pinned floating overlay
- hides it back into its hidden special workspace

The first show uses the configured `size` and `position`. If `preserve_aspect = true`, later hide/show cycles keep the live size and position you last left the stash at.

## Commands

<PluginCommands plugin="stash"  version="3.3.1" />

## Configuration

<PluginConfig plugin="stash"  version="3.3.1" />

### Example

```toml
[pyprland]
plugins = ["stash"]

[stash.S]
animation = ""
size = "24% 54%"
position = "76% 22%"
preserve_aspect = true

[stash.C]
animation = ""
size = "24% 54%"
position = "76% 22%"
preserve_aspect = true
```

## Notes

- `animation` is currently reserved and does not change behavior yet.
- Stash windows are backed by hidden `special:st-<name>` workspaces when not shown.
- During a clean `pypr` shutdown, stash windows are released back to the active workspace as a best effort cleanup.
