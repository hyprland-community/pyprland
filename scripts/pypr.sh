#!/bin/sh
socat - "UNIX-CONNECT:${XDG_RUNTIME_DIR}/hypr/${HYPRLAND_INSTANCE_SIGNATURE}/.pyprland.sock" <<< $@
