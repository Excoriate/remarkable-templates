"""Drawing style shared by every family that renders vector artwork."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    """How a drawn template looks.

    A template is background. Its lines want to be visible without competing
    with the ink written on top, which is why the defaults are grey rather than
    black and why stroke width is clamped: a line rendered at true scale is
    right on a large drawing and heavy on a small one.
    """

    #: Primary line colour.
    ink: str = "#4a4a4a"
    #: Secondary marks — ticks, hatching, anything subordinate.
    ink_soft: str = "#8a8a8a"
    background: str = "#ffffff"

    #: Multiplier on a family's true-to-scale line width.
    line_scale: float = 1.0
    #: Never render a stroke thinner than this many device pixels.
    min_stroke_px: float = 1.8
    #: Never render a stroke thicker than this many device pixels.
    max_stroke_px: float = 4.2
    #: Blank border kept around the drawn area, in device pixels.
    margin_px: float = 26.0

    #: For broken arcs: how many painted segments, and the painted:gap ratio.
    #: Expressing it as a count and a ratio makes a dash pattern land cleanly
    #: on any radius instead of leaving a stub at one end.
    dash_segments: int = 8
    dash_ratio: float = 14.0 / 16.0


DEFAULT_STYLE = Style()
