#!/usr/bin/env python3
"""Lay each built template set out on one sheet, for the README.

    tools/contact_sheet.py templates docs/images

Writes ``docs/images/<set>.png`` for every directory under the build root that
contains rendered PNGs, so a new family gets a preview without touching this
script.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

TILE_H = 460
GAP = 22
PAD = 26
LABEL = 22
COLS = 4
BG = (255, 255, 255)
RULE = (214, 214, 214)
TEXT = (74, 74, 74)


def sheet(files: list[Path], dest: Path) -> tuple[int, int]:
    tiles = []
    for f in files:
        with Image.open(f) as opened:
            img = opened.convert("RGB")
        w = round(img.width * TILE_H / img.height)
        tiles.append((f.stem, img.resize((w, TILE_H), Image.LANCZOS)))

    rows = (len(tiles) + COLS - 1) // COLS
    col_w = max(t.width for _, t in tiles)
    size = (PAD * 2 + COLS * col_w + (COLS - 1) * GAP,
            PAD * 2 + rows * (TILE_H + LABEL) + (rows - 1) * GAP)
    canvas = Image.new("RGB", size, BG)
    draw = ImageDraw.Draw(canvas)

    for i, (name, tile) in enumerate(tiles):
        r, c = divmod(i, COLS)
        x = PAD + c * (col_w + GAP) + (col_w - tile.width) // 2
        y = PAD + r * (TILE_H + LABEL + GAP)
        canvas.paste(tile, (x, y))
        draw.rectangle([x, y, x + tile.width - 1, y + TILE_H - 1], outline=RULE)
        draw.text((x, y + TILE_H + 5), name.replace("-", " "), fill=TEXT)

    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest, optimize=True)
    return size


def main() -> int:
    root, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    made = 0
    for png_dir in sorted(root.glob("*/png")):
        files = sorted(png_dir.glob("*.png"))
        if not files:
            continue
        name = png_dir.parent.name
        size = sheet(files, out_dir / f"{name}.png")
        print(f"{out_dir / f'{name}.png'}  {size[0]}x{size[1]}  "
              f"{len(files)} templates")
        made += 1
    if not made:
        print(f"no rendered PNGs under {root}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
