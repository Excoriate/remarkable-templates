"""End to end: build every family into a temporary tree, then verify it."""

from __future__ import annotations

import hashlib
import json

import pytest
from PIL import Image

from rmtpl import devices, manifest, registry
from rmtpl.checks import namespaces, run_checks
from rmtpl.family import BuildOptions
from rmtpl.vector import pdf_pages

DEVICE = devices.PAPER_PRO


def _build_all(root, want_pdf=True, options=None):
    made = {}
    for family in registry.families().values():
        opts = options or BuildOptions(want_pdf=want_pdf)
        ns_dir = root / family.key
        built = family.build(ns_dir, DEVICE, opts)
        manifest.write(
            ns_dir / manifest.MANIFEST_NAME,
            manifest.entries_for(family.key, built,
                                 categories=[family.category]),
            manifest.build_record(namespace=family.key, device_key=DEVICE.key,
                                  expected=family.expected_stems(opts),
                                  complete=not opts.variants,
                                  margin_px=opts.style.margin_px))
        made[family.key] = built
    return made


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("templates")
    return root, _build_all(root)


def test_every_family_produces_templates(built):
    _, made = built
    assert made
    for key, items in made.items():
        assert items, f"{key} built nothing"


def test_rasters_are_exactly_the_device_canvas(built):
    _, made = built
    for items in made.values():
        for b in items:
            img = Image.open(b.png)
            assert img.size == DEVICE.canvas(b.landscape)
            assert img.mode == "L", "templates must not carry an alpha channel"


def test_pages_are_white_where_nothing_is_drawn(built):
    _, made = built
    for items in made.values():
        for b in items:
            px = Image.open(b.png).convert("L")
            assert px.getpixel((0, 0)) >= 250
            assert px.getpixel((px.width - 1, px.height - 1)) >= 250


def test_pdf_pages_match_the_panel(built):
    _, made = built
    for items in made.values():
        for b in items:
            assert b.pdf.read_bytes()[:4] == b"%PDF"
            sizes = pdf_pages(b.pdf)
            assert len(sizes) == 1
            want = tuple(round(v, 2) for v in DEVICE.page_pt(b.landscape))
            assert all(abs(a - w) <= 0.1
                       for a, w in zip(sizes[0], want, strict=True))


def test_each_set_gets_a_valid_namespaced_manifest(built):
    root, made = built
    found = {p.name for p in namespaces(root)}
    assert found == set(made)
    for ns in namespaces(root):
        data = json.loads((ns / manifest.MANIFEST_NAME).read_text())
        assert manifest.validate(data["templates"]) == []
        assert all(t["filename"].startswith(f"{ns.name}/")
                   for t in data["templates"])


def test_doctor_passes(built):
    root, _ = built
    assert run_checks(root, DEVICE, verbose=False) == 0


def test_doctor_catches_a_broken_edge_convention(tmp_path, monkeypatch):
    """The verification must be able to fail, or it proves nothing.

    A three-inch error is injected into the one function that resolves published
    edges into path centres, the set is rebuilt, and the checker is expected to
    notice. It measures pixels and compares against the rule book, so it does.
    """
    import rmtpl.families.basketball.geometry as geometry

    original = geometry.to_path
    monkeypatch.setattr(geometry, "to_path",
                        lambda v, e, w: original(v, e, w) + 0.25)

    root = tmp_path / "broken"
    _build_all(root, want_pdf=False)
    assert run_checks(root, DEVICE, verbose=False) == 1


def test_builds_are_byte_reproducible(tmp_path):
    """Rebuild the same source twice and every artefact must hash the same.

    PDF writers stamp a creation time into their output, so this only holds
    because the build normalises it away. Without it the committed templates
    could never be checked against a rebuild.
    """
    digests = []
    for run in ("a", "b"):
        root = tmp_path / run
        made = _build_all(root)
        digests.append({
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for items in made.values() for b in items
            for p in (b.png, b.svg, b.pdf)
        })
    assert digests[0] == digests[1]


def test_doctor_catches_a_template_that_was_never_built(tmp_path):
    """A set with half of it missing must not look like a small set.

    Verification that only inspects the files it finds cannot tell the
    difference; the build record is what gives it something to compare against.
    """
    root = tmp_path / "short"
    family = registry.get("basketball")
    opts = BuildOptions(want_pdf=False)
    built = family.build(root / family.key, DEVICE, opts)[:-2]
    manifest.write(
        root / family.key / manifest.MANIFEST_NAME,
        manifest.entries_for(family.key, built, categories=[family.category]),
        manifest.build_record(namespace=family.key, device_key=DEVICE.key,
                              expected=family.expected_stems(opts),
                              complete=True))
    assert run_checks(root, DEVICE, verbose=False) == 1


def test_doctor_catches_a_globally_wrong_scale(tmp_path):
    """Render checks derive scale from the image so they can talk in feet.

    That verifies ratios, and a court drawn uniformly small is internally
    perfect. The absolute scale check is what notices, so it has to fail when
    the drawing does not match the fit its own build record describes.
    """
    from rmtpl.style import Style

    root = tmp_path / "small"
    family = registry.get("basketball")
    opts = BuildOptions(want_pdf=False, style=Style(margin_px=90))
    built = family.build(root / family.key, DEVICE, opts)
    manifest.write(
        root / family.key / manifest.MANIFEST_NAME,
        manifest.entries_for(family.key, built, categories=[family.category]),
        # the record claims the default margin; the drawing used 90
        manifest.build_record(namespace=family.key, device_key=DEVICE.key,
                              expected=family.expected_stems(opts),
                              margin_px=26.0))
    assert run_checks(root, DEVICE, verbose=False) == 1


def test_doctor_catches_a_pdf_in_the_wrong_orientation(tmp_path):
    root = tmp_path / "rot"
    _build_all(root)
    pdf_dir = root / "basketball" / "pdf"
    (pdf_dir / "nba-half-court.pdf").write_bytes(
        (pdf_dir / "nba-full-court.pdf").read_bytes())
    assert run_checks(root, DEVICE, verbose=False) == 1


def test_doctor_catches_a_set_built_for_another_device(tmp_path):
    root = tmp_path / "xdev"
    _build_all(root, want_pdf=False)
    assert run_checks(root, devices.RM2, verbose=False) == 1


def test_a_family_can_be_built_alone(tmp_path):
    family = registry.get("basketball")
    built = family.build(tmp_path / "basketball", DEVICE,
                         BuildOptions(want_pdf=False, variants=("nba",)))
    assert {b.stem.split("-")[0] for b in built} == {"nba"}
