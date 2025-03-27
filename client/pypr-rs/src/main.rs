use std::env;
use std::io::{Write};
use std::os::unix::net::UnixStream;
use std::process;

fn main() {
    // If no argument passed, just exit
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("No command passed! Try 'help'");
        process::exit(0);
    }

    // if the argument is help, print the help text
    if args[1] == "help" {
        let help_text = r#"
Syntax: pypr-client [command]

Available commands:
exit                 Exit the daemon.
help                 Show this help.
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
"#;
        println!("{}", help_text);
        process::exit(0);
    }

    // Get the socket path from environment variables
    let runtime_dir = env::var("XDG_RUNTIME_DIR").unwrap_or_else(|_| {
        eprintln!("Error: XDG_RUNTIME_DIR environment variable not set");
        process::exit(1);
    });
    let signature = env::var("HYPRLAND_INSTANCE_SIGNATURE").unwrap_or_else(|_| {
        eprintln!("Error: HYPRLAND_INSTANCE_SIGNATURE environment variable not set");
        process::exit(1);
    });

    // Construct the socket path
    let socket_path = format!("{}/hypr/{}/.pyprland.sock", runtime_dir, signature);

    // Connect to the Unix socket
    let mut conn = UnixStream::connect(&socket_path).unwrap_or_else(|err| {
        eprintln!("Error connecting to socket {}: {}", socket_path, err);
        process::exit(1);
    });

    // Concatenate all command-line arguments with spaces
    let message = args[1..].join(" ");

    // Send the message to the socket
    conn.write_all(message.as_bytes()).unwrap_or_else(|err| {
        eprintln!("Error writing to socket: {}", err);
        process::exit(1);
    });
}
