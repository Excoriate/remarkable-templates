# remarkable-templates

Basketball court templates for reMarkable tablets, drawn from the rule books
rather than traced, and the small toolkit that builds them.

Eight templates ship here — NBA, NCAA, FIBA and NFHS high school, each as a
full court in portrait and a half court in landscape — rendered natively at
1620 × 2160 for the reMarkable Paper Pro. Every line is placed from a published
dimension, and the build verifies its own output by measuring the finished
pixels back into feet and comparing them with the rule book.

![Every template in the set](docs/images/contact-sheet.png)

The same toolkit turns *any* folder of PNGs into reMarkable templates, so if you
have artwork of your own, point `just ingest` at it.

---

## Quick start

```bash
just setup                 # create .venv and install dependencies
just all                   # build, document and verify
just install               # copy onto a tablet over SSH
```

`just install` needs developer mode and SSH. If you would rather not enable
either, `templates/pdf/` holds the same courts as PDFs you can drop into the
reMarkable app — see [docs/install.md](docs/install.md) for all three routes and
their trade-offs.

## What is in the box

| | Portrait — full court | Landscape — half court |
| --- | --- | --- |
| **NBA** | 94 × 50 ft, 16 ft lane, 23 ft 9 in arc | to the division line |
| **NCAA** | 94 × 50 ft, 12 ft lane, 22 ft 1¾ in arc | men's restricted arc |
| **FIBA** | 28 × 15 m, 4.90 m lane, 6.75 m arc | no-charge semicircle |
| **High school (NFHS)** | 84 × 50 ft, 12 ft lane, 19 ft 9 in arc | no restricted arc |

Built artefacts live in `templates/`:

```
templates/png/          the templates themselves, 1620x2160 / 2160x1620
templates/svg/          the same drawings as vectors, for editing or reuse
templates/pdf/          per-court PDFs, plus one bundle per orientation
templates/templates.d/  the templates.json fragment the installer merges in
```

## Why these are drawn the way they are

**Nothing is cropped and nothing is squeezed.** A portrait template shows the
whole floor end to end; a landscape template shows a complete half court,
division line included. That rules out the two compromises court templates
usually make — a full court that runs off the bottom of the page, or one
squeezed lengthwise until both baskets fit. A cropped court cannot diagram a
press break, and a squeezed one puts every distance on it slightly wrong.

The cost is honest: fitting a 94 ft court to the page leaves about 250 px of
white down each side. That margin is useful. It is where personnel notes go, and
it is where reMarkable's own toolbar strip sits, so the tool rail never lands on
top of the paint.

**Grey lines, not black.** Court markings are drawn at about 30% black so your
ink stays the darkest thing on the page. `--ink` changes it if you disagree.

**Line weight follows the rule book, within reason.** A 2 in line at Paper Pro
density is 3.7 px on a full court and 5.5 px on a half court; the renderer caps
it around 4 px so a half-court template does not turn into a colouring book.
Geometry is computed from the true painted width regardless, so the *edges* stay
where the rule book puts them.

More on all of this, including a side-by-side with the rM2-era templates this
project started from, in [docs/design-notes.md](docs/design-notes.md).

## Accuracy

Rule books dimension a marking to a specific **edge** of the painted line — the
NBA's three-point arc is 23 ft 9 in to the *outside* of a 2 in line — while a
drawing program strokes along a path *centre*. Every published figure is
converted once, in `to_path()`, and the conversion is recorded per dimension.
Get that wrong and a court is a line-width off everywhere.

[docs/court-geometry.md](docs/court-geometry.md) lists every number used, with
its source and its measurement edge. It is generated from
`src/courts/specs.py`, so it cannot drift away from what is actually drawn.

Where a rule book disagrees with its own diagram, the published radii win and
the junction is derived. The NBA diagram labels the arc/corner junction "14
FEET"; holding the 23 ft 9 in radius, the 22 ft corner offset and the 5 ft 3 in
basket centre puts true tangency at 14 ft 2.4 in. Rounding the junction instead
would leave the arc and the straight not quite meeting.

`just check` runs three kinds of verification:

- **Rule-book cross-checks** play independently published figures against each
  other. The NBA states separately that the backboard stands 4 ft from the end
  line, that the ring's near edge is 6 in from the board, and that the ring is
  18 in across; those must reconstruct the 5 ft 3 in basket centre the arcs are
  struck from. This is the only check that can catch a mistyped dimension.
- **Contract checks** confirm each file is what a tablet will accept: exact
  canvas size, opaque 8-bit raster, a manifest that parses and points at files
  that exist.
- **Render checks** re-measure the finished PNGs and report what they find in
  feet, deriving scale from the image itself. They share no code with the
  drawing path, and the test suite proves they can fail by injecting a
  three-inch error into the edge conversion and asserting the checker notices.

**Builds are byte-reproducible.** Rebuild from source and every PNG, SVG and
PDF hashes the same as the file committed here, so you can verify the artwork
against the code that claims to produce it rather than taking it on trust. PDF
writers stamp a creation time into their output; the build strips it, and CI
fails if the committed `templates/` and `docs/` are not exactly what the current
source produces.

## Using the toolkit on your own artwork

```bash
just ingest ~/Downloads/my-templates mine 'Mine '
just install                       # or install/install.sh --host <ip>
```

`ingest` resamples each PNG onto the target canvas, takes orientation from the
source image, flattens transparency onto white, writes an 8-bit greyscale PNG
and a matching PDF, and generates a `templates.json` fragment. Sources that do
not share the screen's 3:4 aspect ratio are letterboxed onto white by default
and the build says so; `--fit cover` crops instead, `--fit stretch` distorts.

Build for another device with `RM_DEVICE=rm2` or `RM_DEVICE=rmppm`
(Paper Pro Move).

## How the install stays installed

A firmware update replaces `/usr/share`, which is where reMarkable keeps its
templates — the usual reason custom templates vanish. The installer puts the
artwork under `/home/root/.local/share/remarkable/templates/`, which updates
leave alone, and symlinks it into place. After an update, `just relink` restores
the link and the manifest entries without re-copying anything.

`templates.json` is never overwritten. It is fetched from the tablet, merged on
your machine, written back, and then read again from the device to verify. The
file is backed up on the tablet before any change, and the very first install
also keeps a pristine `templates.json.orig`. Only entries under this project's
own namespace directories are ever replaced; the installer refuses to run if one
of its template names would shadow something already on your device.

## Licence

The code is MIT ([LICENSE](LICENSE)). The generated court templates in
`templates/` are released into the public domain under CC0 1.0
([LICENSE-ART](LICENSE-ART)) — court geometry is a published fact, and these
drawings are an original rendering of it, so use them for anything.

The rM2-era court PNGs this project started from are the work of Kyle Gentry and
are **not** redistributed here. `just legacy <folder>` runs the pipeline over
your own copy of them and writes to a git-ignored directory. See
[NOTICE.md](NOTICE.md).

## Requirements

Python 3.10+, and `cairosvg`, `pillow` and `numpy` (installed by `just setup`).
`just` is optional — every recipe is a one-line wrapper over `python -m rmtpl`.
Installing to a tablet needs `ssh` and `scp`; nothing is required on the device
itself, which is why the manifest merge runs on your machine.
