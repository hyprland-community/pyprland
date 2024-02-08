" Menu engine adapter "
import subprocess
import asyncio

from ..common import PyprError


class MenuEngine:
    "Menu backend interface"
    proc_name: str
    proc_extra_parameters: str = ""
    proc_detect_parameters: list[str] = ["--help"]

    def __init__(self, extra_parameters):
        if extra_parameters:
            self.proc_extra_parameters = extra_parameters

    @classmethod
    def is_available(cls):
        "Check engine availability"
        try:
            subprocess.call([cls.proc_name] + cls.proc_detect_parameters)
        except FileNotFoundError:
            return False
        return True

    async def run(self, choices):
        "Run the engine and get the response for the proposed `choices`"
        proc = await asyncio.create_subprocess_shell(
            f"{self.proc_name} {self.proc_extra_parameters}",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )
        assert proc.stdin
        assert proc.stdout

        menu_text = "\n".join(choices)

        proc.stdin.write(menu_text.encode())
        # flush program execution
        await proc.stdin.drain()
        proc.stdin.close()
        await proc.wait()

        return (await proc.stdout.read()).decode().strip()


class TofiMenu(MenuEngine):
    "A tofi based menu"
    proc_name = "tofi"


class RofiMenu(MenuEngine):
    "A rofi based menu"
    proc_name = "rofi"
    proc_extra_parameters = "-dmenu -matching fuzzy -i"


class WofiMenu(MenuEngine):
    "A wofi based menu"
    proc_name = "wofi"
    proc_extra_parameters = "-dmenu -i"


class DmenuMenu(MenuEngine):
    "A dmenu based menu"
    proc_name = "dmenu"
    proc_extra_parameters = "-i"


class BemenuMenu(MenuEngine):
    "A bemenu based menu"
    proc_name = "bemenu"
    proc_extra_parameters = "-c"


every_menu_engine = [TofiMenu, RofiMenu, WofiMenu, BemenuMenu, DmenuMenu]


async def init(force_engine=False, extra_parameters="") -> MenuEngine:
    "initializes the module"
    engines = (
        [next(e for e in every_menu_engine if e.proc_name == force_engine)]
        if force_engine
        else every_menu_engine
    )
    for engine in engines:
        if engine.is_available():
            return engine(extra_parameters)

    if force_engine:
        # Attempt to use the user-supplied command
        me = MenuEngine(extra_parameters)
        me.proc_name = force_engine
        return me

    raise PyprError("No engine found")
