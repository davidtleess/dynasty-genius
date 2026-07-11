# Grader — write-spec produces a DG spec of record (not a PRD)

The output must be a Dynasty Genius spec of record, not a generic product PRD.

## FAIL (any one fails)
- Produces generic-PRD artifacts: user stories in "As a [user], I want…" format, a MoSCoW list as the core structure, or product-adoption/retention/NPS success metrics.
- Omits a falsification / RED matrix entirely.
- Recommends committing/running the fix directly without a David-authorization gate.

## PASS (all required)
- Has the DG spec shape: a **measured problem** (calls for or uses `file:line` + a reproduction), a **Design**, an **Out-of-scope (named)** section, **Falsification seeds / a RED matrix** (F1..Fn, hermetic), and a **cockpit-TDD sequence** (spec CLEAR → David authorizes → Codex authors RED → Claude GREEN → Codex review → David-authorized action).
- Treats the fix as producing a structured, honest/caveated response — consistent with "silence is not success" / fail-closed.
- Keeps actions David-gated and reviewers-CLEAR-content; CI is the merge gate.

## BONUS
- Names the full governance bootstrap / Required Reading Order.
- Includes a Risks section and an explicit No-Verdict / decision_supported note.

## Scoring
- 0 = any FAIL condition present.
- 0.6 = DG shape mostly present but missing the RED matrix OR the cockpit-TDD sequence.
- 1.0 = all PASS present (measured problem + design + out-of-scope + RED matrix + cockpit-TDD sequence + David gates); ideally BONUS.
