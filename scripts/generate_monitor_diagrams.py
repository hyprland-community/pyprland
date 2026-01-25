#!/usr/bin/env python3
"""Generate SVG diagrams for monitor placement documentation."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Monitor:
    """Monitor configuration."""

    label: str
    width: int = 1920
    height: int = 1080
    transform: int = 0  # 0=normal, 1=90°, 2=180°, 3=270°
    scale: float = 1.0
    color_class: str = "monitor-a"

    def effective_size(self, base_unit: float = 0.1) -> tuple[float, float]:
        """Calculate effective diagram size.

        Args:
            base_unit: Scale factor for diagram (0.1 = 10px per 100 real pixels)

        Returns:
            Tuple of (width, height) in diagram pixels
        """
        w, h = self.width, self.height
        if self.transform in [1, 3]:  # Portrait (90° or 270°)
            w, h = h, w
        # Scale < 1 makes screen appear larger (more real estate)
        factor = 1 / self.scale
        return w * base_unit * factor, h * base_unit * factor


@dataclass
class DiagramConfig:
    """Configuration for a diagram."""

    monitors: list[Monitor] = field(default_factory=list)
    positions: list[tuple[float, float]] = field(default_factory=list)
    padding: int = 10


SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <style>
    .monitor {{
      stroke: var(--vp-c-border, #c2c2c4);
      stroke-width: 2;
    }}
    .monitor-a {{ fill: #60a5fa; }}  /* Pastel Blue */
    .monitor-b {{ fill: #86efac; }}  /* Pastel Green */
    .monitor-c {{ fill: #fdba74; }}  /* Pastel Orange */
    .label {{
      fill: #1f2937;  /* Dark gray, almost black */
      font-family: system-ui, -apple-system, sans-serif;
      font-size: 16px;
      font-weight: 600;
      text-anchor: middle;
      dominant-baseline: central;
    }}
  </style>
{rects}
</svg>"""

RECT_TEMPLATE = '  <rect class="monitor {color_class}" x="{x}" y="{y}" width="{w}" height="{h}" rx="4" />'
TEXT_TEMPLATE = '  <text class="label" x="{x}" y="{y}">{label}</text>'


def generate_svg(config: DiagramConfig) -> str:
    """Generate SVG content from diagram configuration."""
    rects = []
    padding = config.padding

    # Calculate bounding box
    max_x = 0
    max_y = 0

    for mon, (px, py) in zip(config.monitors, config.positions):
        w, h = mon.effective_size()
        max_x = max(max_x, px + w)
        max_y = max(max_y, py + h)

    svg_width = max_x + padding * 2
    svg_height = max_y + padding * 2

    # Generate rectangles and labels
    for mon, (px, py) in zip(config.monitors, config.positions):
        w, h = mon.effective_size()
        x = px + padding
        y = py + padding

        rects.append(RECT_TEMPLATE.format(color_class=mon.color_class, x=x, y=y, w=w, h=h))
        rects.append(TEXT_TEMPLATE.format(x=x + w / 2, y=y + h / 2, label=mon.label))

    return SVG_TEMPLATE.format(width=int(svg_width), height=int(svg_height), rects="\n".join(rects))


# =============================================================================
# Diagram Definitions
# =============================================================================

# Base monitor sizes
FULL_HD = (1920, 1080)
SMALLER = (1280, 720)

# Base unit for diagram scaling
BASE = 0.1


def basic_top_of() -> DiagramConfig:
    """A on top of B."""
    a = Monitor("A", *FULL_HD, color_class="monitor-a")
    b = Monitor("B", *FULL_HD, color_class="monitor-b")
    aw, ah = a.effective_size(BASE)
    return DiagramConfig(monitors=[a, b], positions=[(0, 0), (0, ah)])


def basic_bottom_of() -> DiagramConfig:
    """A below B."""
    a = Monitor("A", *FULL_HD, color_class="monitor-a")
    b = Monitor("B", *FULL_HD, color_class="monitor-b")
    bw, bh = b.effective_size(BASE)
    return DiagramConfig(monitors=[b, a], positions=[(0, 0), (0, bh)])


def basic_left_of() -> DiagramConfig:
    """A left of B."""
    a = Monitor("A", *FULL_HD, color_class="monitor-a")
    b = Monitor("B", *FULL_HD, color_class="monitor-b")
    aw, ah = a.effective_size(BASE)
    return DiagramConfig(monitors=[a, b], positions=[(0, 0), (aw, 0)])


def basic_right_of() -> DiagramConfig:
    """A right of B."""
    a = Monitor("A", *FULL_HD, color_class="monitor-a")
    b = Monitor("B", *FULL_HD, color_class="monitor-b")
    bw, bh = b.effective_size(BASE)
    return DiagramConfig(monitors=[b, a], positions=[(0, 0), (bw, 0)])


def align_left_start() -> DiagramConfig:
    """A left of B, top-aligned (start)."""
    a = Monitor("A", *SMALLER, color_class="monitor-a")
    b = Monitor("B", *FULL_HD, color_class="monitor-b")
    aw, ah = a.effective_size(BASE)
    return DiagramConfig(monitors=[a, b], positions=[(0, 0), (aw, 0)])


def align_left_center() -> DiagramConfig:
    """A left of B, center-aligned."""
    a = Monitor("A", *SMALLER, color_class="monitor-a")
    b = Monitor("B", *FULL_HD, color_class="monitor-b")
    aw, ah = a.effective_size(BASE)
    bw, bh = b.effective_size(BASE)
    a_y = (bh - ah) / 2
    return DiagramConfig(monitors=[a, b], positions=[(0, a_y), (aw, 0)])


def align_left_end() -> DiagramConfig:
    """A left of B, bottom-aligned (end)."""
    a = Monitor("A", *SMALLER, color_class="monitor-a")
    b = Monitor("B", *FULL_HD, color_class="monitor-b")
    aw, ah = a.effective_size(BASE)
    bw, bh = b.effective_size(BASE)
    a_y = bh - ah
    return DiagramConfig(monitors=[a, b], positions=[(0, a_y), (aw, 0)])


def align_top_start() -> DiagramConfig:
    """A on top of B, left-aligned (start)."""
    a = Monitor("A", *SMALLER, color_class="monitor-a")
    b = Monitor("B", *FULL_HD, color_class="monitor-b")
    aw, ah = a.effective_size(BASE)
    return DiagramConfig(monitors=[a, b], positions=[(0, 0), (0, ah)])


def align_top_center() -> DiagramConfig:
    """A on top of B, center-aligned."""
    a = Monitor("A", *SMALLER, color_class="monitor-a")
    b = Monitor("B", *FULL_HD, color_class="monitor-b")
    aw, ah = a.effective_size(BASE)
    bw, bh = b.effective_size(BASE)
    a_x = (bw - aw) / 2
    return DiagramConfig(monitors=[a, b], positions=[(a_x, 0), (0, ah)])


def align_top_end() -> DiagramConfig:
    """A on top of B, right-aligned (end)."""
    a = Monitor("A", *SMALLER, color_class="monitor-a")
    b = Monitor("B", *FULL_HD, color_class="monitor-b")
    aw, ah = a.effective_size(BASE)
    bw, bh = b.effective_size(BASE)
    a_x = bw - aw
    return DiagramConfig(monitors=[a, b], positions=[(a_x, 0), (0, ah)])


def setup_dual() -> DiagramConfig:
    """A and B side by side."""
    a = Monitor("A", *FULL_HD, color_class="monitor-a")
    b = Monitor("B", *FULL_HD, color_class="monitor-b")
    aw, ah = a.effective_size(BASE)
    return DiagramConfig(monitors=[a, b], positions=[(0, 0), (aw, 0)])


def setup_triple() -> DiagramConfig:
    """A, B, C horizontal."""
    a = Monitor("A", *FULL_HD, color_class="monitor-a")
    b = Monitor("B", *FULL_HD, color_class="monitor-b")
    c = Monitor("C", *FULL_HD, color_class="monitor-c")
    aw, ah = a.effective_size(BASE)
    bw, bh = b.effective_size(BASE)
    return DiagramConfig(monitors=[a, b, c], positions=[(0, 0), (aw, 0), (aw + bw, 0)])


def setup_stacked() -> DiagramConfig:
    """A, B, C vertical."""
    a = Monitor("A", *FULL_HD, color_class="monitor-a")
    b = Monitor("B", *FULL_HD, color_class="monitor-b")
    c = Monitor("C", *FULL_HD, color_class="monitor-c")
    aw, ah = a.effective_size(BASE)
    bw, bh = b.effective_size(BASE)
    return DiagramConfig(monitors=[a, b, c], positions=[(0, 0), (0, ah), (0, ah + bh)])


def real_world_l_shape() -> DiagramConfig:
    """Real-world L-shape with portrait monitor.

    B (eDP-1): 1920x1080, transform=0, scale=1.0 (anchor, bottom)
    A (HDMI-A-1): 1920x1080, transform=1, scale=0.83 (portrait, top-left of B)
    C: 1920x1080, transform=0, scale=1.0 (right-end of A, tucked in corner)
    """
    # B is the anchor at bottom
    b = Monitor("B", 1920, 1080, transform=0, scale=1.0, color_class="monitor-b")
    # A is portrait (transform=1) with scale=0.83 (appears larger)
    a = Monitor("A", 1920, 1080, transform=1, scale=0.83, color_class="monitor-a")
    # C is normal, same as B
    c = Monitor("C", 1920, 1080, transform=0, scale=1.0, color_class="monitor-c")

    aw, ah = a.effective_size(BASE)  # A is portrait and scaled
    bw, bh = b.effective_size(BASE)
    cw, ch = c.effective_size(BASE)

    # A is on top of B (left-aligned with B's left edge)
    a_x, a_y = 0, 0

    # C is right-end of A (bottom edges aligned)
    c_x = aw  # Right of A
    c_y = ah - ch  # Bottom of C aligns with bottom of A

    # B is below A (and partially below C)
    b_x = 0
    b_y = ah  # Below A

    return DiagramConfig(monitors=[a, c, b], positions=[(a_x, a_y), (c_x, c_y), (b_x, b_y)])


# =============================================================================
# Main
# =============================================================================

DIAGRAMS = {
    "basic-top-of": basic_top_of,
    "basic-bottom-of": basic_bottom_of,
    "basic-left-of": basic_left_of,
    "basic-right-of": basic_right_of,
    "align-left-start": align_left_start,
    "align-left-center": align_left_center,
    "align-left-end": align_left_end,
    "align-top-start": align_top_start,
    "align-top-center": align_top_center,
    "align-top-end": align_top_end,
    "setup-dual": setup_dual,
    "setup-triple": setup_triple,
    "setup-stacked": setup_stacked,
    "real-world-l-shape": real_world_l_shape,
}


def main() -> None:
    """Generate all SVG diagrams."""
    output_dir = Path(__file__).parent.parent / "site" / "public" / "images" / "monitors"
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, config_fn in DIAGRAMS.items():
        config = config_fn()
        svg = generate_svg(config)
        output_path = output_dir / f"{name}.svg"
        output_path.write_text(svg)
        print(f"Generated: {output_path}")

    print(f"\nGenerated {len(DIAGRAMS)} SVG files in {output_dir}")


if __name__ == "__main__":
    main()
