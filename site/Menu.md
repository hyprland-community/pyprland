# Menu capability

Menu based plugins have the following configuration options:

### `engine` (optional)

Not set by default, will autodetect the available menu engine.

Supported engines:

- tofi
- rofi
- wofi
- bemenu
- dmenu
- anyrun

> [!note]
> If your menu system isn't supported, you can open a [feature request](https://github.com/hyprland-community/pyprland/issues/new?assignees=fdev31&labels=bug&projects=&template=feature_request.md&title=%5BFEAT%5D+Description+of+the+feature)
>
> In case the engine isn't recognized, `engine` + `parameters` configuration options will be used to start the process, it requires a dmenu-like behavior.

### `parameters` (optional)

Extra parameters added to the engine command, the default value is specific to each engine.

> [!important]
> Setting this will override the default value!
>
> In general, *rofi*-like programs will require at least `-dmenu` option.

> [!tip]
> *Since version 2.0*, you can use '[prompt]' in the parameters, it will be replaced by the prompt, eg:
> ```sh
> -dmenu -matching fuzzy -i -p '[prompt]'
> ```
