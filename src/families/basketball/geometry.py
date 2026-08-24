"""Draw a basketball court from a :class:`~families.basketball.specs.CourtSpec`.

Court coordinates run in feet with the origin at the middle of one end line, on
its inside edge: ``x`` across the width, ``y`` up the length of the floor.

Rule books dimension a marking to a specific *edge* of a painted line, while a
drawing program strokes along a path *centre*. Every published figure is
converted once, here, by :func:`to_path`, and all downstream geometry is in
path-centre coordinates. A worked consequence: NFHS's straight corner segments
stay exactly tangent to its three-point arc after conversion, because both the
radius and the corner offset shift inward by the same half line width.
"""

from __future__ import annotations

import math

from rmtpl.draw import Canvas, Fit, fit_box
from rmtpl.style import DEFAULT_STYLE, Style

from .specs import CourtSpec, Edge

#: A drawn extent of the floor. ``full`` is the whole court; ``half`` is one
#: half, up to and including the division line.
REGIONS = ("full", "half")
Region = str


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


def court_fit(spec: CourtSpec, region: Region, page: tuple[int, int],
              style: Style = DEFAULT_STYLE) -> Fit:
    """Fit the whole drawn region inside the page. Nothing is ever cropped."""
    if region not in REGIONS:
        raise ValueError(f"region must be one of {REGIONS}, not {region!r}")
    bw, lw = spec.boundary_line_width, spec.line_width
    # Outer edge to outer edge of the painted boundary lines.
    span = spec.width + 2 * bw
    depth = (spec.length + 2 * bw if region == "full"
             else spec.half_length + bw + lw / 2.0)
    return fit_box(span, depth, page, style, top_pad=bw)


def _orient(angles: tuple[float, float], flip: bool) -> tuple[float, float]:
    """Mirror a pair of angles about the x axis when the end is flipped."""
    return angles if not flip else (-angles[0], -angles[1])


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
    # Angles are written for the un-flipped end, where 0..pi sweeps away from
    # the basket; _orient mirrors them for the far end. Do not pre-mirror.
    ft_r = to_path(s.ft_circle_radius, s.ft_circle_edge, lw)
    c.arc(0, Y(ft_y), ft_r, *_orient((0.0, math.pi), flip), lw)
    if s.ft_circle_dashed_inner:
        c.arc(0, Y(ft_y), ft_r, *_orient((math.pi, 2 * math.pi), flip), lw,
              dash=c.dash(math.pi * ft_r))

    # --- lane space marks -------------------------------------------------
    outer = s.lane_width / 2.0
    for mk in s.lane_marks:
        for sign in (-1, 1):
            c.rect_filled(sign * outer, Y(mk.near),
                          sign * (outer + mk.depth), Y(mk.near + mk.length),
                          colour=c.style.ink_soft)

    # --- three-point line -------------------------------------------------
    r3 = to_path(s.three_radius, s.three_edge, lw)
    cx3 = to_path(s.three_corner_x, s.three_corner_edge, lw)
    junction = s.basket_centre + math.sqrt(max(r3 * r3 - cx3 * cx3, 0.0))
    for sign in (-1, 1):
        c.line(sign * cx3, Y(0), sign * cx3, Y(junction), lw)
    a0 = math.atan2(junction - s.basket_centre, cx3)
    c.arc(0, Y(s.basket_centre), r3, *_orient((a0, math.pi - a0), flip), lw)

    # --- restricted (no-charge) area --------------------------------------
    if s.restricted_radius is not None:
        rr = to_path(s.restricted_radius, s.restricted_edge, lw)
        c.arc(0, Y(s.basket_centre), rr, *_orient((0.0, math.pi), flip), lw)
        for sign in (-1, 1):
            c.line(sign * rr, Y(s.basket_centre), sign * rr,
                   Y(s.backboard_face), lw)

    # --- additional floor marks (the NBA lower defensive box) -------------
    for mx, my, mlen, perpendicular in s.floor_marks:
        for sign in (-1, 1):
            if perpendicular:
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


def build_svg(spec: CourtSpec, region: Region, page: tuple[int, int],
              ppi: float, style: Style = DEFAULT_STYLE) -> str:
    """Render one court template as a standalone SVG document."""
    fit = court_fit(spec, region, page, style)
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
        c.line(-side_x - bw / 2, spec.length + bw / 2,
               side_x + bw / 2, spec.length + bw / 2, bw)

    # --- division line and centre circle ----------------------------------
    c.line(-side_x, half, side_x, half, lw)
    cr = to_path(spec.centre_circle_radius, spec.centre_circle_edge, lw)
    inner = (to_path(spec.inner_circle_radius, Edge.INNER, lw)
             if spec.inner_circle_radius is not None else None)
    if region == "full":
        c.circle(0, half, cr, lw)
        if inner is not None:
            c.circle(0, half, inner, lw)
    else:
        c.arc(0, half, cr, math.pi, 2 * math.pi, lw)
        if inner is not None:
            c.arc(0, half, inner, math.pi, 2 * math.pi, lw)

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

    label = "full court" if region == "full" else "half court"
    return c.document(f"{spec.label} basketball court ({label})", ppi)
