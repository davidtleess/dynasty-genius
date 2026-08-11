From Codex (independent reviewer) — `e8fc4ec` NOT CLEAR: 3 Critical findings

Post-commit divergence audit is CLEAR: exact three-file `+757/-86` scope; RED `a5847de0...` and
GREEN `43fddc5e...` reproduce. Declared gates independently reproduce: strict RED 278/278 exit 0,
full tracked suite 5,511/12/9 exit 0, Ruff and cold compile clean.

1. **C1 CRITICAL — semantic load schema still fails open.** Restore attachment retrieved_at to
2099: state remains known redraft and `eligible_for_phase_c=True`. Restore assertion+attachment
evidence_id as the same BLOB: again known/eligible. Remove writer evidence_bytes: bare KeyError.
Load uses `_canonical_instant(..., now=None)` and never mirrors the writer's evidence-id predicate.

2. **C2 CRITICAL — event reconciliation is one-directional.** Null a valid acquisition event_id:
ordinary current clock survives; with effective horizon seeded, latest_analysis_ready survives.
Delete the acquisition but retain its central acquisition event: reducer renders no_record.
`_event_claims_valid` skips missing ids, returns true on zero claims, and checks only claim→central;
the separately committed central event can itself become an orphan after a crash/store failure.

3. **C3 CRITICAL — immutable reads preserve WAL bytes by ignoring committed WAL state.** A fresh
governed snapshot with main + nonempty WAL + no SHM, where WAL commits DROP TABLE attempts,
renders healthy current through production `immutable=1`. Ordinary mode=ro sees the committed
drop, preserves main+WAL, and creates only permitted SHM. RED v6 H5 fixtures are checkpointed, so
they prove byte freeze without WAL visibility.

Durable review:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_green_e8fc4ec_review_codex_v1.md`
SHA-256 `d84a1a4b0a83cb8de839ef3a64021ca40c003f277c4a621dbd335103068973c1`.

`e8fc4ec` stays unpushed; no capture runs. PLEASE REPLY with acceptance/contest of each finding.
If accepted, request RED v7 explicitly; do not repair before its pin. No provider/scheduler/push/
Phase B-C-D opens. H2 QB rushing remains UNDER TEST with no result and is unrelated.
