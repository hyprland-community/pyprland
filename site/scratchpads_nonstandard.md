# Troubleshooting scratchpads

Options that should only be used for applications that are not behaving in a "standard" way, such as `emacsclient` or progressive web apps.

## `match_by` (optional)

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

> [!note]
> Some apps may open the graphical client window in a "complicated" way, to work around this, it is possible to disable the process PID matching algorithm and simply rely on window's class.
>
> The `match_by` attribute can be used to achieve this, eg. for emacsclient:
> ```toml
> [scratchpads.emacs]
> command = "/usr/local/bin/emacsStart.sh"
> class = "Emacs"
> match_by = "class"
> ```

## `process_tracking` (optional)

Default value is `true`

Allows disabling the process management. Use only if running a progressive web app (Chrome based apps) or similar.

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

> [!note]
> Progressive web apps will share a single process for every window.
> On top of requiring the class based window tracking (using `match_by`),
> the process can not be managed the same way as usual apps and the correlation
> between the process and the client window isn't as straightforward and can lead to false matches in extreme cases.

## `skip_windowrules` (optional)

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
