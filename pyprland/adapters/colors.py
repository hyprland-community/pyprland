"""Color conversion & misc color related helpers."""


def convert_color(description: str) -> str:
    """Get a color description and returns the 6 HEX digits as string.

    Args:
        description: Color description (e.g. "#FF0000" or "rgb(255, 0, 0)")
    """
    if description[0] == "#":
        return description[1:]
    if description.startswith("rgb("):
        return "".join([f"{int(i):02x}" for i in description[4:-1].split(", ")])
    return description
