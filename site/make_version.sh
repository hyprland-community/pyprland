#!/bin/sh
if [ -z "$1" ]; then
    read version
else
    version=$1
fi
mkdir versions/$version
cp *.md versions/$version/
git add versions/$version/*.md
