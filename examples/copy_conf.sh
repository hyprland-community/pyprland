#!/bin/sh
if [ -z "$1" ]; then
    echo -n "config name: "
    read name
else
    name=$1
fi
[ -d $name/hypr/ ] || mkdir $name/hypr/
FILENAMES=("hyprland.conf" "pyprland.toml")
for fname in ${FILENAMES[@]}; do
    install -T ~/.config/hypr/$fname $name/hypr/$fname
done

for fname in "config" "style.scss" ; do
    install -T ~/.config/gBar/$fname $name/hypr/gBar/$fname
done
