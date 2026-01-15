"""Shift workspaces across monitors."""

from typing import cast

from .interface import Plugin


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    """Shift workspaces across monitors."""

    environments = ["hyprland"]

    monitors: list[str] = []

    async def init(self) -> None:
        """Initialize the plugin."""
        if self.state.environment == "niri":
            await self.niri_outputschanged({})
        else:
            self.monitors: list[str] = [mon["name"] for mon in cast("list[dict]", await self.hyprctl_json("monitors"))]

    async def niri_outputschanged(self, _data: dict) -> None:
        """Track monitors on Niri.

        Args:
            _data: The event data (unused)
        """
        try:
            outputs = await self.nirictl_json("outputs")
            self.monitors = list(outputs.keys())
        except Exception:
            self.log.exception("Failed to update monitors from Niri event")

    async def run_shift_monitors(self, arg: str) -> None:
        """<direction> Swaps monitors' workspaces in the given direction.

        Args:
            arg: The direction to shift
        """
        if self.state.environment == "niri":
            # Niri doesn't support swapping workspaces between monitors easily.
            # We'll implement a "move workspace to monitor" shift instead for the active workspace.
            direction_int = int(arg)
            if direction_int > 0:
                await self.nirictl(["action", "move-workspace-to-monitor-right"])
            else:
                await self.nirictl(["action", "move-workspace-to-monitor-left"])
            return

        if not self.monitors:
            return

        direction: int = int(arg)
        # Using modulo arithmetic to simplify logic
        # If direction is +1: swap 0-1, then 1-2, then 2-3...
        # If direction is -1: swap 0-(-1), ... wait, logic check

        # Original logic:
        # mon_list = self.monitors[:-1] if direction > 0 else list(reversed(self.monitors[1:]))
        # for i, mon in enumerate(mon_list):
        #    await self.hyprctl(f"swapactiveworkspaces {mon} {self.monitors[i + direction]}")

        # New logic with modulo for cyclic shift feeling or just simple swap
        # The original code swaps active workspaces.
        # If we have [A, B, C] and direction +1:
        # i=0 (A): swap A B -> B has old A, A has old B. List effectively [B, A, C] relative to content?
        # No, Hyprland command "swapactiveworkspaces MON1 MON2" swaps the workspaces ON the monitors.
        # So if Mon1 has WS1, Mon2 has WS2. swap Mon1 Mon2 -> Mon1 has WS2, Mon2 has WS1.

        # Goal: Shift workspaces "Right" (+1) means Mon2 gets Mon1's WS, Mon3 gets Mon2's WS, Mon1 gets Mon3's WS.
        # This is a cyclic shift of workspaces.
        # A simple series of swaps can achieve this.
        # [A, B, C] -> want [C, A, B] (workspaces on monitors)

        # Swap A B: [B, A, C]
        # Swap B C: [B, C, A] -> Result Mon1=B, Mon2=C, Mon3=A.
        # This matches "Shift Left" if we consider monitors ordered 1,2,3.
        # WS from 1 goes to 3? No.
        # Mon1 had A, now has B. Mon2 had B, now has C. Mon3 had C, now has A.
        # So A went to 3. B went to 1. C went to 2.
        # This is -1 shift.

        # Let's verify standard behavior.
        # We need to swap safely.

        n = len(self.monitors)
        if n < 2:
            return

        if direction > 0:
            # Shift +1: Mon1->Mon2, Mon2->Mon3, Mon3->Mon1
            # Swap M1 M2 -> [M2, M1, M3] (M1 holds M2's old, M2 holds M1's old)
            # Swap M2 M3 -> [M2, M3, M1] (M2 holds M3's old, M3 holds M1's old)
            # Result: M1 has M2's old? No wait.

            # Let's trace values (Workspaces)
            # Start: M1=W1, M2=W2, M3=W3
            # swap M1 M2: M1=W2, M2=W1, M3=W3
            # swap M2 M3: M1=W2, M2=W3, M3=W1
            # Final: M1=W2, M2=W3, M3=W1.
            # W1 went to M3. W2 went to M1. W3 went to M2.
            # This looks like direction -1 (Left shift).

            # If we want W1 -> M2, W2 -> M3, W3 -> M1 (Right shift/+1)
            # Start: M1=W1, M2=W2, M3=W3
            # swap M3 M2: M1=W1, M2=W3, M3=W2
            # swap M2 M1: M1=W3, M2=W1, M3=W2
            # Final: M1=W3 (from M3), M2=W1 (from M1), M3=W2 (from M2).
            # Correct!

            # So for +1: Iterate backwards: swap(i, i-1)
            # For -1: Iterate forwards: swap(i, i+1)

            for i in range(n - 1, 0, -1):
                await self.hyprctl(f"swapactiveworkspaces {self.monitors[i]} {self.monitors[i - 1]}")
        else:
            for i in range(n - 1):
                await self.hyprctl(f"swapactiveworkspaces {self.monitors[i]} {self.monitors[i + 1]}")

    async def event_monitoradded(self, monitor: str) -> None:
        """Keep track of monitors.

        Args:
            monitor: The monitor name
        """
        self.monitors.append(monitor)

    async def event_monitorremoved(self, monitor: str) -> None:
        """Keep track of monitors.

        Args:
            monitor: The monitor name
        """
        try:
            self.monitors.remove(monitor)
        except ValueError:
            self.log.warning("Monitor %s not found in state - can't be removed", monitor)
