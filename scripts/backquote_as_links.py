#!/bin/env python
import os
import re


def replace_links(match):
    """Substitution handler for regex, replaces backquote items with links when relevant."""
    text = match.group(1)
    if os.path.exists(f"wiki/{text}.md"):
        return f"[{text}](https://github.com/hyprland-community/pyprland/wiki/{text})"
    return f"`{text}`"


def main(filename):
    """Replace `link` with a markdown link if the .md file exists."""
    with open(filename, encoding="utf-8") as file:
        content = file.read()

    replaced_content = re.sub(r"`([^`]+)`", replace_links, content)

    with open(filename, "w", encoding="utf-8") as file:
        file.write(replaced_content)


if __name__ == "__main__":
    main("RELEASE_NOTES.md")
