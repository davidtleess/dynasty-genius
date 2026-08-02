# Framing — PFF NCAA passing as a candidate QB college-production source

**Lane:** Claude Code (framing author) · **Status:** v1, awaiting Codex adversarial challenge
**David's word:** "all three green light approved" (2026-08-01), item 2.
**Layers served: 1-2 primary (ingest + curate), with a layer-3 consumer question deferred.**

**Layers 1-2 dependency check.** Not applicable as a *dependency* — this work IS layers 1-2. Stated
explicitly so its omission is not read as an oversight (`05` §3 proportionality).

---

## 1. The concrete situation this serves

Engine A grades rookie quarterbacks. `00` §Rookie Evaluation Rules puts draft capital first and
age second, with **position-specific production and efficiency** third — for QBs that means
completion rate, efficiency, and TD:INT from the college seasons.

Today that third input comes from CFBD, and this session established what it was worth. Even after
the identity repair (commit `4d8127d`) the family is thin: pre-fix, only **62 of 126** QB payloads
carried passing values at all, `sack_rate` was **0/126**, and the values that existed were
misattributed. The repair makes the source *honest* — it now refuses rather than inventing — but
refusing is not the same as covering.

Meanwhile Codex's PFF inventory holds **NCAA Passing Summary and Passing Depth, complete
2017-2025**, with **2,954/2,954 QBs reconciling** `base_attempts`, `base_dropbacks` and
`player_game_count` against the verified summary, a populated numeric `player_id` on every row, and
**zero within-file identity collisions** — the exact injectivity test the CFBD path just failed.
There are also **840 PFF ids spanning NCAA and NFL**, a college-to-pro bridge Engine A has never had.

**The question:** should PFF NCAA passing replace or supplement CFBD as the QB college-production
source? **This framing does not answer it.** It scopes what would have to be true.

## 2. Mislead / nudge risks

- **"Better verified" is not "better predictive."** PFF's reconciliation record says its rows are
  internally consistent. It says nothing about whether these features forecast dynasty outcomes.
  Conflating the two is the central risk here, and it is seductive precisely because the CFBD
  alternative just failed so publicly.
- **PFF grades are diagnostic-only** (Codex's standing verdict across every family). A grade column
  entering a model input is a talent judgement smuggled in as a measurement.
- **Replacement hides a coverage question.** Swapping sources could quietly change *which* players
  have data, altering a cohort without anyone deciding to.
- **Vendor disagreement is not vendor error.** Codex's own NCAA Receiving-vs-Scheme work found
  classified share ~85% with an unclassified residual that must be retained. A CFBD/PFF disagreement
  most likely exposes a different **denominator**, not a wrong vendor — definitions before values,
  which was Codex's reframe and I adopted it.
- **Paid-source lock-in:** making Engine A depend on a subscription export is a durability decision,
  not just a data one. Worth naming for David even though it is his call, not ours.

## 3. Candidate falsification seeds for the RED

1. **Identity injectivity must be enforced, not assumed.** The archive currently shows zero
   collisions; an adapter must still refuse on one rather than rely on that record (Codex's own
   caveat about the audit being evidence, not permission).
2. PFF-id → GSIS join: the bridge runs through PlayerProfiler's vendor-supplied 2023+ identity.
   Pre-2023 college seasons resolve only by inference — that must be labelled, never silently
   resolved (the same `identity_basis` discipline the PlayerProfiler roster ingest already uses).
3. Definition/denominator reconciliation on a **small GSIS-resolved cohort before any value
   comparison**; a disagreement opens a semantic question, not a vendor verdict.
4. Coverage floors per season; the 2017 boundary is healthy for passing but partial for NCAA
   Receiving vs Scheme — do not generalize one family's health to another.
5. Grade columns explicitly excluded at the contract level, with a test that fails if one appears.
6. Repeated-export drift: Codex measured three distinct byte hashes for one 2017 export with two
   cells differing by 0.01. Raw exports must be preserved and fine-grained values must not be
   represented as exactly reproducible without a source-vintage rule.
7. Era/scope discipline: REGPO vs REG is a real trap here — a REGPO slice was already rejected once
   for inflating targets and games against a REG baseline.

## 4. Overclaim check against the No-Verdict Line

Ingesting and curating a source makes **no claim** that any feature derived from it has value.
`decision_supported=False` holds; nothing is promoted; no tier, grade, or ranking moves. Under `00`
§Backtesting and `01` §Validation Gates, **feature promotion requires a pre-registered validation
David ratifies** — that is a separate word, after this, and this framing does not pre-authorize it.

**Sequencing I recommend, for the challenge round to attack:** curate PFF NCAA passing into a
comparable shape → run the definition/denominator reconciliation against CFBD on a small resolved
cohort → *then* put a replace/supplement/neither decision to David with measured coverage on both
sides. **Not** replace-then-validate.

## 5. Open questions for the challenge round

- Is "replacement" even the right frame, or is the honest answer **two sources with a reconciliation
  layer**, given each covers players the other misses?
- Does the 840-id NCAA↔NFL bridge belong in this thread at all, or is it a separate and larger
  identity-substrate thread that this one should not quietly absorb?
- What is the minimum cohort size for the reconciliation to mean anything, and who sets it?
