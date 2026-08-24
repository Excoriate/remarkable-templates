"""Command line entry point: ``python -m rmtpl <command>``.

The Justfile wraps these, but every recipe is a thin shell over one of these
sub-commands, so the toolkit works with or without ``just`` installed.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from PIL import Image

from . import devices, manifest, raster, registry
from .checks import namespaces, run_checks
from .family import BuildOptions
from .style import DEFAULT_STYLE, Style
from .vector import png_to_pdf

#: Defaults are relative to the working directory, so the toolkit behaves the
#: same whether it is run from a checkout or from an installed wheel.
DEFAULT_OUT = Path("templates")
DEFAULT_DOCS = Path("docs")


def _short(path: Path) -> str:
    """A path relative to the working directory when that is shorter."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _style(args: argparse.Namespace) -> Style:
    return Style(
        ink=args.ink,
        ink_soft=args.ink_soft,
        line_scale=args.line_scale,
        margin_px=args.margin,
    )


# --------------------------------------------------------------------------- #

def cmd_list(args: argparse.Namespace) -> int:
    print("families")
    for family in registry.families().values():
        variants = ", ".join(family.variants) or "-"
        print(f"  {family.key:<14} {family.label}")
        print(f"  {'':<14} {family.summary}")
        print(f"  {'':<14} variants: {variants}")
    print("\ndevices")
    for d in devices.DEVICES.values():
        w, h = d.portrait
        print(f"  {d.key:<14} {d.label}  {w}x{h} portrait, {d.ppi:g} PPI")
    out = Path(args.out)
    built = namespaces(out)
    print(f"\nbuilt sets under {out}")
    if not built:
        print("  (none yet — run: just build)")
    for ns in built:
        count = len(manifest.load(ns / manifest.MANIFEST_NAME)["templates"])
        print(f"  {ns.name:<14} {count} template(s)")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    device = devices.get(args.device)
    out = Path(args.out)
    selected = registry.resolve(args.families)
    if not selected:
        print("no families found in this checkout", file=sys.stderr)
        return 2

    options = BuildOptions(
        style=_style(args),
        want_pdf=not args.no_pdf,
        variants=tuple(v for v in args.variants.split(",") if v) if args.variants
        else (),
    )
    total = 0
    for family in selected:
        ns_dir = out / family.key
        if args.clean and ns_dir.exists():
            shutil.rmtree(ns_dir)
        built = family.build(ns_dir, device, options)
        entries = manifest.entries_for(
            family.key, built,
            categories=(args.categories.split(",") if args.categories
                        else [family.category]),
            blank_icons=args.blank_icons,
        )
        manifest.write(ns_dir / manifest.MANIFEST_NAME, entries)
        print(f"{family.label} -> {ns_dir}")
        for item in built:
            w, h = item.canvas
            print(f"  {item.stem:<24} {w}x{h}  {item.detail}  {item.display}")
        total += len(built)
    print(f"built {total} template(s) for {device.label}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Turn any folder of PNGs into a template set. The generic path."""
    device = devices.get(args.device)
    src = Path(args.source).expanduser()
    if not src.is_dir():
        print(f"not a directory: {src}", file=sys.stderr)
        return 2
    if args.namespace in registry.keys():
        print(f"namespace {args.namespace!r} belongs to a built-in family; "
              f"choose another with --namespace", file=sys.stderr)
        return 2

    ns_dir = Path(args.out) / args.namespace
    pngs = sorted(p for p in src.iterdir()
                  if p.suffix.lower() == ".png" and not p.name.startswith("."))
    if not pngs:
        print(f"no PNG files in {src}", file=sys.stderr)
        return 2

    from .family import BuiltTemplate
    built: list[BuiltTemplate] = []
    results = []
    for png in pngs:
        label = png.stem
        if args.strip and label.lower().startswith(args.strip.lower()):
            label = label[len(args.strip):]
        stem = raster.slugify(label)
        res = raster.normalise(png, ns_dir / "png" / f"{stem}.png", device,
                               mode=args.fit)
        results.append(res)
        built.append(BuiltTemplate(
            stem=stem, display=raster.titleise(label), landscape=res.landscape,
            canvas=res.out_size, png=res.out,
        ))
        flag = "  LETTERBOXED" if res.letterboxed else ""
        print(f"  {png.name:<34} {res.src_size[0]}x{res.src_size[1]}"
              f" -> {res.out_size[0]}x{res.out_size[1]}"
              f"  x{res.scale:.4f}{flag}")

    entries = manifest.entries_for(
        args.namespace, built,
        categories=(args.categories.split(",") if args.categories
                    else [args.namespace.title()]),
        name_prefix=args.prefix, blank_icons=args.blank_icons)
    manifest.write(ns_dir / manifest.MANIFEST_NAME, entries)

    if not args.no_pdf:
        for item in built:
            png_to_pdf([item.png], ns_dir / "pdf" / f"{item.stem}.pdf",
                       device.page_pt(item.landscape))

    letterboxed = sum(1 for r in results if r.letterboxed)
    print(f"ingested {len(results)} template(s) for {device.label} -> {ns_dir}")
    if letterboxed:
        print(f"note: {letterboxed} source image(s) did not match the "
              f"{device.label} aspect ratio and were letterboxed onto white; "
              f"use --fit cover to crop instead, or --fit stretch to distort.")
    return 0


def cmd_bundle(args: argparse.Namespace) -> int:
    """One multi-page PDF per orientation, for the no-developer-mode route."""
    device = devices.get(args.device)
    out = Path(args.out)
    sets = namespaces(out)
    if not sets:
        print(f"nothing built under {out}; run 'just build' first",
              file=sys.stderr)
        return 2
    made = []
    for ns_dir in sets:
        pngs = sorted((ns_dir / "png").glob("*.png"))
        for landscape, label in ((False, "portrait"), (True, "landscape")):
            canvas = device.canvas(landscape)
            pages = [p for p in pngs if Image.open(p).size == canvas]
            pages = [p for p in pages for _ in range(args.copies)]
            if not pages:
                continue
            target = ns_dir / "pdf" / f"{ns_dir.name}-{label}.pdf"
            png_to_pdf(pages, target, device.page_pt(landscape))
            made.append((target, len(pages)))
    for target, n in made:
        print(f"  {_short(target)}  {n} page(s)")
    return 0 if made else 2


def cmd_docs(args: argparse.Namespace) -> int:
    docs = Path(args.docs)
    written = []
    for family in registry.resolve(args.families):
        written.extend(family.write_docs(docs))
    for path in written:
        print(f"wrote {path}")
    if not written:
        print("no family generates documentation")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    return run_checks(Path(args.out), devices.get(args.device),
                      verbose=not args.quiet)


# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="rmtpl", description="reMarkable template toolkit")
    ap.add_argument("--device", default="rmpp",
                    help="target device: " + ", ".join(sorted(devices.DEVICES)))
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="build output root")
    sub = ap.add_subparsers(dest="command", required=True)

    style_parent = argparse.ArgumentParser(add_help=False)
    style_parent.add_argument("--ink", default=DEFAULT_STYLE.ink)
    style_parent.add_argument("--ink-soft", default=DEFAULT_STYLE.ink_soft)
    style_parent.add_argument("--line-scale", type=float,
                              default=DEFAULT_STYLE.line_scale)
    style_parent.add_argument("--margin", type=float,
                              default=DEFAULT_STYLE.margin_px)

    p = sub.add_parser("list", help="show families, devices and built sets")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("build", parents=[style_parent],
                       help="render one or every template family")
    p.add_argument("families", nargs="?", default="",
                   help="comma separated family keys; default is all of them")
    p.add_argument("--variants", default="",
                   help="comma separated subset of a family's own variants")
    p.add_argument("--categories", default="",
                   help="template-picker tabs; default is the family's own")
    p.add_argument("--blank-icons", action="store_true")
    p.add_argument("--no-pdf", action="store_true")
    p.add_argument("--clean", action="store_true")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("ingest", help="turn a folder of PNGs into templates")
    p.add_argument("source", help="folder containing PNG artwork")
    p.add_argument("--namespace", default="imported")
    p.add_argument("--prefix", default="", help="prepended to every name")
    p.add_argument("--strip", default="",
                   help="drop this leading text from each file stem")
    p.add_argument("--categories", default="")
    p.add_argument("--fit", default="fit", choices=raster.FIT_MODES)
    p.add_argument("--blank-icons", action="store_true")
    p.add_argument("--no-pdf", action="store_true")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("bundle", help="multi-page PDFs for the no-dev-mode route")
    p.add_argument("--copies", type=int, default=1,
                   help="repeat each template this many times")
    p.set_defaults(func=cmd_bundle)

    p = sub.add_parser("docs", help="regenerate documentation from the specs")
    p.add_argument("families", nargs="?", default="")
    p.add_argument("--docs", default=str(DEFAULT_DOCS))
    p.set_defaults(func=cmd_docs)

    p = sub.add_parser("doctor", help="verify built artefacts")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_doctor)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
