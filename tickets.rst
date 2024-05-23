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

improve groups support
======================

:bugid: 37
:created: 2024-04-15T00:27:52
:priority: 0

Instead of making it in "layout_center" by lack of choice, refactor:

- make run_command return a code compatible with shell (0 = success, < 0 = error)
- by default it returns 0

else: Add it to "layout_center" overriding prev & next

if grouped, toggle over groups, when at the limit, really changes the focus

Option: think about a "chaining" in handlers, (eg: "pypr groups prev OR layout_center prev") in case of a separate plugin called "groups"

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

--------------------------------------------------------------------------------

Test a configuration with zero initial command/window
=====================================================

:bugid: 46
:created: 2024-05-01T23:37:31
:priority: 0
