# A-C Steps 1-3 Round-3 Recheck — Codex v3

**Date:** 2026-08-06 ET  
**Layer:** Layer 1 inventory  
**Role:** independent reviewing lane  
**Artifact reviewed:** `docs/layer-1-data-inventory-catalog.md`  
**Reviewed SHA-256:** `ff25c9c8fba760c7d23ca8251b85162f4a0f7e9afdfcd7201c130f041b0ada91`  
**Verdict:** **NOT CLEAR**

The R1-R5 dispositions were checked against the seven-class definitions, the executable
FantasyCalc writers, the installed plist, the Sleeper fetch log, the R7 tables, and the whole
catalog. All five local repairs hold. N11's new `blocked` class is correct: the route is technically
writable, but its superseded/parallel-acquisition state is a named use/route blocker that prevents
scheduling. Five reconciliation findings remain.

## Q1 — MATERIAL: §6A's canonical cadence matrix still excludes N19 from the open set

Section 6E now correctly changes N19's source-publish cadence to `UNVERIFIED`, and the prose below
that table correctly says both N1-N8 and N19 remain open. But the §6A Closure Matrix still says:

> every §4.4 member now carries all five fields except N1-N8 PlayerProfiler source-publish cadence

That is false at this pin. The matrix is the declared closure surface and its pass condition says
`UNVERIFIED` leaves the row open. It must name **both** unverified groups. A downstream reader who
uses §6A rather than the later correction prose would incorrectly believe N19 is settled.

## Q2 — Canonical progress prose still describes pre-batch state

The top-level §1 progress block and the live summary near §3 still state that the following work is
"missing" or "unreconciled":

- Sleeper/FantasyCalc route reconciliation;
- complete Table B-N R7 states; and
- final automation classifications.

Sections 6B, 6D, and 6E now contain that work and mark it measured/awaiting review. The checkboxes
must remain open until independent clearance, but **authored-and-awaiting-review is not missing**.
Update the live progress prose to state the actual remaining gates: independent review plus the
specific unverified source clocks. This is the catalog's recurring correction-without-canonical-
reconciliation defect at its highest-level status surface.

## Q3 — N12/N14b still carry stale `manual_only` labels

The R2 line at §3 was fixed, but two other live canonical cells still carry the withdrawn class:

- registry row R13 calls `league_transactions.db` `manual_only`; and
- Table B-N row N14b ends its **Consumer state** cell with `manual_only`.

Section 4.4/6C/6E correctly classify N12-N14b as `automatic_candidate`. R13 should describe the
physical fact as **manually run / unscheduled**, without using a conflicting automation class.
N14b's consumer state should name its role as N12's raw-before-parse input/evidence and whether it
has a downstream consumer; an automation-class token does not belong in that column.

## Q4 — N19's `manual_only` class contradicts the seven-class vocabulary

`manual_only` is defined as a current access path requiring a human export or upload. N19 was
captured directly from Sleeper HTTP: `fetch_log.json` records 176 API calls and zero failures. Its
row itself says the unresolved condition is a **recurring-use decision**. That is a named **use
blocker**, which is the definition of `blocked`, not `manual_only`.

The honest current class is `blocked` pending a recurring-use decision. If that blocker is later
lifted, the technically available API route may become an `automatic_candidate`; the fact that the
first pull was manually initiated does not make its acquisition path a human export. Reconcile
§§4.4, 6C, and 6E. This is the same distinction correctly applied to N12 one row away.

## Q5 — N11's R7 consumer is mislabeled as the current market overlay

Section 6D says N11 is consumed by `market overlay`. The canonical N11 row and the code say
otherwise: `fc_snapshots.db` is an **optional legacy backtest instrument**, consumed only when
`scripts/run_backtest.py --market-store ...` supplies it to `WalkForwardDriver`. Repository search
finds no current app/service overlay consumer of `MarketSnapshotStore`.

Keep `consumed = yes`, but name the consumer accurately as the optional legacy backtest/market-
comparison harness. Calling it the market overlay contradicts the catalog's own statement that N11
is not the current overlay source and blurs the market-overlay separation this inventory is meant
to preserve.

## Independently checked and accepted

- Fresh hash matches `ff25c9c8...`; `git diff --numstat` is 258/65, `git diff --check` is clean,
  governance validation passes, and the ledger now records the correct pin-scoped numbers.
- N11 `blocked` is the correct current class. The installed `fc-snapshot` plist invokes
  `run_fc_forward_capture.py` against `fc_forward_capture.db`, while three executable legacy writers
  still default to `fc_snapshots.db`. Dormant is not immutable; desired `static_pinned` state needs
  physical write immunity.
- The declared-vs-physical gap in the plist comment is real and correctly recorded rather than
  silently repaired.
- The stale N12/N13 class assertion at the original R2 location is struck while its consumerless
  fact is preserved.
- N19's source cadence is correctly changed from local-capture `n/a` to `UNVERIFIED` in §6E.
- B20 now accurately distinguishes absent source capture from persisted derived values.
- No §1 checkbox moved and no executable surface changed.

This review authorizes no code, capture, scheduler, consumer migration, commit, push, or Layer 2
work. H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
