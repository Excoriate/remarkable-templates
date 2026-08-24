"""Basketball courts, drawn from the governing bodies' rule books.

Four rule sets — NBA, NCAA, FIBA and NFHS high school — each as a full court in
portrait and a half court in landscape.

Every template shows a complete, undistorted, true-scale region of the floor.
That rules out the two compromises court templates usually make: a full court
cropped at the page edge, and one squeezed lengthwise until both baskets fit. A
cropped court cannot diagram a press break; a squeezed one puts every distance
on it slightly wrong.
"""

from __future__ import annotations

from pathlib import Path

from rmtpl.devices import Device
from rmtpl.family import BuildOptions, BuiltTemplate, TemplateFamily
from rmtpl.vector import svg_to_pdf, svg_to_png

from . import checks as _checks
from . import specs
from .docgen import write_geometry_doc
from .geometry import build_svg, court_fit

#: Region -> (page orientation, display suffix).
#:
#: A full court belongs in portrait, where the long axis of the floor lines up
#: with the long axis of the page; a half court belongs in landscape, the shape
#: of every coaching board ever made. Each pairing shows its whole region at the
#: largest scale that does not crop it.
LAYOUTS: dict[str, tuple[bool, str]] = {
    "full": (False, "full court"),
    "half": (True, "half court"),
}


class BasketballFamily(TemplateFamily):
    key = "basketball"
    label = "Basketball"
    summary = "Rule-book court diagrams: NBA, NCAA, FIBA and high school."

    @property
    def variants(self) -> tuple[str, ...]:
        return specs.ORDER

    def build(self, out_dir: Path, device: Device,
              options: BuildOptions) -> list[BuiltTemplate]:
        rulesets = options.variants or specs.ORDER
        built: list[BuiltTemplate] = []
        for key in rulesets:
            spec = specs.get(key)
            for region, (landscape, suffix) in LAYOUTS.items():
                page = device.canvas(landscape)
                svg_text = build_svg(spec, region, page, device.ppi,
                                     options.style)
                stem = f"{key}-{region}-court"

                svg_path = out_dir / "svg" / f"{stem}.svg"
                svg_path.parent.mkdir(parents=True, exist_ok=True)
                svg_path.write_text(svg_text, encoding="utf-8")
                png_path = svg_to_png(svg_text, out_dir / "png" / f"{stem}.png",
                                      page)
                pdf_path = out_dir / "pdf" / f"{stem}.pdf"
                if options.want_pdf:
                    svg_to_pdf(svg_text, pdf_path)

                scale = court_fit(spec, region, page, options.style).scale
                built.append(BuiltTemplate(
                    stem=stem,
                    display=f"{spec.label} {suffix}",
                    landscape=landscape,
                    canvas=page,
                    png=png_path,
                    svg=svg_path,
                    pdf=pdf_path if options.want_pdf else None,
                    detail=f"{scale:6.3f} px/ft",
                ))
        return built

    def write_docs(self, docs_dir: Path) -> list[Path]:
        return [write_geometry_doc(docs_dir)]

    def verify(self, report, out_dir: Path, device: Device) -> None:
        _checks.verify(report, out_dir, device)


FAMILY = BasketballFamily()
