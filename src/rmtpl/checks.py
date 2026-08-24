"""Verification pass over built artefacts.

Three kinds of check live here, and keeping them apart is the point.

*Contract checks* confirm the files satisfy what a reMarkable device requires:
exact canvas size, opaque 8-bit raster, a manifest that parses and points at
files that exist.

*Render checks* re-measure the finished rasters and express what they find in
**feet**, using a scale derived from the image itself rather than from the
drawing code. Nothing in this section imports ``courts.geometry``: it converts
pixels back into feet with its own arithmetic and compares the result with the
published rule-book figures. A mistake in the edge conventions, the page fit or
the mirroring of the far end therefore shows up as a disagreement measured in
inches, instead of moving the drawing and the expectation together.

*Spec cross-checks* are the only thing here that can catch a wrong rule-book
number, and they work by playing published figures off against each other. The
NBA rule book states separately that the backboard stands 4'0" from the end
line, that the ring's near edge is 6" from the board, and that the ring is 18"
across; those three must reconstruct the 5'3" basket centre that the
three-point arc is struck from. Re-measuring a drawing can never establish
that. Agreement between independent statements can.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

from courts import specs as court_specs
from courts.specs import CourtSpec, Edge, inch, m

from . import manifest
from .devices import Device
from .vector import pdf_pages

#: Agreement required between drawing and rule book. One inch is about two
#: pixels at Paper Pro density, so this is a genuinely tight bound.
TOLERANCE_FT = inch(1.5)

#: Region -> is the page landscape. Duplicated from courts.build on purpose:
#: the checker is meant to share as little as possible with the build.
REGION_LANDSCAPE = {"full": False, "half": True}


class Report:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.failures: list[str] = []
        self.checks = 0

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        self.checks += 1
        if not ok:
            self.failures.append(f"{label}: {detail}" if detail else label)
        if self.verbose:
            print(f"  [{'ok  ' if ok else 'FAIL'}] {label}"
                  + (f"   {detail}" if detail and not ok else ""))
        return ok

    def near_ft(self, got: float, want: float, label: str,
                tol: float = TOLERANCE_FT) -> bool:
        return self.check(
            abs(got - want) <= tol, label,
            f"measured {got:.4f} ft, rule book {want:.4f} ft "
            f"(off by {(got - want) * 12:+.2f} in, tolerance "
            f"{tol * 12:.2f} in)")

    def near_px(self, got: float, want: float, label: str,
                tol: float = 1.5) -> bool:
        return self.check(
            abs(got - want) <= tol, label,
            f"measured {got:.2f} px, expected {want:.2f} px "
            f"(off by {got - want:+.2f}, tolerance {tol})")


# --------------------------------------------------------------------------- #
# pixel measurement
# --------------------------------------------------------------------------- #

def _dark(path: Path, threshold: int = 200) -> np.ndarray:
    return np.array(Image.open(path).convert("L")) < threshold


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            out.append((i, j - 1))
            i = j
        else:
            i += 1
    return out


def _centres(profile: np.ndarray, span: int, coverage: float) -> list[float]:
    return [(a + b) / 2.0 for a, b in _runs(profile > span * coverage)]


def _arc_ink(dark: np.ndarray, cx: float, cy: float, r: float,
             a0: float, a1: float, samples: int = 240, band: int = 3) -> float:
    """Fraction of an arc that is painted.

    Walks the arc in page pixels and, at each step, looks a couple of pixels
    either side along the radius so a sub-pixel wobble does not read as a gap.
    A solid arc comes back near 1.0; the broken half of a free-throw circle
    comes back near the painted:gap ratio it was drawn with.
    """
    h, w = dark.shape
    hits = 0
    for i in range(samples):
        a = a0 + (a1 - a0) * i / (samples - 1)
        ca, sa = math.cos(a), math.sin(a)
        for d in range(-band, band + 1):
            x = int(round(cx + (r + d) * ca))
            y = int(round(cy + (r + d) * sa))
            if 0 <= x < w and 0 <= y < h and dark[y, x]:
                hits += 1
                break
    return hits / samples


# --------------------------------------------------------------------------- #
# render checks
# --------------------------------------------------------------------------- #

def _check_render(rep: Report, path: Path, spec: CourtSpec, region: str,
                  device: Device) -> None:
    label = path.name
    dark = _dark(path)
    h, w = dark.shape
    canvas = device.canvas(REGION_LANDSCAPE[region])
    if not rep.check((w, h) == canvas, f"{label}: canvas", f"{(w, h)} != {canvas}"):
        return

    verticals = _centres(dark.sum(axis=0), h, 0.55)
    horizontals = _centres(dark.sum(axis=1), w, 0.55)
    if not rep.check(len(verticals) >= 2 and len(horizontals) >= 2,
                     f"{label}: boundary lines found",
                     f"{len(verticals)} verticals, {len(horizontals)} horizontals"):
        return

    left, right = verticals[0], verticals[-1]

    # Scale comes from the picture, not from the build. The two sideline paths
    # are one boundary-line width further apart than the playing surface.
    scale = (right - left) / (spec.width + spec.boundary_line_width)
    ft = lambda px: px / scale                                   # noqa: E731

    # Centring is a page-layout property, so it is checked in pixels, against
    # arithmetic written here rather than imported.
    rep.near_px((left + right) / 2.0, w / 2.0, f"{label}: court centred on page")

    # The end line's painted centre sits half a boundary width outside the
    # floor, so the floor's origin is that much further into the page.
    end_line = horizontals[0]
    origin = end_line + spec.boundary_line_width / 2.0 * scale

    rep.near_ft(ft(right - left) - spec.boundary_line_width, spec.width,
                f"{label}: floor width")

    div = [r for r in horizontals if abs(ft(r - origin) - spec.half_length) < 1.5]
    if rep.check(bool(div), f"{label}: division line found"):
        rep.near_ft(ft(div[0] - origin), spec.half_length,
                    f"{label}: division line from end line")

    if region == "full":
        far = horizontals[-1]
        rep.near_ft(ft(far - origin) - spec.boundary_line_width / 2.0,
                    spec.length, f"{label}: court length")

    # free-throw line: the full-width row inside the lane
    lane_half_px = (spec.lane_width / 2.0 - spec.line_width) * scale
    cx = (left + right) / 2.0
    x0, x1 = int(cx - lane_half_px), int(cx + lane_half_px)
    band = dark[:, x0:x1]
    lane_rows = _centres(band.sum(axis=1), x1 - x0, 0.94)
    want = spec.lane_length - spec.line_width / 2.0
    hit = [r for r in lane_rows if abs(ft(r - origin) - want) < 1.0]
    if rep.check(bool(hit), f"{label}: free-throw line found"):
        rep.near_ft(ft(hit[0] - origin) + spec.line_width / 2.0, spec.lane_length,
                    f"{label}: free-throw line (outer edge) from end line")

    # lane width, measured between the two long verticals flanking the centre
    lane_cands = [v for v in _centres(dark.sum(axis=0), h, 0.18)
                  if 0 < abs(v - cx) < lane_half_px * 1.6]
    pair = sorted(lane_cands, key=lambda v: abs(abs(v - cx) - lane_half_px))[:2]
    if rep.check(len(pair) == 2, f"{label}: lane lines found"):
        rep.near_ft(ft(abs(pair[0] - pair[1])) + spec.line_width, spec.lane_width,
                    f"{label}: lane width (outer to outer)")

    # The free-throw circle: solid away from the basket, broken inside the
    # lane. Getting these two halves the wrong way round at the far end of a
    # full court is invisible to any check that only measures positions, so
    # ink coverage is measured along each half separately.
    ends = [(0.0, 1.0)] + ([(spec.length, -1.0)] if region == "full" else [])
    for base, direction in ends:
        cy = origin + (base + direction * (spec.lane_length
                                           - spec.line_width / 2.0)) * scale
        r_px = (spec.ft_circle_radius - spec.line_width / 2.0) * scale
        away = _arc_ink(dark, cx, cy, r_px, 0.0, math.pi * direction)
        into = _arc_ink(dark, cx, cy, r_px, math.pi * direction,
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
            stray = _arc_ink(dark, cx, cy, 4.0 * scale, 0.0, math.pi * direction)
            rep.check(stray < 0.25,
                      f"{label}: {end_name} end has no restricted arc, as the "
                      f"rules require", f"{stray:.0%} of that arc is painted")
            continue
        rr = spec.restricted_radius + (
            spec.line_width / 2.0 if spec.restricted_edge is Edge.INNER
            else -spec.line_width / 2.0)
        ink = _arc_ink(dark, cx, cy, rr * scale, 0.0, math.pi * direction)
        rep.check(ink > 0.90, f"{label}: {end_name} restricted-area arc drawn",
                  f"only {ink:.0%} of the arc is painted")

    # three-point apex on the court centre line
    col = dark[:, int(round(cx))]
    apex_ft = spec.basket_centre + spec.three_radius
    lo = int(origin + (apex_ft - 1.0) * scale)
    hi = int(min(h, origin + (apex_ft + 1.0) * scale))
    window = _runs(col[lo:hi])
    if rep.check(bool(window), f"{label}: three-point apex found"):
        # Compare painted-line centres, not edges: antialiasing spreads an edge
        # by about a pixel either side but leaves the centre where it belongs.
        a, b = window[0]
        centre = lo + (a + b) / 2.0
        rep.near_ft(ft(centre - origin) + spec.line_width / 2.0, apex_ft,
                    f"{label}: three-point apex (outer edge) from end line")


# --------------------------------------------------------------------------- #
# spec cross-checks
# --------------------------------------------------------------------------- #

def _spec_crosschecks(rep: Report) -> None:
    """Play independently published rule-book figures off against each other."""
    tol = inch(0.5)

    for key in ("nba", "ncaa", "nfhs"):
        s = court_specs.get(key)
        rebuilt = s.backboard_face + inch(6) + s.rim_radius
        rep.check(abs(rebuilt - s.basket_centre) <= tol,
                  f"{key}: basket centre reconstructs from board + ring",
                  f"4'0\" + 6\" + 9\" = {rebuilt:.4f} ft "
                  f"vs stated {s.basket_centre:.4f} ft")
        rep.check(abs((s.backboard_face + 15.0) - s.lane_length) <= tol,
                  f"{key}: free-throw line 15' from the backboard face",
                  f"{s.backboard_face + 15.0:.4f} vs {s.lane_length:.4f} ft")
        rep.check(abs(s.line_width - inch(2)) <= 1e-9, f"{key}: 2-inch lines")

    nba = court_specs.NBA
    rep.check(abs(nba.three_corner_from_sideline - 3.0) <= tol,
              "nba: corner three 3'0\" from the sideline",
              f"{nba.three_corner_from_sideline:.4f} ft")
    rep.check(abs(nba.length - 94.0) < 1e-9 and abs(nba.width - 50.0) < 1e-9,
              "nba: 94 x 50 floor")

    nfhs = court_specs.NFHS
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

    fiba = court_specs.FIBA
    reconstructed = fiba.backboard_face + m(0.151) + m(0.2275)
    rep.check(abs(reconstructed - fiba.basket_centre) <= m(0.005),
              "fiba: basket centre reconstructs from board + ring offsets",
              f"1.200 + 0.151 + 0.2275 = {reconstructed * 0.3048:.4f} m vs "
              f"stated {fiba.basket_centre * 0.3048:.4f} m")
    rep.check(abs(fiba.three_corner_from_sideline - m(0.90)) <= m(0.005),
              "fiba: corner three 0.90 m from the sideline",
              f"{fiba.three_corner_from_sideline * 0.3048:.4f} m")
    rep.check(abs(fiba.line_width - m(0.05)) <= 1e-9, "fiba: 5 cm lines")

    ncaa = court_specs.NCAA
    rep.check(abs(ncaa.three_radius - court_specs.FIBA.three_radius) <= inch(0.25),
              "ncaa: three-point radius matches the FIBA distance it adopted",
              f"{ncaa.three_radius:.4f} vs {court_specs.FIBA.three_radius:.4f} ft")

    for key in court_specs.ORDER:
        s = court_specs.get(key)
        rep.check(s.three_radius >= s.three_corner_x,
                  f"{key}: three-point arc reaches its corner segments")
        if not s.three_corner_tangent_at_basket:
            junction = s.basket_centre + math.sqrt(
                s.three_radius ** 2 - s.three_corner_x ** 2)
            rep.check(0 < junction < s.half_length,
                      f"{key}: arc/corner junction lands on the floor",
                      f"{junction:.4f} ft")


# --------------------------------------------------------------------------- #

def _check_raster(rep: Report, path: Path, canvas: tuple[int, int]) -> None:
    img = Image.open(path)
    rep.check(img.size == canvas, f"{path.name}: canvas size",
              f"got {img.size}, want {canvas}")
    rep.check(img.mode in ("L", "RGB"), f"{path.name}: opaque raster",
              f"mode {img.mode} carries transparency")
    arr = np.array(img.convert("L"))
    corners = [int(arr[0, 0]), int(arr[0, -1]), int(arr[-1, 0]), int(arr[-1, -1])]
    rep.check(all(c >= 250 for c in corners), f"{path.name}: white page",
              f"corner values {corners}")


def _check_pdfs(rep: Report, out: Path, device: Device) -> None:
    """Every PDF page must be the panel's size, or the tablet rescales it."""
    for pdf in sorted((out / "pdf").glob("*.pdf")):
        try:
            sizes = pdf_pages(pdf)
        except Exception as exc:                      # noqa: BLE001
            rep.check(False, f"{pdf.name}: opens as a PDF", str(exc))
            continue
        if not rep.check(bool(sizes), f"{pdf.name}: has pages"):
            continue
        landscape = sizes[0][0] > sizes[0][1]
        want = tuple(round(v, 2) for v in device.page_pt(landscape))
        ok = all(abs(a - b) <= 0.1
                 for s in sizes for a, b in zip(s, want, strict=True))
        rep.check(ok, f"{pdf.name}: pages are the panel size",
                  f"got {sorted(set(sizes))}, want {want}")


def run_checks(out: Path, device: Device, verbose: bool = True) -> int:
    rep = Report(verbose)

    if verbose:
        print("rule-book cross-checks")
    _spec_crosschecks(rep)

    if verbose:
        print("manifest and raster contract")
    frags = sorted((out / "templates.d").glob("*.json"))
    rep.check(bool(frags), "manifest fragments exist",
              f"none under {out / 'templates.d'}")
    all_entries: list[dict] = []
    for frag in frags:
        try:
            data = json.loads(frag.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            rep.check(False, f"{frag.name}: parses as JSON", str(exc))
            continue
        problems = manifest.validate(data["templates"])
        rep.check(not problems, f"{frag.name}: schema", "; ".join(problems))
        all_entries.extend(data["templates"])
        for entry in data["templates"]:
            stem = Path(entry["filename"]).name
            png = out / "png" / f"{stem}.png"
            if rep.check(png.exists(), f"{frag.name}: {stem} has a PNG",
                         f"missing {png}"):
                _check_raster(rep, png,
                              device.canvas(bool(entry.get("landscape"))))

    dupes = [p for p in manifest.validate(all_entries) if p.startswith("duplicate")]
    rep.check(not dupes, "template names unique across fragments", "; ".join(dupes))
    _check_pdfs(rep, out, device)

    if verbose:
        print("rendered geometry, measured back out of the pixels")
    for key in court_specs.ORDER:
        for region in REGION_LANDSCAPE:
            png = out / "png" / f"{key}-{region}-court.png"
            if png.exists():
                _check_render(rep, png, court_specs.get(key), region, device)

    print()
    if rep.failures:
        print(f"{len(rep.failures)} of {rep.checks} checks FAILED")
        for f in rep.failures:
            print(f"  - {f}")
        return 1
    print(f"all {rep.checks} checks passed")
    return 0
