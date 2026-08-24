# User guide

Everything you can do with this repository, in the order you are likely to want
it. Every command here was run against a clean checkout before being written
down.

- [Setup](#setup)
- [Building](#building)
- [Getting templates onto a tablet](#getting-templates-onto-a-tablet)
- [Your own artwork](#your-own-artwork)
- [Other devices](#other-devices)
- [Styling](#styling)
- [Verification](#verification)
- [Every recipe](#every-recipe)
- [Troubleshooting](#troubleshooting)

## Setup

Python 3.10 or newer. [`just`](https://github.com/casey/just) is optional —
every recipe is one line, and the Justfile shows you the command it runs.

```bash
git clone https://github.com/Excoriate/remarkable-templates.git
cd remarkable-templates
just setup
```

That creates `.venv` and installs the package in editable mode. Without `just`:

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

Installing to a tablet also needs `ssh` and `scp`. Nothing is required on the
device itself.

## Building

```bash
just list      # what this checkout knows about
just build     # render every family
just all       # build, generate docs, bundle PDFs, preview, verify, test
```

`just list` is the orientation command:

```
families
  basketball     Basketball
                 Rule-book court diagrams: NBA, NCAA, FIBA and high school.
                 variants: nba, ncaa, fiba, nfhs

devices
  rmpp           reMarkable Paper Pro  1620x2160 portrait, 229 PPI
  rm2            reMarkable 1 / 2  1404x1872 portrait, 226 PPI
  rmppm          reMarkable Paper Pro Move  954x1696 portrait, 264 PPI

built sets under .../templates
  basketball     8 template(s)
```

`just build` writes one directory per set:

```
templates/basketball/
├── manifest.json     the templates.json entries the installer merges in
├── png/              what the tablet renders — exact device canvas, 8-bit, opaque
├── svg/              the same drawings as vectors, for editing or reuse
└── pdf/              one per template, plus a bundle per orientation
```

Build a single family with `just build basketball`. Skip the PDFs during
iteration with `python -m rmtpl build --no-pdf`.

Builds are byte-reproducible. Rebuild and the files hash the same as the ones
committed, which is why CI can fail when the committed output is stale.

## Getting templates onto a tablet

Two routes. The first asks nothing of your tablet; the second puts the templates
in the built-in picker.

| | Developer mode | In the template picker | Survives a firmware update |
| --- | --- | --- | --- |
| **PDF** | no | no — it is a notebook | yes |
| **SSH** | yes | yes | yes, via `just relink` |

### PDF — no developer mode

`templates/<set>/pdf/` holds one PDF per template plus a bundle per orientation.
Drag one into the reMarkable desktop or mobile app and it syncs as a notebook
you write on top of.

```bash
just bundle 10     # ten pages of each template, ready to fill
```

Pages are sized to the panel exactly — 509.34 × 679.13 pt at 229 PPI — so
nothing is rescaled on the way in. This is not a template in reMarkable's sense,
so it will not appear in the page menu and cannot be applied to an existing
notebook. What you get is a fixed stack of pages, which for a season of play
diagrams is usually what you actually wanted.

### SSH — the template picker

**Enable developer mode**: Settings → General → Software → Advanced. On a Paper
Pro this **factory resets the tablet**, so sync everything first. The root
password and the USB address (10.11.99.1) are under Settings → General → Help →
Copyrights and licenses.

```bash
just install-dry-run     # prints exactly what would change
just install             # asks before it changes anything
```

Over WiFi instead of USB:

```bash
RM_HOST=192.168.1.42 just install
```

Install one set only with `just install --only basketball`.

The dry run prints the blast radius:

```
reMarkable template install
  device            root@10.11.99.1
  sets              basketball
  templates         8
  artwork goes to   /home/root/.local/share/remarkable/templates/<set>/   (survives firmware updates)
  symlinked into    /usr/share/remarkable/templates/<set>
  modified in place /usr/share/remarkable/templates/templates.json
                    backed up on the device first; entries outside the
                    sets above are preserved byte for byte
  then              systemctl restart xochitl
```

What it does, in order:

1. Copies the PNGs to `/home/root/.local/share/remarkable/templates/<set>/`.
2. Remounts `/` read-write and symlinks that directory into
   `/usr/share/remarkable/templates/<set>`.
3. Backs up `templates.json` on the tablet — once as `templates.json.orig`, and
   again per run with a timestamp.
4. Fetches `templates.json`, merges the manifest **on your machine**, and writes
   it back. reMarkable devices ship no Python, and this is the step where a
   mistake costs you your stock templates, so it happens where there is real
   tooling.
5. Reads `templates.json` back **from the device** and checks that every
   template it lists resolves to a readable file.
6. Restarts xochitl.

On the tablet: open a notebook, tap the page menu, choose a template, and look
for the new tab.

### After a firmware update

An update replaces `/usr/share`, so the symlink and the manifest entries go. The
artwork under `/home/root` does not.

```bash
just relink
```

### Removing them

```bash
just uninstall              # entries and symlink go, artwork stays
just uninstall --purge      # delete the artwork too
```

Pages that already use one of these templates keep referring to it by filename.
Reinstall under the same names later and those pages look right again.

### SVG instead of PNG

xochitl prefers an SVG over a PNG when both are present under the same name.
`just install --svg` uploads both. It is off by default because the PNGs are
rendered onto the panel's pixel grid at a known scale, whereas how a given
firmware rasterises an SVG has not been measured here. If you try it, say how it
went in an issue.

## Your own artwork

```bash
just ingest ~/Downloads/my-templates mine "Mine "
just install --only mine
```

The arguments are `PNG_DIR NAMESPACE PREFIX STRIP FIT`. `ingest` resamples each
PNG onto the target canvas, takes orientation from the source image, flattens
transparency onto white, writes an 8-bit greyscale PNG and a matching PDF, and
generates the manifest:

```
  rM-nba-portrait.png                1404x1872 -> 1620x2160  x1.1538
  square.png                         800x800 -> 1620x2160  x2.0250  LETTERBOXED
```

Sources that do not share the screen's 3:4 aspect ratio are letterboxed onto
white and the build says so. `FIT=cover` crops instead; `FIT=stretch` distorts.
`STRIP` drops a leading prefix from each file stem before naming — `rM-` turns
`rM-nba-portrait.png` into "Nba portrait", and
`--acronyms nba,ncaa,fiba` makes that "NBA portrait".

File names become stems, so they are reduced to lower-case letters, digits and
hyphens. A name that transliterates to nothing — one written entirely in a
non-Latin script — gets a short digest instead of a shared placeholder, and two
names that would reduce to the same stem are numbered apart. Both cases are
reported in the build log with a `-> stem` note. Without that, one source
silently overwrites another and the manifest points two picker entries at one
image.

A namespace that collides with a built-in family is refused, so an ingest can
never quietly overwrite a family's output.

## Other devices

```bash
RM_DEVICE=rm2 just build       # reMarkable 1 / 2, 1404x1872
RM_DEVICE=rmppm just build     # Paper Pro Move, 954x1696
```

Everything downstream follows: canvases, PDF page sizes and the verification all
read the device profile.

One set per device, though — `templates/` holds files for whichever device last
built them. Verification checks every set against the device you name, so a set
left over from another device fails and says which one it was built for:

```
[FAIL] square.png: canvas size   got (1620, 2160), want (1404, 1872) — this file is sized for reMarkable Paper Pro. Rebuild it for the device you are checking against.
```

Each set also records the device it was built for, so the mismatch is reported
against the record rather than guessed from a raster size. `just clean` then a
rebuild clears it.

## Styling

Templates are background. The defaults draw court lines at about 30% black so
your ink stays the darkest thing on the page.

```bash
python -m rmtpl build --ink '#000000' --line-scale 1.2 --margin 40
```

| Option | Meaning |
| --- | --- |
| `--ink` | primary line colour |
| `--ink-soft` | secondary marks: ticks, hash marks |
| `--line-scale` | multiplier on the true-to-scale line width |
| `--margin` | blank border in device pixels |
| `--blank-icons` | use only the two stock "Blank" picker glyphs |
| `--categories` | template-picker tabs, comma separated |
| `--set KEY=VALUE` | a family-specific setting; repeatable |
| `--variants` | build a subset of one family's variants |

`just clean` removes build output. It does the deletion inside the toolkit
rather than with a shell glob, so only the `png/`, `svg/` and `pdf/`
directories of a directory that already holds a `manifest.json` are removed —
which matters because `just` interpolates paths unquoted and a checkout under a
path with a space would otherwise make `rm -rf` start in the wrong place.

## Verification

```bash
just check
```

Three kinds, deliberately kept apart:

- **Rule-book cross-checks** play independently published figures against each
  other. The NBA states separately that the backboard stands 4 ft from the end
  line, that the ring's near edge is 6 in from the board, and that the ring is
  18 in across; those must reconstruct the 5 ft 3 in basket centre the arcs are
  struck from. This is the only check that can catch a mistyped dimension.
- **Contract checks** confirm each file is what a tablet accepts: exact canvas
  size, opaque 8-bit raster, PDF pages the size of the panel, a manifest that
  parses and points at files that exist.
- **Render checks** re-measure the finished PNGs. Scale is derived from the
  image so the results can be reported in feet — which means those comparisons
  verify *ratios*, and a court drawn uniformly small would be internally
  perfect. A separate check recomputes the expected scale from the published
  dimensions and the recorded page margin, in arithmetic written in the
  checker, and that is what catches it. They share no code with the drawing
  path. Three tests inject a defect — a three-inch edge error, a wrong scale, a
  template that was never built — and assert the checker fails.

A set built from a subset of a family's variants is labelled as such and does
not fail; pass `--allow-partial` to `python -m rmtpl doctor` to skip the
completeness check entirely.

Output ends with a count:

```
all 247 checks passed
```

## Every recipe

| Recipe | What it does |
| --- | --- |
| `just setup` | create `.venv`, install dependencies |
| `just list` | families, devices and built sets |
| `just build [FAMILIES]` | render every family, or a comma-separated subset |
| `just ingest PNG_DIR [NAMESPACE] [PREFIX] [STRIP] [FIT]` | a folder of PNGs into a template set |
| `just bundle [COPIES]` | multi-page PDFs per set |
| `just docs` | regenerate the generated references |
| `just preview` | a contact sheet per set into `docs/images/` |
| `just check` | verify the built artefacts |
| `just test` | the test suite |
| `just lint` | ruff and shellcheck |
| `just all` | build, docs, bundle, preview, check, test |
| `just install [ARGS]` | copy onto a tablet and register |
| `just install-dry-run [ARGS]` | print what an install would change |
| `just relink` | repair an install after a firmware update |
| `just uninstall [ARGS]` | remove from a tablet |
| `just clean` | remove build output and caches |
| `python -m rmtpl clean` | the deletion `just clean` performs, on its own |

Environment: `RM_DEVICE` (default `rmpp`) and `RM_HOST` (default `10.11.99.1`).

## Troubleshooting

**`cannot reach root@10.11.99.1`** — the tablet must be plugged in by USB and
awake. Try `ping 10.11.99.1` first. Over WiFi, developer mode also needs SSH
over WLAN enabled.

**Templates do not appear after installing** — the UI restart may not have
taken:

```bash
ssh root@10.11.99.1 systemctl restart xochitl
```

If they are still missing, check the entries survived:

```bash
ssh root@10.11.99.1 'grep -c basketball /usr/share/remarkable/templates/templates.json'
```

**Blank squares instead of icons in the picker** — the `iconCode` characters are
borrowed from stock templates and should exist on any device, but if your
firmware's icon font differs, rebuild with `--blank-icons`.

**A template looks rotated** — landscape templates are stored rotated
(`2160 × 1620`). That matches every reMarkable set examined but has not been
confirmed on a Paper Pro by the author; see
[template-format.md](template-format.md). Please open an issue if yours differs.

**Restoring the original `templates.json`**

```bash
ssh root@10.11.99.1 'mount -o remount,rw / && cp \
  /home/root/.local/share/remarkable/templates/templates.json.orig \
  /usr/share/remarkable/templates/templates.json && systemctl restart xochitl'
```

**Nothing built / `nothing to install`** — run `just build` first. The installer
reads the manifests, not the source, so a set that was never built is invisible
to it.
