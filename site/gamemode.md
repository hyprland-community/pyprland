---
---

# gamemode

Toggle game mode for improved performance. When enabled, disables animations, blur, shadows, gaps, and rounding. When disabled, reloads the Hyprland config to restore original settings.

This is useful when gaming or running performance-intensive applications where visual effects may cause frame drops or input lag.

<details>
    <summary>Example</summary>

Sample `hyprland.conf`:

```sh
bind = $mainMod, G, exec, pypr gamemode
```

</details>

## Commands

<PluginCommands plugin="gamemode" />

## Configuration

<PluginConfig plugin="gamemode" linkPrefix="config-" />

### `auto` <ConfigBadges plugin="gamemode" option="auto" /> {#config-auto}

Enable automatic game mode detection. When enabled, pyprland monitors window open/close events and automatically enables game mode when a window matching one of the configured patterns is detected. Game mode is disabled when all matching windows are closed.

```toml
[gamemode]
auto = true
```

### `patterns` <ConfigBadges plugin="gamemode" option="patterns" /> {#config-patterns}

List of glob patterns to match window class names for automatic game mode activation. Uses shell-style wildcards (`*`, `?`, `[seq]`, `[!seq]`).

The default pattern `steam_app_*` matches all Steam games, which have window classes like `steam_app_870780`.

```toml
[gamemode]
auto = true
patterns = ["steam_app_*", "gamescope*", "lutris_*"]
```

To find the window class of a specific application, run:

```sh
hyprctl clients -j | jq '.[].class'
```

### `border_size` <ConfigBadges plugin="gamemode" option="border_size" /> {#config-border_size}

Border size to use when game mode is enabled. Since gaps are removed, a visible border helps distinguish window boundaries.

### `notify` <ConfigBadges plugin="gamemode" option="notify" /> {#config-notify}

Whether to show a notification when toggling game mode on or off.
