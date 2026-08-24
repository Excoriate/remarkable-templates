"""Build the court template set from the rule-book specs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rmtpl import icons
from rmtpl.devices import Device
from rmtpl.manifest import NAMESPACE, TemplateEntry
from rmtpl.vector import svg_to_pdf, svg_to_png

from . import specs
from .geometry import DEFAULT_STYLE, Style, build_svg, fit_region

#: Region -> (page orientation, display suffix).
#:
#: A full court belongs in portrait, where the long axis of the floor lines up
#: with the long axis of the page; a half court belongs in landscape, which is
#: the shape of every coaching board ever made. Each pairing is the one that
#: shows the whole region at the largest possible scale without cropping it.
LAYOUTS: dict[str, tuple[bool, str]] = {
    "full": (False, "full court"),
    "half": (True, "half court"),
}


@dataclass(frozen=True)
class Built:
    key: str
    region: str
    stem: str
    display: str
    landscape: bool
    png: Path
    svg: Path
    pdf: Path
    scale_px_per_ft: float
    canvas: tuple[int, int]


def build(out_root: Path, device: Device, *, style: Style = DEFAULT_STYLE,
          rulesets: tuple[str, ...] = specs.ORDER,
          categories: tuple[str, ...] = ("Basketball",),
          blank_icons: bool = False,
          want_pdf: bool = True) -> tuple[list[Built], list[TemplateEntry]]:
    built: list[Built] = []
    entries: list[TemplateEntry] = []
    index = 0
    for key in rulesets:
        spec = specs.get(key)
        for region, (landscape, suffix) in LAYOUTS.items():
            page = device.canvas(landscape)
            svg_text = build_svg(spec, region, page, device.ppi, style)
            stem = f"{key}-{region}-court"
            display = f"{spec.label} {suffix}"

            svg_path = out_root / "svg" / f"{stem}.svg"
            svg_path.parent.mkdir(parents=True, exist_ok=True)
            svg_path.write_text(svg_text, encoding="utf-8")

            png_path = svg_to_png(svg_text, out_root / "png" / f"{stem}.png", page)
            pdf_path = out_root / "pdf" / f"{stem}.pdf"
            if want_pdf:
                svg_to_pdf(svg_text, pdf_path)

            entries.append(TemplateEntry(
                name=display,
                filename=f"{NAMESPACE}/{stem}",
                icon_code=icons.pick(index, landscape, blank_only=blank_icons),
                landscape=landscape,
                categories=list(categories),
            ))
            built.append(Built(
                key=key, region=region, stem=stem, display=display,
                landscape=landscape, png=png_path, svg=svg_path, pdf=pdf_path,
                scale_px_per_ft=fit_region(spec, region, page, style).scale,
                canvas=page,
            ))
            index += 1
    return built, entries
