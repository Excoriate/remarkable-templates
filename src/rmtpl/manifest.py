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

``filename`` carries no extension and may include a sub-directory, which is what
makes a namespaced install directory a reliable marker for our own entries.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Sub-directory under the device template root that this tool owns outright.
NAMESPACE = "basketball"


@dataclass
class TemplateEntry:
    name: str
    filename: str
    icon_code: str
    landscape: bool = False
    categories: list[str] = field(default_factory=lambda: ["Basketball"])

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


def dumps(entries: Iterable[TemplateEntry]) -> str:
    payload = {"templates": [e.to_dict() for e in entries]}
    return json.dumps(payload, indent=2, ensure_ascii=True) + "\n"


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "templates" not in data:
        raise ValueError(f"{path} is not a templates.json (no 'templates' key)")
    if not isinstance(data["templates"], list):
        raise ValueError(f"{path}: 'templates' is not a list")
    return data


def merge(device: dict[str, Any], ours: Iterable[TemplateEntry], *,
          namespace: str = NAMESPACE) -> tuple[dict[str, Any], int, int]:
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
                "outside our namespace; rename it before installing"
            )
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
