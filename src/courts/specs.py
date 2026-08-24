"""Basketball court geometry, taken from the governing rule books.

Every dimension below is traceable. Each :class:`CourtSpec` carries a
``sources`` mapping and a ``caveats`` list; ``docs/court-geometry.md`` is
generated from these fields, so the published documentation cannot drift away
from the numbers actually used to draw the courts.

Units
-----
All lengths are stored in **feet**. FIBA's rule book is metric, so its values
are written as ``m(x)`` and converted with the exact factor 1 ft = 0.3048 m.
``native_unit`` records which unit the rule book itself uses, so the docs can
quote the original figure.

Measurement edges
-----------------
Rule books dimension a marking to a specific *edge* of the painted line, not to
its centre. A drawing program strokes along a path centre. Mixing the two is the
classic way to end up with a court that is a line-width wrong everywhere, so the
convention is recorded per dimension via :class:`Edge` and resolved once, in
``geometry.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

FT_PER_M = 1.0 / 0.3048


def m(metres: float) -> float:
    """Metres -> feet (exact factor)."""
    return metres * FT_PER_M


def inch(inches: float) -> float:
    """Inches -> feet."""
    return inches / 12.0


class Edge(str, Enum):
    """Which edge of a painted line a published dimension refers to."""

    OUTER = "outer"   # far edge, measured away from the reference point
    INNER = "inner"   # near edge, measured toward the reference point
    CENTRE = "centre"  # line centre (rare; used when a rule book is silent)


@dataclass(frozen=True)
class LaneMark:
    """One marking along a free-throw lane boundary line.

    ``near`` is the distance from the inside edge of the end line to the edge of
    the mark closest to that end line; ``length`` runs along the lane; ``depth``
    is how far the mark protrudes sideways, away from the lane.
    """

    near: float
    length: float
    depth: float
    filled: bool = False   # True for the neutral-zone block


@dataclass(frozen=True)
class CourtSpec:
    key: str
    label: str
    body: str
    edition: str

    # --- playing surface, measured inside the boundary lines ---------------
    length: float
    width: float

    # --- line weights ------------------------------------------------------
    line_width: float
    boundary_line_width: float

    # --- basket ------------------------------------------------------------
    basket_centre: float          # end line inside edge -> centre of the ring
    backboard_face: float         # end line inside edge -> front face of board
    backboard_width: float
    rim_radius: float

    # --- free-throw lane ---------------------------------------------------
    lane_width: float             # outer edge to outer edge of the lane lines
    lane_length: float            # end line -> far edge of the free-throw line
    ft_circle_radius: float
    ft_circle_edge: Edge
    ft_circle_dashed_inner: bool

    # --- three-point line --------------------------------------------------
    three_radius: float           # from the basket centre
    three_edge: Edge
    three_corner_x: float         # |x| of the straight corner segment
    three_corner_edge: Edge
    #: NFHS runs its corner segments only as far as the basket centre, where the
    #: arc is exactly tangent. Everyone else meets the arc further up the court.
    three_corner_tangent_at_basket: bool

    # --- centre circle -----------------------------------------------------
    centre_circle_radius: float
    centre_circle_edge: Edge
    inner_circle_radius: float | None

    # --- restricted (no-charge) area ---------------------------------------
    restricted_radius: float | None
    restricted_edge: Edge | None

    # --- discretionary markings -------------------------------------------
    lane_marks: tuple[LaneMark, ...]
    #: ``(distance from the end line, mark length, drawn inside the court)``
    sideline_hashes: tuple[tuple[float, float, bool], ...]
    #: ``(|x|, y, length, runs perpendicular to the end line)`` floor marks
    #: near each basket, mirrored left/right. The NBA lower defensive box.
    floor_marks: tuple[tuple[float, float, float, bool], ...]

    native_unit: str
    sources: dict[str, str] = field(default_factory=dict)
    caveats: tuple[str, ...] = ()

    # ------------------------------------------------------------------ #
    @property
    def half_length(self) -> float:
        return self.length / 2.0

    @property
    def three_corner_from_sideline(self) -> float:
        return self.width / 2.0 - self.three_corner_x


# --------------------------------------------------------------------------- #
# Lane markings.
#
# Every rule book publishes the *size* of a lane-space mark and says nothing
# about where along the lane it sits, deferring to a court diagram that is
# printed as artwork. The positions below therefore come from standard
# court-marking practice rather than from rule text, and were cross-checked
# against measurements taken from an independently drawn court. They are
# accurate to about an inch, and are flagged as such in the caveats.
# --------------------------------------------------------------------------- #

_LANE_MARKS_12FT = (
    LaneMark(near=7.0, length=1.0, depth=inch(8), filled=True),      # neutral zone
    LaneMark(near=11.0, length=inch(2), depth=inch(8)),
    LaneMark(near=14.0 + inch(2), length=inch(2), depth=inch(8)),
    LaneMark(near=17.0 + inch(4), length=inch(2), depth=inch(8)),
)

_LANE_MARKS_NBA = (
    LaneMark(near=7.0, length=1.0, depth=inch(6), filled=True),      # neutral zone
    LaneMark(near=11.0, length=inch(2), depth=inch(6)),
    LaneMark(near=14.0 + inch(2), length=inch(2), depth=inch(6)),
)

_LANE_MARKS_FIBA = (
    LaneMark(near=m(1.75), length=m(0.05), depth=m(0.10)),
    LaneMark(near=m(2.60), length=m(0.40), depth=m(0.10), filled=True),
    LaneMark(near=m(3.85), length=m(0.05), depth=m(0.10)),
    LaneMark(near=m(4.70), length=m(0.05), depth=m(0.10)),
)


NBA = CourtSpec(
    key="nba",
    label="NBA",
    body="National Basketball Association",
    edition="Official 2025-26 NBA Playing Rules, Rule 1",
    length=94.0,
    width=50.0,
    line_width=inch(2),
    boundary_line_width=inch(2),
    basket_centre=5.25,
    backboard_face=4.0,
    backboard_width=6.0,
    rim_radius=0.75,
    lane_width=16.0,
    lane_length=19.0,
    ft_circle_radius=6.0,
    ft_circle_edge=Edge.OUTER,
    ft_circle_dashed_inner=True,
    three_radius=23.75,
    three_edge=Edge.OUTER,
    three_corner_x=22.0,
    three_corner_edge=Edge.OUTER,
    three_corner_tangent_at_basket=False,
    centre_circle_radius=6.0,
    centre_circle_edge=Edge.OUTER,
    inner_circle_radius=2.0,
    restricted_radius=4.0,
    restricted_edge=Edge.OUTER,
    lane_marks=_LANE_MARKS_NBA,
    sideline_hashes=((28.0, 3.0, True),),
    floor_marks=(
        (11.0, 0.0, 0.5, True),    # Rule 1 I(6): 3' from the lane line
        (11.0, 13.0, 0.5, False),  # Rule 1 I(7): 13' from the baseline
    ),
    native_unit="ft",
    sources={
        "rule text": "https://official.nba.com/rule-no-1-court-dimensions-equipment",
        "court diagram": "https://cdn.nba.com/manage/2026/01/Official-2025-26-NBA-Playing-Rules.pdf",
    },
    caveats=(
        "The official diagram labels the arc/corner junction '14 FEET'. Holding "
        "the published 23'9\" radius, 22'0\" corner offset and 5'3\" basket "
        "centre puts true tangency at 14'2.4\". The radius is held and the "
        "junction is derived, so the arc closes cleanly on the straight.",
        "Lane-space mark positions are not published in rule text; sizes "
        "(2\" x 6\") and the 1'0\" neutral zone are.",
    ),
)


NCAA = CourtSpec(
    key="ncaa",
    label="NCAA",
    body="National Collegiate Athletic Association (men's)",
    edition="2026-27 NCAA Men's Basketball Rules Book, Rule 1",
    length=94.0,
    width=50.0,
    line_width=inch(2),
    boundary_line_width=inch(2),
    basket_centre=5.25,
    backboard_face=4.0,
    backboard_width=6.0,
    rim_radius=0.75,
    lane_width=12.0,
    lane_length=19.0,
    ft_circle_radius=6.0,
    ft_circle_edge=Edge.OUTER,
    ft_circle_dashed_inner=True,
    three_radius=22.0 + inch(1.75),
    three_edge=Edge.OUTER,
    three_corner_x=21.0 + inch(7.875),
    three_corner_edge=Edge.OUTER,
    three_corner_tangent_at_basket=False,
    centre_circle_radius=6.0,
    centre_circle_edge=Edge.OUTER,
    inner_circle_radius=None,
    restricted_radius=4.0,
    restricted_edge=Edge.INNER,
    lane_marks=_LANE_MARKS_12FT,
    sideline_hashes=((28.0, 3.0, True),),
    floor_marks=(),
    native_unit="ft",
    sources={
        "men's rules": "https://ncaaorg.s3.amazonaws.com/championships/sports/basketball/rules/men/PRMBB_RulesBook.pdf",
        "court diagram": "https://ncaaorg.s3.amazonaws.com/championships/sports/basketball/rules/common/PRXBB_CourtDiagram.pdf",
    },
    caveats=(
        "The lane is 12'0\" for both men and women. The 16' lane is NBA/FIBA, "
        "not NCAA.",
        "The restricted-area arc is a men's marking. The official diagram "
        "labels it 'RESTRICTED AREA (MEN ONLY)'; a women's-only court omits it.",
        "The diagram prints the arc/corner junction as 9'10.75\"; the two "
        "published radii give 9'10.57\". The diagram is marked 'not drawn to "
        "scale', so the radii are held and the junction derived.",
        "Men's and women's three-point lines are now identical at 22'1.75\" "
        "(men from 2019-20 DI, women from 2021-22).",
        "NCAA rule text specifies only the solid outer semicircle of the "
        "free-throw circle. The broken inner half is drawn here because it is "
        "universal lining practice, not because a rule requires it.",
    ),
)


NFHS = CourtSpec(
    key="nfhs",
    label="High school",
    body="National Federation of State High School Associations",
    edition="NFHS Basketball Rules Book 2026-27, Rule 1",
    length=84.0,
    width=50.0,
    line_width=inch(2),
    boundary_line_width=inch(2),
    basket_centre=5.25,
    backboard_face=4.0,
    backboard_width=6.0,
    rim_radius=0.75,
    lane_width=12.0,
    lane_length=19.0,
    ft_circle_radius=6.0,
    ft_circle_edge=Edge.OUTER,
    ft_circle_dashed_inner=True,
    three_radius=19.75,
    three_edge=Edge.OUTER,
    three_corner_x=19.75,
    three_corner_edge=Edge.OUTER,
    three_corner_tangent_at_basket=True,
    centre_circle_radius=6.0,
    centre_circle_edge=Edge.OUTER,
    inner_circle_radius=None,
    restricted_radius=None,
    restricted_edge=None,
    lane_marks=_LANE_MARKS_12FT,
    sideline_hashes=(),
    floor_marks=(),
    native_unit="ft",
    sources={
        "rule 1 text": "https://abilenebasketballrefs.com/nfhs-rules-book/nfhs-rules-book-rule-1-court-and-equipment/",
        "court diagram": "https://assets.nfhs.org/umbraco/media/7213108/basketball-court-diagram.pdf",
        "lining practice": "https://media.hillyard.com/docs/lit-hillyard-sports-floor-layout-and-lining-guide.pdf",
    },
    caveats=(
        "84 x 50 ft is the NFHS 'ideal' high-school court; 94 x 50 is the "
        "permitted maximum. NFHS publishes no minimum.",
        "NFHS has no restricted-area arc. Sources that give one for high "
        "school are applying the NCAA/NBA figure by mistake.",
        "The three-point line is not a pure semicircle: Rule 1-4-1 extends it "
        "with straight segments 63\" long, perpendicular to the end line, which "
        "are exactly tangent to the arc at the basket centre.",
        "The free-throw circle and the three-point arc are exactly tangent at "
        "25'0\" from the end line: 5'3\" + 19'9\" = 19'0\" + 6'0\".",
        "NFHS specifies no sideline hash marks; the '28-foot mark' officials "
        "refer to is the coaching-box line, which is drawn off the court.",
    ),
)


FIBA = CourtSpec(
    key="fiba",
    label="FIBA",
    body="Fédération Internationale de Basketball",
    edition="FIBA Official Basketball Rules 2026, Art. 2",
    length=m(28.0),
    width=m(15.0),
    line_width=m(0.05),
    boundary_line_width=m(0.05),
    basket_centre=m(1.575),
    backboard_face=m(1.20),
    backboard_width=m(1.80),
    rim_radius=m(0.2275),
    lane_width=m(4.90),
    lane_length=m(5.80),
    ft_circle_radius=m(1.80),
    ft_circle_edge=Edge.OUTER,
    ft_circle_dashed_inner=True,
    three_radius=m(6.75),
    three_edge=Edge.OUTER,
    three_corner_x=m(6.60),
    three_corner_edge=Edge.OUTER,
    three_corner_tangent_at_basket=False,
    centre_circle_radius=m(1.80),
    centre_circle_edge=Edge.OUTER,
    inner_circle_radius=None,
    restricted_radius=m(1.25),
    restricted_edge=Edge.INNER,
    lane_marks=_LANE_MARKS_FIBA,
    sideline_hashes=((m(8.325), m(0.15), False),),
    floor_marks=(),
    native_unit="m",
    sources={
        "rules": "https://assets.fiba.basketball/image/upload/documents-corporate-fiba-official-rules-2026-v1-1.pdf",
        "equipment": "https://assets.fiba.basketball/image/upload/documents-corporate-fiba-official-rules-2026-equipment-v1-0.pdf",
    },
    caveats=(
        "Art. 2 geometry is unchanged between the 2024 and 2026 editions; the "
        "2026 change was to line colour only.",
        "The no-charge semicircle reads 1.30 m to the outer edge in the 2022 "
        "and later editions and 1.25 m to the inner edge before that. With 5 cm "
        "lines these describe the same physical circle.",
        "The 8.325 m sideline mark is the throw-in line. Editions from 2024 "
        "carry four of them, two per sideline; the 2022 edition had two.",
        "Free-throw rebound-place positions are published only as diagram "
        "artwork; the sizes (0.05 m x 0.10 m marks, 0.40 m neutral zone) are in "
        "the rule text.",
    ),
)


SPECS: dict[str, CourtSpec] = {s.key: s for s in (NBA, NCAA, FIBA, NFHS)}
ORDER = ("nba", "ncaa", "fiba", "nfhs")


def get(key: str) -> CourtSpec:
    try:
        return SPECS[key]
    except KeyError:
        raise SystemExit(
            f"unknown ruleset {key!r}; choose one of: {', '.join(ORDER)}"
        ) from None
