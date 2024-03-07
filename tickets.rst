Tickets
=======

:total-count: 33

--------------------------------------------------------------------------------

Make an "system_notifier" plugin
================================

:bugid: 21
:created: 2024-02-16T00:16:11
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

preserve_aspect to manage multi-screen setups
=============================================

:bugid: 30
:created: 2024-03-04T22:21:41
:priority: 0

--------------------------------------------------------------------------------

offset & margin: support % and px units
=======================================

:bugid: 33
:created: 2024-03-08T00:07:02
:priority: 0
