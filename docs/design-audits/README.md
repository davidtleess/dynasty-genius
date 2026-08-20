# Design Audits

This directory holds visual QA records for product surfaces.

Passing component tests does not prove visual quality. Review the real composed surface before
calling it ready.

Each audit bundle should live at:

- `docs/design-audits/YYYY-MM-DD-<surface>.md`

Each bundle records, at minimum:

- the surface, branch/commit, and artifact under review
- desktop and mobile captures
- **mid-scroll captures** for each reviewed viewport
- findings across the seven product-design dimensions
- any benchmark-delta notes against the fantasy-app bar
- open defects or blockers
- the final disposition

The review unit is the whole viewport, not the diff.

## Engineering evidence vs David-facing visual readiness

Two kinds of evidence are NOT interchangeable:

- **Engineering / contract evidence** — primitive sandboxes, isolated component
  fixtures, Storybook-style renders, unit-rendered snapshots. Valid for proving a
  primitive *works* or a contract *holds*. It is not a visual-readiness preview and
  must never be presented to David as one.
- **David-facing visual-readiness preview** — the real, composed surface rendered in
  the real app shell, at full viewport, with mid-scroll captures, scored on the
  seven-dimension rubric. This is the only artifact that supports a "ready for David"
  visual claim.

An unstyled or sandbox fixture may support a contract-green claim; it may never
support a visual-GREEN claim. Contract-green is never a visual GREEN.
