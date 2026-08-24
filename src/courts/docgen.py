"""Generate docs/court-geometry.md from the specs themselves.

The documentation is generated rather than written so it cannot drift away from
the numbers the courts are actually drawn with. If you change a dimension, run
``just docs`` and the table changes with it.
"""

from __future__ import annotations

import math
from pathlib import Path

from . import specs
from .specs import CourtSpec, Edge

M_PER_FT = 0.3048


def _fmt(value: float, unit: str) -> str:
    """Format a length in the unit its rule book uses."""
    if unit == "m":
        return f"{value * M_PER_FT:.3f} m"
    feet = int(value)
    inches = (value - feet) * 12.0
    exact = abs(inches - round(inches)) < 0.005
    if abs(inches) < 0.005:
        return f"{feet}'"
    shown = f"{round(inches)}" if exact else f"{inches:.2f}"
    return f'{shown}"' if feet == 0 else f"{feet}'{shown}\""


def _rows(s: CourtSpec) -> list[tuple[str, str, str]]:
    u = s.native_unit
    f = lambda v: _fmt(v, u)                                   # noqa: E731
    junction = (s.basket_centre if s.three_corner_tangent_at_basket
                else s.basket_centre + math.sqrt(
                    s.three_radius ** 2 - s.three_corner_x ** 2))
    edge = lambda e: {  # noqa: E731
        Edge.OUTER: "outer edge",
        Edge.INNER: "inner edge",
        Edge.CENTRE: "line centre",
    }[e]
    rows = [
        ("Playing surface", f"{f(s.length)} x {f(s.width)}",
         "inside the boundary lines"),
        ("Line width", f(s.line_width), "all markings"),
        ("Division line", f(s.half_length), "from either end line"),
        ("Centre circle radius", f(s.centre_circle_radius),
         edge(s.centre_circle_edge)),
    ]
    if s.inner_circle_radius is not None:
        rows.append(("Inner circle radius", f(s.inner_circle_radius), "inner edge"))
    rows += [
        ("Free-throw lane width", f(s.lane_width),
         "outer edge to outer edge"),
        ("Free-throw line", f(s.lane_length),
         "end line to the far edge of the line"),
        ("Free-throw circle radius", f(s.ft_circle_radius),
         edge(s.ft_circle_edge)),
        ("Backboard face", f(s.backboard_face), "from the end line"),
        ("Basket centre", f(s.basket_centre),
         "from the end line; the point the arcs are struck from"),
        ("Ring radius", f(s.rim_radius), "inside the ring"),
        ("Three-point radius", f(s.three_radius),
         f"{edge(s.three_edge)}, from the basket centre"),
        ("Three-point corner line", f(s.three_corner_x),
         f"{edge(s.three_corner_edge)}, from the court centre line "
         f"({f(s.three_corner_from_sideline)} from the sideline)"),
        ("Arc meets corner line at", f(junction),
         "from the end line; **derived** so the two close cleanly"),
    ]
    if s.restricted_radius is not None:
        rows.append(("Restricted-area radius", f(s.restricted_radius),
                     f"{edge(s.restricted_edge)}, from the basket centre"))
    else:
        rows.append(("Restricted-area arc", "none",
                     "this code does not define one"))
    for i, (hy, hlen, inward) in enumerate(s.sideline_hashes):
        where = "onto the court" if inward else "outside the sideline"
        rows.append((f"Sideline mark {i + 1}", f(hy),
                     f"from the end line, {f(hlen)} {where}"))
    return rows


def render() -> str:
    out: list[str] = [
        "# Court geometry",
        "",
        "*Generated from `src/courts/specs.py` by `just docs`. Do not edit by "
        "hand: change the spec and regenerate, so the documentation and the "
        "drawings cannot disagree.*",
        "",
        "Every figure below is the one used to draw the templates. Rule books "
        "dimension a marking to a particular **edge** of the painted line, "
        "never to its centre, so the edge is recorded next to each value and "
        "resolved once, in `to_path()`.",
        "",
        "Where a rule book publishes a figure that is not quite consistent "
        "with its own diagram, the caveats say which one this project holds "
        "and why.",
        "",
    ]
    for key in specs.ORDER:
        s = specs.get(key)
        out += [
            f"## {s.label}",
            "",
            f"**{s.body}** — {s.edition}",
            "",
            "| Dimension | Value | Measured |",
            "| --- | --- | --- |",
        ]
        for name, value, note in _rows(s):
            out.append(f"| {name} | {value} | {note} |")
        out.append("")
        if s.lane_marks:
            out += [
                "Lane markings (from the end line, along the lane line):",
                "",
                "| Mark | Starts at | Length | Depth |",
                "| --- | --- | --- | --- |",
            ]
            for mk in s.lane_marks:
                kind = "neutral zone" if mk.filled else "lane-space mark"
                out.append(f"| {kind} | {_fmt(mk.near, s.native_unit)} | "
                           f"{_fmt(mk.length, s.native_unit)} | "
                           f"{_fmt(mk.depth, s.native_unit)} |")
            out.append("")
        out += ["**Sources**", ""]
        for label, url in s.sources.items():
            out.append(f"- {label}: <{url}>")
        out.append("")
        if s.caveats:
            out += ["**What to know**", ""]
            for c in s.caveats:
                out.append(f"- {c}")
            out.append("")
    out += [
        "## What is not published anywhere",
        "",
        "Every rule book here gives the **size** of a free-throw lane-space "
        "mark and then defers its **position** to a court diagram printed as "
        "artwork. The NBA's diagram has no leader-line geometry in its text "
        "layer; the NFHS diagram has no text layer at all. The positions this "
        "project draws therefore come from standard court-marking practice, "
        "and were cross-checked against measurements taken from an "
        "independently drawn court set. They are good to roughly an inch. "
        "Nothing else in the tables above depends on them.",
        "",
    ]
    return "\n".join(out) + "\n"


def write_geometry_doc(docs_dir: Path) -> Path:
    docs_dir.mkdir(parents=True, exist_ok=True)
    path = docs_dir / "court-geometry.md"
    path.write_text(render(), encoding="utf-8")
    return path
