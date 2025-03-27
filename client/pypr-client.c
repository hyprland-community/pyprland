#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>

void print_help() {
    const char *helpText =
        "Syntax: pypr-client [command]\n"
        "\n"
        "Available commands:\n"
        "exit                 Exit the daemon.\n"
        "help                 Show this help.\n"
        "reload               Load the configuration (new plugins will be added & config updated). [pyprland]\n"
        "toggle_special       [name] Toggles switching the focused window to the special workspace \"name\" (default: minimized). [toggle_special]\n"
        "attract_lost         Brings lost floating windows to the current workspace. [lost_windows]\n"
        "shift_monitors       <+1/-1> Swaps monitors' workspaces in the given direction. [shift_monitors]\n"
        "toggle_dpms          Toggle dpms on/off for every monitor. [toggle_dpms]\n"
        "zoom                 [factor] zooms to \"factor\" or toggles zoom level if factor is omitted. [magnify]\n"
        "expose               Expose every client on the active workspace. [expose]\n"
        "bar                  Start gBar on the first available monitor. [menubar]\n"
        "change_workspace     <+1/-1> Switch workspaces of current monitor, avoiding displayed workspaces. [workspaces_follow_focus]\n"
        "fetch_client_menu    Select a client window and move it to the active workspace. [fetch_client_menu]\n"
        "unfetch_client       Return a window back to its origin. [fetch_client_menu]\n"
        "layout_center        <toggle|next|prev> turn on/off or change the active window. [layout_center]\n"
        "relayout             Recompute & apply every monitors's layout. [monitors]\n"
        "attach               Attach the focused window to the last focused scratchpad. [scratchpads]\n"
        "hide                 <name> hides scratchpad \"name\". [scratchpads]\n"
        "show                 <name> shows scratchpad \"name\". [scratchpads]\n"
        "toggle               <name> toggles visibility of scratchpad \"name\". [scratchpads]\n"
        "menu                 [name] Shows the menu, if \"name\" is provided, will only show this sub-menu. [shortcuts_menu]\n"
        "wall                 <next|clear> skip the current background image or stop displaying it. [wallpapers]\n";
    printf("%s", helpText);
}

int main(int argc, char *argv[]) {
    // If no argument passed, just exit
    if (argc < 2) {
        fprintf(stderr, "No command passed! Try 'help'\n");
        exit(0);
    }

    // if the argument is help, print the help text
    if (strcmp(argv[1], "help") == 0) {
        print_help();
        exit(0);
    }

    // Get the socket path from environment variables
    const char *runtimeDir = getenv("XDG_RUNTIME_DIR");
    const char *signature = getenv("HYPRLAND_INSTANCE_SIGNATURE");
    if (runtimeDir == NULL || signature == NULL) {
        fprintf(stderr, "Error: XDG_RUNTIME_DIR or HYPRLAND_INSTANCE_SIGNATURE environment variable not set\n");
        exit(1);
    }

    // Construct the socket path
    char socketPath[256];
    snprintf(socketPath, sizeof(socketPath), "%s/hypr/%s/.pyprland.sock", runtimeDir, signature);

    // Connect to the Unix socket
    int sockfd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sockfd < 0) {
        perror("Error creating socket");
        exit(1);
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, socketPath, sizeof(addr.sun_path) - 1);

    if (connect(sockfd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("Error connecting to socket");
        close(sockfd);
        exit(1);
    }

    // Concatenate all command-line arguments with spaces
    char message[1024] = {0};
    int offset = 0;
    for (int i = 1; i < argc; i++) {
        offset += snprintf(message + offset, sizeof(message) - offset, "%s", argv[i]);
        if (i < argc - 1) {
            offset += snprintf(message + offset, sizeof(message) - offset, " ");
        }
    }

    // Send the message to the socket
    if (write(sockfd, message, strlen(message)) < 0) {
        perror("Error writing to socket");
        close(sockfd);
        exit(1);
    }

    close(sockfd);
    return 0;
}
