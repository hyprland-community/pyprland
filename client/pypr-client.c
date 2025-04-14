#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>

int main(int argc, char *argv[]) {
    // If no argument passed, just exit
    if (argc < 2) {
        fprintf(stderr, "No command passed! Try 'help'\n");
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

    // send EOF to indicate end of message
    if (shutdown(sockfd, SHUT_WR) < 0) {
        perror("Error shutting down writer");
        close(sockfd);
        exit(1);
    }

    // read the response from the socket until EOF
    char buffer[1024];
    ssize_t bytesRead;
    while ((bytesRead = read(sockfd, buffer, sizeof(buffer) - 1)) > 0) {
        buffer[bytesRead] = '\0'; // Null-terminate the string
        printf("%s", buffer);
    }

    close(sockfd);
    return 0;
}
