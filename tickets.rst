Tickets
=======

:total-count: 54

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

preserve_aspect could recall aspect per screen resolution/size
==============================================================

:bugid: 39
:created: 2024-04-17T23:55:01
:priority: 0

--------------------------------------------------------------------------------

Fix multi-monitor layout changes (including attached clients)
=============================================================

:bugid: 40
:created: 2024-04-23T22:01:39
:priority: 0

Status
------

broken in corner case scenarios (eg: monitor layout change)

Identified problem
------------------

Position is relative to the last one, without any state in hyprland, as in `preserve` option.

Proposed solution
-----------------

- on hide
    Compute relative distance from the main scratchpad window
- on show
    Compute the absolute position from the saved distance and perform an absolute positioning

Blocker
-------

Hyprland doesn't notify in case of layout change. Querying monitors each time seems overkill...

--------------------------------------------------------------------------------

Test a configuration with zero initial command/window
=====================================================

:bugid: 46
:created: 2024-05-01T23:37:31
:priority: 0

--------------------------------------------------------------------------------

Generalize a "monitors" call filtering out the invalid ones (cf gBar)
=====================================================================

:bugid: 50
:created: 2024-06-04T22:53:36
:priority: 0

--------------------------------------------------------------------------------

Experiment with minisearch on the website
=========================================

:bugid: 51
:created: 2024-06-05T22:21:07
:priority: 0

--------------------------------------------------------------------------------

AI voice assistant / task manager
=================================

:bugid: 53
:created: 2024-11-30T23:17:37
:priority: 0

Allow setting tasks with different properties
urgent: bool
due date: date
description: text
priority: int

Will sort them according to priorities, making urgent or soon due tasks first (so priority applies last - have less importance than those)

Will speak when a user event is received every X minutes depending on the urgency of the task

--------------------------------------------------------------------------------

configreloaded event should trigger a reload of pyprload
========================================================

:bugid: 54
:created: 2025-08-07T21:27:25
:priority: 0
