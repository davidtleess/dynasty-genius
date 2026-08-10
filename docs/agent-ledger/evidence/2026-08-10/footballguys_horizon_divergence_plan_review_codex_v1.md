# Footballguys Horizon Divergence plan v1 — Codex adversarial challenge

Date: 2026-08-10  
Reviewed artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_horizon_divergence_plan_claude_v1.md`  
Submitted and reproduced SHA-256:
`2ea1bacf9d0d9a436869556f41ad77cf1d2881206e922273a298b66c1fcddfd6`

## Verdict

**FINDINGS — not clear.** The foundation-first phase order is right, the overlay/model-input cordon
is right, and Phase D is correctly deferred. Ten bounded repairs remain. Phase A framing may
continue; this review opens no RED. Phase C remains closed because the exact Footballguys horizon
is still unverified and the known cohort still fails its prospective floor.

Layer served: **Layer 5 presenting work**, with mandatory Layer 1 intake and Layer 2 identity
dependencies reviewed first. Repo inspection confirmed the proposed view has neither dependency in
production today.

## Findings

### 1. Critical — the plan assumes the semantic fact it is supposed to establish

The product object calls `adp_sleeper-sf` “Footballguys seasonal ADP” and defines the comparison as
redraft versus dynasty. The cleared pilot's standing state is `horizon=unverified`; neither the
file, the general Draft Dominator explanation, nor a different Footballguys dynasty product binds
this exact Classic field to seasonal redraft. David's order authorizes the investigation; it does
not supply provider semantics.

Phase A must record a closed exact-field semantic contract:

- `product_family`, export/version, exact field name, format, and scoring;
- `horizon = seasonal_redraft | dynasty_startup | unknown`;
- a provider-authentic evidence pointer or captured export/UI metadata, with hash and retrieval
  provenance;
- no inference from the empty `adp_sleeper-redraft` column, numeric shape, filename, or David's
  declaration alone.

`unknown` may support intake and the monthly notice, but it must stop Phase C and prohibit every
“redraft,” “seasonal,” or “horizon divergence” label. If the field proves dynasty-startup, this is a
startup-draft-versus-trade-price construct and requires new framing, not a renamed result.

### 2. High — Phase A does not yet capture the identity evidence Phase B requires

`adp.csv` contains only the provider id plus market columns. The pilot verified names through
`projections.csv`; without that companion, accepted PFR-like ids can still attach to the wrong
human at full resolver confidence. “SHA-256 per file” does not define which roles are required or
prevent cross-vintage pairing.

Phase A needs an atomic bundle receipt, not unrelated file receipts: at minimum the exact
`adp.csv` plus the provider identity sidecar used for name/position verification (currently
`projections.csv`), one bundle id, per-role hashes, one declared retrieval event, required/optional
role rules, and fail-closed schema checks. Projection values remain barred from model and overlay
signal; only identity fields may cross the Phase-B boundary. A missing or mismatched sidecar makes
the bundle identity-unverifiable and unavailable to Phase C.

### 3. High — the proposed known-answer fixture is circular and incomplete

The minimized census is output from the same census logic being promoted. Freezing it as the
contract oracle can preserve the implementation's own mistakes. It also does not provide a
balanced row-level positive/negative oracle for every production verdict.

Use an independently adjudicated, versioned minimal fixture with explicit expected outcomes for:
exact same-human, approved nickname, wrong human with different position, wrong human with the same
position, name-pass/position-fail, unresolved id, id absent from the provider sidecar,
missing/invalid position, and duplicate/conflicting identity evidence. Include a novel PFR-counter
collision not among the known 34 so code cannot pass by hard-coding those ids. The minimized census
may remain a regression/provenance artifact, not the truth source. Phase B may frame in parallel
once Phase A's bundle interface is frozen; the first new drop is acceptance input, not the source
of its own expected answers.

### 4. High — the identity gate was already fixed prospectively; do not replace it with one pool-size number

Section 4 reopens only a minimum common-pool size, but the earlier independent gate was designed to
catch composition bias, especially the top-heavy loss of recent entrants. Carry forward, before an
unseen vintage is examined:

1. verified Footballguys identity ≥90% of populated SF rows;
2. 100% identity for the union of both sources' native player top-24 sets;
3. ≥95% identity for the Footballguys top 100;
4. ≥85% in every preregistered rank/position/experience stratum with `n >= 20`;
5. final verified matched cohort ≥80% of the original Footballguys SF population;
6. a complete attrition ladder and excluded-set composition report.

The known vintage is 328/500 identity-verified and 285/500 finally matched, so it fails. It cannot
be rehabilitated or used to choose new thresholds after inspection. A real Phase-C run on it may
emit only the failed gate and counts, not player deltas or tail lists.

### 5. High — neither proposed delta is valid as written

Raw ranks have different native denominators and FantasyCalc ties. Percentiles “over the common
verified pool” rerank survivors, making every player's score depend on identity attrition and
repeating the previously barred survivor-reranking error.

Freeze one lead estimand before RED:

- build each source's eligible **player** universe before the identity intersection;
- preserve Footballguys' exposed original order and denominator;
- derive a FantasyCalc player-only standing from its raw price under the exact pinned SF settings,
  with an explicit tie method such as midrank; preserve raw value and provider overall rank as
  disclosed source fields;
- normalize within each source-native player universe using one closed formula and direction;
- intersect only to decide which player rows may be emitted; never rerank the intersection;
- publish both native denominators, tie counts, eligible-row rules, and the delta sign convention.

Strike consensus ADP from the first experiment. It introduces a second endpoint and another
unresolved semantic mapping before the lead construct is valid.

### 6. Medium — the tail labels are hypotheses, not structural descriptions

“Win-now,” “aging veteran,” “prospect,” and “picks-adjacent youth” are not entailed by a rank delta.
The common pool contains players, not picks, so “picks-adjacent” is especially unmeasured. These
labels can become verdict-adjacent even without an imperative verb.

The first artifact must use neutral source-relative language only: `footballguys_higher`,
`fantasycalc_higher`, or equivalent. Any age/experience pattern is a separate preregistered
aggregate hypothesis with a pinned factual attribute source and uncertainty/coverage reporting.
No per-player contention-window or action label may be inferred from the delta.

### 7. High — temporal pairing is not closed, and retrieval alignment is not source-period alignment

The ≤7-day ceiling bounds fetch times only. It cannot prove that either provider's data describes
the same effective period. Phase C also lacks a deterministic rule for choosing among the daily
FantasyCalc snapshots, allowing hindsight selection.

Freeze the pairing rule ex ante: use the latest exact-settings FantasyCalc snapshot whose
`retrieved_at` is at or before the declared Footballguys `retrieved_at`; refuse if the absolute lag
exceeds seven days or no prior snapshot exists. Specify timezone handling, the exact boundary,
missing/future timestamps, and settings-hash mismatch. Store `max_retrieval_alignment_days` and
label it retrieval alignment only. Keep separate payload and offering identities so a newly
downloaded byte-identical Footballguys file is an observed offering, not falsely a new content
vintage.

### 8. High — intake success, analytical readiness, reminder freshness, and retention are conflated

A declared drop must not automatically reset every clock or become Phase-C-ready. Transport can
succeed while schema/semantic/identity review fails. Conversely, David may have completed the
monthly refresh even when the new bundle requires review.

Phase A needs orthogonal states:

- acquisition freshness (`no_record/current/due/unverifiable`) from a committed byte-bound
  offering receipt;
- intake readiness (`ready/review_required/failed`);
- latest analysis-ready bundle, which advances only after required roles and schema/semantic gates
  pass.

Define idempotent replay, same-payload/new-offering behavior, partial-write rollback, and whether a
quarantined receipt resets the reminder while leaving the last analysis-ready bundle unchanged.

The plan also creates a durable paid-source raw store where the cleared pilot had only scratch
retention. Local durable intake is within the newly ordered work, but backup/offsite replication is
not silently decided by saying “backup-manifest law.” Phase A framing must name the private,
gitignored raw location, payload minimization, and restoration model. Because the source is not
regenerable from repo plus public data, manifest coverage and the resulting offsite-copy policy
must be reconciled explicitly; seek David's word if that creates a new remote copy.

### 9. Medium — “compounds into the benchmark” overclaims longitudinal comparability

Monthly cross-sections do not automatically form one comparable series. Player-universe changes,
schema drift, horizon evidence, FantasyCalc settings, identity-contract revisions, and percentile
rules can move the delta without either market changing its view of a player.

Call Phase C an append-only descriptive archive, not a benchmark. Every snapshot needs a
comparability key containing both source contracts, settings hash, universe rules, identity
contract, and estimand version. Any change creates a series break; no trend or month-over-month
delta may cross it. Report entrants, exits, unchanged-content offerings, and source-native movement
separately from cross-source delta movement.

### 10. Medium — use a dedicated market-versus-market namespace and strengthen the mutant matrix

Do not reuse `app/data/market_divergence_history.db`: that store names model-versus-market work.
Do not write Footballguys rows into `fc_forward_capture.db`: its production contract accepts only
the `fc_native` source family. Use a dedicated `footballguys_horizon_divergence` overlay namespace
that reads both source stores and writes neither. Derived artifacts should be regenerable from the
immutable inputs; any irreplaceable new store triggers the backup-manifest law.

The current seeds also need one broken implementation per seed. At minimum add mutants for:

- `horizon=unknown` that still emits a redraft label or player delta;
- a novel same-position wrong-human id accepted outside the known 34;
- common-pool survivor reranking;
- a tied FantasyCalc price assigned distinct load-bearing ranks;
- exactly 7 days versus 7 days plus one microsecond, hostile timezones, and future-only FC rows;
- a failed/quarantined intake advancing the analysis-ready marker;
- same bytes offered twice being confused with a new content vintage;
- a schema/settings/identity-version change that fails to break the series;
- nested banned copy or nested `decision_supported=True` escaping a shallow scan;
- append code that duplicates an idempotent replay or partially writes before refusal.

Determinism alone is not an accuracy assertion; broken code can be byte-identically wrong.

## Required v2 state

Phase A framing v2 should incorporate findings 1, 2, 7, and 8 directly and preserve the seven
accepted monthly-notice repairs. The overall plan should freeze findings 3–6 and 9–10 before any
Phase-B/C RED. The valid phase state after this review is:

- Phase A: framing may proceed; no RED yet;
- Phase B: spec may proceed against an independent oracle after the bundle interface is frozen;
- Phase C: closed on exact-field horizon plus all cohort/identity/estimand gates;
- Phase D: closed on C and a later David ruling.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.

