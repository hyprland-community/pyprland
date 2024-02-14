#!/bin/sh
echo -n "config name: "
read name
[ -d $name/hypr/ ] || mkdir $name/hypr/
FILENAMES=("hyprland.conf" "pyprland.toml")
for fname in ${FILENAMES[@]}; do
    install -T ~/.config/hypr/$fname $name/hypr/$fname
done
