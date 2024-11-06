---
commands:
    - name: shift_monitors <direction>
      description: Swaps the workspaces of every screen in the given direction.
---

# shift_monitors

Swaps the workspaces of every screen in the given direction.

> [!Note]
> the behavior can be hard to predict if you have more than 2 monitors (depending on your layout).
> If you use this plugin with many monitors and have some ideas about a convenient configuration, you are welcome ;)

Example usage in `hyprland.conf`:

```
bind = $mainMod, O, exec, pypr shift_monitors +1
bind = $mainMod SHIFT, O, exec, pypr shift_monitors -1
```

## Command

<CommandList :commands="$frontmatter.commands" />

