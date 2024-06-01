# Troubleshooting

## General

In case of trouble running a `pypr` command:
- kill the existing pypr if any (try `pypr exit` first)
- run from the terminal adding `--debug /dev/null` to the arguments to get more information

If the client says it can't connect, then there is a high chance pypr daemon didn't start, check if it's running using `ps axuw |grep pypr`. You can try to run it from a terminal with the same technique: `pypr --debug /dev/null` and see if any error occurs.

## Force hyprland version

_Added in 2.3.3_

In case your `hyprctl version -j` command isn't returning an accurate version, you can make Pyprland ignore it and use a provided value instead:

```toml
[pyprland]
hyprland_version = "0.41.0"
```

> If a process isn't behaving properly, try `process_tracking = false` or `match_by = "class"`.
> Check [this page](scratchpads_nonstandard).

## Unresponsive scratchpads

Scratchpads aren't responding for few seconds after trying to show one (which didn't show!)

This may happen if an application is very slow to start.
In that case pypr will wait for a window blocking other scratchpad's operation, before giving up after a few seconds.

Note that other plugins shouldn't be blocked by it.

More scratchpads troubleshooting can be found [here](scratchpads_nonstandard).
