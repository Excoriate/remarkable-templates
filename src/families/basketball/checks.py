"""Checks that only a basketball court can make of itself.

Two kinds, and the difference decides what each can catch.

*Rule-book cross-checks* play independently published figures against each
other. The NBA states separately that the backboard stands 4'0" from the end
line, that the ring's near edge is 6" from the board, and that the ring is 18"
across; those three must reconstruct the 5'3" basket centre the arcs are struck
from. This is the only thing here that can catch a mistyped dimension, because
re-measuring a drawing can never establish that the number drawn was right.

*Render checks* re-measure the finished rasters and express what they find in
**feet**, using a scale derived from the image itself. Nothing in this section
imports the drawing module: it converts pixels back into feet with its own
arithmetic and compares against the rule book. A mistake in the edge
conventions, the page fit or the mirroring of the far end therefore shows up as
a disagreement measured in inches, instead of moving the drawing and the
expectation together.
"""

from __future__ import annotations

import math
from pathlib import Path

from rmtpl.checks import Report, arc_ink, centres, dark_mask, runs
from rmtpl.devices import Device

from . import specs
from .specs import CourtSpec, Edge, inch, m

#: Agreement required between drawing and rule book. One inch is about two
#: pixels at Paper Pro density, so this is a genuinely tight bound.
TOLERANCE_FT = inch(1.5)

#: Region -> is the page landscape. Duplicated from the family module on
#: purpose: a checker that imports its expectations from the thing it checks
#: proves consistency, not correctness.
REGION_LANDSCAPE = {"full": False, "half": True}


def _near_ft(rep: Report, got: float, want: float, label: str,
             tol: float = TOLERANCE_FT) -> bool:
    return rep.check(
        abs(got - want) <= tol, label,
        f"measured {got:.4f} ft, rule book {want:.4f} ft "
        f"(off by {(got - want) * 12:+.2f} in, tolerance {tol * 12:.2f} in)")


# --------------------------------------------------------------------------- #
# rule-book cross-checks
# --------------------------------------------------------------------------- #

def _cross_checks(rep: Report) -> None:
    tol = inch(0.5)

    for key in ("nba", "ncaa", "nfhs"):
        s = specs.get(key)
        rebuilt = s.backboard_face + inch(6) + s.rim_radius
        rep.check(abs(rebuilt - s.basket_centre) <= tol,
                  f"{key}: basket centre reconstructs from board + ring",
                  f"4'0\" + 6\" + 9\" = {rebuilt:.4f} ft "
                  f"vs stated {s.basket_centre:.4f} ft")
        rep.check(abs((s.backboard_face + 15.0) - s.lane_length) <= tol,
                  f"{key}: free-throw line 15' from the backboard face",
                  f"{s.backboard_face + 15.0:.4f} vs {s.lane_length:.4f} ft")
        rep.check(abs(s.line_width - inch(2)) <= 1e-9, f"{key}: 2-inch lines")

    nba = specs.NBA
    rep.check(abs(nba.three_corner_from_sideline - 3.0) <= tol,
              "nba: corner three 3'0\" from the sideline",
              f"{nba.three_corner_from_sideline:.4f} ft")
    rep.check(abs(nba.length - 94.0) < 1e-9 and abs(nba.width - 50.0) < 1e-9,
              "nba: 94 x 50 floor")

    nfhs = specs.NFHS
    rep.check(abs(nfhs.basket_centre - inch(63)) <= tol,
              "nfhs: 63-inch corner segment ends exactly at the basket centre",
              f"basket centre {nfhs.basket_centre:.4f} ft vs 63 in "
              f"= {inch(63):.4f} ft")
    rep.check(abs((nfhs.lane_length + nfhs.ft_circle_radius)
                  - (nfhs.basket_centre + nfhs.three_radius)) <= tol,
              "nfhs: free-throw circle and three-point arc are tangent at 25'",
              f"{nfhs.lane_length + nfhs.ft_circle_radius:.4f} vs "
              f"{nfhs.basket_centre + nfhs.three_radius:.4f} ft")
    rep.check(abs(nfhs.three_corner_from_sideline - inch(63)) <= tol,
              "nfhs: corner segment 63\" from the sideline on a 50' floor")

    fiba = specs.FIBA
    rebuilt = fiba.backboard_face + m(0.151) + m(0.2275)
    rep.check(abs(rebuilt - fiba.basket_centre) <= m(0.005),
              "fiba: basket centre reconstructs from board + ring offsets",
              f"1.200 + 0.151 + 0.2275 = {rebuilt * 0.3048:.4f} m vs "
              f"stated {fiba.basket_centre * 0.3048:.4f} m")
    rep.check(abs(fiba.three_corner_from_sideline - m(0.90)) <= m(0.005),
              "fiba: corner three 0.90 m from the sideline",
              f"{fiba.three_corner_from_sideline * 0.3048:.4f} m")
    rep.check(abs(fiba.line_width - m(0.05)) <= 1e-9, "fiba: 5 cm lines")

    rep.check(abs(specs.NCAA.three_radius - fiba.three_radius) <= inch(0.25),
              "ncaa: three-point radius matches the FIBA distance it adopted",
              f"{specs.NCAA.three_radius:.4f} vs {fiba.three_radius:.4f} ft")

    for key in specs.ORDER:
        s = specs.get(key)
        rep.check(s.three_radius >= s.three_corner_x,
                  f"{key}: three-point arc reaches its corner segments")
        if not s.three_corner_tangent_at_basket:
            junction = s.basket_centre + math.sqrt(
                s.three_radius ** 2 - s.three_corner_x ** 2)
            rep.check(0 < junction < s.half_length,
                      f"{key}: arc/corner junction lands on the floor",
                      f"{junction:.4f} ft")


# --------------------------------------------------------------------------- #
# render checks
# --------------------------------------------------------------------------- #

def _check_render(rep: Report, path: Path, spec: CourtSpec, region: str,
                  device: Device) -> None:
    label = path.name
    dark = dark_mask(path)
    h, w = dark.shape
    canvas = device.canvas(REGION_LANDSCAPE[region])
    if not rep.check((w, h) == canvas, f"{label}: canvas", f"{(w, h)} != {canvas}"):
        return

    verticals = centres(dark.sum(axis=0), h, 0.55)
    horizontals = centres(dark.sum(axis=1), w, 0.55)
    if not rep.check(len(verticals) >= 2 and len(horizontals) >= 2,
                     f"{label}: boundary lines found",
                     f"{len(verticals)} verticals, {len(horizontals)} horizontals"):
        return

    left, right = verticals[0], verticals[-1]

    # Scale comes from the picture, not from the build. The two sideline paths
    # are one boundary-line width further apart than the playing surface.
    scale = (right - left) / (spec.width + spec.boundary_line_width)
    ft = lambda px: px / scale                                    # noqa: E731

    # Centring is a page-layout property, so it is checked in pixels, against
    # arithmetic written here rather than imported.
    rep.near((left + right) / 2.0, w / 2.0, f"{label}: court centred on page",
             tol=1.5, unit=" px")

    # The end line's painted centre sits half a boundary width outside the
    # floor, so the floor's origin is that much further into the page.
    origin = horizontals[0] + spec.boundary_line_width / 2.0 * scale

    _near_ft(rep, ft(right - left) - spec.boundary_line_width, spec.width,
             f"{label}: floor width")

    div = [r for r in horizontals if abs(ft(r - origin) - spec.half_length) < 1.5]
    if rep.check(bool(div), f"{label}: division line found"):
        _near_ft(rep, ft(div[0] - origin), spec.half_length,
                 f"{label}: division line from end line")

    if region == "full":
        _near_ft(rep, ft(horizontals[-1] - origin) - spec.boundary_line_width / 2.0,
                 spec.length, f"{label}: court length")

    # free-throw line: the full-width row inside the lane
    lane_half_px = (spec.lane_width / 2.0 - spec.line_width) * scale
    cx = (left + right) / 2.0
    x0, x1 = int(cx - lane_half_px), int(cx + lane_half_px)
    band = dark[:, x0:x1]
    lane_rows = centres(band.sum(axis=1), x1 - x0, 0.94)
    want = spec.lane_length - spec.line_width / 2.0
    hit = [r for r in lane_rows if abs(ft(r - origin) - want) < 1.0]
    if rep.check(bool(hit), f"{label}: free-throw line found"):
        _near_ft(rep, ft(hit[0] - origin) + spec.line_width / 2.0,
                 spec.lane_length,
                 f"{label}: free-throw line (outer edge) from end line")

    # lane width, measured between the two long verticals flanking the centre
    lane_cands = [v for v in centres(dark.sum(axis=0), h, 0.18)
                  if 0 < abs(v - cx) < lane_half_px * 1.6]
    pair = sorted(lane_cands, key=lambda v: abs(abs(v - cx) - lane_half_px))[:2]
    if rep.check(len(pair) == 2, f"{label}: lane lines found"):
        _near_ft(rep, ft(abs(pair[0] - pair[1])) + spec.line_width,
                 spec.lane_width, f"{label}: lane width (outer to outer)")

    # The free-throw circle: solid away from the basket, broken inside the
    # lane. Getting these two halves the wrong way round at the far end of a
    # full court is invisible to any check that only measures positions, so ink
    # coverage is measured along each half separately.
    ends = [(0.0, 1.0)] + ([(spec.length, -1.0)] if region == "full" else [])
    for base, direction in ends:
        cy = origin + (base + direction * (spec.lane_length
                                           - spec.line_width / 2.0)) * scale
        r_px = (spec.ft_circle_radius - spec.line_width / 2.0) * scale
        away = arc_ink(dark, cx, cy, r_px, 0.0, math.pi * direction)
        into = arc_ink(dark, cx, cy, r_px, math.pi * direction,
                       2 * math.pi * direction)
        end_name = "near" if direction > 0 else "far"
        rep.check(
            away > 0.93,
            f"{label}: {end_name} free-throw circle solid away from the basket",
            f"only {away:.0%} of that half is painted")
        if spec.ft_circle_dashed_inner:
            rep.check(0.30 < into < 0.85,
                      f"{label}: {end_name} free-throw circle broken inside the lane",
                      f"{into:.0%} painted; expected roughly half")

    # The restricted-area arc, where the rules provide one.
    for base, direction in ends:
        cy = origin + (base + direction * spec.basket_centre) * scale
        end_name = "near" if direction > 0 else "far"
        if spec.restricted_radius is None:
            # NFHS defines no restricted arc, so confirm nothing was drawn
            # where one would sit. A 4 ft arc is what the other codes use.
            stray = arc_ink(dark, cx, cy, 4.0 * scale, 0.0, math.pi * direction)
            rep.check(stray < 0.25,
                      f"{label}: {end_name} end has no restricted arc, as the "
                      f"rules require", f"{stray:.0%} of that arc is painted")
            continue
        rr = spec.restricted_radius + (
            spec.line_width / 2.0 if spec.restricted_edge is Edge.INNER
            else -spec.line_width / 2.0)
        ink = arc_ink(dark, cx, cy, rr * scale, 0.0, math.pi * direction)
        rep.check(ink > 0.90, f"{label}: {end_name} restricted-area arc drawn",
                  f"only {ink:.0%} of the arc is painted")

    # three-point apex on the court centre line
    col = dark[:, int(round(cx))]
    apex_ft = spec.basket_centre + spec.three_radius
    lo = int(origin + (apex_ft - 1.0) * scale)
    hi = int(min(h, origin + (apex_ft + 1.0) * scale))
    window = runs(col[lo:hi])
    if rep.check(bool(window), f"{label}: three-point apex found"):
        # Compare painted-line centres, not edges: antialiasing spreads an edge
        # by about a pixel either side but leaves the centre where it belongs.
        a, b = window[0]
        _near_ft(rep, ft(lo + (a + b) / 2.0 - origin) + spec.line_width / 2.0,
                 apex_ft, f"{label}: three-point apex (outer edge) from end line")


def verify(rep: Report, out_dir: Path, device: Device) -> None:
    _cross_checks(rep)
    for key in specs.ORDER:
        for region in REGION_LANDSCAPE:
            png = out_dir / "png" / f"{key}-{region}-court.png"
            if png.exists():
                _check_render(rep, png, specs.get(key), region, device)


__all__ = ["verify"]
