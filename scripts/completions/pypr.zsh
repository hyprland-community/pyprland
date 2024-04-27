#compdef pypr

local commands

commands=('dumpjson: Dumps the configuration in JSON format'
    'edit: Edit the configuration file'
    'help: Show this help message'
    'version: Show the version of pypr'
    'reload: Reloads the configuration (new plugins will be added & config updated)'
    'gbar: Starts gBar on the first available monitor'
    'menu: Shows the menu, if "name" is provided, will only show this sub-menu'
    'toggle_special: Toggles switching the focused window to the special workspace "name" (default: minimized)'
    'attach: Attach the focused window to the last focused scratchpad'
    'hide: Hides scratchpad "name"'
    'show: Shows scratchpad "name"'
    'toggle: Toggles visibility of scratchpad "name"'
    'layout_center: Turn on/off or change the active window'
    'attract_lost: Brings lost floating windows to the current workspace'
    "relayout: Recompute & apply every monitors's layout"
    "shift_monitors: Swaps monitors' workspaces in the given direction"
    'toggle_dpms: Toggles dpms on/off for every monitor'
    'zoom: Zooms to "factor" or toggles zoom level if factor is ommited'
    'expose: Expose every client on the active workspace.'
    'change_workspace: Switch workspaces of current monitor, avoiding displayed workspaces'
    'wall: Skip the current background image or stop displaying it'
    'fetch_client_menu: Select a client window and move it to the active workspace'
    'unfetch_client: Returns a window back to its origin')


_arguments '--debug[log file]:filename:_files'


case "$words[2]" in
    layout_center)
        _arguments '1::' ':action arg:(next prev clear)'
        ;;
    zoom)
        _arguments '1::' ':factor arg:(+1 -1 ++1 --1 ++0.5 --0.5)'
        ;;
    shift_monitors|change_workspace)
        _arguments '1::' ':direction arg:(+1 -1)'
        ;;
    wall)
        _arguments '1::' ':action arg:(clear next)'
        ;;
    gbar)
        _arguments '1::' ':action arg:(restart)'
        ;;
    --debug|wall|toggle_special|toggle_dpms|expose|fetch_client_menu|unfetch_client|relayout|toggle|show|hide|attach|toggle_special|menu|reload|version|help|edit|dumpjson)
        ;;
    *)
        _describe 'command' commands
        ;;
esac
