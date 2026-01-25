"""Terminal handling utilities for interactive programs."""

import fcntl
import os
import pty
import select
import struct
import subprocess
import sys
import termios

__all__ = [
    "run_interactive_program",
    "set_raw_mode",
    "set_terminal_size",
]


def set_terminal_size(descriptor: int, rows: int, cols: int) -> None:
    """Set the terminal size.

    Args:
        descriptor: File descriptor of the terminal
        rows: Number of rows
        cols: Number of columns
    """
    fcntl.ioctl(descriptor, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def set_raw_mode(descriptor: int) -> None:
    """Set a file descriptor in raw mode.

    Args:
        descriptor: File descriptor to set to raw mode
    """
    # Get the current terminal attributes
    attrs = termios.tcgetattr(descriptor)
    # Set the terminal to raw mode
    attrs[3] &= ~termios.ICANON  # Disable canonical mode (line buffering)
    attrs[3] &= ~termios.ECHO  # Disable echoing of input characters
    termios.tcsetattr(descriptor, termios.TCSANOW, attrs)


def run_interactive_program(command: str) -> None:
    """Run an interactive program in a blocking way.

    Args:
        command: The command to run
    """
    # Create a pseudo-terminal
    master, slave = pty.openpty()

    # Start the program in the pseudo-terminal
    process = subprocess.Popen(  # pylint: disable=consider-using-with
        command, shell=True, stdin=slave, stdout=slave, stderr=slave
    )

    # Close the slave end in the parent process
    os.close(slave)

    # Get the size of the real terminal
    rows, cols = os.popen("stty size", "r").read().split()

    # Set the terminal size for the pseudo-terminal
    set_terminal_size(master, int(rows), int(cols))

    # Set the terminal to raw mode
    set_raw_mode(sys.stdin.fileno())
    set_raw_mode(master)

    # Forward input from the real terminal to the program and vice versa
    try:
        while process.poll() is None:
            r, _, _ = select.select([sys.stdin, master], [], [])
            for fd in r:
                if fd == sys.stdin:
                    # Read input from the real terminal
                    user_input = os.read(sys.stdin.fileno(), 1024)
                    # Forward input to the program
                    os.write(master, user_input)
                elif fd == master:
                    # Read output from the program
                    output = os.read(master, 1024)
                    # Forward output to the real terminal
                    os.write(sys.stdout.fileno(), output)
    except OSError:
        pass
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSANOW, termios.tcgetattr(0))
