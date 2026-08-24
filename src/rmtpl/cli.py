"""Command line entry point: ``python -m rmtpl <command>``.

The Justfile wraps these, but every recipe is a thin shell over one of these
sub-commands, so the toolkit works with or without ``just`` installed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

from courts import specs as court_specs
from courts.build import build as build_courts
from courts.geometry import DEFAULT_STYLE, Style

from . import devices, icons, manifest, raster
from .vector import png_to_pdf

REPO = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _style(args: argparse.Namespace) -> Style:
    return Style(
        ink=args.ink,
        ink_soft=args.ink_soft,
        line_scale=args.line_scale,
        margin_px=args.margin,
    )


def _write_manifest(path: Path, entries: list[manifest.TemplateEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.dumps(entries), encoding="utf-8")


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #

def cmd_courts(args: argparse.Namespace) -> int:
    device = devices.get(args.device)
    out = Path(args.out)
    if args.clean and out.exists():
        for sub in ("png", "svg", "pdf"):
            shutil.rmtree(out / sub, ignore_errors=True)
    rulesets = tuple(args.rulesets.split(",")) if args.rulesets else court_specs.ORDER
    for key in rulesets:
        court_specs.get(key)  # fail fast on a typo
    built, entries = build_courts(
        out, device, style=_style(args), rulesets=rulesets,
        categories=tuple(args.categories.split(",")),
        blank_icons=args.blank_icons, want_pdf=not args.no_pdf,
    )
    _write_manifest(out / "templates.d" / "basketball.json", entries)
    for b in built:
        print(f"  {b.stem:24s} {b.canvas[0]}x{b.canvas[1]}  "
              f"{b.scale_px_per_ft:6.3f} px/ft  {b.display}")
    print(f"built {len(built)} court templates for {device.label} -> {out}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Turn any folder of PNGs into a template set. The generic path."""
    device = devices.get(args.device)
    src = Path(args.source).expanduser()
    if not src.is_dir():
        print(f"not a directory: {src}", file=sys.stderr)
        return 2
    out = Path(args.out)
    namespace = args.namespace
    pngs = sorted(p for p in src.iterdir()
                  if p.suffix.lower() == ".png" and not p.name.startswith("."))
    if not pngs:
        print(f"no PNG files in {src}", file=sys.stderr)
        return 2

    entries: list[manifest.TemplateEntry] = []
    results = []
    counter = {False: 0, True: 0}   # a separate icon cycle per orientation
    for png in pngs:
        label = png.stem
        if args.strip and label.lower().startswith(args.strip.lower()):
            label = label[len(args.strip):]
        stem = raster.slugify(label)
        res = raster.normalise(png, out / "png" / f"{stem}.png", device,
                               mode=args.fit)
        results.append(res)
        entries.append(manifest.TemplateEntry(
            name=args.prefix + raster.titleise(label),
            filename=f"{namespace}/{stem}",
            icon_code=icons.pick(counter[res.landscape], res.landscape,
                                 blank_only=args.blank_icons),
            landscape=res.landscape,
            categories=list(args.categories.split(",")),
        ))
        counter[res.landscape] += 1
        flag = "  LETTERBOXED" if res.letterboxed else ""
        print(f"  {png.name:34s} {res.src_size[0]}x{res.src_size[1]}"
              f" -> {res.out_size[0]}x{res.out_size[1]}"
              f"  x{res.scale:.4f}{flag}")

    _write_manifest(out / "templates.d" / f"{namespace}.json", entries)
    if not args.no_pdf:
        for res, entry in zip(results, entries, strict=True):
            page = device.page_pt(res.landscape)
            png_to_pdf([res.out], out / "pdf" / f"{Path(entry.filename).name}.pdf",
                       page)
    letterboxed = sum(1 for r in results if r.letterboxed)
    print(f"ingested {len(results)} template(s) for {device.label} -> {out}")
    if letterboxed:
        print(f"note: {letterboxed} source image(s) did not match the "
              f"{device.label} aspect ratio and were letterboxed onto white; "
              f"use --fit cover to crop instead, or --fit stretch to distort.")
    return 0


def cmd_bundle(args: argparse.Namespace) -> int:
    """One multi-page PDF per orientation, for the no-developer-mode route."""
    device = devices.get(args.device)
    out = Path(args.out)
    pngs = sorted((out / "png").glob("*.png"))
    if not pngs:
        print(f"no built PNGs under {out / 'png'}; build first", file=sys.stderr)
        return 2
    made = []
    for landscape, label in ((False, "portrait"), (True, "landscape")):
        canvas = device.canvas(landscape)
        pages = [p for p in pngs if Image.open(p).size == canvas]
        pages = [p for p in pages for _ in range(args.copies)]
        if not pages:
            continue
        target = out / "pdf" / f"{args.name}-{label}.pdf"
        png_to_pdf(pages, target, device.page_pt(landscape))
        made.append((target, len(pages)))
    for target, n in made:
        print(f"  {target.relative_to(REPO)}  {n} page(s)")
    return 0 if made else 2


def cmd_manifest(args: argparse.Namespace) -> int:
    """Validate every manifest fragment, and optionally merge them into one."""
    frags = sorted(Path(args.out, "templates.d").glob("*.json"))
    if not frags:
        print("no manifest fragments found", file=sys.stderr)
        return 2
    all_entries: list[dict] = []
    bad = 0
    for frag in frags:
        data = json.loads(frag.read_text(encoding="utf-8"))
        problems = manifest.validate(data["templates"])
        status = "ok" if not problems else f"{len(problems)} problem(s)"
        print(f"  {frag.name:28s} {len(data['templates']):3d} entries  {status}")
        for p in problems:
            print(f"      - {p}")
            bad += 1
        all_entries.extend(data["templates"])
    dup = manifest.validate(all_entries)
    for p in dup:
        if p.startswith("duplicate"):
            print(f"  across fragments: {p}")
            bad += 1
    return 1 if bad else 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Check built artefacts against the device contract and the rule books."""
    from .checks import run_checks
    return run_checks(Path(args.out), devices.get(args.device),
                      verbose=not args.quiet)


def cmd_docs(args: argparse.Namespace) -> int:
    from courts.docgen import write_geometry_doc
    path = write_geometry_doc(Path(args.docs))
    print(f"wrote {path}")
    return 0


# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="rmtpl", description="reMarkable template toolkit")
    ap.add_argument("--device", default="rmpp",
                    help="target device: " + ", ".join(sorted(devices.DEVICES)))
    ap.add_argument("--out", default=str(REPO / "templates"),
                    help="build output root")
    sub = ap.add_subparsers(dest="command", required=True)

    style_parent = argparse.ArgumentParser(add_help=False)
    style_parent.add_argument("--ink", default=DEFAULT_STYLE.ink)
    style_parent.add_argument("--ink-soft", default=DEFAULT_STYLE.ink_soft)
    style_parent.add_argument("--line-scale", type=float,
                              default=DEFAULT_STYLE.line_scale)
    style_parent.add_argument("--margin", type=float,
                              default=DEFAULT_STYLE.margin_px)

    p = sub.add_parser("courts", parents=[style_parent],
                       help="render the rule-book court templates")
    p.add_argument("--rulesets", default="",
                   help="comma separated subset of " + ",".join(court_specs.ORDER))
    p.add_argument("--categories", default="Basketball")
    p.add_argument("--blank-icons", action="store_true")
    p.add_argument("--no-pdf", action="store_true")
    p.add_argument("--clean", action="store_true")
    p.set_defaults(func=cmd_courts)

    p = sub.add_parser("ingest", help="turn a folder of PNGs into templates")
    p.add_argument("source", help="folder containing PNG artwork")
    p.add_argument("--namespace", default="imported")
    p.add_argument("--prefix", default="",
                   help="prepended to every display name")
    p.add_argument("--strip", default="",
                   help="drop this leading text from each file stem")
    p.add_argument("--categories", default="Basketball")
    p.add_argument("--fit", default="fit", choices=raster.FIT_MODES)
    p.add_argument("--blank-icons", action="store_true")
    p.add_argument("--no-pdf", action="store_true")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("bundle", help="multi-page PDFs for the no-dev-mode route")
    p.add_argument("--name", default="basketball-courts")
    p.add_argument("--copies", type=int, default=1,
                   help="repeat each template this many times")
    p.set_defaults(func=cmd_bundle)

    p = sub.add_parser("manifest", help="validate templates.json fragments")
    p.set_defaults(func=cmd_manifest)

    p = sub.add_parser("doctor", help="verify built artefacts")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("docs", help="regenerate docs from the specs")
    p.add_argument("--docs", default=str(REPO / "docs"))
    p.set_defaults(func=cmd_docs)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
