# W5b — Cross-Lane `market_package_requires_manual_review` Producer (Design Spec)

- Status: **v3 — round-2 bucket-pick defect (Codex C2) resolved via fail-closed Option A; Gemini governance CLEAR on v2 + pre-cleared Option A. Awaiting Codex final technical CLEAR. Q3 sensitivity (B) stricter per David (adjustable at CLEAR). NO RED until dual-CLEAR + David approval.**
- Authorship: Claude Code authors; Codex technical-reviews; Gemini governance-reviews (David-assigned lanes)
- Date: 2026-06-22
- Governance: constitution 1.0.0, north-star 1.0.0, operating-loop 1.0.0, code-hygiene 1.0.0
- Sequence context: David-selected next initiative after S1 shipped. Closes the verified deferred-by-design Trade Lab residual (2026-06-20 W5b audit, "Path 1 — cross-lane producer").

## 0. Round-1 review resolution (v1 → v2)

Both lanes independently **verified the §3.1 `adjusted_favors` normalization
direction is correct** (`reconciler.py:107-121` no-overflow side_b=received=david;
`reconciler.py:169-184` overflow adjusted_received>sent=david). Gemini **confirmed
Q3 option B avoids implying a validated edge** (scale-blind comparison treats both
lanes symmetrically) — resolving the §7.3 concern. Integrated defects:

- **C1 (MEDIUM)** coverage completeness must include forced-cut penalty candidates, not just traded assets → §3.3.
- **C2 (MEDIUM)** pick hydration uses `draft_pick_valuation.value_pick` (NOT the deprecated `value_draft_pick`) → §5. **Round-2 resolution:** `value_pick` has no `bucket` parameter (`draft_pick_valuation.py:358-367`) and the market lane already treats bucket picks as unresolved (`market_reconciler.py:193-199`). v3 adopts **Option A (fail-closed)** — bucket-only refs are NOT priced (model-coverage-incomplete); no invented bucket→tier mapping. Both lanes agree.
- **C3 (LOW/MED)** non-regression expressed as concrete spy/behavioral contract tests, not "byte-unchanged" → §5.1 + §9.
- **C4 / G1** metrics under-auditable → expose model floats + direction codes → §6.
- **G2** split the suppression caveat per-lane (don't hide which lane is incomplete) → §4.
- **G3** lock the exact message template (no dynamic string = banned-language vector) → §6.

## 1. Authorization & scope

David authorized building the cross-lane producer that finally emits
`market_package_requires_manual_review`. The enum value already exists
(`market_reconciler.py:120`) but is **never emitted**; W4's
`attach_competitive_realism_warnings` documents why (`market_reconciler.py:668`):
the market-blind lane has no model-native package delta, so it cannot detect a
model-vs-market directional divergence. W5b builds the missing producer.

**Goal:** advisory-only flag, fired when the MODEL and the MARKET disagree on
*which side a trade favors* by enough to warrant manual review — the
constitutional "honest uncertainty" defense on multi-player / package swaps.

**In scope:**
- one new **pure** module `src/dynasty_genius/trade_lab/cross_lane_review.py`;
- model-asset xVAR **hydration** + the producer call wired into
  `app/api/routes/trade_market.py::reconcile_trade_market_endpoint`;
- emit the single `market_package_requires_manual_review` warning into the
  existing `realism_warnings` list.

**Out of scope (hard boundary):** any change to market math
(`market_reconciler.py` stays guard-tested market-blind), any Engine A/B model
feature/training change, any new endpoint, any consumer rewiring beyond
populating `realism_warnings`, and any frontend code (`MarketLanePanel` renders
`realism_warnings` generically — confirm in §8). `decision_supported` stays
locked `False`; frontend HOLD otherwise intact.

## 2. Converged scoping positions (Q1–Q6)

| Q | Position |
|---|----------|
| **Q1 Location** | New **pure** `cross_lane_review.py`; route calls it after W4. Nothing in `market_reconciler.py`. |
| **Q2 Model delta** | Reuse Trade Lab math via a **hydrated** `reconcile_trade_roster` → post-penalty `adjusted_favors` label + signed `adjusted_david_received_value − base_evaluation.side_a.side_value`. No raw xVAR-sum re-implementation. |
| **Q3 Trigger** | **Scale-blind label comparison.** Classify each lane → {`david`,`counterparty`,`neutral`,`unavailable`}; **(B) emit ONLY on opposite directional**. No cross-scale subtraction. |
| **Q4 Fail-closed** | Either lane `unavailable` (incomplete coverage incl. forced cuts) → **suppress** + a per-lane envelope caveat. Never emit on partial evidence. |
| **Q5 Shape** | Reuse `MarketRealismWarning` (`severity:"advisory"`, `decision_supported=False`); float-only `metrics` incl. model + market + direction codes; **locked** message template. |
| **Q6 Scope** | One warning type only; no market-math/model/endpoint/consumer/FE change. |

## 3. Lane label derivation (the core)

Each lane is reduced to a directional label on **its own scale** using the
existing `TRADE_PARITY_BAND = 0.10` (`engine_b_contract.py:67`) as a
**dimensionless within-lane neutrality band** (never a model↔market blend). No
model and market values are ever subtracted from each other.

### 3.1 Model label (post-penalty)
From a **hydrated** `reconcile_trade_roster(...)` (§5), read `adjusted_favors`.

`adjusted_favors` has **two vocabularies** by roster overflow; the producer MUST
normalize both (verified correct by both lanes round 1):
- no-overflow (`reconciler.py:120`): {`neutral`,`side_a`(sent),`side_b`(received)};
- overflow (`reconciler.py:180-184`): {`neutral`,`david`,`counterparty`}.

Normalization (received-favors-David invariant): `side_b`→`david`;
`side_a`→`counterparty`; `david`→`david`; `counterparty`→`counterparty`;
`neutral`→`neutral`. Any other value (incl. wrong-type `None`/`int`) → fail loud
`ValueError`; never silently mapped.

Signed model floats for audit/metrics (§6): `adjusted_model_received =
adjusted_david_received_value`; `adjusted_model_sent =
base_evaluation.side_a.side_value`; `model_delta_signed = received − sent`;
`model_relative_delta = |model_delta_signed| / max(sent, received)` (0 if max≤0).

### 3.2 Market label
From `market_delta_for_david = adjusted_market_received − adjusted_market_sent`
(`market_reconciler.py:498`; sign>0 = favors David):
`market_relative_delta = |market_delta_for_david| / max(adjusted_market_sent,
adjusted_market_received)` (band undefined when both 0 → `neutral`).
- `market_relative_delta ≤ TRADE_PARITY_BAND` → `neutral`;
- else `market_delta_for_david > 0` → `david`; `< 0` → `counterparty`.

### 3.3 Coverage → `unavailable` (C1: includes forced-cut candidates)
A lane is `unavailable` (and the warning is suppressed, §4) when its adjusted
delta is built on partial data. Both the traded assets AND the forced-cut
penalty candidates that move the adjusted values must be covered:

- **Model incomplete** when: any traded asset (sent or received) lacks model xVAR
  after hydration (player xVAR `None`, **bucket-only pick** per §5 Option A,
  unrostered prospect, unresolved ref); OR
  the hydrated `reconcile_trade_roster` `roster_penalty` reports
  unresolved/uncovered forced-cut candidates (a forced-cut candidate without a
  usable xVAR — surfaced via `penalty_caveats` / unresolved count). Never infer 0.
- **Market incomplete** when: any traded asset has `market_value None` or
  `resolution == "unresolved"`; OR `reconciliation.coverage_gaps` is non-empty; OR
  the David (and, when requested, counterparty) forced-cut penalty has
  `unresolved_cut_count > 0`. Never infer 0.

## 4. Divergence policy (Q3 = B, David-set) + fail-closed caveats (G2)

Emit `market_package_requires_manual_review` **iff**:
`(model_label, market_label) ∈ {(david, counterparty), (counterparty, david)}`.
Every other combination (any `neutral`, any `unavailable`, or agreement) → **no
emit**.

When suppression is due to `unavailable`, attach the **specific** per-lane
envelope caveat(s) so David sees *which* lane was incomplete (G2 — no single
obfuscating caveat):
- model incomplete → `cross_lane_manual_review_suppressed_model_coverage_incomplete`
- market incomplete → `cross_lane_manual_review_suppressed_market_coverage_incomplete`
(both, when both incomplete). The producer returns the specific abort reason; the
route maps it to the caveat(s).

This is the **stricter** v1 (high-signal). Gemini noted a technical preference
for the **looser (A)** variant (also firing on directional-vs-neutral, "where a
human should review"); David ruled **B**, and Gemini concurred B is
governance-safe. David may switch to A at CLEAR by widening the emit set —
no other code change.

## 5. Route wiring & non-regression invariant

In `reconcile_trade_market_endpoint`, AFTER W4 (step 7), add a cross-lane step:

1. **Hydrate** model `TradeAsset`s from the `MarketAssetRef`s, reusing existing
   pricing (C2 — use the live `draft_pick_valuation.value_pick`; the deprecated
   `value_draft_pick` is barred). Explicit per-kind policy:
   - player → `pvo_lookup[sleeper_id]["valuation"]["xvar"]`;
   - **exact-slot** pick (`year`+`round`+`slot`) → `value_pick(year, round_,
     slot=slot, curve=…)`;
   - **round-only** pick (`year`+`round`, no slot, no bucket) →
     `value_pick(year, round_, curve=…)`;
   - **bucket-only** pick (`MarketAssetRef.bucket` ∈ {early,mid,late} set) →
     **NOT priced** → xVAR `None` (Option A, fail-closed): `value_pick` has no
     bucket arg (`draft_pick_valuation.py:358-367`) and the market lane already
     treats bucket picks as unresolved (`market_reconciler.py:193-199`). A
     concrete bucket→tier mapping is deferred to a future backtested spec.
   - unrostered prospect / otherwise unresolvable → xVAR `None`.
   Any `None` xVAR drives §3.3 model `unavailable` (suppress + caveat).
2. Run a **dedicated** `reconcile_trade_roster(hydrated_sent, hydrated_received,
   universe_pvo, sleeper_snapshot)` to obtain `adjusted_favors` + signed model
   floats (§3.1).
3. Compute coverage flags (§3.3) and call the pure producer (§6).
4. Append any returned warning to `realism_warnings`; append the specific §4
   coverage caveat(s) to the envelope `caveats` on suppression.

### 5.1 Non-regression invariant (C3 — behavioral, not "byte-unchanged")
Proven by **spy/behavioral contract tests**, since runtime tests prove behavior
and call-separation, not source byte-identity:
- the EXISTING cut-selection call `reconcile_trade_roster(david_assets,
  received_model_assets, …)` (`trade_market.py:176`) still receives `xvar=None`
  assets and feeds `david_roster_penalty` into `reconcile_trade_market`
  unchanged;
- the W5b hydrated reconcile is a **separate** call occurring only **after**
  market reconciliation + W3 + W4, and its result is used **only** for the
  cross-lane warning;
- in a fixture where **no** cross-lane warning fires, these response fields are
  **identical** with and without the W5b step: `market_sent_raw`,
  `market_received_raw`, `adjusted_market_sent`, `adjusted_market_received`,
  `market_delta_for_david`, both forced-cut penalty blocks,
  `*.divergence_context` (W3), and existing W4 `realism_warnings`. Only
  `realism_warnings` (new entry) / `caveats` (coverage) may change when W5b acts.

## 6. Pure producer contract (`cross_lane_review.py`)

```
def evaluate_cross_lane_manual_review(
    *, model_favors_raw: object, model_coverage_complete: bool,
    model_delta_signed: float, adjusted_model_sent: float,
    adjusted_model_received: float,
    market_delta_for_david: float, adjusted_market_sent: float,
    adjusted_market_received: float, market_coverage_complete: bool,
    parity_band: float = TRADE_PARITY_BAND,
) -> CrossLaneReviewResult
```
- normalizes `model_favors_raw` (§3.1, fail-loud on unknown/wrong-type);
- derives both labels (§3.1/§3.2), coverage→`unavailable` (§3.3);
- returns `CrossLaneReviewResult(warning: Optional[MarketRealismWarning],
  suppressed_reason: Optional[Literal["model_coverage_incomplete",
  "market_coverage_incomplete"]] | set)` so the route emits the precise G2
  caveat(s). Pure, no I/O, unit-testable in isolation.

`MarketRealismWarning` fields when emitted:
- `warning_type="market_package_requires_manual_review"`, `severity="advisory"`,
  `decision_supported=False`;
- `metrics` (float-only — G1/C4, reconstruct-without-prose): `model_delta_signed`,
  `adjusted_model_sent`, `adjusted_model_received`, `model_relative_delta`,
  `model_direction_code`, `market_delta_for_david`, `adjusted_market_sent`,
  `adjusted_market_received`, `market_relative_delta`, `market_direction_code`,
  `parity_band`. Direction codes: `-1.0` counterparty, `0.0` neutral, `1.0` david;
- `message` — **locked template (G3)**, labels strictly `"David"`/`"Counterparty"`:
  `"Model favors {model_label} but Market favors {market_label}. Manual review of
  the asset package is recommended."` (No dynamic per-asset prose. Symmetric
  naming of both lanes — does not assert the model is correct.)
- `caveats`: `["market_realism_warning_only", "market_overlay_display_only",
  "model_market_scales_not_comparable", "decision_supported_false"]`.

## 7. Governance items (resolved round 1)

1. **Message neutrality / banned-language (G3):** locked template, fixed
   substitution set {David, Counterparty} — no dynamic banned-language vector.
2. **Fail-closed honesty (G2):** per-lane suppression caveats — David sees which
   lane was incomplete; never a silent or single obfuscating suppression.
3. **Divergence is unvalidated (§7.3, Gemini-confirmed):** the scale-blind
   symmetric comparison treats both lanes neutrally and the message names both
   symmetrically; it does not assert a validated edge or "model right / market
   wrong" (`[[feedback_divergence_is_unvalidated]]`; QB model weakest, G3 deferred).
   `decision_supported=False` locked on the warning and recursively.

## 8. Open items for CLEAR

- **Q3 sensitivity** — B default; David may relax to A by widening the §4 emit set.
- **Market parity band** — reuse `TRADE_PARITY_BAND=0.10` as a within-lane band
  (v1 choice for principled symmetry); cockpit may argue a dedicated constant.
- **FE confirmation** — verify `MarketLanePanel.tsx:51-60` renders an arbitrary
  `realism_warnings[*].warning_type` generically; if it switches per type, a
  one-line copy/test addition is in scope (else no FE code).

## 9. Acceptance criteria & falsification matrix

AC: producer pure + fail-loud on unknown/wrong-type model token; both
`adjusted_favors` vocabularies normalized; labels derived per-lane (no
cross-scale subtraction); emits only on §4 opposite-directional set; suppresses +
per-lane caveat on `unavailable` incl. forced-cut gaps; warning advisory /
`decision_supported=False` / float-only auditable metrics / locked message /
banned-language clean; cut-selection call + market math + W3/W4 behaviorally
unchanged; no OpenAPI/model/FE change (or one-line FE only).

Falsification matrix (each → a RED test):
- **valid-nominal divergence**: model `david` × market `counterparty` → emit; reverse → emit.
- **agreement**: `david`×`david` → no emit; `counterparty`×`counterparty` → no emit.
- **neutral suppression (B)**: `david`×`neutral` → no emit; `neutral`×`counterparty` → no emit.
- **vocabulary normalization**: `side_b` & `david` → `david`; `side_a` & `counterparty` → `counterparty`.
- **wrong-type / unknown model token**: unknown string, `None`, `int` → `ValueError`.
- **market band boundary**: `market_relative_delta = band` exactly → `neutral` (≤); `band+ε` → directional.
- **both market sides 0** → market `neutral` → no emit.
- **model coverage — traded asset** xVAR `None` → `unavailable` → no emit + model caveat.
- **model coverage — forced-cut gap** (C1): a forced-cut candidate lacks xVAR → `unavailable` + model caveat.
- **market coverage — traded asset** `market_value None`/`unresolved` → `unavailable` + market caveat.
- **market coverage — forced-cut gap** (C1): David forced-cut `unresolved_cut_count>0` → `unavailable` + market caveat; same for counterparty when requested.
- **both lanes incomplete** → both caveats present.
- **pick hydration** (C2, Option A): exact-slot → `value_pick(..., slot=slot)`; round-only → `value_pick(...)`; **bucket-only → NOT priced → model-coverage-incomplete** (suppress + model caveat); deprecated `value_draft_pick` not imported/used.
- **duplicate pick `quantity_id`s** preserved through hydration + coverage.
- **negative/sub-replacement xVAR** follows evaluator (`xvar ≤ 0` not counted in side value); documented in model label/coverage tests.
- **non-finite numeric inputs** (`NaN`/`±inf`) → fail loud or suppress, never emit.
- **audit metrics**: emitted warning's float metrics reconstruct why it fired without parsing prose.
- **non-regression spy** (C3, §5.1): first cut-selection reconcile receives `xvar=None`; W5b hydrated reconcile is separate + post-W4; listed response fields identical before/after W5b when no warning fires.
- **banned-language**: emitted `message` scanned word-boundary → clean.

## 10. Build sequence (post-approval only)

spec dual-CLEAR (Codex technical + Gemini governance) → David approves (incl. Q3
B-vs-A final call) → Codex RED → Claude GREEN → dual-CLEAR per task →
David-authorized commit → zero-divergence audit → close-the-loop. No RED before
this spec is dual-CLEARED and David-approved. Likely a 2-task build: T1 pure
producer (`cross_lane_review.py` + RED matrix), T2 route hydration + wiring +
non-regression spy guard.
