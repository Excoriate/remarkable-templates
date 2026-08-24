# Design notes

## The rule the templates follow

**Every template shows a complete, undistorted, true-scale region of the floor.**
Portrait shows the whole court. Landscape shows a whole half court, division
line included. Nothing is cropped and nothing is squeezed.

That single rule is what decides everything else, and it is worth saying why,
because the obvious alternative is tempting and this project started from a set
that took it.

## What the rM2-era templates did, and why not to copy it

The court templates that prompted this repository — Kyle Gentry's rM2 set,
still very good drawings — fill the page **width** with the court's 50 ft and
let the length run off the bottom. On an NBA portrait template at 1404 × 1872,
that means about 70 ft of a 94 ft court is on the page.

Measured off those files:

| | drawn scale | region shown |
| --- | --- | --- |
| NBA portrait | 26.08 px/ft | 50 × 70 ft — the far baseline is off the page |
| NBA landscape | 34.78 px/ft | 50 × 38 ft — stops short of the division line |
| High school portrait | 26.08 px/ft | both baskets, but the floor is 72 ft long, not 84 |

The trade is real: filling the width buys about 25% more drawing scale, and for
a half-court set nothing important is past 38 ft anyway.

Two things argue the other way. A portrait full court exists to diagram
full-court situations — press breaks, transition, an inbounds under the far
basket — and a court whose far baseline is off the page cannot show any of them;
at that point the landscape half court is both bigger and more complete. And the
high-school template fits both baskets by shortening the floor to 72 ft, which
keeps everything within 25 ft of each baseline correct and quietly compresses
the middle. That is invisible until you use the template to measure something.

So: the redraw takes the whole-region rule, and the legacy set is still
available for anyone who wants the extra scale — `just ingest <folder> legacy` rebuilds it
from your own copy of the files, at Paper Pro resolution.

That the two disagree is useful. The independently drawn courts were measured
pixel by pixel while researching this, and their NFHS geometry agreed with the
rule book on every dimension checked — free-throw line at 19 ft, lane 12 ft,
three-point apex at 25 ft, backboard at 4 ft, centre circle 6 ft. Two
unconnected sources landing on the same numbers is worth more than either alone.

## What the whole-region rule costs, and what it buys back

Fitting 94 × 50 ft to a 1620 × 2160 page leaves roughly 250 px of white down
each side. Two things use it:

- Notes. Personnel, a call, a score — the margin is the obvious place.
- reMarkable's toolbar strip, about 104 px on the left of the writing surface.
  With the court inset, the tool rail never lands on the paint.

Scale still works out fine: 22.3 px/ft on an NBA full court means the lane is
357 px across. Half-court templates run at 33–37 px/ft, roughly what the rM2
landscape templates managed, on a screen with half again as many pixels.

## Ink

Court lines are drawn at `#4a4a4a`, about 30% black, with lane marks and hash
marks lighter at `#8a8a8a`. A template is background: your ink should be the
darkest thing on the page. `--ink '#000000'` if you disagree.

## Line weight

A 2 in line is 3.7 px on a full-court portrait and 5.5 px on a half-court
landscape at Paper Pro density. The first is right; the second is heavy enough
to read as a colouring book. The renderer caps strokes near 4 px and floors them
near 1.8 px, so nothing vanishes on a small canvas and nothing bloats on a large
one.

Geometry is computed from the **true** painted width regardless of what gets
stroked. The visual weight changes; the edges do not move more than a pixel.

## Why SVG is built but not installed

Every template is rendered from an SVG, and both are kept: the vector is the
honest artefact, and it is what you would edit to make a variant. xochitl
prefers an SVG over a PNG when both exist, which is exactly why the installer
uploads PNGs only by default — the PNGs are rendered onto the panel's pixel grid
at a known scale, and how a given firmware rasterises an SVG has not been
measured here. `--svg` is one flag away for anyone who wants to find out.

## Where the drawing is least certain

Lane-space marks. Every rule book publishes the **size** of one and then defers
its **position** to a diagram printed as artwork — the NBA's has no leader-line
geometry in its text layer, the NFHS one has no text layer at all. The positions
drawn here come from standard court-marking practice, cross-checked against
measurements from an independently drawn set, and are good to about an inch.
Nothing else in the geometry depends on them, and
[basketball-court-geometry.md](basketball-court-geometry.md) says so at the bottom of every table.
