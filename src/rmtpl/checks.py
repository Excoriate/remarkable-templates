"""Verification over built artefacts.

Two kinds of check live here, and keeping them apart is the point.

*Contract checks* confirm the files satisfy what a reMarkable device requires:
exact canvas size, opaque 8-bit raster, PDF pages the size of the panel, and a
manifest that parses and points at files that exist. They are true of any
template, so they live in the toolkit.

*Family checks* are delegated. Each family measures its own finished artwork —
see :meth:`rmtpl.family.TemplateFamily.verify` — because only the family knows
what its drawings are supposed to mean.

The measurement helpers below are shared with families deliberately. Reading
pixels back out of a finished image is fiddly, and a family that re-implements
it tends to re-implement it wrongly; what a family must *not* share with its
drawing code is the expectation it compares against.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

from . import manifest, registry
from .devices import Device
from .vector import pdf_pages


class Report:
    """Collects check results. Non-zero failures mean a non-zero exit code."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.failures: list[str] = []
        self.checks = 0

    def section(self, title: str) -> None:
        if self.verbose:
            print(title)

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        self.checks += 1
        if not ok:
            self.failures.append(f"{label}: {detail}" if detail else label)
        if self.verbose:
            print(f"  [{'ok  ' if ok else 'FAIL'}] {label}"
                  + (f"   {detail}" if detail and not ok else ""))
        return ok

    def near(self, got: float, want: float, label: str, tol: float,
             unit: str = "", scale: float = 1.0) -> bool:
        """Compare two measurements, reporting the miss in readable units."""
        return self.check(
            abs(got - want) <= tol, label,
            f"measured {got:.4f}{unit}, expected {want:.4f}{unit} "
            f"(off by {(got - want) * scale:+.2f}, tolerance "
            f"{tol * scale:.2f})")


# --------------------------------------------------------------------------- #
# measurement helpers, shared with families
# --------------------------------------------------------------------------- #

def dark_mask(path: Path, threshold: int = 200) -> np.ndarray:
    """Boolean array of painted pixels, indexed ``[y, x]``."""
    return np.array(Image.open(path).convert("L")) < threshold


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Inclusive ``(start, end)`` spans of consecutive True values."""
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


def centres(profile: np.ndarray, span: int, coverage: float) -> list[float]:
    """Centres of runs where at least ``coverage`` of the other axis is dark."""
    return [(a + b) / 2.0 for a, b in runs(profile > span * coverage)]


def arc_ink(dark: np.ndarray, cx: float, cy: float, r: float,
            a0: float, a1: float, samples: int = 240, band: int = 3) -> float:
    """Fraction of an arc that is painted.

    Walks the arc in page pixels and, at each step, looks a couple of pixels
    either side along the radius so a sub-pixel wobble does not read as a gap.
    A solid arc comes back near 1.0; a broken one comes back near the
    painted:gap ratio it was drawn with. This is what makes a mirrored or
    missing arc fail the build instead of being noticed later by eye.
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
# contract checks
# --------------------------------------------------------------------------- #

def _device_matching(size: tuple[int, int]) -> str | None:
    """Which known device profile, if any, this raster is the right size for."""
    from .devices import DEVICES
    for d in DEVICES.values():
        if size in (d.portrait, d.landscape):
            return d.label
    return None


def check_raster(rep: Report, path: Path, canvas: tuple[int, int]) -> None:
    img = Image.open(path)
    detail = f"got {img.size}, want {canvas}"
    if img.size != canvas and (other := _device_matching(img.size)):
        # A set built for one device and checked against another is the common
        # cause, and the fix is a rebuild rather than a hunt.
        detail += (f" — this file is sized for {other}. Rebuild it for the "
                   f"device you are checking against.")
    rep.check(img.size == canvas, f"{path.name}: canvas size", detail)
    rep.check(img.mode in ("L", "RGB"), f"{path.name}: opaque raster",
              f"mode {img.mode} carries transparency")
    arr = np.array(img.convert("L"))
    corners = [int(arr[0, 0]), int(arr[0, -1]), int(arr[-1, 0]), int(arr[-1, -1])]
    rep.check(all(c >= 250 for c in corners), f"{path.name}: white page",
              f"corner values {corners}")


def check_pdfs(rep: Report, pdf_dir: Path, device: Device) -> None:
    """Every PDF page must be the panel's size, or the tablet rescales it."""
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        try:
            sizes = pdf_pages(pdf)
        except Exception as exc:                       # noqa: BLE001
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


def namespaces(root: Path) -> list[Path]:
    """Built template sets: any directory under ``root`` with a manifest."""
    if not root.is_dir():
        return []
    return sorted(d for d in root.iterdir()
                  if d.is_dir() and (d / manifest.MANIFEST_NAME).is_file())


# --------------------------------------------------------------------------- #

def run_checks(root: Path, device: Device, verbose: bool = True) -> int:
    rep = Report(verbose)

    rep.section("built template sets")
    sets = namespaces(root)
    rep.check(bool(sets), "at least one built template set",
              f"nothing with a {manifest.MANIFEST_NAME} under {root}")

    all_entries: list[dict] = []
    for ns_dir in sets:
        path = ns_dir / manifest.MANIFEST_NAME
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            rep.check(False, f"{ns_dir.name}: manifest parses as JSON", str(exc))
            continue
        problems = manifest.validate(data.get("templates", []))
        rep.check(not problems, f"{ns_dir.name}: manifest schema",
                  "; ".join(problems))
        all_entries.extend(data.get("templates", []))
        for entry in data.get("templates", []):
            stem = Path(entry["filename"]).name
            rep.check(entry["filename"].split("/")[0] == ns_dir.name,
                      f"{ns_dir.name}: {stem} is filed under its own namespace",
                      f"filename is {entry['filename']!r}")
            png = ns_dir / "png" / f"{stem}.png"
            if rep.check(png.exists(), f"{ns_dir.name}: {stem} has a PNG",
                         f"missing {png}"):
                check_raster(rep, png,
                             device.canvas(bool(entry.get("landscape"))))
        check_pdfs(rep, ns_dir / "pdf", device)

    dupes = [p for p in manifest.validate(all_entries) if p.startswith("duplicate")]
    rep.check(not dupes, "template names unique across sets", "; ".join(dupes))

    for family in registry.families().values():
        rep.section(f"{family.label}: family checks")
        family.verify(rep, root / family.key, device)

    print()
    if rep.failures:
        print(f"{len(rep.failures)} of {rep.checks} checks FAILED")
        for f in rep.failures:
            print(f"  - {f}")
        return 1
    print(f"all {rep.checks} checks passed")
    return 0
