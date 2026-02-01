---
---

# workspaces_follow_focus

Make non-visible workspaces follow the focused monitor.
Also provides commands to switch between workspaces while preserving the current monitor assignments:

Syntax:
```toml
[workspaces_follow_focus]
max_workspaces = 4 # number of workspaces before cycling
```
Example usage in `hyprland.conf`:

```ini
bind = $mainMod, K, exec, pypr change_workspace +1
bind = $mainMod, J, exec, pypr change_workspace -1
 ```

## Commands

<PluginCommands plugin="workspaces_follow_focus" />

## Configuration

<PluginConfig plugin="workspaces_follow_focus" linkPrefix="config-" />

