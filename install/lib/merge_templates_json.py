#!/usr/bin/env python3
"""Merge template entries into a copy of a device's templates.json.

Runs on the *host*, never on the tablet: reMarkable devices do not ship a
Python interpreter, and the merge is the one step where a mistake costs someone
their stock templates. Reading the device's file, editing it here and writing it
back keeps the risky part on a machine with real tooling.

    merge_templates_json.py DEVICE_JSON MANIFEST [MANIFEST ...] -o OUT

Entries already filed under a manifest's namespace directory are replaced, so
running an install twice is the same as running it once. Everything else in the
device's file is preserved, in order.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from rmtpl import manifest  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("device_json", type=Path)
    ap.add_argument("manifests", type=Path, nargs="+")
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--remove-only", action="store_true",
                    help="strip our entries and add nothing back")
    args = ap.parse_args()

    device = manifest.load(args.device_json)
    before = len(device["templates"])

    entries: list[manifest.TemplateEntry] = []
    namespaces: set[str] = set()
    for frag in args.manifests:
        data = json.loads(frag.read_text(encoding="utf-8"))
        problems = manifest.validate(data["templates"])
        if problems:
            print(f"{frag}: refusing to install, fragment is invalid:",
                  file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 1
        for t in data["templates"]:
            ns = str(t["filename"]).split("/")[0]
            namespaces.add(ns)
            entries.append(manifest.TemplateEntry(
                name=t["name"], filename=t["filename"], icon_code=t["iconCode"],
                landscape=bool(t.get("landscape", False)),
                categories=list(t["categories"]),
            ))

    merged = device
    removed_total = 0
    for ns in sorted(namespaces):
        merged, removed, _ = manifest.merge(
            merged, [] if args.remove_only else
            [e for e in entries if e.filename.startswith(f"{ns}/")], namespace=ns)
        removed_total += removed

    args.out.write_text(
        json.dumps(merged, indent=4, ensure_ascii=True) + "\n", encoding="utf-8")
    after = len(merged["templates"])
    kept = before - removed_total
    print(f"device had {before} entries; kept {kept}, replaced {removed_total}, "
          f"wrote {after}")
    if kept < before - removed_total:
        print("refusing: entries outside our namespace went missing", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
