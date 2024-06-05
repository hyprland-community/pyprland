#!/bin/sh
set -e
url=$(curl https://pypi.org/pypi/pyprland/json | jq '.urls[] |.url' |grep 'whl"$')

sed -i "s#^URL=.*#URL=${url}#" get-pypr
