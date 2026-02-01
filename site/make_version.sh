#!/bin/bash
# Archive documentation for a specific version.
#
# Creates a full copy of the site's source files including:
# - Markdown content
# - Sidebar configuration (sidebar.json)
# - Vue components
# - Generated JSON data
#
# The archived version will automatically appear in the version picker
# since config.mjs dynamically discovers versions.

set -e

cd "$(dirname "$0")"

echo -n "Current is: "
pypr version
echo -n "Available: "
ls versions

version="${1:-}"
[ -z "$version" ] && { echo -n "Archive current version as: "; read version; }

dest="versions/$version"
echo "Archiving version $version to $dest..."

# Create destination
mkdir -p "$dest"

# Copy markdown files
cp *.md "$dest/"

# Copy sidebar config
cp sidebar.json "$dest/"

# Copy components (for historical reference)
cp -r components "$dest/"

# Copy generated JSON if present
if ls generated/*.json >/dev/null 2>&1; then
    mkdir -p "$dest/generated"
    cp generated/*.json "$dest/generated/"
fi

# Inject version prop into Vue component tags
# This ensures components load data from the correct version's JSON files
echo "Injecting version props into Vue components..."
for file in "$dest"/*.md; do
    # Handle tags with existing attributes
    sed -i -E 's/<(PluginCommands|PluginConfig|PluginList|ConfigBadges)([^>]*[^/])\s*\/>/<\1\2 version="'"$version"'" \/>/g' "$file"
    # Handle tags without attributes
    sed -i -E 's/<(PluginCommands|PluginConfig|PluginList|ConfigBadges)\s*\/>/<\1 version="'"$version"'" \/>/g' "$file"
done

# Truncate index.md to remove dynamic content
sed -i '/## What/,$d' "$dest/index.md"
echo "## Version $version archive" >> "$dest/index.md"

# Stage files
git add "$dest/"

# Commit
git commit -m "Archive documentation for version $version" --no-verify

echo ""
echo "Done! Version $version archived."
echo "The version will automatically appear in the version picker."
