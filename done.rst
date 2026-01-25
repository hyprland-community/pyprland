scratchpads: attach / detach only attaches !
============================================

:bugid: 56
:created: 2026-1-11T22:10:17
:fixed: 2026-01-19T22:03:48
:priority: 0

--------------------------------------------------------------------------------

Hyprpaper integration
=====================

:bugid: 56
:created: 2025-12-16T21:08:03
:fixed: 2025-12-16T21:44:08
:priority: 0

Use the socket $XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.hyprpaper.sock directly if no command is provided in "wallpapers"

--------------------------------------------------------------------------------

Wiki: remove optional and add mandatory (to the titles for the configuration options)
=====================================================================================

:bugid: 52
:created: 2024-07-08T21:51:28
:fixed: 2025-08-07T21:27:38
:priority: 0

--------------------------------------------------------------------------------

improve groups support
======================

:bugid: 37
:created: 2024-04-15T00:27:52
:fixed: 2024-07-08T21:54:09
:priority: 0

Instead of making it in "layout_center" by lack of choice, refactor:

- make run_command return a code compatible with shell (0 = success, < 0 = error)
- by default it returns 0

else: Add it to "layout_center" overriding prev & next

if grouped, toggle over groups, when at the limit, really changes the focus

Option: think about a "chaining" in handlers, (eg: "pypr groups prev OR layout_center prev") in case of a separate plugin called "groups"

--------------------------------------------------------------------------------

Add a fallback to aiofiles (removes one dependency)
===================================================

:bugid: 49
:created: 2024-06-02T01:41:33
:fixed: 2024-07-08T21:51:40
:priority: 0

--------------------------------------------------------------------------------

monitors: allow "screen descr".transform = 3
============================================

:bugid: 48
:created: 2024-05-07T00:50:34
:fixed: 2024-05-23T20:56:53
:priority: 0

also allow `.scale = <something>`

--------------------------------------------------------------------------------

review CanceledError handling
=============================

:bugid: 38
:created: 2024-04-17T23:24:13
:fixed: 2024-05-16T20:38:37
:priority: 0
:timer: 20

--------------------------------------------------------------------------------

Add "satellite" scratchpads
===========================

:bugid: 36
:created: 2024-04-08T23:42:26
:fixed: 2024-05-16T20:38:18
:priority: 0

- add a "scratch" command that sets the focused window into the currently focused scratchpad window

Eg: open a terminal, hover it + "scratch" it while a scratchpad is open.
Behind the hood, it creates attached "ghost scratchpads" for each attached window. They use "perserve_aspect" by default.

**Alternative**

Move focused client into the named scratchpad's special workspace.
Rework pyprland's scratchpad to keep track of every window added to the special workspace and attach it to the last used scratch then hide it if the scratchpad is hidden.
If called on a scratchpad window, will "de-attach" this window.

Every attached window should be synchronized with the main one.


**Option**

Prepare / Simplify this dev by adding support for "ScratchGroups" (contains multiple Scratches which are synchronized).
Would generalize the current feature: passing multiple scratches to the toggle command.

--------------------------------------------------------------------------------

offset & margin: support % and px units
=======================================

:bugid: 33
:created: 2024-03-08T00:07:02
:fixed: 2024-05-16T20:38:09
:priority: 0

--------------------------------------------------------------------------------

scratchpads: experiment handling manual scratchpad workspace change
===================================================================

:bugid: 47
:created: 2024-05-01T23:38:51
:fixed: 2024-05-16T20:37:54
:priority: 0

--------------------------------------------------------------------------------

Check behavior of monitors when no match is found
=================================================

:bugid: 42
:created: 2024-04-26T00:26:22
:fixed: 2024-05-16T20:37:32
:priority: 0

Should ignore applying any rule

--------------------------------------------------------------------------------

CHECK / fix multi-monitor & attach command
==========================================

:bugid: 40
:created: 2024-04-23T22:01:39
:fixed: 2024-05-16T20:36:40
:priority: 0

--------------------------------------------------------------------------------

Review smart_focus when toggling on a special workspace
=======================================================

:bugid: 43
:created: 2024-04-27T18:25:47
:fixed: 2024-05-16T20:36:26
:priority: 0
:timer: 20

--------------------------------------------------------------------------------

Re-introduce focus tracking with a twist
========================================

:bugid: 41
:created: 2024-04-25T23:54:53
:fixed: 2024-05-01T23:42:00
:priority: 0

Only enable it if the focuse changed the active workspace

--------------------------------------------------------------------------------

TESTS: ensure commands are completed (push the proper events in the queue)
==========================================================================

:bugid: 27
:created: 2024-02-29T23:30:02
:fixed: 2024-05-01T23:40:05
:priority: 0

--------------------------------------------------------------------------------

Add a command to update config
==============================

:bugid: 22
:created: 2024-02-18T17:53:17
:fixed: 2024-05-01T23:39:56
:priority: 0

cfg_set and cfg_toggle commands
eg::

  pypr cfg_toggle scratchpads.term.unfocus (toggles will toggle strings to "" and back - keeping a memory)

--------------------------------------------------------------------------------

Rework focus
============

:bugid: 45
:created: 2024-04-29T00:01:27
:fixed: 2024-05-01T23:39:44
:priority: 0


Save workspace before hide,
when hide is done, after processing some events (use a task), focus the workspace again

--------------------------------------------------------------------------------

AUR: add zsh completion file
============================

:bugid: 44
:created: 2024-04-27T23:54:28
:fixed: 2024-05-01T23:38:57
:priority: 0

--------------------------------------------------------------------------------

2.1 ?
=====

:bugid: 35
:created: 2024-03-08T00:22:35
:fixed: 2024-04-09T21:28:26
:priority: 0

- lazy = true
- positions in % and px (defaults to px if no unit is provided)
- #34 done
- #33 done
- VISUAL REGRESSION TESTS

--------------------------------------------------------------------------------

Make an "system_notifier" plugin
================================

:bugid: 21
:created: 2024-02-16T00:16:11
:fixed: 2024-04-08T19:58:46
:priority: 0

Reads journalctl -fxn and notifies some errors,
user can use some patterns to match additional errors
and create their own notifications

> Started, works but better examples are needed


.. code:: toml

    [system_notifier]
    builtin_rules = true

    [[system_notifier.source]]
    name = "kernel"
    source = "sudo journalctl -fkn"
    duration = 10
    rules = [
        {match="xxx", filter=["s/foobar//", "s/meow/plop/g"], message="bad"},
        {contains="xxx", filter=["s/foobar//", "s/meow/plop/g"], message="xxx happened [orig] [filtered]"},
    ]

    [[system_notifier.source]]
    name = "user journal"
    source = "journalctl -fxn --user"
    rules = [
        {match="Consumed \d+.?\d*s CPU time", filter="s/.*: //", message="[filtered]"},
        {match="xxx", filter=["s/foobar//", "s/meow/plop/g"], message="bad"},
        {contains="xxx", filter=["s/foobar//", "s/meow/plop/g"], message="xxx happened [orig] [filtered]"},
    ]

    [[system_notifier.source]]
    name = "user journal"
    source = "sudo journalctl -fxn"
    rules = [
        {match="systemd-networkd\[\d+\]: ([a-z0-9]+): Link (DOWN|UP)", filter="s/.*: ([a-z0-9]+): Link (DOWN|UP)/\1 \2/", message="[filtered]"}
        {match="wireplumber[1831]: Failure in Bluetooth audio transport "}
        {match="usb 7-1: Product: USB2.0 Hub", message="detected"}
        {match="févr. 02 17:30:24 gamix systemd-coredump[11872]: [🡕] Process 11801 (tracker-extract) of user 1000 dumped core."}
    ]

    [[system_notifier.source]]
    name = "Hyprland"
    source = "/tmp/pypr.log"
    duration = 10
    rules = [
        {message="[orig]"},
    ]

    [[system_notifier.source]]
    name = "networkd"

--------------------------------------------------------------------------------

preserve_aspect to manage multi-screen setups
=============================================

:bugid: 30
:created: 2024-03-04T22:21:41
:fixed: 2024-04-08T19:58:23
:priority: 0

--------------------------------------------------------------------------------

offset computation (hide anim) rework
=====================================

:bugid: 34
:created: 2024-03-08T00:11:31
:fixed: 2024-03-08T21:35:57
:priority: 0

use animation type + margin to do a reverse computation of the placement (out of screen)

--------------------------------------------------------------------------------

set preserve_aspect=true by default
===================================

:bugid: 32
:created: 2024-03-06T23:28:41
:fixed: 2024-03-06T23:29:33
:priority: 0

also add a command "scratch reset <uid>" to set active scratch position and size according to the rules.
Can support ommitting the <uid>, requires tracking of the currently active scratch (or just check focused window)

--------------------------------------------------------------------------------

preserve_aspect should adapt to screen changes
==============================================

:bugid: 29
:created: 2024-03-03T01:56:28
:fixed: 2024-03-06T23:29:32
:priority: 0

--------------------------------------------------------------------------------

BUG: preserve_aspect + offset = KO
==================================

:bugid: 31
:created: 2024-03-05T00:22:34
:fixed: 2024-03-06T23:29:21
:priority: 0
:tags: #bug

tested on "term"

--------------------------------------------------------------------------------

scratchpad: per monitor overrides
=================================

:bugid: 9
:created: 2023-12-02T21:53:48
:fixed: 2024-03-02T15:30:25
:priority: 10

--------------------------------------------------------------------------------

Check for types (schema?) in the config
=======================================

:bugid: 24
:created: 2024-02-21T00:50:34
:fixed: 2024-03-02T15:30:15
:priority: 0

notify an error in case type isn't matching

--------------------------------------------------------------------------------

Make "replace links" script
===========================

:bugid: 23
:created: 2024-02-20T00:15:31
:fixed: 2024-03-02T15:29:57
:priority: 0

Reads a file (like RELEASE NOTES) and replace `links` with something in the wiki
uses difflib to make the job

--------------------------------------------------------------------------------

Hide / Show ALL command
=======================

:bugid: 10
:created: 2023-12-26T21:48:36
:fixed: 2024-02-29T23:30:14
:priority: 10

hide all command for scratchpad

--------------------------------------------------------------------------------

Make a get_bool() util function
===============================

:bugid: 25
:created: 2024-02-21T23:34:39
:fixed: 2024-02-29T23:30:12
:priority: 10


Should detect "no", "False", etc.. (strings) as being false

makes a notification warning, that it has been automatically fixed to `False`

--------------------------------------------------------------------------------

Add "exit" command that exits cleanly (& removing the socket)
=============================================================

:bugid: 20
:created: 2024-02-15T19:29:48
:fixed: 2024-02-29T22:38:15
:priority: 0

--------------------------------------------------------------------------------

scratchpads: autofloat=True
===========================

:bugid: 26
:created: 2024-02-28T19:40:02
:fixed: 2024-02-29T22:37:52
:priority: 0


Allows to disable the automatic float toggle when the scratch is opened
