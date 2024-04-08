Tickets
=======

:total-count: 35

--------------------------------------------------------------------------------

Add a command to update config
==============================

:bugid: 22
:created: 2024-02-18T17:53:17
:priority: 0

cfg_set and cfg_toggle commands
eg::

  pypr cfg_toggle scratchpads.term.unfocus (toggles will toggle strings to "" and back - keeping a memory)

--------------------------------------------------------------------------------

TESTS: ensure commands are completed (push the proper events in the queue)
==========================================================================

:bugid: 27
:created: 2024-02-29T23:30:02
:priority: 0

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

2.1 ?
=====

:bugid: 35
:created: 2024-03-08T00:22:35
:priority: 0

- lazy = true
- positions in % and px (defaults to px if no unit is provided)
- #34 done
- #33 done
- VISUAL REGRESSION TESTS
