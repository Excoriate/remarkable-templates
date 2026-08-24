"""The family seam: discovery, and the contract every family must satisfy."""

from __future__ import annotations

import inspect

import pytest

from rmtpl import registry
from rmtpl.family import BuildOptions, TemplateFamily


def test_at_least_one_family_is_discovered():
    assert registry.keys(), "no families found under src/rmtpl/families"


def test_basketball_is_registered():
    assert "basketball" in registry.keys()


@pytest.mark.parametrize("key", registry.keys())
def test_family_declares_its_identity(key):
    family = registry.get(key)
    assert isinstance(family, TemplateFamily)
    assert family.key == key
    assert family.key.islower() and " " not in family.key
    assert family.label and family.summary
    assert family.category


@pytest.mark.parametrize("key", registry.keys())
def test_family_build_has_the_expected_signature(key):
    sig = inspect.signature(registry.get(key).build)
    assert list(sig.parameters) == ["out_dir", "device", "options"]


def test_resolve_selects_and_defaults():
    assert registry.resolve("") == tuple(registry.families().values())
    assert registry.resolve("basketball")[0].key == "basketball"


def test_unknown_family_fails_loudly():
    with pytest.raises(SystemExit, match="unknown family"):
        registry.get("curling")


def test_build_options_defaults_are_usable():
    options = BuildOptions()
    assert options.want_pdf is True
    assert options.variants == ()
    assert options.style.ink.startswith("#")
