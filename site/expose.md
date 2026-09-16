---
---

# expose

Implements the "expose" effect, showing every client window on the focused screen.

For a similar feature using a menu, try the [fetch_client_menu](./fetch_client_menu) plugin (less intrusive).

Sample `hyprland.lua`:

```lua
--Setup the key binding
hl.bind(mainMod .. " + B", hl.dsp.exec_cmd(pypr .. " expose"))

--Add some style to the "exposed" workspace
hl.workspace_rule({
	workspace = "special:exposed",
	gaps_out = 60,
	gaps_in = 30,
	border_size = 5,
	no_shadow = true,
})
```

`MOD+B` will bring every client to the focused workspace, pressed again it will go to this workspace.

Check [workspace rules](https://wiki.hyprland.org/Configuring/Workspace-Rules/#rules) for styling options.

> [!note]
> If you are looking for `toggle_minimized`, check the [toggle_special](./toggle_special) plugin


## Commands

<PluginCommands plugin="expose" />

## Configuration

<PluginConfig plugin="expose" linkPrefix="config-" />

