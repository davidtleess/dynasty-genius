# Realized-Outcome Scorer Wiring — Codex Framing v2 Re-review

**Cycle:** TW0813-SCORER-1 · **Date:** 2026-08-13 · **Lane:** Codex review  
**Reviewed artifact:** `realized_outcome_scorer_wiring_framing_claude_v2.md`  
**Reviewed SHA-256:** `e31a583cc4c41bf826b8d4eaffe830f2f3c22aa7e5fbf50b152979b7ae3a35c0`  
**Addendum reviewed:** `scorer_dg09_declared_addendum_wire_claude_v1.md`
(`8e763d5e346f153d3828992624bf625ebb3c71b4a0e06cf5f880871583dbc6a8`)  
**Verdict:** **NOT CLEAR — four BLOCKERs, one WARN.**

This is the requested round-2 integration review. It does not change product code. The review
independently re-read the pinned v2, disposition, current +98-line prediction-loader diff,
relevant source contracts, and named local substrates.

## Round-1 integration matrix

| Round-1 item | v2 status | Independent result |
|---|---|---|
| B1 denominator, per-status exclusions, parsed utilization | Integrated by v2 + addendum | §5.1–2 names all required pieces; addendum correctly makes counts declaration-relative, not hard-coded. On declared 2026-08-05 the relevant model-supported joinable denominator is 581: 501 Engine-B `captured` + 80 Engine-A `capture_incomplete`. The separate 12,209 whole-snapshot count is not that denominator. |
| B2 partial-MIF and WOPR parity | **Not integrated safely** | §4/§5 select a contract-forbidden substrate and cite no executable formula. See R2-B1/B2. |
| B3 frozen-cohort seeding and status repair | **Partially integrated** | Seeds are named, but the production derivation is absent. See R2-B3. |
| B4 Q2(c) | Direction integrated | Stability inference is withdrawn and absent anchor stays non-final. The open mechanism still needs an explicit build boundary. See R2-W1. |
| W1 denominators and catastrophic-partial seed | Integrated | §5.1 includes both and does not invent degraded bands. |
| W2 identity provenance/canonical loader | Integrated at framing level | §4 Q1 pins source pull time, SHA, mapping version, frozen DG ID, conflicts, and canonical loader reuse. |
| W3 malformed declaration shapes/types | Integrated | §5.2 names the missing object/type/format/duplicate-key families. |

## Findings

### R2-B1 — BLOCKER: `ff_opportunity` is explicitly `substrate_only`; v2 has not authorized or validated a scorer consumer

V2 §4 Q3 and §5.7 direct the scorer to derive realized WOPR from `ff_opportunity`. The landing
contract says the opposite: `tests/contract/test_ff_opportunity_ingestion_red.py:339-358`
classifies the stream as a third-party model output, states that any feature use requires its
own validation, and fails if any source/script/app Python file consumes or even references the
stream outside the adapter. That boundary test currently passes. The stream containing observed
component columns does not silently lift the consumer ban.

This is also a layer-1/2 dependency failure for a layer-3 scorer. V2 §7 promises no new
ingestion stream, but consumer validation is a different requirement and is neither authorized
nor framed.

**Required correction:** either (a) keep realized WOPR explicitly `unavailable` in this cycle,
or (b) obtain separate authority and frame the validation plus intentional amendment of the
`substrate_only` consumer boundary. Do not evade the test with indirect SQL naming.

### R2-B2 — BLOCKER: `engine_b_contract.py:117` is not an executable WOPR parity anchor and conflicts with the production calculation

The cited line is only a comment saying WOPR is `target_share × air_yards_share`; it specifies
neither coefficients nor denominator/null semantics. The existing assembly at
`scripts/assemble_engine_b_dataset.py:203-205` computes:

`target_share = targets / team_targets` and `air_yards_share = air_yards / team_air_yards`,
with zero denominators replaced by null, then
`weighted_opportunity = 1.5 * target_share.fillna(0) + 0.7 * air_yards_share.fillna(0)`.

Those are materially different contracts. A RED author cannot infer which one represents the
frozen model, nor invent weekly aggregation, residual-row handling, zero-denominator behavior,
or null behavior.

**Required correction:** if R2-B1 is separately authorized, pin the actual frozen-model formula
to executable provenance and specify grain, weekly aggregation, player versus residual rows,
team denominators, zero/null behavior, and numeric validation. Otherwise WOPR remains explicitly
`unavailable`.

### R2-B3 — BLOCKER: named survivorship statuses still have no production source or derivation contract

V2 §5.4 names `bye`, `injured`, `departed`, and `not-yet-played`, but does not say how the
producer obtains them. The frozen joinable table has no team column. The default stat loader
contains only stat-present players; `_build_outcomes` seeds IDs from those rows; and the outcome
store defaults missing input to `player_status="active"` and derives `game_played=True` when
points exist. Existing survivorship tests inject already-classified statuses, so their pass does
not validate production classification.

Local injury and depth-chart tables exist, but selecting them would require an explicit
season/week/identity/team join, freshness rule, precedence rule, and honest behavior for absent
or conflicting evidence. Neither table alone proves all four statuses.

**Required correction:** pin the authorized source and precedence for each status, including
identity/team joins and absent/conflicting evidence, or define a truthful `status_unavailable`
fact and narrow the promised taxonomy. The RED must exercise the production adapter, not only
fixtures that hand it the desired label.

### R2-B4 — BLOCKER: the supposedly exact health boundary has no value, basis, or gate-order contract

V2 §4 Q4 and §5.6 repeatedly say “pinned bound” but never state the number or comparison. The
existing `SCHEDULED_TARGET_MAX_AGE_DAYS = 14` governs a different condition: a finalized stale
scheduled target, checked with `age > 14` only after the current finality gate. Today
`week_not_finalized` returns before that check, so the existing constant cannot catch the health
trap without a new gate-order rule.

**Required correction:** state the authorized age, time/date basis, `>` versus `>=` boundary,
missing/unparseable-gameday behavior, explicit-target behavior, and how the check runs on a
non-finalized week. If 14 days is intended, say so and justify reuse of the stale-target value;
the RED author must not choose a product-health threshold.

### R2-W1 — WARN: Q2(c)'s safe default is integrated, but the open finality-anchor mechanism must be separated from this build's interface

V2 correctly says an absent anchor remains non-final and lists the finality-anchor mechanism as
David-gated. But §4 also says the gate “consumes a David-declared per-week finality anchor” under
current authority, without a governed location/shape/provider. DG-09's now-closed frozen-set
declaration is a different contract and does not close this finality decision. The RED may pin
an injected terminal-evidence interface and prove the absent-anchor honest-red path; it may not choose or
author the real finality declaration mechanism, nor represent that open choice as shipped
connectivity.

## RED authorship

**Codex holds RED authorship.** `docs/governance/02-agent-operating-loop.md` explicitly assigns
Codex the RED role, and the ratified realized-outcome plan also labels the relevant RED steps
Codex. Claude should not author this cycle's RED under “current practice.” After the framing
blockers are resolved, Codex will author the smallest failing contract; Claude remains GREEN.

## Checks and probes run

- Independently matched v2 SHA `e31a583c…`, disposition SHA `ee2f792b…`, and review-v1 SHA
  `980786a6…`.
- Independently matched the addendum SHA `8e763d5e…` and frozen declaration SHA `77544b3b…`;
  read David's verbatim declaration; verified `_default_prediction_loader(2026, 1)` returns
  501 rows locally and 2027 fails loud.
- Read-only SQL on the declared date verified 12,209 total snapshot rows (501 `captured`,
  11,708 `capture_incomplete`) and, critically, 581 model-supported five-key joinable rows
  (501 Engine B captured + 80 Engine A incomplete). B1 therefore binds to the declared
  joinable/model-supported universe at runtime, not either a candidate-date constant or the
  unfiltered whole-snapshot count.
- Re-read every v2 integration point for B1–B4/W1–W3 and the complete current script diff.
- Inspected the executable WOPR assembly, Engine B comment/feature contract,
  `ff_opportunity` stream declaration and `substrate_only` boundary test, outcome store and
  producer, frozen-joinable schema, injury/depth/snap/ff-opportunity DDL, finality/health gate
  order, and the ratified realized-outcome plan.
- Focused boundary/survivorship tests: **5 passed**. This proves the current substrate ban and
  injected store behavior; it does not supply the missing producer contracts.
- `git diff --check` and strict Python compilation on the scorer CLI/outcome store/Engine B
  contract: pass.
- Source databases were queried read-only. Codex did not author or edit the declaration. No
  product code, source store, scheduler, dependency, commit, push, provider, or Studio action
  occurred.
