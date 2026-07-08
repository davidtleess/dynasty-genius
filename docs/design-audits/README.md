# Design Audits

This directory is the tracked home for the mandatory visual-audit bundles named in
`PRODUCT.md`, `DESIGN.md`, and `docs/governance/02-agent-operating-loop.md`.

Rule: **contract-green is never a visual GREEN.** Any David-facing surface claiming
visual readiness must leave an evidence bundle here before David review.

Each audit bundle should live at:

- `docs/design-audits/YYYY-MM-DD-<surface>.md`

Each bundle records, at minimum:

- the surface, branch/commit, and artifact under review
- desktop and mobile captures
- **mid-scroll captures** for each reviewed viewport
- the scored seven-dimension audit rubric
- any benchmark-delta notes against the fantasy-app bar
- open defects or blockers
- the final David verdict when it happens

The review unit is the **whole viewport**, not the diff. The bundle may block ship;
that is still a successful audit outcome.
