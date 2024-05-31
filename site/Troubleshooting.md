# General

In case of trouble running a `pypr` command:
- kill the existing pypr if any
- run from the terminal adding `--debug /dev/null` to the arguments to get more information

If the client says it can't connect, then there is a high chance pypr daemon didn't start, check if it's running using `ps axuw |grep pypr`. You can try to run it from a terminal with the same technique: `pypr --debug /dev/null` and see if any error occurs.

In case you figure iXXXt's broken only when running from `hyprland.conf` using `exec-once`:

> If a process isn't behaving properly, try `process_tracking = false` or `match_by = "class"`.
> Check [this page](scratchpads_nonstandard).

## Disable PID tracking (eg: `emacsclient`)
Some apps may open the graphical client window in a "complicated" way, to work around this, it is possible to disable the process PID matching algorithm and simply rely on window's class.
The `match_by` attribute can be used to achieve this, eg. for emacsclient:
```toml
[scratchpads.emacs]
command = "/usr/local/bin/emacsStart.sh"
class = "Emacs"
match_by = "class"
```
## Disable process management

Progressive web apps will share a single process for every window.
On top of requiring the class based window tracking (using `match_by`), the process can not be managed the same way as usual apps and the correlation between the process and the client window isn't as straightforward and can lead to false matches in extreme cases.

However, this is possible to run those apps in a scratchpad by setting `process_tracking = false`.

Check [the `process_tracking` option](https://github.com/hyprland-community/pyprland/wiki/scratchpads_nonstandard#process_tracking-optional)

## Scratchpads aren't responding for few seconds after trying to show one (which didn't show!)

This may happen if an application is very slow to start.
In that case pypr will wait for a window blocking other scratchpad's operation, before giving up after a few seconds.

Note that other plugins shouldn't be blocked by it.

## Force hyprland version detection

_Added in 2.3.3_

In case your `hyprctl version -j` command isn't returning an accurate version, you can make Pyprland ignore it and use a provided value instead:

```toml
[pyprland]
hyprland_version = "0.41.0"
```
