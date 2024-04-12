" Lookup & update API for Scratch objects "
from typing import Any, cast
from collections import defaultdict

from .objects import Scratch


class ScratchDB:  # {{{
    """Single storage for every Scratch allowing a boring lookup & update API"""

    _by_addr: dict[str, Scratch] = {}
    _by_pid: dict[int, Scratch] = {}
    _by_name: dict[str, Scratch] = {}
    _states: defaultdict[str, set[Scratch]] = defaultdict(set)

    # State management {{{
    def getByState(self, status: str):
        "get a set of `Scratch` being in `status`"
        return self._states[status]

    def hasState(self, scratch: Scratch, status: str):
        "Returns true if `scratch` has state `status`"
        return scratch in self._states[status]

    def setState(self, scratch: Scratch, status: str):
        "Sets `scratch` in the provided status"
        self._states[status].add(scratch)

    def clearState(self, scratch: Scratch, status: str):
        "Unsets the the provided status from the scratch"
        self._states[status].remove(scratch)

    # }}}

    # dict-like {{{
    def __iter__(self):
        "return all Scratch name"
        return iter(self._by_name.keys())

    def values(self):
        "returns every Scratch"
        return self._by_name.values()

    def items(self):
        "return an iterable list of (name, Scratch)"
        return self._by_name.items()

    # }}}

    def reset(self, scratch: Scratch):
        "clears registered address & pid"
        if scratch.address in self._by_addr:
            del self._by_addr[scratch.address]
        if scratch.pid in self._by_pid:
            del self._by_pid[scratch.pid]

    def clear(self, name=None, pid=None, addr=None):
        "clears the index by name, pid or address"
        # {{{

        assert any((name, pid, addr))
        if name is not None and name in self._by_name:
            del self._by_name[name]
        if pid is not None and pid in self._by_pid:
            del self._by_pid[pid]
        if addr is not None and addr in self._by_addr:
            del self._by_addr[addr]
        # }}}

    def register(self, scratch: Scratch, name=None, pid=None, addr=None):
        "set the Scratch index by name, pid or address, or update every index of only `scratch` is provided"
        # {{{
        if not any((name, pid, addr)):
            self._by_name[scratch.uid] = scratch
            self._by_pid[scratch.pid] = scratch
            self._by_addr[scratch.address] = scratch
        else:
            if name is not None:
                d: dict[Any, Scratch] = cast(dict[str, Scratch], self._by_name)
                v = name
            elif pid is not None:
                d = self._by_pid
                v = pid
            elif addr is not None:
                d = self._by_addr
                v = addr
            d[v] = scratch
        # }}}

    def get(self, name=None, pid=None, addr=None) -> Scratch | None:
        "return the Scratch matching given name, pid or address"
        # {{{
        assert 1 == len(list(filter(bool, (name, pid, addr)))), (
            name,
            pid,
            addr,
        )
        if name is not None:
            d: dict[Any, Scratch] = self._by_name
            v = name
        elif pid is not None:
            d = self._by_pid
            v = pid
        elif addr is not None:
            d = self._by_addr
            v = addr
        return d.get(v)
        # }}}


# }}}
