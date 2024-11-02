#!/bin/sh
echo -n "Current is: "
pypr version
echo -n "Available: "
ls versions

if [ -z "$1" ]; then
    echo -n "Archive current version as: "
    read version
else
    version=$1
fi
mkdir versions/$version
cp *.md versions/$version/
sed -i '/## What/,$d' versions/$version/index.md
echo "## Version $version archive" >> versions/$version/index.md
git add versions/$version/*.md

sed -i "/const version_names/s#\]\$#, '${version}']#" .vitepress/config.mjs
git add .vitepress/config.mjs

git commit . -m "Archive documentation for version $version" --no-verify

