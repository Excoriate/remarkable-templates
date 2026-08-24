"""Normalise arbitrary PNG artwork onto a reMarkable canvas.

This is the generic half of the toolkit: point it at a folder of PNGs of any
size and it produces templates the device will accept. A reMarkable template
must be an opaque raster the exact size of the canvas, so the work here is
resampling, flattening, and being explicit about what happens when the source
aspect ratio does not match the screen.
"""

from __future__ import annotations

import hashlib
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


#: Stems are restricted to this so they are safe as a filename, as a JSON
#: value, and as a word in a remote shell command during install.
SAFE_STEM = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def slugify(name: str) -> str:
    """A filesystem- and JSON-safe stem, stable across platforms.

    Transliteration to ASCII loses information, and a name written entirely in
    a non-Latin script can lose all of it. Rather than collapse those to a
    shared placeholder — which silently overwrites one template with another —
    a stem that would otherwise be empty gets a short digest of the original,
    so distinct inputs stay distinct.
    """
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    text = re.sub(r"-{2,}", "-", text)
    if not text:
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
        return f"template-{digest}" if name else "template"
    return text


def unique_slugs(names: list[str]) -> list[str]:
    """Slugs for ``names``, disambiguated so no two collide.

    Two different source files can slugify to the same stem — ``Court 1.png``
    and ``court-1.png``, say. Without this, the second silently overwrites the
    first and the manifest points two entries at one image.
    """
    out: list[str] = []
    seen: dict[str, int] = {}
    for name in names:
        stem = slugify(name)
        if stem in seen:
            seen[stem] += 1
            stem = f"{stem}-{seen[stem]}"
        else:
            seen[stem] = 1
        out.append(stem)
    return out


#: Words the generic titler leaves in capitals. Deliberately generic: a
#: subject's own vocabulary belongs to its family, not to the toolkit. Pass
#: ``acronyms=`` to extend it for one call.
DEFAULT_ACRONYMS = frozenset({"us", "uk", "eu", "a3", "a4", "a5", "pdf", "svg"})


def titleise(stem: str, acronyms: frozenset[str] | None = None) -> str:
    """A human display name from a file stem, leaving known acronyms alone."""
    known = DEFAULT_ACRONYMS if acronyms is None else acronyms
    out = []
    for i, w in enumerate(re.split(r"[-_\s]+", stem)):
        if not w:
            continue
        if w.lower() in known:
            out.append(w.upper())
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

    with Image.open(src) as opened:
        img = opened.copy()
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
