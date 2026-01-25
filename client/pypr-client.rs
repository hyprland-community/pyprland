use std::env;
use std::io::{Read, Write};
use std::os::unix::net::UnixStream;
use std::process::exit;

// Exit codes matching pyprland/models.py ExitCode
const EXIT_SUCCESS: i32 = 0;
const EXIT_USAGE_ERROR: i32 = 1;
const EXIT_ENV_ERROR: i32 = 2;
const EXIT_CONNECTION_ERROR: i32 = 3;
const EXIT_COMMAND_ERROR: i32 = 4;

fn run() -> Result<(), i32> {
    // Collect arguments (skip program name)
    let args: Vec<String> = env::args().skip(1).collect();

    if args.is_empty() {
        eprintln!("No command provided.");
        eprintln!("Usage: pypr <command> [args...]");
        eprintln!("Try 'pypr help' for available commands.");
        return Err(EXIT_USAGE_ERROR);
    }

    // Build command message
    let message = format!("{}\n", args.join(" "));

    if message.len() > 1024 {
        eprintln!("Error: Command too long (max 1022 characters).");
        return Err(EXIT_USAGE_ERROR);
    }

    // Get socket path from environment
    let runtime_dir = env::var("XDG_RUNTIME_DIR").map_err(|_| {
        eprintln!("Environment error: XDG_RUNTIME_DIR or HYPRLAND_INSTANCE_SIGNATURE not set.");
        eprintln!("Are you running under Hyprland?");
        EXIT_ENV_ERROR
    })?;

    let signature = env::var("HYPRLAND_INSTANCE_SIGNATURE").map_err(|_| {
        eprintln!("Environment error: XDG_RUNTIME_DIR or HYPRLAND_INSTANCE_SIGNATURE not set.");
        eprintln!("Are you running under Hyprland?");
        EXIT_ENV_ERROR
    })?;

    let socket_path = format!("{}/hypr/{}/.pyprland.sock", runtime_dir, signature);

    if socket_path.len() >= 256 {
        eprintln!("Error: Socket path too long (max 255 characters).");
        return Err(EXIT_ENV_ERROR);
    }

    // Connect to Unix socket
    let mut stream = UnixStream::connect(&socket_path).map_err(|_| {
        eprintln!("Cannot connect to pyprland daemon at {}.", socket_path);
        eprintln!("Is the daemon running? Start it with: pypr (no arguments)");
        EXIT_CONNECTION_ERROR
    })?;

    // Send command
    stream.write_all(message.as_bytes()).map_err(|_| {
        eprintln!("Error: Failed to send command to daemon.");
        EXIT_CONNECTION_ERROR
    })?;

    // Signal end of message
    stream.shutdown(std::net::Shutdown::Write).map_err(|_| {
        eprintln!("Error: Failed to complete command transmission.");
        EXIT_CONNECTION_ERROR
    })?;

    // Read response
    let mut response = String::new();
    stream.read_to_string(&mut response).map_err(|_| {
        eprintln!("Error: Failed to read response from daemon.");
        EXIT_CONNECTION_ERROR
    })?;

    // Parse response and determine exit code
    if let Some(error_msg) = response.strip_prefix("ERROR: ") {
        eprintln!("Error: {}", error_msg.trim_end());
        Err(EXIT_COMMAND_ERROR)
    } else if let Some(rest) = response.strip_prefix("OK") {
        // Print any content after "OK" (skip leading whitespace/newlines)
        let output = rest.trim_start();
        if !output.is_empty() {
            print!("{}", output);
        }
        Ok(())
    } else if !response.is_empty() {
        // Legacy response (version, help, dumpjson) - print as-is
        println!("{}", response.trim_end_matches('\n'));
        Ok(())
    } else {
        Ok(())
    }
}

fn main() {
    exit(run().err().unwrap_or(EXIT_SUCCESS));
}
