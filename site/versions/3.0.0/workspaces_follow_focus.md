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

| Command | Description |
|---------|-------------|
| `change_workspace <direction>` | Switch workspaces of current monitor, avoiding displayed workspaces. |


## Configuration

| Option | Description |
|--------|-------------|
| `max_workspaces` · *int* · =`10` | Maximum number of workspaces to manage |


