- `scratchpads`
  - fix ghost state after window close causing potential ~500ms delays (#222)
  - fix `excludes = ["*"]` wildcard handling (#223)
  - fix warning using templates (#226)
- `gamemode` add hysteresis (debounce) to game mode switching, with configurable `hysteresis` delay
- defer heavy imports in client path to reduce startup latency (~120ms) (#222)
- add optional native C client build via hatchling build hook (requires having a C compiler installed) (#222)

Thank you all for using and contributing to this project, special shout-out to @koalagang for the quick interactions.
