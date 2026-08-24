"""templates.json: build entries, and merge them into a device's own file.

The device's ``templates.json`` is a single flat list that xochitl owns. The
only safe way to add to it is to read what is there, drop exactly the entries a
previous run of this tool added, append the current set, and write the result
back. Replacing the file wholesale is what loses somebody's stock templates.

Schema, as observed on shipping devices::

    {"templates": [
        {"name": "Blank", "filename": "Blank", "iconCode": "\\ue9fe",
         "landscape": true, "categories": ["Creative", "Grids"]},
        ...
    ]}

``filename`` carries no extension and may include a sub-directory. That is what
makes a namespace directory a reliable marker for one project's entries, and it
is why every template this toolkit builds is filed under ``<namespace>/``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import icons
from .family import BuiltTemplate

#: Written next to a built set's ``png/``, ``svg/`` and ``pdf/`` directories.
MANIFEST_NAME = "manifest.json"


@dataclass
class TemplateEntry:
    name: str
    filename: str
    icon_code: str
    landscape: bool = False
    categories: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "filename": self.filename,
            "iconCode": self.icon_code,
        }
        # xochitl treats a missing key as portrait; stock entries omit it there,
        # so this file matches the convention the device already uses.
        if self.landscape:
            d["landscape"] = True
        d["categories"] = list(self.categories)
        return d


def entries_for(namespace: str, built: Sequence[BuiltTemplate], *,
                categories: Sequence[str], name_prefix: str = "",
                blank_icons: bool = False) -> list[TemplateEntry]:
    """Turn a family's output into manifest entries.

    Icons cycle per orientation so a picker full of portrait templates does not
    show the same glyph six times while the landscape ones go unused.
    """
    counter = {False: 0, True: 0}
    out: list[TemplateEntry] = []
    for item in built:
        out.append(TemplateEntry(
            name=f"{name_prefix}{item.display}",
            filename=f"{namespace}/{item.stem}",
            icon_code=icons.pick(counter[item.landscape], item.landscape,
                                 blank_only=blank_icons),
            landscape=item.landscape,
            categories=list(categories),
        ))
        counter[item.landscape] += 1
    return out


def dumps(entries: Iterable[TemplateEntry]) -> str:
    payload = {"templates": [e.to_dict() for e in entries]}
    return json.dumps(payload, indent=2, ensure_ascii=True) + "\n"


def write(path: Path, entries: Iterable[TemplateEntry]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(entries), encoding="utf-8")
    return path


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "templates" not in data:
        raise ValueError(f"{path} is not a templates.json (no 'templates' key)")
    if not isinstance(data["templates"], list):
        raise ValueError(f"{path}: 'templates' is not a list")
    return data


def merge(device: dict[str, Any], ours: Iterable[TemplateEntry], *,
          namespace: str) -> tuple[dict[str, Any], int, int]:
    """Return ``(merged, removed, added)``.

    Entries whose ``filename`` sits under ``namespace/`` are treated as ours and
    replaced. Everything else in the device's file is preserved verbatim, in
    order.
    """
    prefix = f"{namespace}/"
    kept = [t for t in device["templates"]
            if not str(t.get("filename", "")).startswith(prefix)]
    removed = len(device["templates"]) - len(kept)
    new = [e.to_dict() for e in ours]

    seen = {str(t.get("name", "")) for t in kept}
    for entry in new:
        if entry["name"] in seen:
            raise ValueError(
                f"template name {entry['name']!r} already exists on the device "
                "outside our namespace; rename it before installing")
        seen.add(entry["name"])

    merged = dict(device)
    merged["templates"] = kept + new
    return merged, removed, len(new)


def validate(entries: list[dict[str, Any]]) -> list[str]:
    """Structural checks. Returns a list of problems; empty means good."""
    problems: list[str] = []
    names: dict[str, int] = {}
    for i, t in enumerate(entries):
        where = f"entry {i}"
        for key in ("name", "filename", "iconCode"):
            if not isinstance(t.get(key), str) or not t[key]:
                problems.append(f"{where}: missing or non-string {key!r}")
        cats = t.get("categories")
        if not isinstance(cats, list) or not cats or not all(
                isinstance(c, str) and c for c in cats):
            problems.append(
                f"{where}: 'categories' must be a non-empty list of strings")
        if "landscape" in t and not isinstance(t["landscape"], bool):
            problems.append(f"{where}: 'landscape' must be a boolean")
        icon = t.get("iconCode")
        if isinstance(icon, str) and len(icon) != 1:
            problems.append(f"{where}: 'iconCode' must be exactly one character")
        if Path(str(t.get("filename", ""))).suffix:
            problems.append(
                f"{where}: 'filename' must not carry an extension "
                f"(got {t.get('filename')!r})")
        name = str(t.get("name", ""))
        names[name] = names.get(name, 0) + 1
    for name, count in names.items():
        if count > 1:
            problems.append(f"duplicate template name {name!r} ({count} entries)")
    return problems
