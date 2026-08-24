"""Normalise arbitrary PNG artwork onto a reMarkable canvas.

This is the generic half of the toolkit: point it at a folder of PNGs of any
size and it produces templates the device will accept. A reMarkable template
must be an opaque raster the exact size of the canvas, so the work here is
resampling, flattening, and being explicit about what happens when the source
aspect ratio does not match the screen.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .devices import Device

#: How to reconcile a source image whose aspect ratio differs from the canvas.
FIT_MODES = ("fit", "cover", "stretch")


@dataclass(frozen=True)
class Ingested:
    source: Path
    out: Path
    landscape: bool
    src_size: tuple[int, int]
    out_size: tuple[int, int]
    scale: float
    mode: str
    letterboxed: bool


def slugify(name: str) -> str:
    """A filesystem- and JSON-safe stem, stable across platforms."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return re.sub(r"-{2,}", "-", text) or "template"


def titleise(stem: str) -> str:
    """A human display name from a file stem, leaving known acronyms alone."""
    words = re.split(r"[-_\s]+", stem)
    acronyms = {"nba", "ncaa", "fiba", "nfhs", "hs", "wnba", "us", "uk", "a4"}
    out = []
    for i, w in enumerate(words):
        if not w:
            continue
        if w.lower() in acronyms:
            out.append(w.upper() if w.lower() != "hs" else "High school")
        elif i == 0:
            out.append(w.capitalize())
        else:
            out.append(w.lower())
    return " ".join(out) or stem


def normalise(src: Path, out: Path, device: Device, *, landscape: bool | None = None,
              mode: str = "fit", background: str = "white",
              greyscale: bool = True) -> Ingested:
    """Resample ``src`` onto ``device``'s canvas and write an opaque PNG.

    ``landscape`` defaults to whatever the source image's own orientation
    implies, so a folder of mixed portrait and landscape art comes out right
    without per-file configuration.
    """
    if mode not in FIT_MODES:
        raise SystemExit(f"fit mode must be one of {FIT_MODES}, not {mode!r}")

    img = Image.open(src)
    src_size = img.size
    if landscape is None:
        landscape = src_size[0] > src_size[1]
    canvas = device.canvas(landscape)

    # Flatten any transparency onto the page colour before resampling, so
    # antialiased edges do not pick up a grey halo from premultiplied alpha.
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        flat = Image.new("RGBA", img.size, background)
        flat.alpha_composite(img)
        img = flat.convert("RGB")
    else:
        img = img.convert("RGB")

    sw, sh = img.size
    cw, ch = canvas
    letterboxed = False
    if mode == "stretch":
        placed = img.resize(canvas, Image.LANCZOS)
        scale = min(cw / sw, ch / sh)
    else:
        pick = min if mode == "fit" else max
        scale = pick(cw / sw, ch / sh)
        new = (max(1, round(sw * scale)), max(1, round(sh * scale)))
        resized = img.resize(new, Image.LANCZOS)
        placed = Image.new("RGB", canvas, background)
        ox, oy = (cw - new[0]) // 2, (ch - new[1]) // 2
        if mode == "fit":
            placed.paste(resized, (ox, oy))
            letterboxed = new != canvas
        else:
            placed.paste(resized, (min(ox, 0), min(oy, 0)))

    if greyscale:
        placed = placed.convert("L")
    out.parent.mkdir(parents=True, exist_ok=True)
    placed.save(out, format="PNG", optimize=True)
    return Ingested(src, out, landscape, src_size, canvas, scale, mode, letterboxed)
