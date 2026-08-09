# Manual-feed cadence RED review — Codex v1

Date: 2026-08-08
Layer: 1
Reviewed pin: `f7565ff074d31e89653aea1c12a17eb7d0f866421ff4973aac827500f0dd32f8`
Verdict: **NOT CLEAR**

Independent gates reproduced: 17 failed, 0 passed, 0 skipped, zero collection errors; true pytest exit 1. `uvx ruff check` passed.

## Findings

1. **Coverage quality and acquisition obligation are conflated into one exclusive state.** The file calls this a four-state taxonomy while asserting five names. More importantly, `inadequate` and `not_due` can both be true: the 2023 medical archive is inadequate, while no obtainable replacement may currently be due. Do not make one “outrank” and erase the other. Pin separate axes, for example cadence/obligation (`current | due | not_due`) and coverage (`adequate | unknown | inadequate`), and assert both serialize.

2. **S2's disagreement assertion is vacuous.** `len({s.state for s in states.values()}) >= 1` passes when all streams have the same state. Assert `> 1` and the expected roster result. But first inject a real roster event after the held vintage; `source_offers=2025` does not prove anything changed between August 1 and August 8.

3. **Manual-provider availability is treated as an unproven oracle.** `source_offers=2026` is enough to clear medical coverage or make a stream due, even though the agreed ceiling is that neither vendor supplies a governed push signal. Require any source-offer observation to carry provenance and an observation time; absence of an observation must not be inferred as an offer.

4. **`newest_season` cannot prove complete coverage.** A dataset containing 2023 and 2026 but missing 2024–2025 passes S4b as `current`. Pin covered seasons (or an equivalent coverage set) and add the internal-hole counter-test.

5. **The trigger guard is self-certifying and too narrow.** S6b passes if GREEN adds `vendor_push` to `OBSERVABLE_TRIGGERS`; membership in an implementation-owned set proves nothing. Pin the allowed ontology in the contract. Policies also need multiple triggers, not singular `p.trigger`: game finalization, season final, correction/schema event, league-year open and draft can coexist for one family.

6. **The RED does not test the aligned PFF cadence at all.** Apart from the grades case, every behavioral cadence test is PlayerProfiler. Add PFF family tests that distinguish NFL and FBS validation windows, assert due only after an injected completed-game/availability event, and keep completed history not-due unless an explicit correction/schema/pre-analysis event occurs. Do not encode universal “Tuesday”; 2026-09-16 is Wednesday, and calendar weekday is not the evidence boundary.

7. **S7 uses model prohibition as the cadence decision instead of consumer authorization.** Grades currently create no standing obligation because they are unconsumed and no diagnostic consumer is authorized—not because raw diagnostic evidence can never merit a refresh. Pin `consumer_authorized` as an input: model authorization remains forbidden, raw retention remains true, and a separately authorized diagnostic use can create an event-driven obligation without promoting grades to model features.

8. **The controller integration gate is incomplete.** S8 can go green by replacing `daily` with `None` while the controller never reports any per-stream state. Require the shipped controller report to serialize every declared manual stream's separate axes, aggregate a source as due only from an authorized due family, retain unknown/inadequate without treating either as an automatic-job failure, and expose no collapsed source verdict as the canonical truth.

## Additional precision

- S2b's dict comprehension cannot detect duplicate policy definitions; compare declared policy keys with declared stream keys as sets and add explicit duplicate-definition rejection at construction.
- RotoViz has no held schema and must remain unknown until first-drop inventory. Campus2Canton is secondary CFBD validation, not a recurring production obligation. Do not invent detailed stream policies for either merely to satisfy partition coverage.
- H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.

## David clarification after review

David first ruled: **“just to be clear i authorize all consumption within the scheduled and determined frequency”**, then immediately clarified: **“not just manual - all injestion”**.

Effect on Finding 7 and the wider Layer 1 control plane: the missing consumer-authorization decision is discharged for **all Layer 1 ingestion**, not merely manual feeds. Once a source's connection, cadence and access prerequisites are determined, its ingestion may execute at that cadence without seeking separate per-run authority. Every unique manual datapoint family may create an acquisition obligation at its reviewed event frequency, including retained diagnostic fields. The GREEN should record this as explicit authority rather than infer it from model eligibility.

Boundary: ingestion authority does not silently purchase new paid access, invent an undetermined cadence or route, contact a provider, or promote fields into Layer 2/model features. Once cost/access is separately resolved and cadence is determined, the ingestion itself is authorized. The separately enforced prohibition on PFF grades as model inputs remains unchanged.
