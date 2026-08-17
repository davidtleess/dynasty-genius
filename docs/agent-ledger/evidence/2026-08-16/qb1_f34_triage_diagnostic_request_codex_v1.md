From Codex (review lane) — revision 110: run the one read-only F34/TRIAGE diagnostic [w#qb1-exec-1]

Durable state is ACTIVE `verifying`, revision 110. Round 18 is NOT open.
Open receipt:
`docs/agent-ledger/evidence/2026-08-16/qb1_f34_triage_diagnostic_continuation_open_receipt_codex_v1.md`.
Transition script SHA-256:
`5cf7a7c5c6b25124aaeab08ca976847fef61c7516cf9bb4d51d39bad13e97213`.

Run exactly ONE read-only diagnostic over the frozen admitted study-QB
surface. Use the shipped admission, matrix, and F34 resolver semantics; do not
invent a parallel resolution law. Do not invoke `scripts/run_qb1_study.py` or
the top-level registered composition. The admitted matrix/F34 stage is the
ceiling: no folds, ridge fit, inference, comparison, or report.

The durable evidence must include:

1. Every affected study player-season key that would carry any null member of
   `{draft_round, draft_overall, is_udfa}` into H4 after the exact shipped
   eligibility, target, label-presence, and >50%-missingness ordering.
2. For each affected key, the exact `resolve_draft_join` resolution, `reason`,
   `matched_by`, audit fields, and player identity/name/season fields needed to
   distinguish the registered F34 states without guessing.
3. Match multiplicity on both routes: exact usable-GSIS candidate count and
   normalized-name fallback candidate count, plus the considered draft-row
   keys/season/round/pick/name/GSIS fields. Keep raw values safely represented;
   do not mutate them.
4. Exact reconciliation tables: all F34 `TRIAGE` player identities -> matrix
   player-season rows -> rows surviving the ridge lane's pre-draft-capital
   gates -> every H4 null-capital key. Reconcile totals in both directions and
   disclose any TRIAGE identity that never reaches H4 or any H4 null without a
   TRIAGE resolution.
5. One admission/load accounting record and SHA-256-style canonical frame
   digests before and after for every frame touched, proving no mutation.
6. Full grouped counts by resolution/reason and affected target season, while
   retaining the complete per-key enumeration. State the boundary: this
   diagnoses F34/H4 only and makes no last-wall claim.

Evidence artifacts may be written only under
`docs/agent-ledger/evidence/2026-08-16/` (diagnostic script, recorded output,
and routing note). No product code, tests, frozen inputs, registration,
manifests, state pins, or terminal report may change. No provider fetch,
repair, composition, rerun, commit, push, publication, or registered-result
access. Any accidental registered output is discarded unread. H2 QB rushing
remains UNDER TEST with no result.

Route the stable script/output hashes and the measured facts to me. Do not
propose a repair as authority; I will independently audit the evidence and
perform the registration read before any Round 18 transition.

PLEASE REPLY with: (a) ACK revision 110 and the exact diagnostic boundary, then route the completed measured evidence, OR (b) name a durable-state/pin mismatch before running anything.
