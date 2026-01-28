#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <libgen.h>

// Exit codes matching pyprland/models.py ExitCode
#define EXIT_SUCCESS_CODE 0
#define EXIT_USAGE_ERROR 1
#define EXIT_ENV_ERROR 2
#define EXIT_CONNECTION_ERROR 3
#define EXIT_COMMAND_ERROR 4

// Response prefixes
#define RESPONSE_OK "OK"
#define RESPONSE_ERROR "ERROR"

int main(int argc, char *argv[]) {
    // If no argument passed, show usage
    if (argc < 2) {
        fprintf(stderr, "No command provided.\n");
        fprintf(stderr, "Usage: pypr <command> [args...]\n");
        fprintf(stderr, "Try 'pypr help' for available commands.\n");
        exit(EXIT_USAGE_ERROR);
    }

    // Get environment variables for socket path detection
    const char *runtimeDir = getenv("XDG_RUNTIME_DIR");
    const char *signature = getenv("HYPRLAND_INSTANCE_SIGNATURE");
    const char *niriSocket = getenv("NIRI_SOCKET");
    const char *dataHome = getenv("XDG_DATA_HOME");
    const char *home = getenv("HOME");

    // Construct the socket path based on environment priority: Hyprland > Niri > Standalone
    char socketPath[256];
    int pathLen;

    if (signature != NULL && runtimeDir != NULL) {
        // Hyprland environment
        pathLen = snprintf(socketPath, sizeof(socketPath), "%s/hypr/%s/.pyprland.sock", runtimeDir, signature);
    } else if (niriSocket != NULL) {
        // Niri environment - use dirname of NIRI_SOCKET
        char *niriSocketCopy = strdup(niriSocket);
        if (niriSocketCopy == NULL) {
            fprintf(stderr, "Error: Memory allocation failed.\n");
            exit(EXIT_ENV_ERROR);
        }
        char *niriDir = dirname(niriSocketCopy);
        pathLen = snprintf(socketPath, sizeof(socketPath), "%s/.pyprland.sock", niriDir);
        free(niriSocketCopy);
    } else {
        // Standalone fallback - use XDG_DATA_HOME or ~/.local/share
        if (dataHome != NULL) {
            pathLen = snprintf(socketPath, sizeof(socketPath), "%s/.pyprland.sock", dataHome);
        } else if (home != NULL) {
            pathLen = snprintf(socketPath, sizeof(socketPath), "%s/.local/share/.pyprland.sock", home);
        } else {
            fprintf(stderr, "Error: Cannot determine socket path. HOME not set.\n");
            exit(EXIT_ENV_ERROR);
        }
    }

    if (pathLen >= (int)sizeof(socketPath)) {
        fprintf(stderr, "Error: Socket path too long (max %zu characters).\n", sizeof(socketPath) - 1);
        exit(EXIT_ENV_ERROR);
    }

    // Connect to the Unix socket
    int sockfd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sockfd < 0) {
        fprintf(stderr, "Error: Failed to create socket.\n");
        exit(EXIT_CONNECTION_ERROR);
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, socketPath, sizeof(addr.sun_path) - 1);

    if (connect(sockfd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        fprintf(stderr, "Cannot connect to pyprland daemon at %s.\n", socketPath);
        fprintf(stderr, "Is the daemon running? Start it with: pypr (no arguments)\n");
        close(sockfd);
        exit(EXIT_CONNECTION_ERROR);
    }

    // Concatenate all command-line arguments with spaces, plus newline
    char message[1024] = {0};
    int offset = 0;
    for (int i = 1; i < argc; i++) {
        int remaining = sizeof(message) - offset - 2; // Reserve space for \n and \0
        if (remaining <= 0) {
            fprintf(stderr, "Error: Command too long (max %zu characters).\n", sizeof(message) - 2);
            close(sockfd);
            exit(EXIT_USAGE_ERROR);
        }
        int written = snprintf(message + offset, remaining + 1, "%s", argv[i]);
        if (written > remaining) {
            fprintf(stderr, "Error: Command too long (max %zu characters).\n", sizeof(message) - 2);
            close(sockfd);
            exit(EXIT_USAGE_ERROR);
        }
        offset += written;
        if (i < argc - 1) {
            if (offset < (int)sizeof(message) - 2) {
                message[offset++] = ' ';
            }
        }
    }
    // Add newline for protocol
    message[offset++] = '\n';
    message[offset] = '\0';

    // Send the message to the socket
    if (write(sockfd, message, strlen(message)) < 0) {
        fprintf(stderr, "Error: Failed to send command to daemon.\n");
        close(sockfd);
        exit(EXIT_CONNECTION_ERROR);
    }

    // send EOF to indicate end of message
    if (shutdown(sockfd, SHUT_WR) < 0) {
        fprintf(stderr, "Error: Failed to complete command transmission.\n");
        close(sockfd);
        exit(EXIT_CONNECTION_ERROR);
    }

    // Read the response from the socket until EOF
    char buffer[4096];
    char response[65536] = {0};
    size_t totalRead = 0;
    ssize_t bytesRead;

    while ((bytesRead = read(sockfd, buffer, sizeof(buffer) - 1)) > 0) {
        if (totalRead + bytesRead >= sizeof(response) - 1) {
            // Response too large, just print what we have
            buffer[bytesRead] = '\0';
            printf("%s", buffer);
        } else {
            memcpy(response + totalRead, buffer, bytesRead);
            totalRead += bytesRead;
        }
    }
    response[totalRead] = '\0';

    close(sockfd);

    // Parse response and determine exit code
    int exitCode = EXIT_SUCCESS_CODE;

    if (strncmp(response, RESPONSE_ERROR ":", strlen(RESPONSE_ERROR ":")) == 0) {
        // Error response - extract message after "ERROR: "
        const char *errorMsg = response + strlen(RESPONSE_ERROR ": ");
        // Trim trailing whitespace
        size_t len = strlen(errorMsg);
        while (len > 0 && (errorMsg[len-1] == '\n' || errorMsg[len-1] == ' ')) {
            len--;
        }
        fprintf(stderr, "Error: %.*s\n", (int)len, errorMsg);
        exitCode = EXIT_COMMAND_ERROR;
    } else if (strncmp(response, RESPONSE_OK, strlen(RESPONSE_OK)) == 0) {
        // OK response - check for additional output after "OK"
        const char *remaining = response + strlen(RESPONSE_OK);
        // Skip whitespace/newlines
        while (*remaining == ' ' || *remaining == '\n') {
            remaining++;
        }
        if (*remaining != '\0') {
            printf("%s", remaining);
        }
        exitCode = EXIT_SUCCESS_CODE;
    } else if (totalRead > 0) {
        // Legacy response (version, help, dumpjson) - print as-is
        // Trim trailing newlines for cleaner output
        while (totalRead > 0 && response[totalRead-1] == '\n') {
            totalRead--;
        }
        response[totalRead] = '\0';
        if (totalRead > 0) {
            printf("%s\n", response);
        }
        exitCode = EXIT_SUCCESS_CODE;
    }

    return exitCode;
}
