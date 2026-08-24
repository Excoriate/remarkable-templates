"""Rule-book cross-checks for the basketball family.

These are the only tests that can catch a wrong dimension, and they work by
playing independently published figures off against each other rather than by
re-reading the numbers back out of the same table.
"""

from __future__ import annotations

import math

import pytest

from families.basketball import specs
from families.basketball.specs import Edge, inch, m

FOOT_CODES = ("nba", "ncaa", "nfhs")


@pytest.mark.parametrize("key", FOOT_CODES)
def test_basket_centre_reconstructs_from_equipment(key):
    """4'0" board + 6" to the ring's near edge + a 9" ring radius = 5'3"."""
    s = specs.get(key)
    assert s.backboard_face + inch(6) + s.rim_radius == pytest.approx(
        s.basket_centre, abs=inch(0.25))


@pytest.mark.parametrize("key", FOOT_CODES)
def test_free_throw_line_is_fifteen_feet_from_the_board(key):
    s = specs.get(key)
    assert s.backboard_face + 15.0 == pytest.approx(s.lane_length, abs=inch(0.25))


def test_fiba_basket_centre_reconstructs():
    """1.200 m board + 0.151 m ring offset + 0.2275 m ring radius = 1.575 m."""
    s = specs.FIBA
    assert s.backboard_face + m(0.151) + m(0.2275) == pytest.approx(
        s.basket_centre, abs=m(0.005))


def test_nba_corner_three_is_three_feet_from_the_sideline():
    assert specs.NBA.three_corner_from_sideline == pytest.approx(3.0, abs=inch(0.1))


def test_fiba_corner_three_is_ninety_centimetres_from_the_sideline():
    assert specs.FIBA.three_corner_from_sideline == pytest.approx(
        m(0.90), abs=m(0.002))


def test_nfhs_corner_segment_is_sixty_three_inches():
    """The rule gives 63"; the basket centre derives to 5'3". They must agree."""
    s = specs.NFHS
    assert s.basket_centre == pytest.approx(inch(63), abs=inch(0.1))
    assert s.three_corner_from_sideline == pytest.approx(inch(63), abs=inch(0.1))


def test_nfhs_free_throw_circle_is_tangent_to_the_three_point_arc():
    """19' + 6' and 5'3" + 19'9" are two ways to reach the same 25' point."""
    s = specs.NFHS
    assert s.lane_length + s.ft_circle_radius == pytest.approx(
        s.basket_centre + s.three_radius, abs=inch(0.1))


def test_ncaa_adopted_the_fiba_three_point_distance():
    assert specs.NCAA.three_radius == pytest.approx(
        specs.FIBA.three_radius, abs=inch(0.25))


def test_ncaa_lane_is_twelve_feet_not_sixteen():
    """A common error: the 16' lane is NBA and FIBA, never NCAA."""
    assert specs.NCAA.lane_width == 12.0
    assert specs.NFHS.lane_width == 12.0
    assert specs.NBA.lane_width == 16.0


def test_nfhs_has_no_restricted_area_arc():
    assert specs.NFHS.restricted_radius is None
    for key in ("nba", "ncaa", "fiba"):
        assert specs.get(key).restricted_radius is not None


@pytest.mark.parametrize("key", specs.ORDER)
def test_arc_reaches_its_corner_segments(key):
    s = specs.get(key)
    assert s.three_radius >= s.three_corner_x
    junction = (s.basket_centre if s.three_corner_tangent_at_basket
                else s.basket_centre + math.sqrt(
                    s.three_radius ** 2 - s.three_corner_x ** 2))
    assert 0 < junction < s.half_length


@pytest.mark.parametrize("key", specs.ORDER)
def test_markings_fit_inside_the_floor(key):
    s = specs.get(key)
    assert s.three_corner_x < s.width / 2.0
    assert s.basket_centre + s.three_radius < s.half_length
    assert s.lane_length < s.half_length
    assert s.lane_width < s.width
    for mark in s.lane_marks:
        assert 0 < mark.near < s.lane_length
        assert mark.near + mark.length <= s.lane_length


def test_line_widths_match_the_rule_books():
    for key in FOOT_CODES:
        assert specs.get(key).line_width == pytest.approx(inch(2))
    assert specs.FIBA.line_width == pytest.approx(m(0.05))


def test_every_spec_cites_its_sources():
    for key in specs.ORDER:
        s = specs.get(key)
        assert s.sources, f"{key} has no sources"
        assert all(u.startswith("http") for u in s.sources.values())
        assert s.edition


def test_edge_conventions_move_the_path_the_right_way():
    from families.basketball.geometry import to_path
    w = inch(2)
    assert to_path(10.0, Edge.OUTER, w) == pytest.approx(10.0 - w / 2)
    assert to_path(10.0, Edge.INNER, w) == pytest.approx(10.0 + w / 2)
    assert to_path(10.0, Edge.CENTRE, w) == 10.0


def test_generated_docs_stay_in_step_with_the_specs(tmp_path):
    from families.basketball.docgen import write_geometry_doc
    text = write_geometry_doc(tmp_path).read_text()
    for key in specs.ORDER:
        assert specs.get(key).label in text
    assert "22'1.75\"" in text or "22'1.75" in text   # NCAA three-point radius
    assert "no restricted arc" in text.lower() or "none" in text.lower()
