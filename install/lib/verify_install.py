#!/usr/bin/env python3
"""Confirm a device's templates.json really contains what was installed.

Read back from the tablet after writing, so this checks the device's state
rather than the file that was uploaded a moment earlier.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    device_file, before_s, *manifests = sys.argv[1:]
    data = json.loads(Path(device_file).read_text(encoding="utf-8"))
    before = int(before_s)

    wanted: set[str] = set()
    for frag in manifests:
        for t in json.loads(Path(frag).read_text(encoding="utf-8"))["templates"]:
            wanted.add(t["filename"])

    present = {t["filename"] for t in data["templates"]}
    missing = sorted(wanted - present)
    if missing:
        print(f"templates missing from the device file: {missing}", file=sys.stderr)
        return 1

    namespaces = {w.split("/")[0] for w in wanted}
    ours = {n for n in present if n.split("/")[0] in namespaces}
    kept = len(data["templates"]) - len(ours)
    print(f"verified on the device: {len(data['templates'])} entries "
          f"({len(ours)} ours, {kept} pre-existing; it had {before} before)")
    if kept > before:
        print("unexpected: more pre-existing entries than before", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
