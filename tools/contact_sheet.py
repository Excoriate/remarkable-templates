#!/usr/bin/env python3
"""Lay every built template out on one sheet, for the README.

    tools/contact_sheet.py templates/png docs/images/contact-sheet.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

TILE_H = 460
GAP = 22
PAD = 26
LABEL = 22
BG = (255, 255, 255)
RULE = (214, 214, 214)
TEXT = (74, 74, 74)


def main() -> int:
    src, dest = Path(sys.argv[1]), Path(sys.argv[2])
    files = sorted(src.glob("*.png"))
    if not files:
        print(f"no PNGs in {src}", file=sys.stderr)
        return 2

    tiles = []
    for f in files:
        img = Image.open(f).convert("RGB")
        w = round(img.width * TILE_H / img.height)
        tiles.append((f.stem, img.resize((w, TILE_H), Image.LANCZOS)))

    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    col_w = max(t.width for _, t in tiles)
    sheet_w = PAD * 2 + cols * col_w + (cols - 1) * GAP
    sheet_h = PAD * 2 + rows * (TILE_H + LABEL) + (rows - 1) * GAP
    sheet = Image.new("RGB", (sheet_w, sheet_h), BG)
    draw = ImageDraw.Draw(sheet)

    for i, (name, tile) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = PAD + c * (col_w + GAP) + (col_w - tile.width) // 2
        y = PAD + r * (TILE_H + LABEL + GAP)
        sheet.paste(tile, (x, y))
        draw.rectangle([x, y, x + tile.width - 1, y + TILE_H - 1], outline=RULE)
        draw.text((x, y + TILE_H + 5), name.replace("-", " "), fill=TEXT)

    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest, optimize=True)
    print(f"{dest}  {sheet.size[0]}x{sheet.size[1]}  {len(tiles)} templates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
