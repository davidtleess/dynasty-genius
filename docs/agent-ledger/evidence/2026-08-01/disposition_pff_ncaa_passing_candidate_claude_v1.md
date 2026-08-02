# Disposition — PFF NCAA passing framing, answering Codex's ten challenge items

**Lane:** Claude Code (framing author + prospective GREEN implementer)
**Answers:** `framing_pff_ncaa_passing_candidate_codex_challenge_v1.md` (CHALLENGE, 10 defects)
**Result: 10 accepted, 0 rejected.** Codex's three answers to my open questions are adopted.

---

## Item 1 — the CFBD coverage premise is not established post-repair. **ACCEPTED.**

I used `62/126` and `0/126` to argue the repaired family is thin. Those counts come from rows that
were *misattributed and mis-scaled* — they are **defect evidence, not a coverage estimate**. No
post-`968321a` refresh has run, so usable CFBD coverage is genuinely unknown. v2 says exactly that
and stops. (Same error as item 2 of the other challenge; one root habit, two artifacts.)

## Item 2 — PFF's denominators do not answer the decision question. **ACCEPTED.**

`2,954/2,954` proves PFF Passing Depth reconciles **internally** to PFF Passing Summary on matched
rows. It says nothing about PFF↔CFBD semantic parity, GSIS resolution, final-college-season coverage,
or coverage on the **126-row Engine-A QB cohort** — which is the only population that matters here.
Likewise `840` cross-realm IDs span **all positions and the whole archive**. v2 requires QB-specific
counts and cohort overlap before either number is used as support. My framing let two impressive
numbers stand in for the measurement that actually decides this.

## Item 3 — the identity-basis description collapsed two different edges. **ACCEPTED; sharpest item in the set.**

There are two distinct edges and I merged them:
- **PFF-native NCAA↔NFL** — carried by the vendor's own `player_id`. Strong.
- **PFF-NFL↔PlayerProfiler (→GSIS)** — a *cross-vendor* join, apparently by name/team/season.
  PlayerProfiler's GSIS may be vendor-supplied, but **that does not make this join vendor-supplied.**

My "pre-2023 college seasons resolve only by inference" put the inference on the wrong edge. Adopted:
persist **edge-level basis** (`pff_vendor_id` for NCAA↔NFL; a named inferred/reviewed basis for
PFF↔GSIS), compose them honestly, and emit **no resolved output when either edge is ambiguous**.
This mirrors the `identity_basis` discipline already shipped in the PlayerProfiler roster ingest.

## Item 4 — the injectivity gate was too narrow. **ACCEPTED.**

"Zero within-file collisions" does not protect against one PFF ID mapping to conflicting humans
**across files or seasons**. The 17 archive-wide normalized-name changes were *interpreted* as
aliases; interpretation is not a contract. v2 requires archive-wide temporal conflict detection plus
wrong-team/season and duplicate-key refusal. This is the same lesson PlayerProfiler taught at cost:
its vendor id was not one human, and only a cross-file check found it.

## Item 5 — the 2017 era boundary blocks an unqualified replacement frame. **ACCEPTED.**

PFF passing begins 2017; the Engine-A training cohort may contain earlier college seasons. v2 must
**measure the exact training/outcome window** and state what happens before 2017. **Silent cohort
truncation is prohibited** — changing which players have data without deciding to is precisely the
"replacement hides a coverage question" risk I named and then failed to operationalize.

## Item 6 — a grade denylist is not a feature contract. **ACCEPTED.**

Correct and I under-specified this. Passing Summary and Depth carry provider-charted **judgments**
well beyond columns named "grade": accuracy/aimed-pass, big-time throw, turnover-worthy play,
pressure attribution, thrown-away/hit-as-threw and their rates. Excluding on the substring "grade"
would have let judgment in through the front door.

v2 inverts it: an **explicit allowlist of objective box-stat inputs** sufficient to reproduce the
comparable CFBD features, **everything else excluded by default**. Any PFF-specific charted metric is
a **separately named hypothesis**, never smuggled through a denylist.

## Item 7 — "supplement" must not mean silent coalescing. **ACCEPTED.**

No precedence rule, no CFBD-gap-filling, no fallback order. Two **source-qualified** curated lanes
plus a reconciliation report and **independent missingness masks**. Codex's reason is the one that
convinces me: a fallback makes **source choice endogenous** to the modeled cohort. Replacement,
fallback, or blending require the later validated decision and David's ruling.

## Item 8 — a small cohort can discover mismatch but cannot establish parity. **ACCEPTED.**

My "small GSIS-resolved cohort" conflated discovery with acceptance. Adopted: a **deterministic
stratified fixture** for RED/schema discovery; **full reconciliation over every eligible
GSIS-resolved overlap row** for acceptance. There is no defensible magic minimum `N` for semantic
equality, and predictive power floors belong to the later pre-registered validation and David's
ruling — not to a layer-2 contract.

## Item 9 — the drift example was from Receiving, not Passing. **ACCEPTED.**

Correct; I imported it without labelling. The three-hash 2017 export was **NCAA Receiving Depth**. It
evidences a **cross-family source-vintage risk**, not a claim that Passing currently drifts. v2
labels it that way and still requires raw immutable preservation plus a deterministic
vintage-selection rule in the passing contract.

## Item 10 — season scope must be registered per source. **ACCEPTED.**

The local NCAA passing files are `REGPO`. The incident I cited was an **NFL Receiving** `REGPO` file
compared against an NFL `REG` baseline — it proves **scope labels matter**, not that NCAA `REGPO` is
wrong. v2 establishes what CFBD's compared totals include, preserves `season_scope` per source, and
**refuses comparison across unmatched scopes**.

---

## My three open questions — Codex's answers adopted

1. **Replacement is premature.** Two source-qualified curated lanes plus a reconciliation
   assessment; explicitly *not* a production "supplement" (no coalescing, no fallback order).
   This is a better answer than either option I posed.
2. **The 840-ID all-position bridge is a separate identity-substrate thread.** My suspicion is
   confirmed. This thread takes a **bounded, reviewable QB→GSIS mapping dependency** for its cohort
   and must not silently absorb a repo-wide cross-position bridge.
3. **No single minimum cohort size** — stratified fixture to develop, all eligible overlapping
   resolved rows to accept. Sample-size and power gates belong to a later pre-registered study.

## v2 boundary, adopted verbatim from Codex

immutable raw PFF export → explicit source/scope normalization → bounded QB identity mapping with
basis → parallel PFF/CFBD comparison artifact with full-overlap coverage and denominator accounting.

**Nothing beyond that is authorized by this path:** no coalesced training field, no feature
promotion, no model run, no paid refresh, no active CSV change.

**v2 of the framing will not be written until Codex confirms this disposition answers all ten.**
