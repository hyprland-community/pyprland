# Troubleshooting configuration options for scratchpads

### `skip_windowrules` (optional)

> _Added in 2.2.17_

Default value is `[]`
Allows you to skip the window rules for a specific scratchpad.
Available rules are:

- "aspect" controlling size and position
- "float" controlling the floating state
- "workspace" which moves the window to its own workspace

If you are using an application which can spawn multiple windows and you can't see them, you can skip rules made to improve the initial display of the window.

```toml
[scratchpads.filemanager]
animation = "fromBottom"
command = "nemo"
class = "nemo"
size = "60% 60%"
skip_windowrules = ["aspect", "workspace"]
```

### `match_by` (optional)

> _Added in 2.2.5_

Default value is `"pid"`
When set to a sensitive client property value (eg: `class`, `initialClass`, `title`, `initialTitle`), will match the client window using the provided property instead of the PID of the process.
This property must be set accordingly, eg:

```toml
match_by = "class"
class = "my-web-app"
```

or

```toml
match_by = "initialClass"
initialClass = "my-web-app"
```

You can add the "re:" prefix to use a regular expression, eg:

```toml
match_by = "title"
title = "re:.*some string.*"
```

### `class_match` (DEPRECATED)

> [!important]
> Has been replaced by `match_by` in versions > 2.2.4

Will set `match_by="class"` if set to `true` - support will be dropped in the future.

### `process_tracking` (optional)

Default value is `true`

Allows disabling the process management. Use only if running a progressive web app (Chrome based apps) or similar.
Check [this wiki page](https://github.com/hyprland-community/pyprland/wiki/Troubleshooting#disable-process-management) for some details.

This will automatically force `lazy = true` and set `match_by="class"` if no `match_by` rule is provided, to help with the fuzzy client window matching.

It requires defining a `class` option (or the option matching your `match_by` value).

```toml
## Chat GPT on Brave
[scratchpads.gpt]
animation = "fromTop"
command = "brave --profile-directory=Default --app=https://chat.openai.com"
class = "brave-chat.openai.com__-Default"
size = "75% 60%"
process_tracking = false

## Some chrome app
[scratchpads.music]
command = "google-chrome --profile-directory=Default --app-id=cinhimbnkkaeohfgghhklpknlkffjgod"
class = "chrome-cinhimbnkkaeohfgghhklpknlkffjgod-Default"
size = "50% 50%"
process_tracking = false
```

> [!tip]
> To list windows by class and title you can use:
> - `hyprctl -j clients | jq '.[]|[.class,.title]'`
> - or if you prefer a graphical tool: `rofi -show window`
