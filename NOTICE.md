# Attribution and third-party material

## The template artwork

Everything under `templates/` that this repository commits was generated from
source in this repository. It is not traced from, derived from, or a
modification of anyone else's artwork.

For the basketball family, every figure used is listed with its source in
[docs/families/basketball-court-geometry.md](docs/families/basketball-court-geometry.md).
The generated templates are released under CC0 — see [LICENSE-ART](LICENSE-ART).

## The reMarkable 2 court templates this project started from

This project began with a set of reMarkable 2 basketball court templates by
**Kyle Gentry**, whose name is embedded in the artwork itself. They are good
drawings, and measuring them was useful: their high-school geometry
independently agreed with the NFHS rule book on every dimension checked, which
is worth more than one source alone.

**Those files are not redistributed here.** No copy of them, and no derivative
of them, is committed to this repository. What is here is the pipeline. Point it
at your own copy:

```bash
just ingest "~/path/to/those/pngs" legacy "Legacy " rM-
just install --only legacy
```

That upscales them to the target device's resolution and writes to
`templates/legacy/`, which is git-ignored. If you did not obtain those PNGs
yourself, this repository will not get them for you.

If you are Kyle Gentry and you would like the set included here under a licence
of your choosing, or you would like this note worded differently, please open an
issue.

## Rule books and governing bodies

NBA, NCAA, FIBA and NFHS are the trademarks of their respective organisations.
This project is not affiliated with, endorsed by, or connected to any of them.
Their rule books are cited as sources of factual dimensions; no rule-book text
or diagram is reproduced.

## Device compatibility

reMarkable is a trademark of reMarkable AS. This project is not affiliated with
or endorsed by reMarkable. The template format it targets is not a documented
public interface, and installing over SSH requires developer mode; both are used
at your own risk. See [docs/template-format.md](docs/template-format.md) for
what has been verified and what has not.
