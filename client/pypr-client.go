package main

import (
	"fmt"
	"net"
	"os"
	"strings"
)


func main() {
	// If no argument passed, just exit
	if len(os.Args) < 2 {
		fmt.Fprintf(os.Stderr, "No command passed!\n")
		os.Exit(0);
	}
	// if the argument is help, print the help text
	if os.Args[1] == "help" {

		helpText := `
Syntax: pypr-client [command]

Available commands:
dumpjson             Dump the configuration in JSON format.
edit                 Edit the configuration file.
exit                 Exit the daemon.
help                 Show this help.
version              Show the version.
reload               Load the configuration (new plugins will be added & config updated). [pyprland]
toggle_special       [name] Toggles switching the focused window to the special workspace "name" (default: minimized). [toggle_special]
attract_lost         Brings lost floating windows to the current workspace. [lost_windows]
shift_monitors       <+1/-1> Swaps monitors' workspaces in the given direction. [shift_monitors]
toggle_dpms          Toggle dpms on/off for every monitor. [toggle_dpms]
zoom                 [factor] zooms to "factor" or toggles zoom level if factor is omitted. [magnify]
expose               Expose every client on the active workspace. [expose]
bar                  Start gBar on the first available monitor. [menubar]
change_workspace     <+1/-1> Switch workspaces of current monitor, avoiding displayed workspaces. [workspaces_follow_focus]
fetch_client_menu    Select a client window and move it to the active workspace. [fetch_client_menu]
unfetch_client       Return a window back to its origin. [fetch_client_menu]
layout_center        <toggle|next|prev> turn on/off or change the active window. [layout_center]
relayout             Recompute & apply every monitors's layout. [monitors]
attach               Attach the focused window to the last focused scratchpad. [scratchpads]
hide                 <name> hides scratchpad "name". [scratchpads]
show                 <name> shows scratchpad "name". [scratchpads]
toggle               <name> toggles visibility of scratchpad "name". [scratchpads]
menu                 [name] Shows the menu, if "name" is provided, will only show this sub-menu. [shortcuts_menu]
wall                 <next|clear> skip the current background image or stop displaying it. [wallpapers]
		`
		fmt.Print(helpText)
		os.Exit(0)
	}

	// Get the socket path from environment variables
	runtimeDir := os.Getenv("XDG_RUNTIME_DIR")
	signature := os.Getenv("HYPRLAND_INSTANCE_SIGNATURE")
	if runtimeDir == "" || signature == "" {
		fmt.Fprintf(os.Stderr, "Error: XDG_RUNTIME_DIR or HYPRLAND_INSTANCE_SIGNATURE environment variable not set\n")
		os.Exit(1)
	}

	// Construct the socket path
	socketPath := fmt.Sprintf("%s/hypr/%s/.pyprland.sock", runtimeDir, signature)

	// Connect to the Unix socket
	conn, err := net.Dial("unix", socketPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error connecting to socket %s: %v\n", socketPath, err)
		os.Exit(1)
	}
	defer conn.Close()

	// Concatenate all command-line arguments with spaces
	message := strings.Join(os.Args[1:], " ")

	// Send the message to the socket
	_, err = conn.Write([]byte(message))
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error writing to socket: %v\n", err)
		os.Exit(1)
	}
}
