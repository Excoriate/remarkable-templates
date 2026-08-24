"""Template picker glyphs.

``iconCode`` is a single character from a private-use block in the icon font
xochitl ships. There is no basketball glyph, and adding one means patching that
font, so the codes below are borrowed from stock templates: every one of them is
known to exist on a shipping device, and each is orientation-appropriate. Names
in the picker do the actual discriminating.

Codes are written as escapes rather than literal private-use characters so that
this file survives any editor, terminal or diff tool.
"""

from __future__ import annotations

#: Guaranteed present, and orientation-matched: the stock "Blank" templates.
BLANK_PORTRAIT = ""
BLANK_LANDSCAPE = ""

#: Further stock codes, kept in a fixed order so builds are reproducible.
#: Portrait: Blank, Perspective 1, Perspective 2, Isometric, One storyboard,
#: Four storyboards.
PORTRAIT_POOL = (BLANK_PORTRAIT, "", "", "", "", "")
#: Landscape: Blank, One storyboard, One storyboard 2, Two storyboards,
#: Four storyboards, Margin medium.
LANDSCAPE_POOL = (BLANK_LANDSCAPE, "", "", "", "", "")


def pool(landscape: bool) -> tuple[str, ...]:
    return LANDSCAPE_POOL if landscape else PORTRAIT_POOL


def pick(index: int, landscape: bool, *, blank_only: bool = False) -> str:
    """Deterministically choose a glyph for the ``index``-th template."""
    if blank_only:
        return BLANK_LANDSCAPE if landscape else BLANK_PORTRAIT
    codes = pool(landscape)
    return codes[index % len(codes)]
