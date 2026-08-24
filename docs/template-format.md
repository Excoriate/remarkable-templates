# The reMarkable template contract

What a tablet requires of a template file, what this project verified, and what
it is taking on trust. The distinction matters: everything below is either
checked in code, corroborated across independent sources, or explicitly marked
as unconfirmed.

## Canvas

| Device | Portrait canvas | PPI | Page size at that PPI |
| --- | --- | --- | --- |
| reMarkable Paper Pro | 1620 × 2160 | 229 | 509.34 × 679.13 pt |
| reMarkable 1 / 2 | 1404 × 1872 | 226 | 447.36 × 596.48 pt |
| reMarkable Paper Pro Move | 954 × 1696 | 264 | 260.18 × 462.55 pt |

**Verified.** The Paper Pro figures come from reMarkable's own product
comparison page, and the derived page size matches what template vendors
publish independently. All three panels are 3:4, which is why rM2-era artwork
upscales to a Paper Pro without letterboxing — at 1.1538×, and visibly softer.

A landscape template is the same canvas rotated: the raster is
`height × width`, not the portrait size with a flag set.

**Partly inferred.** That landscape rasters are stored rotated is consistent
with reMarkable's own `LS …` stock templates and with every third-party set
examined, including the rM2 court templates this project started from. It has
not been confirmed against a Paper Pro by the author. If a landscape template
comes out rotated on your device, that is the assumption to question first.

## File requirements

- PNG, exactly the canvas size.
- Opaque. No alpha channel; a white page, not a transparent one.
- 8-bit greyscale is safe everywhere. The Paper Pro panel renders colour, so
  colour templates are possible, but grey keeps your ink the darkest mark.
- An SVG of the same name **takes precedence** over the PNG. Ship one only if
  you want that.

Checked by `just check` for every built file.

## templates.json

Lives at `/usr/share/remarkable/templates/templates.json`. One flat list that
xochitl owns:

```json
{
  "templates": [
    {
      "name": "Blank",
      "filename": "Blank",
      "iconCode": "\ue9fe",
      "categories": ["Creative", "Lines", "Grids", "Life/organize"]
    },
    {
      "name": "NBA half court",
      "filename": "basketball/nba-half-court",
      "iconCode": "\ue9fd",
      "landscape": true,
      "categories": ["Basketball"]
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `name` | shown under the icon; must be unique across the whole file |
| `filename` | path relative to the templates directory, **without an extension**; may name a sub-directory |
| `iconCode` | one character from a private-use block in xochitl's icon font |
| `landscape` | optional; absent means portrait, which is how stock entries write it |
| `categories` | list of tab names; unknown names create a new tab |

**Verified** against a real device's file. `filename` carrying no extension is
what makes a namespaced sub-directory a reliable marker for one project's
entries, which is what the installer's merge relies on.

**Inferred.** That the Paper Pro uses the same schema as an rM2 is inferred, not
confirmed on hardware. The installer is built so it does not matter much: it
merges into whatever the device already has rather than writing a file of its
own shape, so an extra field this project has never seen is preserved rather
than dropped.

### Icons

There is no basketball glyph. Adding one means patching the icon font that
xochitl ships, which is out of scope here, so `src/rmtpl/icons.py` borrows codes
from stock templates — every one is known to exist on a shipping device, and
each is orientation-appropriate. Names do the discriminating. `--blank-icons`
falls back to the two "Blank" glyphs if a firmware's font surprises you.

### Categories

`Basketball` is a category this project invents. Custom category names are
reported to work, creating their own tab. If yours does not appear, build with
`--categories Creative` to file them under a stock tab instead.

## Persistence across firmware updates

`/usr/share` is replaced by an update. `/home/root` is not. Installing the
artwork under `/home/root/.local/share/remarkable/templates/` and symlinking it
into place means an update costs you the symlink and the manifest entries, not
the files.

**Inferred from practice**, not from reMarkable documentation: this is the
approach RCU uses and the reason it can repair templates after an update. The
recovery path (`just relink`) is cheap either way, and re-running the full
install rebuilds everything from this repository regardless.

## What is not established

- Whether a Paper Pro rasterises a template SVG the way the PNG path does. Not
  measured. `--svg` exists; it is not the default.
- Whether the Paper Pro's stock `templates.json` carries fields an rM2's does
  not. The merge preserves anything it does not recognise, so this is defensive
  rather than answered.
- The exact width of the toolbar strip on a Paper Pro. 104 px is the figure
  reported for firmware 3.5 on an rM2 and is used here as advisory: it is why
  the templates keep a margin, not a number anything depends on.
