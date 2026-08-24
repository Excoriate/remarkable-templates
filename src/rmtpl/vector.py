"""Rasterise, paginate and normalise SVG for reMarkable canvases.

Builds here are byte-reproducible: rebuild the repository from source and the
files should hash the same as the ones committed. That is only true because
PDFs get normalised — both cairo and Pillow stamp a creation time into every
PDF they write, which would otherwise make every rebuild a diff and make the
committed artefacts impossible to verify.
"""

from __future__ import annotations

import io
from pathlib import Path

import cairosvg
import pikepdf
from PIL import Image


def _deterministic_pdf(raw: bytes) -> bytes:
    """Strip timestamps and identifiers so the same drawing yields the same file."""
    with pikepdf.open(io.BytesIO(raw)) as pdf:
        with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
            meta.clear()
        if "/Info" in pdf.trailer:
            for key in list(pdf.trailer["/Info"].keys()):
                del pdf.trailer["/Info"][key]
        out = io.BytesIO()
        pdf.save(out, deterministic_id=True, compress_streams=True,
                 stream_decode_level=pikepdf.StreamDecodeLevel.generalized)
        return out.getvalue()


def svg_to_png(svg: str, out: Path, size: tuple[int, int],
               greyscale: bool = True) -> Path:
    """Render ``svg`` to an opaque PNG of exactly ``size`` device pixels.

    reMarkable templates want a white, fully opaque background and no alpha
    channel. cairosvg produces RGBA, so the result is flattened onto white and
    written as 8-bit greyscale unless ``greyscale`` is off.
    """
    width, height = size
    raw = cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        output_width=width,
        output_height=height,
        background_color="white",
    )
    with Image.open(io.BytesIO(raw)) as opened:
        img = opened.convert("L" if greyscale else "RGB")
    if img.size != (width, height):  # pragma: no cover - cairosvg is exact
        img = img.resize((width, height), Image.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG", optimize=True)
    return out


def svg_to_pdf(svg: str, out: Path) -> Path:
    """Render ``svg`` to a single-page PDF at the page size the SVG declares."""
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = cairosvg.svg2pdf(bytestring=svg.encode("utf-8"))
    out.write_bytes(_deterministic_pdf(raw))
    return out


def png_to_pdf(pngs: list[Path], out: Path, page_pt: tuple[float, float]) -> Path:
    """Pack rasters into a multi-page PDF sized in points, one image per page."""
    if not pngs:
        raise ValueError("no pages to write")
    w_pt, h_pt = page_pt
    pages = []
    for p in pngs:
        with Image.open(p) as opened:
            pages.append(opened.convert("RGB"))
    first, rest = pages[0], pages[1:]
    dpi = min(first.size[0] / (w_pt / 72.0), first.size[1] / (h_pt / 72.0))
    buf = io.BytesIO()
    first.save(buf, "PDF", resolution=dpi, save_all=True, append_images=rest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(_deterministic_pdf(buf.getvalue()))
    return out


def pdf_pages(path: Path) -> list[tuple[float, float]]:
    """Page sizes in points, for verification."""
    with pikepdf.open(path) as pdf:
        sizes = []
        for page in pdf.pages:
            box = [float(v) for v in page.mediabox]
            sizes.append((round(box[2] - box[0], 2), round(box[3] - box[1], 2)))
        return sizes
