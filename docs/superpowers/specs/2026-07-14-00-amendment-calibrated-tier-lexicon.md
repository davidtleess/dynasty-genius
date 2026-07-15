# 00 Amendment — Calibrated Tier Lexicon (named tiers legal only when statistically earned)

- Status: DRAFT v3 for adversarial cockpit cycle (Codex technical + Gemini governance). Ratification/commit = David's word. v2 repaired Codex R1 (full-dataflow earned-gate, sequence reorder, named disclosure primitive, lane-specific calibration); v3 adds the numeric denominator + immutable calibration identity (Codex R2). Gemini CONCUR on sequence/pipeline-gating/schema.
- Author: Claude Code · 2026-07-14
- Target: `docs/governance/00-product-constitution.md` — the "Ranks and tiers must disclose their basis, never nudge" bullet (line 168) of the No-Verdict Line. Bumps 00 to v1.1.0 on ratification.
- Source directive: David, 2026-07-14 (verbatim): "the use of prose tiering is fine on the front end and frankly even the backend so long as it is backed by statistical evidence. We should only call a player Generational if he is in fact statistically generational … either in terms of his DVS or his production or both … we must create a model that puts players into tiers strategically and logically — no guessing."
- Executes Step 1 of the David-ratified manager-voice roadmap (`docs/superpowers/specs/2026-07-05-h2-manager-voice-doctrine-claude.md`); the hard ordering constraint (law before enforcement) is satisfied by landing this amendment before any enforcement-surface edit.

## The principle

The current text bans named tier labels outright ("avoid subjective static tier labels ('Elite', 'Bust', 'Starter Depth') that smuggle a value judgment"). David's ruling reframes the problem: the defect was never the *word* — it was an *unearned* word. A tier label assigned by a real statistical calibration model is not a smuggled verdict; it is a disclosed-basis descriptor of where the player sits, in the hobby's native language. The amendment therefore does not "allow verdicts"; it converts subjective labels into objective, calibrated, disclosed-basis ones — and keeps the ban on any label a model has not earned.

## Proposed replacement text (line 168 bullet)

> **Ranks and tiers must disclose their basis, never nudge.** A default sort or rank must be tied to a declared transparent metric or rule, and any composite ordering must disclose its components and not function as a hidden recommended action order. Present raw percentile position alongside any tier label.
>
> **Named tier labels (e.g. "Generational", "Elite", "Cornerstone", "Starter", "Depth") are legal only when assigned by a David-ratified statistical tier-calibration model** — never by hand, never by an arbitrary fixed bucket (e.g. "dozen-based") chosen for convenience. A named tier is a descriptive statement about a player's calibrated position (by DVS, by production, or both, per the calibration contract), it carries its basis on the surface (the percentile/metric that earned it), and it remains descriptive (`decision_supported` is governed separately and a tier label never flips it). "Bust" remains banned — it is a pejorative verdict, not a calibrated position. A label a model has not earned, or a label detached from its disclosed basis, is exactly the smuggled value judgment this line prohibits.
>
> **"Earned" gates the whole dataflow, not just the pixel (Codex R1-1).** Until a valid David-ratified `tier_calibration` artifact authorizes a given label, that named label may not be **computed, serialized, emitted on any API, persisted to any artifact, or rendered** — front end or back end. David's ruling permits prose tiers on FE *and* backend, but only *when earned*; an unearned named tier has no legal existence anywhere in the dataflow, and every occurrence outside the calibration path stays fail-closed.
>
> **Lane-specific calibration (Codex R1-4).** A market-lane tier and a model-lane tier are different claims and must be calibrated on their own lane's basis: a market label is earned from the market basis (e.g. FantasyCalc position rank), a model label from the model basis (DVS/production) — neither reuses the other's calibration or input. Each renders with its lane and its own basis; the two never blend into a single tier (two-lane isolation holds).

## Binding sequence (reordered per Codex R1-2 — the earned-gate must exist before the vocabulary relaxes)

The original roadmap order (relax vocabulary → then build the gate) opens a window: the banned-language scanner is frontend-only and documents embedded-label/dataflow enforcement as out of scope (`tests/contract/test_frontend_banned_language_linter_contract.py:244-292`), and the `players.py` backend suppressor is vocabulary-only — so removing "elite"/"starter"/"depth" from `banned_vocabulary.json` before a structural earned-gate exists would leave *nothing* enforcing "earned." Reordered:

1. **This amendment lands** (law) — full cockpit cycle → David ratifies → commit. No enforcement-surface edit before this.
2. **The `tier_calibration` schema/producer + a structural allowlist RED land first (or atomically with step 3).** The structural gate enforces that a named tier may only exist when carrying a valid calibration reference — this is what replaces the blanket vocabulary ban's protection. The `tier_calibration` model/artifact is the "no guessing" requirement (the real work; connects to the PVO-scale / Value Board tier-calibration thread on the board) and is David-ratified.
3. **Only then** is the vocabulary relaxed: `banned_vocabulary.json` (remove standalone "elite"/"starter"/"depth"; **keep "bust"**), the `ValueBandDivider` RED, and the banned-language fixtures — each citing this amendment. Every occurrence NOT carrying a valid calibration reference stays fail-closed.
4. **Only then** do named labels compute/emit/persist/render on any surface, each backed by the calibration artifact and its disclosed basis.

A named label may not ship — or exist anywhere in the dataflow — on the strength of this amendment alone; the amendment makes the labels *legal-when-earned*, the calibration model + structural gate make them *earned* and *enforceable*.

## Named disclosure primitive (Codex R1-3)

A calibrated tier renders only through a dedicated `CalibratedTier` primitive/contract, not a generic `ValueHero` basis string and not behind a click-hidden `ReceiptTrigger`. The primitive requires, **visible and adjacent to the label**:

- the tier label
- its lane
- the metric/band that earned it
- the named population it is ranked within, **with its numeric denominator** — a raw rank and/or percentile plus `population_count` (Codex R2), e.g. "Elite · WR13 of 154 · 92nd pct". This satisfies the constitution's standing "present raw percentile position" law and makes the sample-floor contract enforceable: a tier over a population too small to earn it is visibly self-refuting.

Its receipt carries the calibration **version / as-of / health** **and an immutable calibration identity** — `calibration_artifact_id` / content hash (Codex R2) — so any rendered tier is auditable back to the exact ratified run/cohort that earned it. A named tier whose basis is only reachable behind a click, that omits lane/population/denominator, or that cannot be traced to a specific calibration artifact, does not satisfy "carries its basis on the surface" and is non-compliant.

## Out of scope

- The statistical design of the tier-calibration model itself (thresholds, whether Generational = DVS percentile vs production vs both, cohort definitions) — that is the calibration contract (step 3), authored separately and David-ratified. This amendment only removes the blanket prohibition and replaces it with the earned-label rule.
- `decision_supported` promotion (the Tier-2/Gate-4 path) — untouched; a tier label never flips it.
- Market-lane pricing tiers vs model-lane tiers — both must disclose which lane and which basis; neither blends into the other (two-lane isolation holds).

## Falsification seeds (for the reviewers)

1. RESOLVED v2 (Codex R1-1/R1-2): the earned-gate now covers compute/emit/persist/render (not just render), and the sequence lands the structural gate before the vocabulary relaxes, so no interim hand-bucketed label can exist. Re-falsify: is there any occurrence path (existing embedded label, fixture, generated client) the reordered gate still misses?
2. RESOLVED v2 (Codex R1-3): the `CalibratedTier` primitive is now named with required visible-adjacent fields + non-click-hidden basis. Re-falsify: is the required field set (label · lane · metric/band · population + version/as-of/health receipt) complete, or is a field missing?
3. Does keeping "Bust" banned while allowing "Depth"/"Replaceable-range" create an inconsistency (both are low-tier)? (Roadmap keeps "bust" as pejorative; confirm the calibrated low tiers read as position, not insult.)
4. Two-lane: a market "Elite" (FantasyCalc position rank) and a model "Elite" (calibrated DVS) are different claims — does the amendment force each to disclose its lane+basis so they never read as one verdict?
5. Does this weaken the No-Verdict Line's core (no buy/sell/hold)? It must not — a calibrated tier is a position, not an action; confirm no path from a tier label to an imperative.
