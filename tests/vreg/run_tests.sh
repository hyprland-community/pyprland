#!/bin/sh
cd tests/vreg
export WAYLAND_DISPLAY=wayland-1
export DISPLAY=:0
for n in *.py; do
    python $n
done
