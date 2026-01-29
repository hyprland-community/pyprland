#!/bin/sh
# Archive documentation for a specific version.
#
# This script:
# 1. Copies current markdown files to versions/<version>/
# 2. Copies generated JSON files for static rendering
# 3. Renders Vue components to static markdown tables
# 4. Removes JSON files (no longer needed after rendering)
# 5. Updates the version selector in VitePress config
# 6. Commits all changes

set -e

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

echo "Archiving version $version..."

# Create version directory and copy markdown files
mkdir -p versions/$version
cp *.md versions/$version/

# Copy generated JSON files for static rendering
mkdir -p versions/$version/generated
cp generated/*.json versions/$version/generated/

# Render Vue components to static markdown
echo "Rendering Vue components to static markdown..."
python3 ../scripts/render_static_docs.py versions/$version

# Remove JSON files (no longer needed after static rendering)
rm -rf versions/$version/generated

# Truncate index.md to remove dynamic content
sed -i '/## What/,$d' versions/$version/index.md
echo "## Version $version archive" >> versions/$version/index.md

# Stage markdown files
git add versions/$version/*.md

# Append version to the version selector in VitePress config
sed -i "/const version_names/s#\[\$#[\n  '${version}',#" .vitepress/config.mjs
git add .vitepress/config.mjs

# Commit changes
git commit . -m "Archive documentation for version $version" --no-verify

echo "Done! Version $version archived."
