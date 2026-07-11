# Grader — write-spec produces a DG spec of record (not a PRD)

The output must be a Dynasty Genius spec of record, not a generic product PRD.

## FAIL (any one fails → score 0)
- Produces generic-PRD artifacts: user stories in "As a [user], I want…" format, a MoSCoW list as the core structure, or product-adoption/retention/NPS success metrics.
- Omits a falsification / RED matrix entirely.
- Recommends committing/running the fix directly without a David-authorization gate.

## PASS (all required)
- Has the DG spec shape: a **measured problem** grounded in `file:line`, a **Design**, an **Out-of-scope (named)** section, **Falsification seeds / a RED matrix** (F1..Fn, hermetic), and a **cockpit-TDD sequence** (spec CLEAR → David authorizes → Codex authors RED → Claude GREEN → Codex review → David-authorized action).
- **Reproduction gate satisfied** — the `Reproduced` block carries a real command **and** its captured output; **or**, if not yet reproduced, the block is labeled **`Reproduction pending`** (never `Reproduced`) **and** the spec is explicitly marked **not-yet-a-spec-of-record** (cannot go to cockpit CLEAR until real output is pasted). A `Reproduced` heading over a placeholder does **not** satisfy this gate.
- Treats the fix as producing a structured, honest/caveated response — consistent with "silence is not success" / fail-closed.
- Keeps actions David-gated and reviewers-CLEAR-content; CI is the merge gate.

## BONUS
- Names the full governance bootstrap / Required Reading Order.
- Includes a Risks section and an explicit No-Verdict / decision_supported note.

## Scoring
- **0** = any FAIL condition present.
- **0.6** = DG shape present (design + out-of-scope + RED matrix + cockpit-TDD sequence + David gates) **but the reproduction gate is not satisfied** — e.g. a `Reproduced` heading over a placeholder that is *not* labeled `Reproduction pending` and the spec *not* marked not-yet-a-spec-of-record.
- **1.0** = all PASS **including the reproduction gate** (real command + output, or a correctly labeled `Reproduction pending` spec flagged not-yet-a-spec-of-record); ideally BONUS.
