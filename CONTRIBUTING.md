# Contributing

## Changing a dimension

`src/courts/specs.py` is the single source of truth. Change a value there, then:

```bash
just all      # rebuild, regenerate docs, verify, test
```

`docs/court-geometry.md` is generated, so never edit it by hand — it would only
drift away from what the courts are actually drawn with.

A dimension change needs three things:

1. **A source.** Add or update the entry in the spec's `sources` map. Primary
   sources only: the governing body's own rule book or court diagram. Secondary
   sources can corroborate, and should be labelled as doing so.
2. **The measurement edge.** Rule books dimension to the outer or inner edge of
   a painted line. If you do not know which, the number is not yet usable —
   find out, and record it with `Edge.OUTER` / `Edge.INNER`.
3. **A cross-check, if one exists.** The strongest tests in `tests/test_specs.py`
   confirm that two independently published figures agree — the NBA's basket
   centre reconstructing from the backboard offset plus the ring geometry, for
   instance. If your change makes such a pair available, add the test.

## Adding a ruleset

Add a `CourtSpec` to `specs.py` and its key to `ORDER`. Everything else follows:
the build, the manifest, the documentation and the checks all iterate over
`specs.ORDER`.

If the new code has a marking none of the existing ones do, add it to
`geometry.py` behind an optional field rather than a special case, and add a
render check for it in `checks.py` — `_arc_ink` exists precisely so a missing
or mirrored arc fails the build instead of being noticed later by eye.

## Adding a device

Add a `Device` to `src/rmtpl/devices.py` with a source for its resolution and
PPI. If you can confirm on hardware whether it stores landscape templates
rotated, please say so in the PR: that is currently the largest inferred claim
in `docs/template-format.md`.

## Before opening a PR

```bash
just lint
just all
```

CI runs the same thing, plus a check that the committed `templates/` and `docs/`
are exactly what the current source produces.

## What this project will not take

Pull requests adding third-party template artwork. This repository ships
drawings authored for it and released into the public domain, plus a pipeline
that will happily process whatever you point it at locally. Keeping other
people's artwork out of the tree is what makes the licensing simple enough to
state in one paragraph.
