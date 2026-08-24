#!/usr/bin/env python3
"""Confirm none of our namespaces are left in a device's templates.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    device_file, *namespaces = sys.argv[1:]
    data = json.loads(Path(device_file).read_text(encoding="utf-8"))
    left = [t["filename"] for t in data["templates"]
            if str(t.get("filename", "")).split("/")[0] in set(namespaces)]
    if left:
        print(f"still present on the device: {left}", file=sys.stderr)
        return 1
    print(f"verified: {len(data['templates'])} entries remain, none of them ours")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
