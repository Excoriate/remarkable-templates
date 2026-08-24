"""Turn a :class:`~courts.specs.CourtSpec` into SVG for a reMarkable canvas.

Court coordinates run in feet with the origin at the middle of one end line,
on its inside edge: ``x`` across the width, ``y`` up the length of the floor.

Rule books dimension markings to a specific *edge* of a painted line, while a
drawing program strokes along a path *centre*. Every published figure is
therefore converted once, here, by :func:`to_path`, and all downstream geometry
is in path-centre coordinates. A worked consequence: NFHS's straight corner
segments stay exactly tangent to its three-point arc after conversion, because
both the radius and the corner offset shift inward by the same half line width.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .specs import CourtSpec, Edge

Region = str  # "full" | "half"


# --------------------------------------------------------------------------- #
# edge conventions
# --------------------------------------------------------------------------- #

def to_path(published: float, edge: Edge, line_width: float) -> float:
    """Convert a published dimension to the centre of the painted line.

    ``published`` is measured from the reference point (a basket centre, the
    court centre, an end line) out to ``edge`` of the line.
    """
    if edge is Edge.OUTER:
        return published - line_width / 2.0
    if edge is Edge.INNER:
        return published + line_width / 2.0
    return published


# --------------------------------------------------------------------------- #
# style
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Style:
    ink: str = "#4a4a4a"          # court lines and equipment
    ink_soft: str = "#8a8a8a"     # lane marks, hash marks
    background: str = "#ffffff"
    #: multiplier on the true-to-scale painted line width
    line_scale: float = 1.0
    #: never render a stroke thinner than this many device pixels
    min_stroke_px: float = 1.8
    #: never render a stroke thicker than this many device pixels
    max_stroke_px: float = 4.2
    margin_px: float = 26.0
    #: The broken half of the free-throw circle: how many painted segments, and
    #: the painted:gap ratio. Professional lining guides give eight 16 in
    #: segments and seven 14 in gaps on a 6 ft circle; expressing it as a count
    #: and a ratio makes the pattern land cleanly on any radius.
    dash_segments: int = 8
    dash_ratio: float = 14.0 / 16.0


DEFAULT_STYLE = Style()


# --------------------------------------------------------------------------- #
# page fitting
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Fit:
    """Maps court feet onto page pixels: uniform scale, centred, no crop."""

    scale: float       # device px per foot
    off_x: float       # page px at court x = 0
    off_y: float       # page px at court y = 0
    page_w: int
    page_h: int
    depth: float       # extent of the drawn region along y, in feet
    span: float        # extent along x, in feet

    def px(self, x: float, y: float) -> tuple[float, float]:
        return (self.off_x + x * self.scale, self.off_y + y * self.scale)


def fit_region(spec: CourtSpec, region: Region, page: tuple[int, int],
               style: Style = DEFAULT_STYLE) -> Fit:
    """Fit the whole drawn region inside the page. Nothing is ever cropped."""
    page_w, page_h = page
    bw = spec.boundary_line_width
    lw = spec.line_width
    # The drawn extent, outer edge to outer edge of the painted lines.
    span = spec.width + 2 * bw
    if region == "full":
        depth = spec.length + 2 * bw
    else:
        depth = spec.half_length + bw + lw / 2.0
    usable_w = page_w - 2 * style.margin_px
    usable_h = page_h - 2 * style.margin_px
    scale = min(usable_w / span, usable_h / depth)
    off_x = page_w / 2.0                       # court x = 0 is the page centre
    off_y = (page_h - depth * scale) / 2.0 + bw * scale
    return Fit(scale, off_x, off_y, page_w, page_h, depth, span)


# --------------------------------------------------------------------------- #
# SVG assembly
# --------------------------------------------------------------------------- #

class Canvas:
    def __init__(self, fit: Fit, style: Style):
        self.fit = fit
        self.style = style
        self.parts: list[str] = []
        px_per_ft = fit.scale
        self._stroke_px = lambda w_ft: max(
            style.min_stroke_px,
            min(style.max_stroke_px, w_ft * px_per_ft * style.line_scale),
        )

    # -- primitives ---------------------------------------------------- #
    def line(self, x1, y1, x2, y2, w, colour=None, dash=None):
        a = self.fit.px(x1, y1)
        b = self.fit.px(x2, y2)
        self.parts.append(
            f'<path d="M {a[0]:.3f} {a[1]:.3f} L {b[0]:.3f} {b[1]:.3f}" '
            f'stroke="{colour or self.style.ink}" '
            f'stroke-width="{self._stroke_px(w):.3f}" '
            f'fill="none" stroke-linecap="butt"{self._dash(dash)}/>'
        )

    def polyline(self, pts, w, colour=None, close=False):
        d = " ".join(
            ("M" if i == 0 else "L")
            + f" {self.fit.px(*p)[0]:.3f} {self.fit.px(*p)[1]:.3f}"
            for i, p in enumerate(pts)
        )
        if close:
            d += " Z"
        self.parts.append(
            f'<path d="{d}" stroke="{colour or self.style.ink}" '
            f'stroke-width="{self._stroke_px(w):.3f}" fill="none" '
            f'stroke-linejoin="miter" stroke-linecap="butt"/>'
        )

    def circle(self, cx, cy, r, w, colour=None):
        c = self.fit.px(cx, cy)
        self.parts.append(
            f'<circle cx="{c[0]:.3f}" cy="{c[1]:.3f}" '
            f'r="{r * self.fit.scale:.3f}" '
            f'stroke="{colour or self.style.ink}" '
            f'stroke-width="{self._stroke_px(w):.3f}" '
            f'fill="none"/>'
        )

    def arc(self, cx, cy, r, a0, a1, w, colour=None, dash=None):
        """Arc in court space. Angles in radians, 0 = +x, measured toward +y."""
        p0 = self.fit.px(cx + r * math.cos(a0), cy + r * math.sin(a0))
        p1 = self.fit.px(cx + r * math.cos(a1), cy + r * math.sin(a1))
        rp = r * self.fit.scale
        large = 1 if abs(a1 - a0) > math.pi else 0
        sweep = 1 if a1 > a0 else 0
        self.parts.append(
            f'<path d="M {p0[0]:.3f} {p0[1]:.3f} A {rp:.3f} {rp:.3f} 0 {large} {sweep} '
            f'{p1[0]:.3f} {p1[1]:.3f}" stroke="{colour or self.style.ink}" '
            f'stroke-width="{self._stroke_px(w):.3f}" fill="none" '
            f'stroke-linecap="butt"{self._dash(dash)}/>'
        )

    def rect_filled(self, x0, y0, x1, y1, colour=None):
        a = self.fit.px(min(x0, x1), min(y0, y1))
        b = self.fit.px(max(x0, x1), max(y0, y1))
        self.parts.append(
            f'<rect x="{a[0]:.3f}" y="{a[1]:.3f}" width="{b[0] - a[0]:.3f}" '
            f'height="{b[1] - a[1]:.3f}" '
            f'fill="{colour or self.style.ink}" stroke="none"/>'
        )

    def _dash(self, dash) -> str:
        if not dash:
            return ""
        vals = " ".join(f"{v * self.fit.scale:.3f}" for v in dash)
        return f' stroke-dasharray="{vals}"'


# --------------------------------------------------------------------------- #
# the court itself
# --------------------------------------------------------------------------- #

def _end(c: Canvas, s: CourtSpec, flip: bool) -> None:
    """Draw one end of the court. ``flip`` mirrors it about the court centre."""
    L, lw = s.length, s.line_width

    def Y(y: float) -> float:
        return (L - y) if flip else y

    # --- free-throw lane --------------------------------------------------
    lane_x = to_path(s.lane_width / 2.0, Edge.OUTER, lw)
    ft_y = to_path(s.lane_length, Edge.OUTER, lw)
    c.polyline([(-lane_x, Y(0)), (-lane_x, Y(ft_y)),
                (lane_x, Y(ft_y)), (lane_x, Y(0))], lw)

    # --- free-throw circle ------------------------------------------------
    ft_r = to_path(s.ft_circle_radius, s.ft_circle_edge, lw)
    # Angles are written for the un-flipped end, where 0..pi sweeps away from
    # the basket; _orient mirrors them for the far end. Do not pre-mirror.
    c.arc(0, Y(ft_y), ft_r, *_orient((0.0, math.pi), flip), lw)
    if s.ft_circle_dashed_inner:
        n = c.style.dash_segments
        arc_len = math.pi * ft_r
        on = arc_len / (n + (n - 1) * c.style.dash_ratio)
        c.arc(0, Y(ft_y), ft_r, *_orient((math.pi, 2 * math.pi), flip), lw,
              dash=(on, on * c.style.dash_ratio))

    # --- lane space marks -------------------------------------------------
    outer = s.lane_width / 2.0
    for mk in s.lane_marks:
        for sign in (-1, 1):
            x0 = sign * outer
            x1 = sign * (outer + mk.depth)
            c.rect_filled(x0, Y(mk.near), x1, Y(mk.near + mk.length),
                          colour=c.style.ink_soft)

    # --- three-point line -------------------------------------------------
    r3 = to_path(s.three_radius, s.three_edge, lw)
    cx3 = to_path(s.three_corner_x, s.three_corner_edge, lw)
    inside = max(r3 * r3 - cx3 * cx3, 0.0)
    junction = s.basket_centre + math.sqrt(inside)
    for sign in (-1, 1):
        c.line(sign * cx3, Y(0), sign * cx3, Y(junction), lw)
    a0 = math.atan2(junction - s.basket_centre, cx3)
    c.arc(0, Y(s.basket_centre), r3, *_orient((a0, math.pi - a0), flip), lw)

    # --- restricted (no-charge) area --------------------------------------
    if s.restricted_radius is not None:
        rr = to_path(s.restricted_radius, s.restricted_edge, lw)
        c.arc(0, Y(s.basket_centre), rr, *_orient((0.0, math.pi), flip), lw)
        for sign in (-1, 1):
            c.line(sign * rr, Y(s.basket_centre), sign * rr, Y(s.backboard_face), lw)

    # --- additional floor marks (NBA lower defensive box) -------------------
    for mx, my, mlen, along_baseline in s.floor_marks:
        for sign in (-1, 1):
            if along_baseline:
                c.line(sign * mx, Y(0), sign * mx, Y(mlen), lw,
                       colour=c.style.ink_soft)
            else:
                c.line(sign * mx, Y(my), sign * (mx + mlen), Y(my), lw,
                       colour=c.style.ink_soft)

    # --- backboard and ring ------------------------------------------------
    bb = s.backboard_width / 2.0
    c.line(-bb, Y(s.backboard_face), bb, Y(s.backboard_face), lw * 1.6)
    c.line(0, Y(s.backboard_face), 0, Y(s.basket_centre - s.rim_radius), lw)
    c.circle(0, Y(s.basket_centre), s.rim_radius, lw)


def _orient(angles: tuple[float, float], flip: bool) -> tuple[float, float]:
    """Mirror a pair of angles about the x axis when the end is flipped."""
    if not flip:
        return angles
    return (-angles[0], -angles[1])


def build_svg(spec: CourtSpec, region: Region, page: tuple[int, int],
              ppi: float, style: Style = DEFAULT_STYLE) -> str:
    """Render one template as a standalone SVG string."""
    if region not in ("full", "half"):
        raise ValueError(f"region must be 'full' or 'half', not {region!r}")

    fit = fit_region(spec, region, page, style)
    c = Canvas(fit, style)
    lw, bw = spec.line_width, spec.boundary_line_width
    half = spec.half_length
    y_far = spec.length if region == "full" else half

    # --- boundary ---------------------------------------------------------
    # The playing surface is measured inside the boundary lines, so the lines
    # themselves sit outside it: their centres are half a line width beyond.
    side_x = to_path(spec.width / 2.0, Edge.INNER, bw)
    end_y = -bw / 2.0
    c.line(-side_x - bw / 2, end_y, side_x + bw / 2, end_y, bw)
    top = (spec.length + bw / 2.0) if region == "full" else half
    for sign in (-1, 1):
        c.line(sign * side_x, end_y - bw / 2, sign * side_x, top, bw)
    if region == "full":
        c.line(-side_x - bw / 2, spec.length + bw / 2, side_x + bw / 2,
               spec.length + bw / 2, bw)

    # --- division line and centre circle ----------------------------------
    c.line(-side_x, half, side_x, half, lw)
    cr = to_path(spec.centre_circle_radius, spec.centre_circle_edge, lw)
    if region == "full":
        c.circle(0, half, cr, lw)
        if spec.inner_circle_radius is not None:
            c.circle(0, half, to_path(spec.inner_circle_radius, Edge.INNER, lw), lw)
    else:
        c.arc(0, half, cr, math.pi, 2 * math.pi, lw)
        if spec.inner_circle_radius is not None:
            c.arc(0, half, to_path(spec.inner_circle_radius, Edge.INNER, lw),
                  math.pi, 2 * math.pi, lw)

    # --- sideline hash marks ----------------------------------------------
    for hy, hlen, inward in spec.sideline_hashes:
        for hy_ in ((hy, spec.length - hy) if region == "full" else (hy,)):
            if hy_ > y_far:
                continue
            for sign in (-1, 1):
                x0 = sign * spec.width / 2.0
                x1 = x0 + (-sign if inward else sign) * hlen
                c.line(x0, hy_, x1, hy_, lw, colour=c.style.ink_soft)

    # --- the ends ---------------------------------------------------------
    _end(c, spec, flip=False)
    if region == "full":
        _end(c, spec, flip=True)

    w_px, h_px = page
    w_pt = w_px * 72.0 / ppi
    h_pt = h_px * 72.0 / ppi
    body = "\n  ".join(c.parts)
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
        f'width="{w_pt:.4f}pt" height="{h_pt:.4f}pt" '
        f'viewBox="0 0 {w_px} {h_px}">\n'
        f'  <title>{spec.label} basketball court '
        f'({"full court" if region == "full" else "half court"})</title>\n'
        f'  <rect x="0" y="0" width="{w_px}" height="{h_px}" '
        f'fill="{style.background}"/>\n'
        f'  {body}\n'
        f'</svg>\n'
    )
