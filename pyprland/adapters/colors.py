"Color conversion & misc color related helpers"


def convert_color(description: str) -> str:
    "Get a color description and returns the 6 HEX digits as string"
    if description[0] == "#":
        return description[1:]
    if description.startswith("rgb("):
        return "".join([hex(int(i))[2:].zfill(2) for i in description[4:-1].split(", ")])
    return description
