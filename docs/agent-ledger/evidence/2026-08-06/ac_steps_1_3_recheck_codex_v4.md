# A-C Steps 1-3 Round-4 Recheck — Codex v4

**Date:** 2026-08-06 ET  
**Layer:** Layer 1 inventory  
**Role:** independent reviewing lane  
**Artifact reviewed:** `docs/layer-1-data-inventory-catalog.md`  
**Reviewed SHA-256:** `0080e46e267fe043b9b536acb8983b2a327834aebb57893c755ff706c2add27f`  
**Verdict:** **NOT CLEAR**

All Q1-Q5 local repairs were checked and hold. The new N9/N10 consumer finding also reproduces:
the governed store feeds Market Divergence and What-Changed, while the live overlay service calls
the request-time `fetch_with_cache()` route. A whole-document sweep found three remaining defects;
T1 is material because it sits in the declared closure surface.

## T1 — MATERIAL: the closure matrix and §3 summary still describe pre-authoring state

The top §1 block is repaired, but the live §3 summary at lines 549-555 still says final automation
classes, complete R7 states, and route reconciliation are "genuinely incomplete." Sections 6B, 6D,
and 6E contain those authored rows and the new §1 block correctly calls them measured/awaiting
review. Q2 therefore was not reconciled at every live status surface.

The §6A Closure Matrix itself retains three stale current-state claims:

- the R7 row says states are "otherwise incomplete" even though §6D carries every enumerated row;
- the automation row says no canonical stream row carries a final class even though §4.4/§6E do;
- the cadence row says the fields are "not yet written onto the canonical rows" even though §6E
  carries them and its status correctly narrows the remaining issue to two `UNVERIFIED` clocks.

The automation-row status also says only one §4.4 cell was edited (N11), but round four explicitly
records N19 as the **second** edited cell. Update the matrix's current-state/question/status cells to
say **authored — awaiting independent review**, with only the actual unverified cells left open.
Checkboxes remain open; this is a truthfulness correction, not a request to close them.

## T2 — N19's canonical §4.4 source clock still repeats the R3 defect

Section 6E correctly records N19's source-publish cadence as `UNVERIFIED`. But §4.4—the declared
single canonical classification table—still places `one-time 2023–2026 replay evidence` in N19's
**Upstream publish / change rhythm** column (line 702). That is our local capture history, not the
source clock, exactly the R3 conflation already accepted twice.

Set the §4.4 upstream field to `UNVERIFIED`; retain the one-time replay fact in a local-capture or
evidence field. The N19 `blocked` class itself is independently accepted and should remain.

## T3 — the growing-store rule is violated by three live count claims

Section 6B.3 adopts an explicit rule: a count for a daily-growing store is published only with an
as-of date, or not at all. The live database is independently measured at 20,518 raw and 20,518
joinable rows through 2026-08-06. Three catalog sites still publish the old 20,043 count without an
as-of qualifier:

- §2.1 R8 physical state;
- the built-route summary immediately below Table A-R; and
- §3's `fc_forward_capture.db` grain decomposition (line 546).

Either update them to `20,518 as of 2026-08-06` or label the 20,043 measurement explicitly `as of
2026-08-05`. Do not silently rewrite historical measurements; satisfy the document's own rule at
each live claim.

## Independently checked and accepted

- Fresh hash matches `0080e46e...`; `git diff --numstat` is 323/81, `git diff --check` is clean,
  governance validation passes, and table shapes remain valid.
- §6A now names both open clock groups, N1-N8 and N19.
- §1 correctly distinguishes authored/awaiting-review from missing; its checkboxes remain open.
- Stale `manual_only` tokens are removed from R13 and N14b; N14b now names its raw-before-parse
  role rather than an automation class in a consumer cell.
- N19 `blocked` is correct: its 176-call direct API route is not a human export, and the unresolved
  recurring-use decision is a named use blocker.
- N11's consumer is correctly named as the optional legacy backtest/market-comparison harness.
- N9/N10's governed-store consumers are correctly named as Market Divergence and What-Changed; the
  live overlay's request-time acquisition defect is real and remains remediation, not inventory
  authority.
- No other non-nflverse summary consumer label contradicted its canonical §3.1 row in this sweep.
- No §1 checkbox moved and no executable surface changed.

This review authorizes no code, capture, scheduler, consumer migration, commit, push, or Layer 2
work. H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
