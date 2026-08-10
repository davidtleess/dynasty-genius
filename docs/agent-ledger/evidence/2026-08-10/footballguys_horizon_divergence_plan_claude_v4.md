# Horizon Divergence plan v4 (Claude, implementing lane)

Date: 2026-08-10 · Supersedes v3 (`ec4e2bb2…`), v2 (`0595cae3…`), v1 (`2ea1bacf…`) · Responsive to
the Codex round-3 review (plan finding 1: stale live pointers — ACCEPT, repaired here; Phase A
findings 2–8 dispositioned in Phase A framing v4). Layer 5 presenting, foundation-first; the `05`
§3 check stands as recorded in v1 §2.

**Round-3 finding 1 (Low), accepted:** v3's §9 and David-word register pointed at superseded Phase A
framing v2 — operational pointers, not historical citations, so a future lane following them lands
on retired retention and transaction rules. Both now name the live companion **by exact identity**,
and this repair note is the only content change from v3.

## 0. Disposition — ten findings, ten accepts, zero contested

| # | Finding | Disposition |
| :-- | :-- | :-- |
| 1 | **Critical** — plan assumed `adp_sleeper-sf` = seasonal redraft; pilot state is `horizon=unverified` | **ACCEPT** → Phase A exact-field semantic contract (§1) |
| 2 | Bundle receipt must be atomic with the identity sidecar | **ACCEPT** → Phase A framing (landed v2 §3; live v4 §3–§5) |
| 3 | Census-as-oracle is circular | **ACCEPT** → independent adjudicated fixture (§2) |
| 4 | Full prospective identity-gate set carries forward, not one pool number | **ACCEPT verbatim** (§3) |
| 5 | Neither proposed delta valid; freeze one estimand; strike consensus ADP | **ACCEPT** (§4) |
| 6 | Tail labels are hypotheses; neutral source-relative language only | **ACCEPT** (§5) |
| 7 | Temporal pairing not closed; retrieval ≠ source-period alignment | **ACCEPT** → §6 here + Phase A framing (landed v2 §5; live v4 §5) |
| 8 | Intake success / readiness / freshness / retention conflated; offsite is a David word | **ACCEPT** → Phase A framing (landed v2 §4/§6; live v4 §5–§8) |
| 9 | "Benchmark" overclaims; archive + comparability key + series breaks | **ACCEPT** (§7) |
| 10 | Dedicated namespace; strengthen mutant matrix | **ACCEPT** (§8) |

**The Critical finding, conceded plainly:** v1's product object was named "redraft vs dynasty"
before any provider-authentic evidence bound the field to a horizon. That is the same defect class
this whole program exists to prevent — an assumed semantic laundered into a construct name. Until
Phase A records the semantic contract, the honest name is **market-A-vs-market-B divergence with
`horizon=unknown`**, and every "redraft/seasonal" label is barred. If the field proves
dynasty-startup, that is a *startup-draft-vs-trade-price* construct requiring a new framing — not a
renamed result.

## 1. Frozen: the semantic contract gate (finding 1)

Phase A records, per bundle: `product_family`, export/version, exact field name, format, scoring,
and `horizon ∈ {seasonal_redraft, dynasty_startup, unknown}` — supported ONLY by a
provider-authentic evidence pointer or captured export/UI metadata with hash + retrieval
provenance. Never inferred from the empty `adp_sleeper-redraft` column, numeric shape, filename, or
David's declaration alone. `unknown` supports intake and the monthly notice; **it closes Phase C
and bars every horizon label.**

## 2. Frozen: the Phase-B oracle (finding 3)

An independently adjudicated, versioned minimal fixture with explicit expected outcomes per verdict
class: exact same-human · approved nickname · wrong human different-position · wrong human
same-position · name-pass/position-fail quarantine · unresolved id · id absent from sidecar ·
missing/invalid position · duplicate/conflicting evidence · **plus a novel PFR-counter collision
not among the known 34**, so hard-coding the known ids cannot pass. The minimized census demotes to
a regression/provenance artifact. Phase B may frame in parallel once Phase A's bundle interface is
frozen; the first new drop is acceptance input, never the source of its own expected answers.

## 3. Frozen: the prospective identity gates (finding 4, carried verbatim)

Before any unseen vintage is examined: (1) verified identity ≥90% of populated SF rows; (2) 100%
for the union of both sources' native top-24 sets; (3) ≥95% for Footballguys top-100; (4) ≥85% in
every preregistered rank/position/experience stratum with n ≥ 20; (5) final verified matched cohort
≥80% of the original SF population; (6) complete attrition ladder + excluded-set composition
report. **The known vintage (328/500 verified, 285/500 matched) FAILS and cannot be rehabilitated
or used to tune thresholds post-inspection; a Phase-C run against it may emit only the failed gate
and counts — no player deltas, no tails.**

## 4. The estimand — REQUIREMENTS BOUND NOW, FORMULA CLOSED IN PHASE-C FRAMING (round-2 finding 1)

**Conceded: v2 called this section "frozen" while it froze requirements around an unspecified
formula — two obedient implementations could emit different deltas.** Since no Phase-C RED is open,
the honest state is: the requirements below are binding, and the **exact contract closes in Phase-C
framing**, which must specify at minimum: the FantasyCalc eligible-player predicate (row-type
predicate, never `sleeper_id IS NOT NULL` as a "player" proxy), the validated complete nonblank
Footballguys ladder, midrank tie assignment, `standing = 1 − (rank − 1)/(N − 1)` for `N ≥ 2` with
`N < 2` unavailable, `delta = footballguys_standing − fantasycalc_standing` (positive ⇒
`footballguys_higher`), classification before display rounding, and an exact `aligned` definition
(zero or a preregistered neutral band). Codex's shape above is adopted as the lead candidate,
subject to that framing's own challenge round.

Binding requirements, unchanged from v2: build each source's eligible **player** universe *before*
intersection · preserve Footballguys' exposed original order and denominator · derive FantasyCalc
player-only standing from raw price under the exact pinned SF settings with **midrank ties**,
retaining raw value + provider overall rank as disclosed fields · normalize within each
source-native universe by one closed formula and direction · intersect only to select emittable
rows — **never rerank the intersection** (the survivor-reranking bar carries forward) · publish
both native denominators, tie counts, eligibility rules, and the delta sign convention.
**Consensus ADP is struck from the first experiment.**

## 5. Frozen: label vocabulary (finding 6)

First-artifact labels are source-relative only: `footballguys_higher` / `fantasycalc_higher` /
`aligned`. No "win-now", "aging veteran", "prospect", "picks-adjacent" — the pool contains players,
not picks, and a rank delta entails none of those. Any age/experience pattern is a separate
preregistered aggregate hypothesis with a pinned factual attribute source and uncertainty/coverage
reporting. No per-player contention-window or action label derives from the delta.

## 6. Frozen: temporal pairing (finding 7)

Deterministic ex-ante rule: pair with the **latest exact-settings FantasyCalc snapshot whose
`retrieved_at` ≤ the declared Footballguys `retrieved_at`**; refuse if |lag| > 7 days or no prior
snapshot exists. Timezone, boundary inclusivity, missing/future timestamps, and settings-hash
mismatch are specified in the Phase-A/C contracts. `max_retrieval_alignment_days` stays labelled
retrieval alignment only. **Payload identity ≠ offering identity:** re-downloading byte-identical
content is a new offering observation, not a new content vintage.

## 7. Frozen: archive, not benchmark (finding 9)

Phase C emits an **append-only descriptive archive**. Every snapshot carries a comparability key
(both source contracts, settings hash, universe rules, identity-contract version, estimand
version); any key change is a **series break** no trend or month-over-month delta may cross.
Entrants, exits, unchanged-content offerings, and source-native movement are reported separately
from cross-source delta movement.

## 8. Frozen: namespace + mutant floor (finding 10)

A dedicated `footballguys_horizon_divergence` overlay namespace that **reads** the two source
stores and **writes neither**; `market_divergence_history.db` (model-vs-market) and
`fc_forward_capture.db` (`fc_native` only) are off-limits. Derived artifacts regenerable from
immutable inputs; any irreplaceable store triggers the manifest law. The RED's mutant matrix
includes, at minimum, Codex's ten named mutants (horizon-unknown emitting labels · novel
same-position wrong-human · survivor reranking · tie-splitting · 7d boundary + hostile timezones +
future-only rows · quarantined intake advancing analysis-ready · same-bytes-as-new-vintage ·
unbroken series across a key change · nested banned copy / nested `decision_supported=True` ·
non-idempotent or partial append), each with one broken implementation that must be caught.
Determinism is never cited as accuracy.

## 9. Phase state after this revision (Codex's required state, adopted)

- **Phase A:** live companion = **`footballguys_phase_a_intake_notice_framing_claude_v4.md`**
  (SHA-256 `e383f605513746b919bcf0a087b5610995d731e5f087704072f55df9dc8d72e2`) — carries the seven notice repairs, plan findings
  1/2/7/8, round-2 findings 2–9, and round-3 findings 2–8. **No RED yet.**
- **Phase B:** spec may proceed against the §2 independent oracle once A's bundle interface is
  frozen.
- **Phase C:** **closed** on exact-field horizon + all cohort/identity/estimand gates.
- **Phase D:** closed on C + a later David ruling.

**David-word register (nothing below is assumed):** offsite/backup replication of licensed raw
payloads (**Phase A framing v4 §8** — three options, his call, gates the Phase A RED) · any Phase RED opening · any landing · any new
remote copy of provider content · Phase D entirely.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
