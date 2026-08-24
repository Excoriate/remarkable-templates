"""The generic PNG pipeline: any artwork, onto any reMarkable canvas."""

from __future__ import annotations

import pytest
from PIL import Image

from rmtpl import devices, raster


def _png(tmp_path, name, size, mode="RGBA"):
    path = tmp_path / name
    img = Image.new(mode, size, (255, 255, 255, 0) if mode == "RGBA" else "white")
    img.save(path)
    return path


def test_same_aspect_source_scales_without_letterboxing(tmp_path):
    src = _png(tmp_path, "portrait.png", (1404, 1872))
    res = raster.normalise(src, tmp_path / "out.png", devices.PAPER_PRO)
    assert res.out_size == (1620, 2160)
    assert not res.letterboxed
    assert res.scale == pytest.approx(1620 / 1404)


def test_orientation_is_taken_from_the_source(tmp_path):
    wide = _png(tmp_path, "wide.png", (1872, 1404))
    res = raster.normalise(wide, tmp_path / "wide-out.png", devices.PAPER_PRO)
    assert res.landscape
    assert res.out_size == (2160, 1620)


def test_mismatched_aspect_is_letterboxed_and_says_so(tmp_path):
    src = _png(tmp_path, "square.png", (1000, 1000))
    res = raster.normalise(src, tmp_path / "sq.png", devices.PAPER_PRO)
    assert res.letterboxed
    assert res.out_size == (1620, 2160)


def test_transparency_is_flattened_onto_white(tmp_path):
    src = tmp_path / "alpha.png"
    img = Image.new("RGBA", (100, 133), (0, 0, 0, 0))
    img.save(src)
    out = raster.normalise(src, tmp_path / "flat.png", devices.PAPER_PRO).out
    result = Image.open(out)
    assert result.mode == "L"
    assert result.getpixel((10, 10)) == 255


def test_every_device_profile_is_portrait_shaped(tmp_path):
    for device in devices.DEVICES.values():
        assert device.width < device.height
        assert device.landscape == (device.height, device.width)
        w_pt, h_pt = device.page_pt(False)
        assert w_pt / h_pt == pytest.approx(device.width / device.height)


def test_paper_pro_page_size_in_points():
    w, h = devices.PAPER_PRO.page_pt(False)
    assert (round(w, 2), round(h, 2)) == (509.34, 679.13)


@pytest.mark.parametrize("raw,slug", [
    ("rM-nba-landscape", "rm-nba-landscape"),
    ("My  Weird Name!!", "my-weird-name"),
    ("", "template"),
])
def test_slugify(raw, slug):
    assert raster.slugify(raw) == slug


def test_titleise_keeps_acronyms():
    assert raster.titleise("nba-portrait") == "NBA portrait"
    assert raster.titleise("hs-landscape") == "High school landscape"
