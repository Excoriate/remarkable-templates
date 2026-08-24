#!/usr/bin/env python3
"""Merge template entries into a copy of a device's templates.json.

Runs on the *host*, never on the tablet: reMarkable devices do not ship a
Python interpreter, and the merge is the one step where a mistake costs someone
their stock templates. Reading the device's file, editing it here and writing it
back keeps the risky part on a machine with real tooling.

    merge_templates_json.py DEVICE_JSON MANIFEST [MANIFEST ...] -o OUT

Entries already filed under a manifest's namespace directory are replaced, so
running an install twice is the same as running it once. Everything else in the
device's file is preserved, in order — and that is asserted rather than assumed:
the count of entries belonging to nobody but the device must come out of the
merge exactly as it went in.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from rmtpl import manifest  # noqa: E402


def foreign(entries: list[dict], namespaces: set[str]) -> list[dict]:
    """Entries that belong to the device rather than to any of our sets."""
    return [t for t in entries
            if str(t.get("filename", "")).split("/")[0] not in namespaces]


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
            print(f"{frag}: refusing to install, manifest is invalid:",
                  file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 1
        for t in data["templates"]:
            namespaces.add(str(t["filename"]).split("/")[0])
            entries.append(manifest.TemplateEntry(
                name=t["name"], filename=t["filename"], icon_code=t["iconCode"],
                landscape=bool(t.get("landscape", False)),
                categories=list(t["categories"]),
            ))

    before_foreign = foreign(device["templates"], namespaces)

    merged = device
    for ns in sorted(namespaces):
        merged, _, _ = manifest.merge(
            merged, [] if args.remove_only else
            [e for e in entries if e.filename.startswith(f"{ns}/")], namespace=ns)

    after_foreign = foreign(merged["templates"], namespaces)

    # The guarantee this whole host-side merge exists to provide, checked
    # rather than asserted in a comment: nothing the device owns may be lost,
    # reordered or altered.
    if after_foreign != before_foreign:
        print(f"refusing to write: the device's own entries changed during the "
              f"merge ({len(before_foreign)} before, {len(after_foreign)} "
              f"after). Nothing has been uploaded.", file=sys.stderr)
        lost = [t.get("name") for t in before_foreign if t not in after_foreign]
        if lost:
            print(f"  missing: {lost}", file=sys.stderr)
        return 1

    args.out.write_text(
        json.dumps(merged, indent=4, ensure_ascii=True) + "\n", encoding="utf-8")
    ours = len(merged["templates"]) - len(after_foreign)
    print(f"device had {before} entries; {len(after_foreign)} of them are the "
          f"device's own and are unchanged; wrote {len(merged['templates'])} "
          f"({ours} ours)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
