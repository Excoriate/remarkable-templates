"""The device-facing half: canvases, PNG ingest, and the manifest merge."""

from __future__ import annotations

import pytest
from PIL import Image

from rmtpl import devices, icons, manifest, raster
from rmtpl.family import BuiltTemplate

# --- devices --------------------------------------------------------------- #

def test_every_device_profile_is_portrait_shaped():
    for device in devices.DEVICES.values():
        assert device.width < device.height
        assert device.landscape == (device.height, device.width)
        w_pt, h_pt = device.page_pt(False)
        assert w_pt / h_pt == pytest.approx(device.width / device.height)


def test_paper_pro_page_size_in_points():
    w, h = devices.PAPER_PRO.page_pt(False)
    assert (round(w, 2), round(h, 2)) == (509.34, 679.13)


def test_unknown_device_fails_loudly():
    with pytest.raises(SystemExit, match="unknown device"):
        devices.get("kindle")


# --- ingest ---------------------------------------------------------------- #

def _png(tmp_path, name, size, mode="RGBA"):
    path = tmp_path / name
    Image.new(mode, size, (255, 255, 255, 0) if mode == "RGBA" else "white").save(path)
    return path


def test_same_aspect_source_scales_without_letterboxing(tmp_path):
    src = _png(tmp_path, "portrait.png", (1404, 1872))
    res = raster.normalise(src, tmp_path / "out.png", devices.PAPER_PRO)
    assert res.out_size == (1620, 2160)
    assert not res.letterboxed
    assert res.scale == pytest.approx(1620 / 1404)


def test_orientation_is_taken_from_the_source(tmp_path):
    res = raster.normalise(_png(tmp_path, "wide.png", (1872, 1404)),
                           tmp_path / "wide-out.png", devices.PAPER_PRO)
    assert res.landscape
    assert res.out_size == (2160, 1620)


def test_mismatched_aspect_is_letterboxed_and_says_so(tmp_path):
    res = raster.normalise(_png(tmp_path, "square.png", (1000, 1000)),
                           tmp_path / "sq.png", devices.PAPER_PRO)
    assert res.letterboxed
    assert res.out_size == (1620, 2160)


def test_transparency_is_flattened_onto_white(tmp_path):
    src = tmp_path / "alpha.png"
    Image.new("RGBA", (100, 133), (0, 0, 0, 0)).save(src)
    out = raster.normalise(src, tmp_path / "flat.png", devices.PAPER_PRO).out
    result = Image.open(out)
    assert result.mode == "L"
    assert result.getpixel((10, 10)) == 255


@pytest.mark.parametrize("raw,slug", [
    ("rM-nba-landscape", "rm-nba-landscape"),
    ("My  Weird Name!!", "my-weird-name"),
    ("", "template"),
])
def test_slugify(raw, slug):
    assert raster.slugify(raw) == slug


def test_titleise_keeps_generic_acronyms_only():
    """Subject vocabulary belongs to a family, not to the toolkit."""
    assert raster.titleise("a4-grid") == "A4 grid"
    assert raster.titleise("my-lined-page") == "My lined page"
    assert raster.titleise("nba-portrait") == "Nba portrait"
    extra = frozenset({"nba"})
    assert raster.titleise("nba-portrait", extra) == "NBA portrait"


def test_slugify_never_collapses_distinct_names_to_one_stem():
    """Transliteration can erase a name entirely; two erased names must not
    become the same file and silently overwrite each other."""
    a, b = raster.slugify("日本語コート"), raster.slugify("Ελληνικά")
    assert a != b
    assert a.startswith("template-") and b.startswith("template-")
    assert raster.slugify("") == "template"
    assert raster.SAFE_STEM.match(a) and raster.SAFE_STEM.match(b)


def test_unique_slugs_disambiguates_a_real_collision():
    names = ["Court 1", "court-1", "COURT  1"]
    stems = raster.unique_slugs(names)
    assert len(set(stems)) == 3, stems
    assert stems[0] == "court-1"


def test_a_set_built_for_another_device_says_which_one(tmp_path):
    """The common cause of a canvas mismatch is a leftover build. Name it."""
    from rmtpl.checks import Report, check_raster

    png = tmp_path / "leftover.png"
    Image.new("L", devices.PAPER_PRO.portrait, 255).save(png)
    rep = Report(verbose=False)
    check_raster(rep, png, devices.RM2.portrait)
    assert any("reMarkable Paper Pro" in f for f in rep.failures)


def test_band_ink_counts_only_the_named_edges():
    import numpy as np

    from rmtpl.checks import band_ink

    dark = np.zeros((10, 10), dtype=bool)
    assert band_ink(dark, left=3) == 0
    dark[5, 1] = True                       # inside the left band
    dark[5, 8] = True                       # outside it
    assert band_ink(dark, left=3) == 1
    assert band_ink(dark, right=3) == 1
    assert band_ink(dark, left=3, right=3) == 2
    assert band_ink(dark, top=1) == 0


# --- manifest -------------------------------------------------------------- #

def _built(stem, landscape=False):
    return BuiltTemplate(stem=stem, display=stem.replace("-", " ").title(),
                         landscape=landscape, canvas=(1620, 2160),
                         png=None)  # type: ignore[arg-type]


def test_entries_are_namespaced_and_orientation_aware():
    built = [_built("a"), _built("b", landscape=True), _built("c")]
    entries = manifest.entries_for("demo", built, categories=["Demo"])
    assert [e.filename for e in entries] == ["demo/a", "demo/b", "demo/c"]
    assert [e.landscape for e in entries] == [False, True, False]
    # icons cycle per orientation, so the first of each is the "Blank" glyph
    assert entries[0].icon_code == icons.BLANK_PORTRAIT
    assert entries[1].icon_code == icons.BLANK_LANDSCAPE
    assert entries[2].icon_code != entries[0].icon_code


def test_landscape_flag_is_omitted_for_portrait():
    d = manifest.TemplateEntry("N", "ns/x", "i", categories=["C"]).to_dict()
    assert "landscape" not in d
    d = manifest.TemplateEntry("N", "ns/x", "i", landscape=True,
                               categories=["C"]).to_dict()
    assert d["landscape"] is True


def test_merge_preserves_foreign_entries_and_is_idempotent():
    entries = manifest.entries_for("demo", [_built("a"), _built("b")],
                                   categories=["Demo"])
    device = {"templates": [
        {"name": "Blank", "filename": "Blank", "iconCode": "",
         "categories": ["Creative"]},
        {"name": "Stale", "filename": "demo/gone", "iconCode": "",
         "categories": ["Demo"]},
    ]}
    merged, removed, added = manifest.merge(device, entries, namespace="demo")
    assert (removed, added) == (1, 2)
    assert merged["templates"][0]["name"] == "Blank"

    again, removed2, _ = manifest.merge(merged, entries, namespace="demo")
    assert again == merged
    assert removed2 == 2


def test_merge_refuses_to_shadow_a_foreign_template_name():
    entries = manifest.entries_for("demo", [_built("a")], categories=["Demo"])
    device = {"templates": [
        {"name": entries[0].name, "filename": "SomeoneElses",
         "iconCode": "", "categories": ["Creative"]}]}
    with pytest.raises(ValueError, match="already exists"):
        manifest.merge(device, entries, namespace="demo")


def test_validate_rejects_a_filename_with_an_extension():
    problems = manifest.validate([
        {"name": "X", "filename": "ns/x.png", "iconCode": "",
         "categories": ["C"]}])
    assert any("extension" in p for p in problems)


def test_validate_rejects_two_entries_sharing_one_image():
    """Two picker entries on one file is what a dropped source looks like."""
    problems = manifest.validate([
        {"name": "A", "filename": "ns/x", "iconCode": "i", "categories": ["C"]},
        {"name": "B", "filename": "ns/x", "iconCode": "i", "categories": ["C"]}])
    assert any("duplicate filename" in p for p in problems)


def test_entries_for_refuses_a_stem_collision():
    with pytest.raises(ValueError, match="share a file stem"):
        manifest.entries_for("ns", [_built("x"), _built("x")],
                             categories=["C"])


def test_validate_rejects_a_multi_character_icon():
    problems = manifest.validate([
        {"name": "X", "filename": "ns/x", "iconCode": "ab",
         "categories": ["C"]}])
    assert any("one character" in p for p in problems)
