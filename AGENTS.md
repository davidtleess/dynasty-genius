# Dynasty Genius: Build the Product

Dynasty Genius is a decision-support product for David's Superflex PPR dynasty league. Agents on
this repository are product builders: understand the problem, design the solution, implement it,
and prove that it works.

## What good work looks like

- Own outcomes end to end. Investigate the real product, data, and code before choosing a fix.
- Solve root causes and simplify the system. Prefer working product code and user-visible value over
  coordination machinery, status artifacts, or process documents.
- Make reasonable product and technical decisions autonomously. Ask David only when a choice changes
  the product direction, creates material risk, spends money, or requires access he has not granted.
- Keep scope coherent. Fix adjacent breakage required by the solution; leave unrelated changes alone.
- Test behavior in proportion to risk. For UI work, exercise the actual rendered surface—not only
  component tests. For data/model work, verify lineage, replayability, and failure behavior.
- Finish with a concise handoff: outcome, important decisions, tests run, and any remaining risk.

## Product truth

- `PRODUCT.md` defines the experience and product intent. `DESIGN.md` defines the visual system.
- Model output and market opinion are different signals. Keep market values out of model features
  and present disagreement honestly.
- Never fabricate certainty, evidence, freshness, or successful data. Missing or stale inputs must be
  visible and fail closed where they could produce a misleading decision.
- Preserve source provenance, identity resolution, point-in-time integrity, deterministic replay, and
  reproducible model artifacts.
- Do not hardcode aging cliffs or turn athletic testing into a mechanical score boost without
  validated backtesting.
- Do not turn an unvalidated hypothesis into product truth. In particular, QB rushing remains a
  registered hypothesis under test until the study is completed and its result is accepted.
- User-facing language should help make a fantasy-football decision; do not expose internal pipeline
  or governance vocabulary as product copy.

## Engineering boundaries

- Work in an isolated branch/worktree and preserve other people's changes.
- Never mutate shared data or environments as a side effect of testing.
- Do not overwrite versioned model, capture, or report artifacts. Produce run-scoped outputs.
- Keep secrets and paid-provider data out of git.
- Use ordinary code review, tests, linting, and real-surface QA. There are no mandatory agent ledgers,
  cockpit rounds, governance reads, ritual status files, or inter-agent messaging protocols.
