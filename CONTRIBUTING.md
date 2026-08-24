# Contributing

`just setup` once, then `just all` before every commit — it builds, regenerates
the documentation, verifies and tests. CI runs the same thing, then rebuilds and
fails if the committed `templates/` and `docs/` differ from what the current
source produces. That comparison uses `git status`, so a new artefact you forgot
to `git add` is caught as well as a changed one. `docs/images/` is exempt: the
contact sheet's labels come from Pillow's bundled font, which changes between
releases.

CI pins the renderers in `constraints-ci.txt`, because a byte-for-byte gate is
only meaningful if cairo, Pillow and pikepdf are held still. Bump those pins in
their own commit, together with the regenerated output.

Coding agents: see [AGENTS.md](AGENTS.md).

## Changing a dimension

Each family's specs are the single source of truth — for basketball,
`src/rmtpl/families/basketball/specs.py`. Change a value there and run `just all`.
`docs/families/basketball-court-geometry.md` is generated, so never edit it by
hand; it would only drift away from what the courts are drawn with.

A dimension change needs three things:

1. **A source.** Add or update the entry in the spec's `sources` map. Primary
   sources only: the governing body's own rule book or court diagram. Secondary
   sources can corroborate, and should be labelled as doing so.
2. **The measurement edge.** Rule books dimension to the outer or inner edge of
   a painted line. If you do not know which, the number is not yet usable — find
   out, and record it with `Edge.OUTER` / `Edge.INNER`.
3. **A cross-check, if one exists.** The strongest tests confirm that two
   independently published figures agree — the NBA's basket centre
   reconstructing from the backboard offset plus the ring geometry, for
   instance. Re-measuring a drawing can never establish that a number was right;
   only agreement between independent statements can. If your change makes such
   a pair available, add the test.

## Adding a family

A family is one package under `src/rmtpl/families/` that exposes a module-level
`FAMILY`. The build, the manifest, the documentation and the checks all iterate
over whatever the registry finds, so nothing else needs to change.

```python
# src/rmtpl/families/planner/__init__.py
from rmtpl.family import BuildOptions, BuiltTemplate, TemplateFamily

class PlannerFamily(TemplateFamily):
    key = "planner"
    label = "Planner"
    summary = "Week and day layouts."

    def build(self, out_dir, device, options) -> list[BuiltTemplate]:
        ...

FAMILY = PlannerFamily()
```

Draw with `rmtpl.draw.Canvas` in whatever units your subject uses; `fit_box`
maps them onto the page, so you never compute a pixel coordinate. Return one
`BuiltTemplate` per file and the toolkit writes the manifest.

Implement `verify` too. `rmtpl.checks` already confirms your files are what a
tablet accepts; `verify` is where you prove the drawings mean what they should,
ideally by measuring the finished artwork rather than by re-reading the numbers
you drew from. `rmtpl.checks` exposes the measurement helpers — `dark_mask`,
`runs`, `centres`, `arc_ink` — so you do not have to reinvent them.

`tests/test_registry.py` checks every family against the contract automatically.
Put your family's own cross-checks in `tests/families/`.

## Adding a device

Add a `Device` to `src/rmtpl/devices.py` with a source for its resolution and
PPI. If you can confirm on hardware whether it stores landscape templates
rotated, please say so in the pull request: that is currently the largest
inferred claim in [docs/template-format.md](docs/template-format.md).

## Repository settings

`scripts/setup-github.sh` sets the GitHub side — remote, push, description,
topics, secret scanning and push protection, Dependabot, a read-only default
`GITHUB_TOKEN`, and branch protection on `main` requiring the `build` check.

```bash
scripts/setup-github.sh --dry-run     # print every call, change nothing
scripts/setup-github.sh               # solo-maintainer protection
scripts/setup-github.sh --strict      # admins included, one review required
```

It sets state rather than toggling it, so re-running is a no-op that confirms
the current configuration, and it reads every setting back at the end.

The default leaves admins exempt from branch protection. That is deliberate: a
single maintainer cannot approve their own pull request, and locking the only
person with access out of `main` is a worse failure than the one it prevents.
`--strict` is the right setting the moment there is a second maintainer.

## What this project will not take

Pull requests adding third-party template artwork. This repository ships
drawings authored for it and released into the public domain, plus a pipeline
that will happily process whatever you point it at locally. Keeping other
people's artwork out of the tree is what makes the licensing simple enough to
state in one paragraph.
