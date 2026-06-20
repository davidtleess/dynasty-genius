# Roster Audit Increment 3 Task B — xVAR Bracket Grouping (Design Spec)

- Status: **v2 — David-approved edge set (COARSE 3-bucket, 2026-06-20); awaiting cockpit dual-CLEAR confirmation (Codex F1/F2 integration; Gemini coarse-amendment match); NO RED until dual-CLEAR**
- Authorship: Claude Code authors; Gemini governance-reviews; Codex technical-reviews (David-assigned)
- Date: 2026-06-20
- Governance: constitution 1.0.0, north-star 1.0.0, operating-loop 1.0.0, code-hygiene 1.0.0
- Sequence context: step 2 of the cockpit-converged sequence (W5b ✅ verified → **Task B** → Subsystem 1)

## 1. Authorization & scope

David green-lit Task B (active surface: live Roster Audit) under a **strict descriptive-only ceiling**. Cockpit converged on the **frontend-only neutral xVAR-bracket display-binning** path (NOT producer-emitted token, NOT role/asset-class tiers). This spec defines that grouping as a fully descriptive, mathematical display binning over the only cross-position-valid value field exposed on the DTO.

In scope: one new client-side `GroupKey = "xvar_bracket"` in `frontend/src/roster/rosterTransform.ts`; selector wiring in the Roster Audit controls/container. Out of scope: any backend/API/OpenAPI/model change; producer tokens; role/quality semantics; aging axis (already covered by `depreciation_band`); decision/action language.

## 2. How this resolves the v1 review findings (F1–F6)

- **F1 (cross-position validity):** group on **raw `xvar`** only. `dynasty_value_score`/`dvs_pct` are within-position (`universe_pvo_batch.py:95`) and are NOT used. `xvar` is the only cross-position value field on `RosterAuditPlayer` (`zod.gen.ts:325-360`; no `xvar_percentile_*` exposed).
- **F2 (no invented scoring logic):** pure **display binning** of an already-computed scalar with documented, fixed edges — no classification/scoring logic. (Producer-token path explicitly NOT taken, per converged decision; that would touch the backend.)
- **F3 (no duplication):** the aging axis stays in the existing `depreciation_band` group; `xvar_bracket` does not re-implement it.
- **F4 (single axis):** one orthogonal axis only — cross-position value magnitude.
- **F5 (no banned tiering):** labels are **strictly numeric**; no "Core Starter/Depth/Elite/Bust" or any quality/role word. (See §5 governance-review item on optional subtext.)
- **F6 (fail-closed contract):** full contract in §4–§6 (edges, provenance, order, null bucket, intra-bucket sort, selector label, acceptance + falsification matrix).

## 3. Data grounding (why fixed edges, and which)

Measured the real cross-position `xvar` distribution to avoid arbitrary edges:
- **David's roster (roster 1, 28 players):** 15 scored, range −22.8 to 29.2, median −2.1; **13 not modeled** (prospects/QBs).
- **Universe (399 xvar-populated rows):** min −101.65, max 58.05, median −12.30.

The earlier 50.0/20.0 edges are miscalibrated: on David's roster the ≥50 bucket is empty and 13/28 are unmodeled. Edges below are chosen from the observed positive cross-position range.

## 4. Contract (v2 — COARSE, David-approved 2026-06-20)

New `GroupKey` value: `"xvar_bracket"` (added to the existing `"none" | "position" | "depreciation_band"` union).

Data source: `p.xvar` (`number | null | undefined`) ONLY.

Deterministic brackets, rendered **high → low**, missing **last**:

| Order | Label | Predicate |
|------|-------|-----------|
| 1 | `xVAR 0.0+` | `Number.isFinite(x) && x >= 0.0` |
| 2 | `xVAR below 0.0 (sub-replacement)` | `Number.isFinite(x) && x < 0.0` |
| 3 | `xVAR not modeled` | `x` null/undefined **or non-finite** (`NaN`/`±Infinity`) |

Provenance (documented, non-model): **`0.0` = replacement level** (xVAR is value-above-replacement; the only mathematically principled edge). No interior/arbitrary edges — the 5-bucket proposal was struck by governance (Gemini) as implicit unversioned tiering; David approved the coarse set 2026-06-20. This resolves Codex F1 (no interior decimal-label mismatch remains) and Gemini's §7 ruling.

Non-finite handling (Codex F2): non-finite `xvar` routes to `xVAR not modeled`, matching the existing `num()` convention (`rosterTransform.ts:12`) that `applySort("xvar")` already relies on — so sort and group treat non-finite identically.

Empty brackets are omitted (no empty buckets rendered). `xVAR not modeled` always renders last and is never merged into a value bucket (no fabricated value for missing). Intra-bucket order = the active sort key (existing `applyGroup(players, key, sortKey)` contract; nulls-last preserved). Selector label: `xVAR bracket`.

Trust: `decision_supported=False` and the EXPERIMENTAL header/disclaimer are untouched. No row hidden. No reordering of trust chips.

## 5. Governance-review items (for Gemini)

1. Confirm strictly-numeric labels clear the descriptive-only ceiling (no banned tiering).
2. **Optional subtext decision:** may `xVAR below 0.0` carry a parenthetical `(sub-replacement)`? It is a literal analytics description of `x < 0`, not an action — Gemini to rule descriptive vs prescriptive. Default: omit (numeric only) unless Gemini clears it.
3. Confirm `xVAR not modeled` is honest framing for the 13 unmodeled roster players (prospects/Engine-A/unscored), consistent with existing Missing-bucket precedent.

## 6. Acceptance criteria & falsification matrix

AC: deterministic high→low order with missing last; correct half-open boundaries; no empty buckets; missing never merged; intra-bucket sort honored; selector lists the option; `decision_supported`/EXPERIMENTAL intact; no backend/OpenAPI/model change; banned-language clean.

Falsification matrix (each → a RED test):
- valid-nominal mixed roster spanning all 3 buckets;
- boundary exactness: `x = 0.0` → bucket 1 (`xVAR 0.0+`); `x = -0.0001` → bucket 2 (`below 0.0`);
- `null` and `undefined` xvar → `xVAR not modeled` (and last);
- non-finite xvar (`NaN`, `Infinity`, `-Infinity`) → `xVAR not modeled` (Codex F2; consistent with `num()`);
- all-missing roster → only the missing bucket;
- empty roster → `[]` (no crash, no fabricated buckets);
- single-bucket roster → only that bucket rendered (others omitted, not empty);
- ties within a bucket → ordered by active sort, deterministic.

## 7. Granularity decision — RESOLVED (David, 2026-06-20)

Bracket granularity vs provenance was the open question. **Gemini (governance) struck** the 5-bucket version: arbitrary interior edges (10/25) function as implicit unversioned quality tiers, violating the "no unversioned scoring logic" mandate. **David ruled COARSE** (3-bucket, §4) — accepting the lower granularity as the governance-safe, frontend-only path. The only principled edge (`0.0` = replacement) is retained.

Deferred (NOT in scope for Task B): granular **percentile-band** value tiers (top-quartile / above-median / etc.) would be principled and versioned but require the backend to expose a cross-position xVAR percentile (a producer change) — a larger, contract-touching initiative the cockpit excluded from Task B. Available as a future David-authorized initiative if granularity is later wanted.

## 8. Build sequence (post-approval only)

spec dual-CLEAR (Codex technical + Gemini governance) → David approves edges → Codex RED → Claude GREEN → dual-CLEAR per task → David-authorized commit → zero-divergence audit. No RED before this spec is dual-CLEARED and David-approved.
