#!/usr/bin/env python3
"""Confirm a device's templates.json really contains what was installed.

Read back from the tablet after writing, so this checks the device's state
rather than the file that was uploaded a moment earlier.

    verify_install.py DEVICE_JSON EXPECTED_FOREIGN MANIFEST [MANIFEST ...]

``EXPECTED_FOREIGN`` is how many entries the device owned before the install.
Comparing against that, rather than against the total, is what makes a
wholesale replacement detectable: a file containing only our own entries has a
plausible total and zero of the device's.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    device_file, expected_foreign_s, *manifests = sys.argv[1:]
    data = json.loads(Path(device_file).read_text(encoding="utf-8"))
    expected_foreign = int(expected_foreign_s)

    wanted: set[str] = set()
    for frag in manifests:
        for t in json.loads(Path(frag).read_text(encoding="utf-8"))["templates"]:
            wanted.add(t["filename"])

    present = {t["filename"] for t in data["templates"]}
    missing = sorted(wanted - present)
    if missing:
        print(f"templates missing from the device file: {missing}",
              file=sys.stderr)
        return 1

    namespaces = {w.split("/")[0] for w in wanted}
    ours = {n for n in present if n.split("/")[0] in namespaces}
    foreign = len(data["templates"]) - len(ours)

    if foreign != expected_foreign:
        print(f"the device's own templates did not survive: {expected_foreign} "
              f"before the install, {foreign} after. Restore from the backup "
              f"this run made before changing anything.", file=sys.stderr)
        return 1

    print(f"verified on the device: {len(data['templates'])} entries "
          f"({len(ours)} ours, {foreign} the device's own, unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
