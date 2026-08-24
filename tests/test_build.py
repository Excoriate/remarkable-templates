"""End-to-end: build into a temporary directory, then verify what came out."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from courts import specs
from courts.build import LAYOUTS, build
from rmtpl import devices, manifest
from rmtpl.checks import run_checks


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("templates")
    device = devices.PAPER_PRO
    made, entries = build(out, device, want_pdf=True)
    (out / "templates.d").mkdir(parents=True, exist_ok=True)
    (out / "templates.d" / "basketball.json").write_text(
        manifest.dumps(entries), encoding="utf-8")
    return out, device, made, entries


def test_one_template_per_ruleset_and_region(built):
    _, _, made, _ = built
    assert len(made) == len(specs.ORDER) * len(LAYOUTS)


def test_rasters_are_exactly_the_device_canvas(built):
    out, device, made, _ = built
    for b in made:
        img = Image.open(b.png)
        assert img.size == device.canvas(b.landscape)
        assert img.mode == "L", "templates must not carry an alpha channel"


def test_pages_are_white_where_nothing_is_drawn(built):
    _, _, made, _ = built
    for b in made:
        px = Image.open(b.png).convert("L")
        assert px.getpixel((0, 0)) >= 250
        assert px.getpixel((px.width - 1, px.height - 1)) >= 250


def test_pdf_pages_match_the_panel(built):
    _, device, made, _ = built
    from rmtpl.vector import pdf_pages
    for b in made:
        assert b.pdf.read_bytes()[:4] == b"%PDF"
        sizes = pdf_pages(b.pdf)
        assert len(sizes) == 1
        want = tuple(round(v, 2) for v in device.page_pt(b.landscape))
        assert all(abs(a - w) <= 0.1
                   for a, w in zip(sizes[0], want, strict=True))


def test_builds_are_byte_reproducible(tmp_path):
    """Rebuild the same source twice and every artefact must hash the same.

    PDF writers stamp a creation time into their output, so this only holds
    because the build normalises it away. Without it the committed templates
    could never be checked against a rebuild.
    """
    import hashlib

    device = devices.PAPER_PRO
    digests = []
    for run in ("a", "b"):
        root = tmp_path / run
        made, _ = build(root, device, want_pdf=True)
        digests.append({
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for b in made for p in (b.png, b.svg, b.pdf)
        })
    assert digests[0] == digests[1]


def test_manifest_validates(built):
    out, _, _, entries = built
    data = json.loads((out / "templates.d" / "basketball.json").read_text())
    assert manifest.validate(data["templates"]) == []
    assert len({e.name for e in entries}) == len(entries)
    assert all(e.filename.startswith("basketball/") for e in entries)


def test_doctor_passes(built, capsys):
    out, device, _, _ = built
    assert run_checks(out, device, verbose=False) == 0


def test_doctor_catches_a_broken_edge_convention(built, tmp_path, monkeypatch):
    """The verification must be able to fail, or it proves nothing.

    A three-inch error is injected into the one function that resolves published
    edges into path centres, the set is rebuilt, and the checker is expected to
    notice. It measures pixels and compares against the rule book, so it does.
    """
    import courts.geometry as geometry

    original = geometry.to_path
    monkeypatch.setattr(geometry, "to_path",
                        lambda v, e, w: original(v, e, w) + 0.25)

    out = tmp_path / "broken"
    device = devices.PAPER_PRO
    _, entries = build(out, device, want_pdf=False)
    (out / "templates.d").mkdir(parents=True, exist_ok=True)
    (out / "templates.d" / "basketball.json").write_text(
        manifest.dumps(entries), encoding="utf-8")

    assert run_checks(out, device, verbose=False) == 1


def test_merge_preserves_foreign_entries_and_is_idempotent(built):
    _, _, _, entries = built
    device_file = {"templates": [
        {"name": "Blank", "filename": "Blank", "iconCode": "",
         "categories": ["Creative"]},
        {"name": "Stale", "filename": "basketball/gone", "iconCode": "",
         "categories": ["Basketball"]},
    ]}
    merged, removed, added = manifest.merge(device_file, entries)
    assert removed == 1
    assert added == len(entries)
    assert merged["templates"][0]["name"] == "Blank"

    again, removed2, added2 = manifest.merge(merged, entries)
    assert again == merged
    assert removed2 == len(entries)


def test_merge_refuses_to_shadow_a_foreign_template_name(built):
    _, _, _, entries = built
    clash = entries[0].name
    device_file = {"templates": [
        {"name": clash, "filename": "SomeoneElses", "iconCode": "",
         "categories": ["Creative"]}]}
    with pytest.raises(ValueError, match="already exists"):
        manifest.merge(device_file, entries)
