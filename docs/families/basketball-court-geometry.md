# Court geometry

*Generated from `src/families/basketball/specs.py` by `just docs`. Do not edit by hand: change the spec and regenerate, so the documentation and the drawings cannot disagree.*

Every figure below is the one used to draw the templates. Rule books dimension a marking to a particular **edge** of the painted line, never to its centre, so the edge is recorded next to each value and resolved once, in `to_path()`.

Where a rule book publishes a figure that is not quite consistent with its own diagram, the caveats say which one this project holds and why.

## NBA

**National Basketball Association** — Official 2025-26 NBA Playing Rules, Rule 1

| Dimension | Value | Measured |
| --- | --- | --- |
| Playing surface | 94' x 50' | inside the boundary lines |
| Line width | 2" | all markings |
| Division line | 47' | from either end line |
| Centre circle radius | 6' | outer edge |
| Inner circle radius | 2' | inner edge |
| Free-throw lane width | 16' | outer edge to outer edge |
| Free-throw line | 19' | end line to the far edge of the line |
| Free-throw circle radius | 6' | outer edge |
| Backboard face | 4' | from the end line |
| Basket centre | 5'3" | from the end line; the point the arcs are struck from |
| Ring radius | 9" | inside the ring |
| Three-point radius | 23'9" | outer edge, from the basket centre |
| Three-point corner line | 22' | outer edge, from the court centre line (3' from the sideline) |
| Arc meets corner line at | 14'2.37" | from the end line; **derived** so the two close cleanly |
| Restricted-area radius | 4' | outer edge, from the basket centre |
| Sideline mark 1 | 28' | from the end line, 3' onto the court |

Lane markings (from the end line, along the lane line):

| Mark | Starts at | Length | Depth |
| --- | --- | --- | --- |
| neutral zone | 7' | 1' | 6" |
| lane-space mark | 11' | 2" | 6" |
| lane-space mark | 14'2" | 2" | 6" |

**Sources**

- rule text: <https://official.nba.com/rule-no-1-court-dimensions-equipment>
- court diagram: <https://cdn.nba.com/manage/2026/01/Official-2025-26-NBA-Playing-Rules.pdf>

**What to know**

- The official diagram labels the arc/corner junction '14 FEET'. Holding the published 23'9" radius, 22'0" corner offset and 5'3" basket centre puts true tangency at 14'2.4". The radius is held and the junction is derived, so the arc closes cleanly on the straight.
- Lane-space mark positions are not published in rule text; sizes (2" x 6") and the 1'0" neutral zone are.

## NCAA

**National Collegiate Athletic Association (men's)** — 2026-27 NCAA Men's Basketball Rules Book, Rule 1

| Dimension | Value | Measured |
| --- | --- | --- |
| Playing surface | 94' x 50' | inside the boundary lines |
| Line width | 2" | all markings |
| Division line | 47' | from either end line |
| Centre circle radius | 6' | outer edge |
| Free-throw lane width | 12' | outer edge to outer edge |
| Free-throw line | 19' | end line to the far edge of the line |
| Free-throw circle radius | 6' | outer edge |
| Backboard face | 4' | from the end line |
| Basket centre | 5'3" | from the end line; the point the arcs are struck from |
| Ring radius | 9" | inside the ring |
| Three-point radius | 22'1.75" | outer edge, from the basket centre |
| Three-point corner line | 21'7.88" | outer edge, from the court centre line (3'4.12" from the sideline) |
| Arc meets corner line at | 9'10.57" | from the end line; **derived** so the two close cleanly |
| Restricted-area radius | 4' | inner edge, from the basket centre |
| Sideline mark 1 | 28' | from the end line, 3' onto the court |

Lane markings (from the end line, along the lane line):

| Mark | Starts at | Length | Depth |
| --- | --- | --- | --- |
| neutral zone | 7' | 1' | 8" |
| lane-space mark | 11' | 2" | 8" |
| lane-space mark | 14'2" | 2" | 8" |
| lane-space mark | 17'4" | 2" | 8" |

**Sources**

- men's rules: <https://ncaaorg.s3.amazonaws.com/championships/sports/basketball/rules/men/PRMBB_RulesBook.pdf>
- court diagram: <https://ncaaorg.s3.amazonaws.com/championships/sports/basketball/rules/common/PRXBB_CourtDiagram.pdf>

**What to know**

- The lane is 12'0" for both men and women. The 16' lane is NBA/FIBA, not NCAA.
- The restricted-area arc is a men's marking. The official diagram labels it 'RESTRICTED AREA (MEN ONLY)'; a women's-only court omits it.
- The diagram prints the arc/corner junction as 9'10.75"; the two published radii give 9'10.57". The diagram is marked 'not drawn to scale', so the radii are held and the junction derived.
- Men's and women's three-point lines are now identical at 22'1.75" (men from 2019-20 DI, women from 2021-22).
- NCAA rule text specifies only the solid outer semicircle of the free-throw circle. The broken inner half is drawn here because it is universal lining practice, not because a rule requires it.

## FIBA

**Fédération Internationale de Basketball** — FIBA Official Basketball Rules 2026, Art. 2

| Dimension | Value | Measured |
| --- | --- | --- |
| Playing surface | 28.000 m x 15.000 m | inside the boundary lines |
| Line width | 0.050 m | all markings |
| Division line | 14.000 m | from either end line |
| Centre circle radius | 1.800 m | outer edge |
| Free-throw lane width | 4.900 m | outer edge to outer edge |
| Free-throw line | 5.800 m | end line to the far edge of the line |
| Free-throw circle radius | 1.800 m | outer edge |
| Backboard face | 1.200 m | from the end line |
| Basket centre | 1.575 m | from the end line; the point the arcs are struck from |
| Ring radius | 0.227 m | inside the ring |
| Three-point radius | 6.750 m | outer edge, from the basket centre |
| Three-point corner line | 6.600 m | outer edge, from the court centre line (0.900 m from the sideline) |
| Arc meets corner line at | 2.990 m | from the end line; **derived** so the two close cleanly |
| Restricted-area radius | 1.250 m | inner edge, from the basket centre |
| Sideline mark 1 | 8.325 m | from the end line, 0.150 m outside the sideline |

Lane markings (from the end line, along the lane line):

| Mark | Starts at | Length | Depth |
| --- | --- | --- | --- |
| lane-space mark | 1.750 m | 0.050 m | 0.100 m |
| neutral zone | 2.600 m | 0.400 m | 0.100 m |
| lane-space mark | 3.850 m | 0.050 m | 0.100 m |
| lane-space mark | 4.700 m | 0.050 m | 0.100 m |

**Sources**

- rules: <https://assets.fiba.basketball/image/upload/documents-corporate-fiba-official-rules-2026-v1-1.pdf>
- equipment: <https://assets.fiba.basketball/image/upload/documents-corporate-fiba-official-rules-2026-equipment-v1-0.pdf>

**What to know**

- Art. 2 geometry is unchanged between the 2024 and 2026 editions; the 2026 change was to line colour only.
- The no-charge semicircle reads 1.30 m to the outer edge in the 2022 and later editions and 1.25 m to the inner edge before that. With 5 cm lines these describe the same physical circle.
- The 8.325 m sideline mark is the throw-in line. Editions from 2024 carry four of them, two per sideline; the 2022 edition had two.
- Free-throw rebound-place positions are published only as diagram artwork; the sizes (0.05 m x 0.10 m marks, 0.40 m neutral zone) are in the rule text.

## High school

**National Federation of State High School Associations** — NFHS Basketball Rules Book 2026-27, Rule 1

| Dimension | Value | Measured |
| --- | --- | --- |
| Playing surface | 84' x 50' | inside the boundary lines |
| Line width | 2" | all markings |
| Division line | 42' | from either end line |
| Centre circle radius | 6' | outer edge |
| Free-throw lane width | 12' | outer edge to outer edge |
| Free-throw line | 19' | end line to the far edge of the line |
| Free-throw circle radius | 6' | outer edge |
| Backboard face | 4' | from the end line |
| Basket centre | 5'3" | from the end line; the point the arcs are struck from |
| Ring radius | 9" | inside the ring |
| Three-point radius | 19'9" | outer edge, from the basket centre |
| Three-point corner line | 19'9" | outer edge, from the court centre line (5'3" from the sideline) |
| Arc meets corner line at | 5'3" | from the end line; **derived** so the two close cleanly |
| Restricted-area arc | none | this code does not define one |

Lane markings (from the end line, along the lane line):

| Mark | Starts at | Length | Depth |
| --- | --- | --- | --- |
| neutral zone | 7' | 1' | 8" |
| lane-space mark | 11' | 2" | 8" |
| lane-space mark | 14'2" | 2" | 8" |
| lane-space mark | 17'4" | 2" | 8" |

**Sources**

- rule 1 text: <https://abilenebasketballrefs.com/nfhs-rules-book/nfhs-rules-book-rule-1-court-and-equipment/>
- court diagram: <https://assets.nfhs.org/umbraco/media/7213108/basketball-court-diagram.pdf>
- lining practice: <https://media.hillyard.com/docs/lit-hillyard-sports-floor-layout-and-lining-guide.pdf>

**What to know**

- 84 x 50 ft is the NFHS 'ideal' high-school court; 94 x 50 is the permitted maximum. NFHS publishes no minimum.
- NFHS has no restricted-area arc. Sources that give one for high school are applying the NCAA/NBA figure by mistake.
- The three-point line is not a pure semicircle: Rule 1-4-1 extends it with straight segments 63" long, perpendicular to the end line, which are exactly tangent to the arc at the basket centre.
- The free-throw circle and the three-point arc are exactly tangent at 25'0" from the end line: 5'3" + 19'9" = 19'0" + 6'0".
- NFHS specifies no sideline hash marks; the '28-foot mark' officials refer to is the coaching-box line, which is drawn off the court.

## What is not published anywhere

Every rule book here gives the **size** of a free-throw lane-space mark and then defers its **position** to a court diagram printed as artwork. The NBA's diagram has no leader-line geometry in its text layer; the NFHS diagram has no text layer at all. The positions this project draws therefore come from standard court-marking practice, and were cross-checked against measurements taken from an independently drawn court set. They are good to roughly an inch. Nothing else in the tables above depends on them.

