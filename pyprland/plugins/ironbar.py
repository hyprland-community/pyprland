" Ironbar Plugin "
import os
import json
import asyncio

from .interface import Plugin

SOCKET = f"/run/user/{os.getuid()}/ironbar-ipc.sock"


async def ipcCall(**params):
    ctl_reader, ctl_writer = await asyncio.open_unix_connection(SOCKET)
    ctl_writer.write(json.dumps(params).encode("utf-8"))
    await ctl_writer.drain()
    ret = await ctl_reader.read()
    ctl_writer.close()
    await ctl_writer.wait_closed()
    return json.loads(ret)


class Extension(Plugin):
    "Toggles ironbar on/off"
    is_visible = True

    async def run_toggle_ironbar(self, bar_name: str):
        self.is_visible = not self.is_visible
        await ipcCall(type="set_visible", visible=self.is_visible, bar_name=bar_name)
