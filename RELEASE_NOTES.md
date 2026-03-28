- **New**: add a `pypr-gui` command with a browser-based GUI to edit the settings, considered it an early release, it will get more polish if there is some demand
- `scratchpads`
  - fix ghost state after window close causing potential ~500ms delays (#222)
  - fix `excludes = ["*"]` wildcard handling (#223)
  - improve template detection (#226)
- `gamemode` add hysteresis to game mode switching, with configurable `hysteresis` delay
- **core**:
    - performance regression fix: defer heavy imports in client path to reduce startup latency (~120ms) (#222)
    - add the optional native C client to hatchling build hook (requires having a C compiler installed) (#222)

A huge thank you to everyone who contributed — special shout-out to @koalagang!
I truly appreciate the community around Pyprland and all the contributions it receives.
This project never would have become such a great tool without your feedback and energy.
