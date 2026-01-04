#!/bin/sh
(for n in $(ls -1 pyprland/plugins/*.py | cut -d/ -f3 | grep -vE '(pyprland|experimental|__|interface|_v[0-9]+.py$)' | sed 's#[.]py$#.md#'); do ls site/$n; done >/dev/null) 2>&1 | grep site

if [ $? -eq 0 ]; then
    echo -e "\033[0;31mWIKI coverage FAILED\033[0m: Some pages are not covered "
    exit 1
else
    echo "wiki coverage ok"
fi
