# Architecture

This section provides a comprehensive overview of Pyprland's internal architecture, designed for developers who want to understand, extend, or contribute to the project.

> [!tip]
> For a practical guide to writing plugins, see the [Development](./Development) document.

## Sections

| Section | Description |
|---------|-------------|
| [Overview](./Architecture_overview) | High-level architecture, executive summary, data flow, directory structure, design patterns |
| [Core Components](./Architecture_core) | Manager, plugins, adapters, IPC layer, socket protocol, C client, configuration, data models |

## Quick Links

### Overview

- [Executive Summary](./Architecture_overview#executive-summary) - What Pyprland is and how it works
- [High-Level Architecture](./Architecture_overview#high-level-architecture) - Visual overview of all components
- [Data Flow](./Architecture_overview#data-flow) - Event processing and command processing sequences
- [Directory Structure](./Architecture_overview#directory-structure) - Source code organization
- [Design Patterns](./Architecture_overview#design-patterns) - Patterns used throughout the codebase

### Core Components

- [Entry Points](./Architecture_core#entry-points) - Daemon vs client mode
- [Manager](./Architecture_core#manager) - The core orchestrator
- [Plugin System](./Architecture_core#plugin-system) - Base class, lifecycle, built-in plugins
- [Backend Adapter Layer](./Architecture_core#backend-adapter-layer) - Hyprland and Niri abstractions
- [IPC Layer](./Architecture_core#ipc-layer) - Window manager communication
- [Socket Protocol](./Architecture_core#pyprland-socket-protocol) - Client-daemon protocol specification
- [pypr-client](./Architecture_core#pypr-client) - Lightweight alternative for keybindings
- [Configuration System](./Architecture_core#configuration-system) - TOML config system
- [Data Models](./Architecture_core#data-models) - TypedDict definitions

## Further Reading

- [Development Guide](./Development) - How to write plugins
- [Plugin Documentation](./Plugins) - List of available plugins
- [Sample Extension](https://github.com/fdev31/pyprland/tree/main/sample_extension) - Example external plugin package
- [Hyprland IPC](https://wiki.hyprland.org/IPC/) - Hyprland's IPC documentation
