---
---

# fetch_client_menu

Bring any window to the active workspace using a menu.

A bit like the [expose](./expose) plugin but using a menu instead (less intrusive).

It brings the window to the current workspace, while [expose](./expose) moves the currently focused screen to the application workspace.

## Commands

| Command | Description |
|---------|-------------|
| `fetch_client_menu` | Select a client window and move it to the active workspace. |
| `unfetch_client` | Return a window back to its origin. |


## Configuration

All the [Menu](./Menu) configuration items are also available.

| Option | Description |
|--------|-------------|
| `engine` · *str* | Menu engine to use (options: `fuzzel` \| `tofi` \| `rofi` \| `wofi` \| `bemenu` \| `dmenu` \| `anyrun` \| `walker`) |
| `parameters` · *str* | Extra parameters for the menu engine command |
| `separator` · *str* · =`"|"` | Separator between window number and title |
| `center_on_fetch` · *bool* · =`true` | Center the fetched window on the focused monitor |
| `margin` · *int* · =`60` | Margin from monitor edges in pixels when centering/resizing |
