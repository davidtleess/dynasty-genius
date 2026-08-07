# Review — PlayerProfiler protocol disposition v2

**Reviewer:** Codex · **Date:** 2026-08-07 · **Layer:** Layer 1 ingestion inventory

**Reviewed artifact:**
`docs/agent-ledger/evidence/2026-08-07/playerprofiler_protocol_disposition_claude_v2.md`
at SHA-256 `b00f9a7241f26eee3309ef08f9d559c921a4ae64bf8179dcbd6f24419b253640`.

## Verdict

**NOT CLEAR — one substantive overclaim in the separable constructive note and one literal
cross-reference error.** The branch-(b), F1/F2, and P1–P8 dispositions are otherwise **CLEAR**.
No catalog edit, checkbox movement, capture, provider call, export request, commit, or push is
authorized by this review.

## Checks that pass

- Branch (b), F1, F2, and the no-catalog-edit boundary are accepted exactly.
- P1 now makes a bounded current-tree/current-capability claim rather than an impossibility claim.
- P2 correctly records execution authority inside the manual-export shape and its human dependency.
- P3 correctly withdraws publication-cadence inference from observation-time state comparisons.
- P4 defines a complete report batch and predeclared block manifest as the experimental unit, with
  David retaining the choice of a cheaper slice-scoped fallback.
- P5 separates coverage/schema validity, raw hashes, and versioned semantic digests.
- P6 makes private retention and backup coverage an explicit David decision.
- P7 defines a three-observation off-season pilot with no cadence-closure threshold.
- P8 scopes the pilot to N6 and leaves N1–N8 open.
- The local §9 measurements reproduce: `league_transaction` has 932 rows; all 932 have non-null
  `created_at`, `status_updated_at`, and `raw_json`; there are 932 distinct `created_at` values and
  597 distinct `status_updated_at` values. The raw directory contains 20 snapshot files.
- Source provenance is real: `normalize_leg()` maps provider payload fields `created` and
  `status_updated` through `_iso_utc()` into the two normalized columns and retains the full payload
  in `raw_json` (`src/dynasty_genius/league_transactions.py:280-296`).

## R1 — §9 confuses event time with publication mechanism · **HIGH**

Lines 161–164 say the distribution of provider-stamped `created_at` values could establish that the
upstream is event-driven rather than periodic and provide a well-supported negative about
periodicity. It cannot.

Those values establish when transaction events occurred according to the provider payload. They do
not establish when the endpoint first exposed each record, when an upstream snapshot was rebuilt,
or whether exposure happened immediately, in periodic batches, or by some hybrid mechanism. A
periodically published endpoint can carry the same irregular original-event timestamps. The
artifact correctly concedes at lines 166–168 that event-to-visibility is unmeasured; that concession
also prevents the stronger publication-mechanism inference at lines 161–164.

The evidence can support this bounded statement:

> For the retained history of one league, Sleeper transaction records carry provider-stamped event
> and status-update times, and the observed transaction occurrence times are irregular. The data do
> not distinguish event-driven from periodic endpoint publication and do not measure publication
> latency.

This is useful evidence about record semantics and a reason an event-driven publication hypothesis
is plausible. It is not yet the independent source-publish evidence M4 requires, and it is not a
stronger cadence evidence class than N19's observation series; the two series answer different
questions and neither observes first visibility.

## R2 — wrong constructive-note cross-reference · **LOW**

Line 18 says `§4 below adds one constructive path`; the constructive note is §9. Replace `§4` with
`§9`.

## Sequencing ruling

Between the two requested next artifacts, repair the asymmetry artifact first, then author the
PlayerProfiler protocol v2. The asymmetry v1 contains accepted F1/F2 defects and is already the
factual basis for the expanded Sleeper open set; pinning its corrected form first leaves one clean
contract record for later catalog work. This sequencing does not change the PlayerProfiler protocol
design and does not authorize either artifact to land or any export request.

Before that sequence is treated as review-complete, revise this disposition's §9 to the bounded
record-semantics statement above and fix the §4/§9 reference. No new measurement run is needed for
those repairs.

**H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
