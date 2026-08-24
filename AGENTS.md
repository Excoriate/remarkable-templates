# AGENTS.md

Working notes for coding agents in this repository. Humans should read
[README.md](README.md) and [docs/USER_GUIDE.md](docs/USER_GUIDE.md) instead;
[CONTRIBUTING.md](CONTRIBUTING.md) covers the same ground for people.

## What this repository is

A toolkit that builds reMarkable paper templates, plus the template families
built with it. The split is the whole design:

```
src/rmtpl/        anything true of ANY reMarkable template
src/families/     one package per subject; only what is true of that subject
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
   Render checks measure finished pixels and compare against published figures,
   deriving scale from the image. A checker that calls the drawing code's own
   `fit` or `to_path` proves consistency, not correctness — this repository had
   exactly that bug once and it passed a deliberately broken build.
   `tests/test_build.py::test_doctor_catches_a_broken_edge_convention` exists to
   keep it honest; if you change the checks, make sure that test still fails the
   build when the defect is injected.
3. **Only cross-checks can catch a wrong number.** Re-measuring a drawing cannot
   tell you the number drawn was right. A new dimension needs a source, its
   measurement edge, and — where two published figures constrain each other — a
   cross-check test.
4. **Generated documentation is generated.** `docs/families/*-geometry.md` comes
   from the specs via `just docs`. Never hand-edit it.
5. **Builds are byte-reproducible.** PDF writers stamp a creation time;
   `rmtpl.vector._deterministic_pdf` strips it. CI fails if committed
   `templates/` or `docs/` differ from a fresh rebuild, so run `just all` and
   commit the output with the change that caused it.
6. **The installer never overwrites `templates.json`.** It fetches the device's
   file, merges on the host, writes back, then re-reads from the device to
   verify. Only entries under our own namespace directories are replaced.
7. **No third-party artwork in the tree.** The repository ships drawings
   authored for it plus a pipeline that processes whatever you point it at
   locally. `templates/imported/` and `templates/legacy/` are git-ignored on
   purpose. See [NOTICE.md](NOTICE.md).

## Adding a family

One package under `src/families/` exposing a module-level `FAMILY`:

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
days — and let `fit_box` map them onto the page. A family never computes a pixel
coordinate.

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
