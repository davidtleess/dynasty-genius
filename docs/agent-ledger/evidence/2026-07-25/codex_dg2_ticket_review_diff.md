# Codex diff against the fresh DG 2.0 ticket review

**Fresh review:** `/tmp/codex_fresh_dg2_ticket_review.md`
**Fresh-review SHA-256:** `33152bbb9ee324be26af2e21fa3a81b7c2d0be56dc393ffb1807e18c874ceeff`
**Coverage check:** all 41 backlog ticket IDs have exactly one verdict; no missing or extra IDs.
**Fresh verdict:** 3 PASS / 12 WEAK / 26 FAIL.

This is my independent comparison, not a capitulation. Before reading the reviewer’s file, I had already identified two likely primary defects: the Sprint-3→Sprint-5 dependency deadlock and acceptance criteria whose decisive threshold can be declared after seeing the result. That pre-review position was stated in the pane while the reviewer was still running.

## 1. What the reviewer found that I would not have found, or that changed my view

### 1.1 Missing final-value assembly and `rent_t` ownership — **reviewer found; I missed**

The strongest fresh finding beyond my own read is that no ticket owns assembly of the spec’s complete quantity:

`V_i(W) = Σ A_i,t · S_i,t · E[v_i,t] − rent_t`

Sprint 3 separately names production, survival, availability, discount, ceiling, lineup, and eligibility, but nobody produces `rent_t` and nobody owns the final aggregate `V_i(W)`. That is not editorial; it leaves the epic’s named product without a builder.

The resulting missing dependencies are also real:

- S4-03 cannot consume a complete value.
- S5-01a depends only on S3-01a and Year-1 outcomes, omitting survival, availability, any selected discount, rent, and final assembly.

I would not have found this as quickly because my first pass concentrated on whether each ticket was finishable, not whether every symbol in the spec had an owner.

### 1.2 S1 preregistration freezes a benchmark before S2 establishes its data ceiling — **reviewer found; I missed**

S1-04 hash-freezes the market benchmark. S2-02 later says that if market history cannot exceed four observations, the S1 benchmark is rescoped. The backlog provides no governed amendment/re-freeze path. That allows either:

- an impossible frozen benchmark; or
- a post-freeze change without a named integrity procedure.

This is a sequencing defect I did not identify independently.

### 1.3 Reciprocal dependency omissions — **reviewer found several I missed**

The following are concrete graph defects:

- S0-04 says it blocks S4-02, but S4-02 omits S0-04.
- S0-10 says it blocks S5-04, but S5-04 omits S0-10.
- S5-01d says no candidate fit may occur before v3, but it blocks none of S5-01a/b/c.
- S5-01b has no dependencies despite an unresolved estimand and currency/bridge interactions.
- S5-01c is not consumed by any pick-output ticket, so its caveat or bridge can be completed and ignored.

I had noticed the large S3/S5 cycle, but not this many one-way declarations whose reverse edge is missing.

### 1.4 Missing current-injury feed for the live surface — **reviewer sharpened my concern**

The backlog has:

- a historical injury/availability obtainability and ingestion path; and
- roster eligibility semantics.

It does not clearly own a current, refreshable injury/IR source for every value surface. I had seen S5-04’s broad “wherever” language but had not isolated the absent live-feed node.

### 1.5 Spec/backlog gate conflicts — **reviewer found; I underweighted**

The review correctly distinguishes the spec’s gates from the backlog’s revised gates:

- Sprint 3 in the spec requires benchmark comparison and named wins/losses.
- Sprint 3 in the backlog requires win-or-tie against all three benchmarks.

Because the spec calls itself the program of record, the same result can pass one gate and fail the other. I had focused on whether the backlog gate was measurable, not whether a second controlling file contradicted it.

### 1.6 S2-05’s market-series dependency is unrelated — **reviewer found; I agree**

The adequacy ticket asks whether the production/injury panel has enough player-seasons by position and age. Market-series depth does not answer that question. Making S2-02 a prerequisite serializes unrelated work and makes the hard data gate broader than its stated purpose.

### 1.7 The “safe fallback” ACs frequently allow a ticket to close without solving its named problem — **reviewer made this more systematic**

Examples:

- S2-01a can close with a “true ceiling” statement instead of ingestion.
- S5-01b can close with all three branches “explicitly not priced.”
- S5-01c can close with an unvalidated bridge plus caveat.

Safe runtime behavior is necessary, but it is not the same thing as completing a build ticket. I had identified S5-01b and S5-01c; the reviewer showed the pattern is broader.

## 2. Where I think the reviewer is wrong or too harsh

### 2.1 It labels governance and architecture constraints as forbidden HOW too indiscriminately

The reviewer’s HOW list is useful, but several quoted items are not developer-discretionary implementation design in this product:

- canonical `player_id` joins and triage rather than silent drops;
- fail-closed behavior on unsupported inputs;
- preregistration before fitting;
- full backup restore verification with SHA-256 and no sampling;
- independent review requirements;
- recursive `decision_supported=false`.

Those are governing invariants or required evidence quality, not choices a developer may replace with a preferred design. Tickets may state them as constraints. The ticket can still avoid prescribing the exact code/test mechanism used to satisfy them.

Concretely, I reject treating these as inherently improper HOW:

- S2-01d: “joinable ... on the canonical `player_id`” and unjoinable rows going to triage.
- DGX-02: preserving full download + SHA-256 restore strength.
- S1-04: tamper-evident freeze before fitting, although “hash in this ledger” can be generalized.
- S0-01: independent reproduction as acceptance evidence, although “second lane” and “2 dp” are unnecessarily specific.

### 2.2 S0-08 is not an automatic FAIL solely because it is open-ended

I grade it **WEAK**, not FAIL.

An exploratory source sweep cannot prove that all GitHub/open-data sources have been exhausted. The ticket nevertheless supplies:

- a bounded size (`M`, 2–4 days);
- named gap categories;
- a license/terms requirement;
- permission to find unanticipated sources.

That is enough to start and produce a useful bounded research deliverable, as today’s completed sweep demonstrates. It still needs a stopping rule such as named minimum ecosystems plus a time-box and query log, so PASS is not justified. But “open-ended discovery” is not inherently unfinishable when its effort and minimum coverage are explicit.

### 2.3 S0-03’s repo-wide zero-stale sweep is an outcome, even if `grep` is a method

I agree that naming `grep` prescribes a test tool. I do not agree that a bounded documentation correction should avoid the requirement that all stale occurrences be gone. Rewrite the AC as “zero stale occurrences remain in tracked text”; let the developer choose the search method. The ticket is WEAK as written, but the underlying finish line is legitimate and objective.

### 2.4 DGX-02 is stronger than WEAK on the backup-verification method, but it has a different concrete defect the reviewer missed

The restore-drill method is binding safety doctrine, not free implementation choice. A developer may choose how to add coverage, but may not weaken full remote download and payload-hash verification.

The real ticket defect is internal counting:

- scope names **four exact files plus two glob families**;
- AC says “all five entries covered.”

That is six protected target families, not five. A developer cannot know which one the AC silently excludes.

The ticket also says “snapshot + coverage globs” even though the runner currently has no glob entry type; that known implementation fact is outside the fresh reviewer’s permitted evidence but is established in `/tmp/codex_backup_change_surface_review.md`. The honest minimum implementation may use exact files plus a declared directory, with family-membership REDs, rather than pretend native glob support exists.

### 2.5 DGX-04 should be **WEAK**, not PASS, on the full known defect family

Against the two-file packet alone, the reviewer’s PASS is understandable. Against the already completed source audit, the ticket omits known sibling shapes:

- the NDCG diagnostic collapse in the shared metrics family;
- `subpopulation_landscape._bootstrap_rho_diff`;
- the guarded Gate-4 zero-width counterexample that should remain pinned as fail-closed.

The ticket deliberately narrows the immediate priority to two helpers, which is defensible, but it should explicitly disposition known siblings rather than let a fresh developer believe the family is exhaustive. I would not block the two high-priority fixes on every sibling; I would mark the ticket WEAK until the scope boundary is explicit.

### 2.6 DGX-03 is prescriptive, but “pin SciPy” is not an arbitrary solution choice

The reviewer calls this textbook HOW. Under the abstract ticket standard, that is fair. In context, D3-d has a registered exact runtime version gate and the defect is that the direct runtime dependency is undeclared. An exact direct pin is the already chosen reproducibility contract, not a random library preference.

I would grade **WEAK**, not FAIL:

- keep the required outcome: a clean environment deterministically resolves the registered runtime version;
- leave packaging-file mechanics and PR shape to the developer;
- retain the sequence-before-study constraint because executing under an accidental transitive version invalidates the registered run.

### 2.7 The reviewer’s three PASS verdicts are not equally strong

- **S0-05:** I would grade **WEAK**, because its AC presumes a “shape-matched request” exists. The spec itself says the product sends no roster shape; the two documents do not establish that the provider exposes a roster-shape request parameter. The ticket needs an allowed “provider cannot express this setting” outcome and an empirical sensitivity alternative.
- **S0-07:** PASS on ticket shape is reasonable, but “what its terms permit” can require interpretation beyond an ops fact read. The safe UNKNOWN state saves it.
- **DGX-04:** downgrade to WEAK for the known sibling-scope issue above.

Thus I would not carry “3 PASS” upward as if those three were uncontested.

### 2.8 Some “two problems in one” calls are related acceptance evidence, not necessarily ticket-splitting defects

I agree that S5-01b and S3-05 are genuinely oversized. I do not automatically split:

- S3-04’s before/after 12-label publication: that is blast-radius evidence for changing starter-strength semantics, not necessarily a second implementation.
- S5-02’s freshness selection and stale-state signal: both are two states of one source-freshness contract, though the surface work can be separated operationally.
- S5-03’s starter-strength and posture centralization: if posture is a direct consumer of starter strength, one authoritative-result boundary may legitimately cover both.

The reviewer is right to flag them for scrutiny, but “two nouns” does not itself prove two tickets are required.

### 2.9 “A developer cannot start Sprint 0” is too absolute

The reviewer later gives the more accurate answer: useful work can begin on S0-01/02/04/05/10 after authorization, but the sprint cannot be objectively completed.

My answer:

- **Can start tomorrow if David authorizes:** yes.
- **Can finish Sprint 0 and advance from the current backlog:** no.
- **First predictable stalls:** S0-08 stopping rule, S0-09 missing `PRODUCT_BRIEFING` locator/bounded downstream set, S0-10 completeness boundary, and conflicting gate consequences.

The DRAFT/no-authorization banner is a governance gate, not a ticket-quality reason that a hypothetical authorized developer lacks enough context to begin.

## 3. What I found that the fresh reviewer did not

### 3.1 DGX-02’s “five entries” count contradicts its six target families

This is the cleanest omitted defect. Four files + snapshot glob + coverage glob = six families. The AC says five.

### 3.2 S3-03 contains a fail-loudly contradiction

Its constraint says:

> “no bound-truncated value ... may reach any downstream consumer”

but its fail-loudly line says:

> “a value that hits any bound is stamped as bounded in its record”

If that bounded record reaches a consumer, it violates the constraint. If it never reaches a consumer, the stamp’s audience and purpose are unspecified. The ticket must distinguish producer diagnostic storage from downstream served values.

### 3.3 The Sprint-2 gate’s `≥1` extrapolation rule is not an adequacy standard

The reviewer notes the logical awkwardness relative to `≥30`. I go further: one observed player-season in an extrapolated band does not validate extrapolation. It only proves the band is not literally empty. If `≥30` is the support threshold, the `≥1` rule must not be described as evidence that an extrapolated band is adequate.

### 3.4 S3-01a’s AC is internally inconsistent

It requires estimates:

> “for every player in the compared cohort across the thesis horizon”

while its fail-loudly rule requires refusal beyond supported age bands. If any compared player’s thesis horizon extends beyond support, both cannot be true. The AC must measure coverage only inside declared support and require explicit unavailable rows outside it.

### 3.5 S5-02’s live-label AC is unstable

The reviewer notices the historical-count risk. The deeper issue is that “the 4 wrong posture labels are corrected” can fail after the source changes even when the code is correct, or pass by coincidence without proving all four consumers are freshest. The finish line should bind source identity/vintage and deterministic recomputation, while the four-label before/after remains evidence from the frozen reproduction date.

## 4. Does the reviewer’s worst-problem call match mine?

**YES — exactly.**

My independent worst problem, identified before reading the reviewer output, was the same dependency deadlock:

1. The program says no sprint starts before the prior sprint closes.
2. S3-04 depends on S3-05.
3. S3-05 depends on S5-02.
4. S5 cannot start until S4 closes.
5. S4 cannot start until S3 closes.

The sequencing note acknowledges a possible lift of S5-02 but says it is only Tower’s recommendation and David has not ruled. Therefore the authorized graph has no path through Sprint 3.

This is worse than any single weak AC because it makes the program impossible to execute even if every engineer understands every ticket perfectly.

## 5. My consolidated verdict

The fresh review is directionally right: the backlog remains too solution-shaped and too permissive about self-declared thresholds. Its exact 3/12/26 grade distribution is harsher than mine because it treats several binding safety/provenance constraints as forbidden HOW.

My binding conclusions for Tower’s consolidation:

1. **Do not open implementation from this v2 backlog.**
2. Fix the Sprint-3→Sprint-5 deadlock first.
3. Add ownership for `rent_t` and final `V_i(W)` assembly.
4. Reconcile spec gates with backlog gates; there must be one controlling gate per sprint.
5. Freeze every decision-bearing metric/tolerance before result production; do not let a ticket declare its own minimum resolution afterward.
6. Repair pick-branch dependencies and make the bridge/plan outputs actually consumed.
7. Separate safe runtime fallback from ticket completion.
8. Preserve governance invariants as constraints, while removing prescriptions of modules, exact test tools, and implementation sequence that are not already governed.

**Developer-start answer:** useful Sprint-0 work can start after David authorization, but a fresh developer cannot objectively finish Sprint 0 or advance the epic from the current documents.
