### Multiple configuration files

You can also split your configuration into multiple files that will be loaded in the provided order after the main file (added in 2.2.4):
```toml
[pyprland]
include = ["/shared/pyprland.toml", "~/pypr_extra_config.toml"]
```
Since 2.2.16 you can also load folders, in which case TOML files in the folder will be loaded in alphabetical order:
```toml
[pyprland]
include = ["~/.config/pypr.d/"]
```

And then add a `~/.config/pypr.d/monitors.toml` file:
```toml
pyprland.plugins = [ "monitors" ]

[monitors.placement]
BenQ.Top_Center_Of = "DP-1" # projo
"CJFH277Q3HCB".top_of = "eDP-1" # work
```

> [!tip]
> To check the final merged configuration, you can use the `dumpjson` command.

