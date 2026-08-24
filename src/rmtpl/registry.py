"""Find the template families available in this checkout.

Discovery is by directory: every package under ``rmtpl/families/`` that exposes
a module-level ``FAMILY`` is registered, in name order so builds are
reproducible. There is no plugin manifest to keep in sync and no list of
families to forget to update.

The families live *inside* ``rmtpl`` rather than beside it. A top-level package
called ``families`` would squat a generic name in every environment that
installs this, and — because ``python -m`` puts the working directory first on
``sys.path`` — any stray ``./families/`` would shadow it and be imported and
executed. Namespacing the sub-package removes both.
"""

from __future__ import annotations

import importlib
import pkgutil

from .family import TemplateFamily

_PACKAGE = "rmtpl.families"
_cache: dict[str, TemplateFamily] | None = None


def _discover() -> dict[str, TemplateFamily]:
    package = importlib.import_module(_PACKAGE)
    found: dict[str, TemplateFamily] = {}
    for info in sorted(pkgutil.iter_modules(package.__path__),
                       key=lambda i: i.name):
        module = importlib.import_module(f"{_PACKAGE}.{info.name}")
        family = getattr(module, "FAMILY", None)
        if family is None:
            continue
        if not isinstance(family, TemplateFamily):
            raise TypeError(
                f"{_PACKAGE}.{info.name}.FAMILY must be a TemplateFamily, "
                f"got {type(family).__name__}")
        if family.key in found:
            raise ValueError(f"two families claim the key {family.key!r}")
        found[family.key] = family
    return found


def families() -> dict[str, TemplateFamily]:
    global _cache
    if _cache is None:
        _cache = _discover()
    return _cache


def keys() -> tuple[str, ...]:
    return tuple(families())


def get(key: str) -> TemplateFamily:
    try:
        return families()[key]
    except KeyError:
        raise SystemExit(
            f"unknown family {key!r}; this checkout has: "
            f"{', '.join(keys()) or '(none)'}") from None


def resolve(selection: str) -> tuple[TemplateFamily, ...]:
    """Turn a comma-separated selection (or an empty string) into families."""
    if not selection.strip():
        return tuple(families().values())
    return tuple(get(k.strip()) for k in selection.split(",") if k.strip())
