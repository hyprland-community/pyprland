# Menu capability

Menu based plugins have the following configuration options:

<PluginConfig plugin="menu" linkPrefix="config-" />

### `engine` {#config-engine}

<ConfigDefault plugin="menu" option="engine" />

Auto-detects the available menu engine if not set.

Supported engines (tested in order):

- fuzzel
- tofi
- rofi
- wofi
- bemenu
- dmenu
- anyrun
- walker

> [!note]
> If your menu system isn't supported, you can open a [feature request](https://github.com/hyprland-community/pyprland/issues/new?assignees=fdev31&labels=bug&projects=&template=feature_request.md&title=%5BFEAT%5D+Description+of+the+feature)
>
> In case the engine isn't recognized, `engine` + `parameters` configuration options will be used to start the process, it requires a dmenu-like behavior.

### `parameters` {#config-parameters}

<ConfigDefault plugin="menu" option="parameters" />

Extra parameters added to the engine command. Setting this will override the engine's default value.

> [!tip]
> You can use `[prompt]` in the parameters, it will be replaced by the prompt, eg for rofi/wofi:
> ```sh
> -dmenu -matching fuzzy -i -p '[prompt]'
> ```

#### Default parameters per engine

<EngineDefaults />
