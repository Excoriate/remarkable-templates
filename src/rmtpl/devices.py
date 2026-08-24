"""reMarkable device canvas profiles.

Every number here is a *verified* device specification, not a guess. Sources are
recorded next to each profile; see docs/template-format.md for the full audit of
what is verified, what is inferred, and what remains unknown.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    """A reMarkable screen, described in portrait orientation.

    ``width``/``height`` are the portrait canvas in device pixels. A landscape
    template is the same canvas rotated a quarter turn, so its raster is
    ``height x width``.
    """

    key: str
    label: str
    width: int          # portrait canvas width, px
    height: int         # portrait canvas height, px
    ppi: float          # pixels per inch of the physical panel
    source: str         # where width/height/ppi came from

    # ------------------------------------------------------------------ #
    @property
    def portrait(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def landscape(self) -> tuple[int, int]:
        return (self.height, self.width)

    def canvas(self, landscape: bool) -> tuple[int, int]:
        return self.landscape if landscape else self.portrait

    @property
    def pt_per_px(self) -> float:
        """PDF points per device pixel (1 pt = 1/72 in)."""
        return 72.0 / self.ppi

    def page_pt(self, landscape: bool) -> tuple[float, float]:
        w, h = self.canvas(landscape)
        return (w * self.pt_per_px, h * self.pt_per_px)


#: reMarkable Paper Pro. 11.8", 2160 x 1620, 229 PPI.
#: Verified against reMarkable's own product comparison page.
PAPER_PRO = Device(
    key="rmpp",
    label="reMarkable Paper Pro",
    width=1620,
    height=2160,
    ppi=229.0,
    source="https://remarkable.com/products/remarkable-paper/pro/details/compare",
)

#: reMarkable 1 and 2. 10.3", 1404 x 1872, 226 PPI.
RM2 = Device(
    key="rm2",
    label="reMarkable 1 / 2",
    width=1404,
    height=1872,
    ppi=226.0,
    source="https://remarkable.jms1.info/templates/",
)

#: reMarkable Paper Pro Move. 7.3", 1696 x 954, 264 PPI.
PAPER_PRO_MOVE = Device(
    key="rmppm",
    label="reMarkable Paper Pro Move",
    width=954,
    height=1696,
    ppi=264.0,
    source="https://remarkable.com/products/remarkable-paper/pro/details/compare",
)

DEVICES: dict[str, Device] = {d.key: d for d in (PAPER_PRO, RM2, PAPER_PRO_MOVE)}
DEFAULT_DEVICE = PAPER_PRO


def get(key: str) -> Device:
    try:
        return DEVICES[key]
    except KeyError:
        raise SystemExit(
            f"unknown device {key!r}; choose one of: {', '.join(sorted(DEVICES))}"
        ) from None


#: Width in device pixels of the collapsed-but-present left toolbar strip on the
#: writing surface. Content underneath is reachable, but a template that puts
#: fine detail here invites stray marks. Reported for firmware 3.5 on rM2; the
#: Paper Pro strip is proportionally similar. Treat as advisory, not exact.
TOOLBAR_STRIP_PX = 104
