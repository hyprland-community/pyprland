"""Lookup & update API for Scratch objects."""

from collections import defaultdict
from typing import Any, cast

from .objects import Scratch


class ScratchDB:  # {{{
    """Single storage for every Scratch allowing a boring lookup & update API."""

    _by_addr: dict[str, Scratch] = {}
    _by_pid: dict[int, Scratch] = {}
    _by_name: dict[str, Scratch] = {}
    _states: defaultdict[str, set[Scratch]] = defaultdict(set)

    # State management {{{
    def get_by_state(self, status: str):
        """Get a set of `Scratch` being in `status`."""
        return self._states[status]

    def has_state(self, scratch: Scratch, status: str):
        """Return true if `scratch` has state `status`."""
        return scratch in self._states[status]

    def set_state(self, scratch: Scratch, status: str) -> None:
        """Set `scratch` in the provided status."""
        self._states[status].add(scratch)

    def clear_state(self, scratch: Scratch, status: str) -> None:
        """Unset the the provided status from the scratch."""
        self._states[status].remove(scratch)

    # }}}

    # dict-like {{{
    def __iter__(self):
        """Return all Scratch name."""
        return iter(self._by_name.keys())

    def values(self):
        """Return every Scratch."""
        return self._by_name.values()

    def items(self):
        """Return an iterable list of (name, Scratch)."""
        return self._by_name.items()

    # }}}

    def reset(self, scratch: Scratch) -> None:
        """Clear registered address & pid."""
        if scratch.address in self._by_addr:
            del self._by_addr[scratch.address]
        if scratch.pid in self._by_pid:
            del self._by_pid[scratch.pid]

    def clear(self, name=None, pid=None, addr=None) -> None:
        """Clear the index by name, pid or address."""
        # {{{

        assert any((name, pid, addr))
        if name is not None and name in self._by_name:
            del self._by_name[name]
        if pid is not None and pid in self._by_pid:
            del self._by_pid[pid]
        if addr is not None and addr in self._by_addr:
            del self._by_addr[addr]
        # }}}

    def register(self, scratch: Scratch, name=None, pid=None, addr=None) -> None:
        """Set the Scratch index by name, pid or address, or update every index of only `scratch` is provided."""
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
            else:
                msg = "name, pid or addr must be provided"
                raise ValueError(msg)
            d[v] = scratch
        # }}}

    def get(self, name=None, pid=None, addr=None) -> Scratch | None:
        """Return the Scratch matching given name, pid or address."""
        # {{{
        assert len(list(filter(bool, (name, pid, addr)))) == 1, (
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
        else:
            msg = "name, pid or addr must be provided"
            raise ValueError(msg)
        return d.get(v)
        # }}}


# }}}
