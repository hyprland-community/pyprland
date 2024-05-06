Tickets
=======

:total-count: 48

--------------------------------------------------------------------------------

"theme" command
===============

:bugid: 28
:created: 2024-03-03T01:54:45
:priority: 0

- save
- list
- use
- forget
- fetch

Can parse hyprland config in such way:

.. code:: python

    import re

    def parse_config(file_path, sections_of_interest):
        config = {}
        current_section = []
        current_key = config

        with open(file_path, 'r') as file:
            for line in file:
                # Remove comments
                line = re.sub(r'#.*', '', line)
                # Match section headers
                section_match = re.match(r'\s*([a-zA-Z_]+)\s*{', line)
                if section_match:
                    section_name = section_match.group(1)
                    if section_name in sections_of_interest:
                        if len(current_section) > 0:
                            # Append the current section name to the hierarchy
                            current_key[section_name] = {}
                            # Update the current section to the new nested section
                            current_key = current_key[section_name]
                        else:
                            # Top-level section
                            config[section_name] = {}
                            current_key = config[section_name]
                        current_section.append(section_name)
                # Match key-value pairs
                key_value_match = re.match(r'\s*([a-zA-Z_]+)\s*=\s*(.+)', line)
                if key_value_match and len(current_section) > 0:
                    key, value = key_value_match.groups()
                    current_key[key.strip()] = value.strip()
                # Match closing braces for sections
                if '}' in line:
                    current_section.pop()
                    if len(current_section) > 0:
                        current_key = config
                        for section in current_section:
                            current_key = current_key[section]

        return config

    file_path = "your_file.txt"
    sections_of_interest = ["general", "decoration", "animations"]
    parsed_config = parse_config(file_path, sections_of_interest)
    print(parsed_config)

--------------------------------------------------------------------------------

offset & margin: support % and px units
=======================================

:bugid: 33
:created: 2024-03-08T00:07:02
:priority: 0

--------------------------------------------------------------------------------

Add "satellite" scratchpads
===========================

:bugid: 36
:created: 2024-04-08T23:42:26
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

improve groups support
======================

:bugid: 37
:created: 2024-04-15T00:27:52
:priority: 0

Instead of making it in "layout_center" by lack of choice, refactor:

- make run_command return a code compatible with shell (0 = success, < 0 = error)
- by default it returns 0

else: Add it to "layout_center" overriding prev & next

if groupped, toggle over groups, when at the limit, really changes the focus

Option: think about a "chaining" in handlers, (eg: "pypr groups prev OR layout_center prev") in case of a separate plugin called "groups"

--------------------------------------------------------------------------------

review CanceledError handling
=============================

:bugid: 38
:created: 2024-04-17T23:24:13
:priority: 0
:started: 2024-05-01T23:40:59

--------------------------------------------------------------------------------

preserve_aspect could recall aspect per screen resolution/size
==============================================================

:bugid: 39
:created: 2024-04-17T23:55:01
:priority: 0

--------------------------------------------------------------------------------

CHECK / fix multi-monitor & attach command
==========================================

:bugid: 40
:created: 2024-04-23T22:01:39
:priority: 0

--------------------------------------------------------------------------------

Check behavior of monitors when no match is found
=================================================

:bugid: 42
:created: 2024-04-26T00:26:22
:priority: 0

Should ignore applying any rule

--------------------------------------------------------------------------------

Review smart_focus when toggling on a special workspace
=======================================================

:bugid: 43
:created: 2024-04-27T18:25:47
:priority: 0
:started: 2024-05-01T23:39:30

--------------------------------------------------------------------------------

Test a configuration with zero initial command/window
=====================================================

:bugid: 46
:created: 2024-05-01T23:37:31
:priority: 0

--------------------------------------------------------------------------------

scratchpads: experiment handling manual scratchpad workspace change
===================================================================

:bugid: 47
:created: 2024-05-01T23:38:51
:priority: 0

--------------------------------------------------------------------------------

monitors: allow "screen descr".transform = 3
============================================

:bugid: 48
:created: 2024-05-07T00:50:34
:priority: 0

also allow `.scale = <something>` 
