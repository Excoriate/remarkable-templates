"""A small SVG drawing surface in world units.

Families describe their artwork in whatever units the subject uses — feet for a
basketball court, millimetres for a music stave, days for a planner grid — and
this maps those units onto a device canvas. Keeping the mapping here means a
family never computes a pixel coordinate, and the page fit is one thing to get
right rather than one per family.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .style import DEFAULT_STYLE, Style


@dataclass(frozen=True)
class Fit:
    """Maps world units onto page pixels: uniform scale, centred, no crop."""

    scale: float       # device px per world unit
    off_x: float       # page px at world x = 0
    off_y: float       # page px at world y = 0
    page_w: int
    page_h: int
    span: float        # drawn extent along x, in world units
    depth: float       # drawn extent along y, in world units

    def px(self, x: float, y: float) -> tuple[float, float]:
        return (self.off_x + x * self.scale, self.off_y + y * self.scale)


def fit_box(span: float, depth: float, page: tuple[int, int],
            style: Style = DEFAULT_STYLE, *, top_pad: float = 0.0) -> Fit:
    """Fit a ``span`` x ``depth`` box inside ``page``, centred, nothing cropped.

    World x = 0 is the horizontal centre of the page. World y = 0 sits
    ``top_pad`` world units below the top of the drawn area, which lets a family
    put its origin on a feature — a court's end line, say — rather than on the
    bounding box.

    The scale is uniform and the box is centred. A family that needs a
    different placement — an edge-to-edge grid, a left-aligned stave — should
    construct :class:`Fit` directly; it is a plain value.
    """
    page_w, page_h = page
    usable_w = page_w - 2 * style.margin_px
    usable_h = page_h - 2 * style.margin_px
    scale = min(usable_w / span, usable_h / depth)
    off_x = page_w / 2.0
    off_y = (page_h - depth * scale) / 2.0 + top_pad * scale
    return Fit(scale, off_x, off_y, page_w, page_h, span, depth)


class Canvas:
    """Accumulates SVG elements, taking coordinates in world units."""

    def __init__(self, fit: Fit, style: Style = DEFAULT_STYLE):
        self.fit = fit
        self.style = style
        self.parts: list[str] = []

    # -- stroke width ---------------------------------------------------- #
    def stroke_px(self, width: float) -> float:
        """A world-unit line width, in device pixels, clamped to be legible."""
        raw = width * self.fit.scale * self.style.line_scale
        return max(self.style.min_stroke_px, min(self.style.max_stroke_px, raw))

    def dash(self, arc_length: float) -> tuple[float, float]:
        """A painted/gap pair that divides ``arc_length`` into whole segments."""
        n = self.style.dash_segments
        on = arc_length / (n + (n - 1) * self.style.dash_ratio)
        return (on, on * self.style.dash_ratio)

    # -- primitives ------------------------------------------------------ #
    def line(self, x1, y1, x2, y2, w, colour=None, dash=None) -> None:
        a, b = self.fit.px(x1, y1), self.fit.px(x2, y2)
        self.parts.append(
            f'<path d="M {a[0]:.3f} {a[1]:.3f} L {b[0]:.3f} {b[1]:.3f}" '
            f'stroke="{colour or self.style.ink}" '
            f'stroke-width="{self.stroke_px(w):.3f}" '
            f'fill="none" stroke-linecap="butt"{self._dash(dash)}/>'
        )

    def polyline(self, pts, w, colour=None, close=False) -> None:
        d = " ".join(
            ("M" if i == 0 else "L")
            + f" {self.fit.px(*p)[0]:.3f} {self.fit.px(*p)[1]:.3f}"
            for i, p in enumerate(pts)
        )
        if close:
            d += " Z"
        self.parts.append(
            f'<path d="{d}" stroke="{colour or self.style.ink}" '
            f'stroke-width="{self.stroke_px(w):.3f}" fill="none" '
            f'stroke-linejoin="miter" stroke-linecap="butt"/>'
        )

    def circle(self, cx, cy, r, w, colour=None) -> None:
        c = self.fit.px(cx, cy)
        self.parts.append(
            f'<circle cx="{c[0]:.3f}" cy="{c[1]:.3f}" '
            f'r="{r * self.fit.scale:.3f}" '
            f'stroke="{colour or self.style.ink}" '
            f'stroke-width="{self.stroke_px(w):.3f}" fill="none"/>'
        )

    def arc(self, cx, cy, r, a0, a1, w, colour=None, dash=None) -> None:
        """Arc in world space. Angles in radians, 0 = +x, sweeping toward +y."""
        p0 = self.fit.px(cx + r * math.cos(a0), cy + r * math.sin(a0))
        p1 = self.fit.px(cx + r * math.cos(a1), cy + r * math.sin(a1))
        rp = r * self.fit.scale
        large = 1 if abs(a1 - a0) > math.pi else 0
        sweep = 1 if a1 > a0 else 0
        self.parts.append(
            f'<path d="M {p0[0]:.3f} {p0[1]:.3f} A {rp:.3f} {rp:.3f} 0 '
            f'{large} {sweep} {p1[0]:.3f} {p1[1]:.3f}" '
            f'stroke="{colour or self.style.ink}" '
            f'stroke-width="{self.stroke_px(w):.3f}" fill="none" '
            f'stroke-linecap="butt"{self._dash(dash)}/>'
        )

    def rect_filled(self, x0, y0, x1, y1, colour=None) -> None:
        a = self.fit.px(min(x0, x1), min(y0, y1))
        b = self.fit.px(max(x0, x1), max(y0, y1))
        self.parts.append(
            f'<rect x="{a[0]:.3f}" y="{a[1]:.3f}" '
            f'width="{b[0] - a[0]:.3f}" height="{b[1] - a[1]:.3f}" '
            f'fill="{colour or self.style.ink}" stroke="none"/>'
        )

    def raw(self, svg: str) -> None:
        """Append a prepared SVG fragment, already in page pixels.

        The escape hatch for anything the primitives above do not cover — most
        obviously text, which needs a font. Use ``fit.px()`` to place it.

        A caution about text specifically: a ``<text>`` element rasterises
        against whatever font the rendering machine has, so a build containing
        one stops being byte-reproducible across environments and the CI gate
        that compares committed output against a rebuild will fail on somebody
        else's machine. A family that needs lettering should convert it to
        paths at build time, or ship the glyphs it needs as path data.
        """
        self.parts.append(svg)

    def _dash(self, dash) -> str:
        if not dash:
            return ""
        vals = " ".join(f"{v * self.fit.scale:.3f}" for v in dash)
        return f' stroke-dasharray="{vals}"'

    # -- output ---------------------------------------------------------- #
    def document(self, title: str, ppi: float) -> str:
        """Wrap what has been drawn in a standalone SVG document.

        The document declares its size in points as well as pixels, so the same
        file rasterises to the exact device canvas and prints to the exact
        panel size without a second set of numbers.
        """
        w_px, h_px = self.fit.page_w, self.fit.page_h
        w_pt, h_pt = w_px * 72.0 / ppi, h_px * 72.0 / ppi
        body = "\n  ".join(self.parts)
        escaped = (title.replace("&", "&amp;").replace("<", "&lt;")
                        .replace(">", "&gt;"))
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
            f'width="{w_pt:.4f}pt" height="{h_pt:.4f}pt" '
            f'viewBox="0 0 {w_px} {h_px}">\n'
            f'  <title>{escaped}</title>\n'
            f'  <rect x="0" y="0" width="{w_px}" height="{h_px}" '
            f'fill="{self.style.background}"/>\n'
            f'  {body}\n'
            '</svg>\n'
        )
