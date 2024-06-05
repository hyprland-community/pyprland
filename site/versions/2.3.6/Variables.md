# Variables & substitutions

Some commands support shared global variables, they must be defined in the *pyprland* section of the configuration:
```toml
[pyprland.variables]
term = "foot"
term_classed = "foot -a" # kitty uses --class
```

If a plugin supports it, you can then use the variables in the attribute that supports it, eg:

```toml
[myplugin]
some_variable = "the terminal is [term]"
```
