# AGENTS.md

Working notes for coding agents in this repository. Humans should read
[README.md](README.md) and [docs/USER_GUIDE.md](docs/USER_GUIDE.md) instead;
[CONTRIBUTING.md](CONTRIBUTING.md) covers the same ground for people.

## What this repository is

A toolkit that builds reMarkable paper templates, plus the template families
built with it. The split is the whole design:

```
src/rmtpl/        anything true of ANY reMarkable template
src/rmtpl/families/  one package per subject; only what is true of it
```

`rmtpl` owns device canvases, the SVG drawing surface, PNG/PDF rendering, the
`templates.json` manifest, the installer and the file-contract checks. A family
owns what to draw, what its dimensions mean, and how to tell whether a drawing
came out right. If you find yourself writing `if family == "basketball"` in
`src/rmtpl/`, the abstraction is wrong — fix the seam instead.

## Commands

```bash
just setup     # once
just all       # build, docs, bundle, preview, check, test — run before every commit
just check     # verification only
just lint      # ruff + shellcheck
```

Every recipe wraps `python -m rmtpl`. `just --list` is the index.

## Invariants

These are enforced by tests or checks. Breaking one should make something fail;
if it does not, the missing check is the bug.

1. **Rule-book edges are resolved once.** A published dimension is measured to a
   specific *edge* of a painted line; a drawing program strokes a path *centre*.
   Families convert in one place (`to_path` for basketball) and record the edge
   next to every value. Never bake an edge adjustment into a call site.
2. **Verification never imports its expectation from the thing it checks.**
   A checker that calls the drawing code's own `fit` or `to_path` proves
   consistency, not correctness — this repository had exactly that bug once and
   it passed a deliberately broken build.

   Know what each kind of check can and cannot catch. Deriving scale from the
   image lets a check talk in feet, but it then verifies **ratios only**: a
   court drawn uniformly 6% small is internally perfect. `_expected_scale`
   recomputes the fit from published dimensions and the recorded margin, in
   arithmetic written in the checker, and that is what notices. A check whose
   expectation is derived from the same two measurements it compares is a
   tautology; there was one of those here too.

   Three tests keep this honest by injecting a defect and asserting the
   checker fails: `test_doctor_catches_a_broken_edge_convention`,
   `test_doctor_catches_a_globally_wrong_scale`, and
   `test_doctor_catches_a_template_that_was_never_built`. If you change the
   checks, make sure they still fail for the right reason.
3. **Only cross-checks can catch a wrong number.** Re-measuring a drawing cannot
   tell you the number drawn was right. A new dimension needs a source, its
   measurement edge, and — where two published figures constrain each other — a
   cross-check test.

4. **A family declares what a complete build looks like.** `expected_stems()`
   is what lets verification notice a template that is *absent*; a checker that
   only inspects the files it finds cannot tell a half-built set from a small
   one. The build record in each `manifest.json` carries that expectation.
5. **Generated documentation is generated.** `docs/families/*-geometry.md` comes
   from the specs via `just docs`. Never hand-edit it.
6. **Builds are byte-reproducible.** PDF writers stamp a creation time;
   `rmtpl.vector._deterministic_pdf` strips it. Nothing may put a clock or a
   random value into an artefact — that includes the build record in each
   set's `manifest.json`. CI compares committed `templates/` and `docs/`
   against a fresh rebuild with `git status`, so an artefact that was never
   `git add`ed is caught too; run `just all` and commit the output with the
   change that caused it. `docs/images/` is excluded from that comparison
   because the contact sheet's labels use Pillow's bundled font, which changes
   between releases. CI pins the renderers in `constraints-ci.txt`.
7. **The installer rewrites `templates.json`, but never blindly.** It backs the
   file up on the device *before* any other change, fetches it, merges on the
   host, writes back, then re-reads from the device to verify. Only entries
   under our own namespace directories are replaced. Two guards enforce that
   rather than assume it: `merge_templates_json.py` refuses to emit a file if
   the device's own entries did not survive the merge, and `verify_install.py`
   compares the count of the device's entries before and after. Both have
   tests that break the merge deliberately and assert the guard fires — if you
   touch either, keep those tests failing for the right reason.
8. **No third-party artwork in the tree.** The repository ships drawings
   authored for it plus a pipeline that processes whatever you point it at
   locally. `templates/imported/` and `templates/legacy/` are git-ignored on
   purpose. See [NOTICE.md](NOTICE.md).

## Adding a family

One package under `src/rmtpl/families/` exposing a module-level `FAMILY`:

```python
from rmtpl.family import BuildOptions, BuiltTemplate, TemplateFamily

class PlannerFamily(TemplateFamily):
    key = "planner"          # directory name and device namespace
    label = "Planner"
    summary = "One line, shown by `just list`."

    def build(self, out_dir, device, options) -> list[BuiltTemplate]: ...
    def write_docs(self, docs_dir): return []          # optional
    def verify(self, report, out_dir, device): ...      # optional but expected

FAMILY = PlannerFamily()
```

Nothing else changes. `rmtpl.registry` discovers packages by directory, and the
build, manifest, docs and checks all iterate over what it finds.

Draw with `rmtpl.draw.Canvas` in whatever units the subject uses — feet, metres,
days — and let `fit_box` map them onto the page. For geometry, a family never
computes a pixel coordinate.

Two known gaps, so you do not discover them halfway:

- **There is no text primitive.** `Canvas` covers lines, polylines, circles,
  arcs and filled rectangles. A family needing lettering — a planner's day
  names, a stave's clef — uses `Canvas.raw()` with `fit.px()` to place it, and
  must deal with the consequence: an SVG `<text>` element rasterises against
  whatever font the machine has, which ends byte-reproducibility and turns the
  CI staleness gate red on somebody else's laptop. Convert lettering to paths
  at build time, or ship the glyphs as path data.
- **`fit_box` is uniform-scale and centred.** Anything else — edge-to-edge,
  left-aligned — means constructing `Fit` directly. It is a plain value; that
  is supported, just not wrapped.

`tests/test_registry.py` checks every family against the contract, so a new one
is covered the moment it is discovered. Add the family's own cross-checks under
`tests/families/`.

## Conventions

- Python 3.10+, ruff-clean at 88 columns, type hints on public functions.
- Comments explain *why*, especially where a number is a judgement call. Do not
  narrate what the next line does.
- Docstrings on modules and on anything non-obvious; they are the documentation
  for this codebase.
- Shell is bash with `set -euo pipefail`, shellcheck-clean at `-S warning`.
- **Quote every `{{...}}` in the Justfile.** `just` substitutes unquoted, so on
  a checkout under a path with a space an interpolated variable becomes two
  shell words. That turned `rm -rf {{out}}/*/png` into a recipe that deleted
  the parent directory. Nothing destructive goes through a shell glob over an
  interpolated path any more — `just clean` calls `rmtpl clean`, which deletes
  known subdirectories of directories that already hold a manifest.
  `tests/test_install_guards.py` enforces both rules.
- Anything that mutates a device states its blast radius, backs up first, and
  verifies afterwards by reading the device back.
- British or American spelling — match the file you are editing.

## What not to do

- Do not commit template artwork you did not generate from source in this repo.
- Do not hand-edit generated files.
- Do not add a dependency without a reason that survives being asked twice;
  `pikepdf` is here only because byte-reproducible PDFs need it.
- Do not weaken a check to make a build pass. If a check is wrong, fix the check
  and say why in the commit message.
- Do not claim a device behaviour you have not verified. `docs/template-format.md`
  separates verified from inferred; keep it that way and move claims across only
  with evidence.
- Do not let a slug or a namespace become a free-form string. Stems and set
  names are restricted to `[a-z0-9][a-z0-9-]*` because they end up as file
  names, JSON values and bare words in a command run over SSH as root on
  somebody's tablet.
