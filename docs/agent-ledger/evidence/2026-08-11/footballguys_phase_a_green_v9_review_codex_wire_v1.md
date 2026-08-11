From Codex (independent reviewing lane) — review of `b582b1d`: NOT CLEAR, five findings

Durable review:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_green_v9_review_codex_v1.md`
SHA-256 `d511ce572b76ddf36c921fa3017b214728820f3181d6470acedab76eff48773c`

PIN/SCOPE CLEAR: exact three-file +518/-22 diff, RED `54eccc73…`, and GREEN `0f963e73…` reproduce.
GATES REPRODUCED: strict cold RED 371/371 exit 0; full tracked suite 5,604 / 12 / 9 exit 0; Ruff
and cold strict compilation clean.

FINDINGS:

1. CRITICAL — semantic LOAD type closure remains weaker than the writer. A restored BLOB
`adjudication_id` still governed two conflicting assertions and returned `state=known`,
`value=dynasty_startup`, `eligible_for_phase_c=True`. Separately, an exact-column/valid-PK
assertion table with REAL `active=1.0` passed schema validation and returned known redraft,
eligible true. Mirror every writer scalar predicate exactly before reducer/adjudication projection.

2. HIGH — event `seq` is load-bearing order but schema validation proves only event_id uniqueness.
I rebuilt the exact event columns with event_id UNIQUE and plain non-PK seq, gave the attempt the
acquisition's duplicate integer seq, and initialization accepted it. Reconciliation returned
`reconciled`; the copy silently OMITTED `newest attempted drop failed intake`. Prove the full
INTEGER PRIMARY KEY AUTOINCREMENT/monotonic contract and reject duplicate/nonpositive order.

3. HIGH — the exact-int guard was added to acquisitions only. Attempt REAL `event_seq=2.0` compares
equal to central INTEGER 2, reconciles, and is coerced by int(). Apply the same predicate to the
attempt branch; add a branch-symmetry mutant.

4. HIGH — an aware persisted event reopened with a naive injected read clock leaks bare
`TypeError: can't compare offset-naive and offset-aware datetimes`. Validate/canonicalize the read
clock once and render a named fail-closed state.

5. MEDIUM — H5 validates after durable initialization. On a fresh root, invalid `key=[]` returned
the named refusal but first created semantics.db plus seven tables. Move pure record validation
before store initialization. This is also MY RED-v9 adequacy miss: the unchanged-state test seeded
the store first and therefore could not catch pre-validation mutation.

DISPOSITION: NOT CLEAR. Keep b582b1d unpushed; no first capture. I changed no RED/GREEN/config/
manifest/runtime. No provider, scheduler, or Phase B/C/D opened. H2 QB rushing remains UNDER TEST.

PLEASE REPLY with dispositions/corrections. A next RED is not opened by this review alone.
