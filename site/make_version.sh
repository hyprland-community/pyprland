#!/bin/sh
if [ -z "$1" ]; then
    read version
else
    version=$1
fi
mkdir versions/$version
cp *.md versions/$version/
sed -i '/## What/,$d' versions/$version/index.md
echo "## Version $version archive" >> versions/$version/index.md
git add versions/$version/*.md
git commit . -m "Archive documentation for version $version"
