# Framing v2 — bakeoff execution-status reporting

**Lane:** Claude Code · **Supersedes:** v1 (premise falsified — see §0)
**Authored against:** `disposition_inert_feature_defect_signal_claude_v1.md`, accepted 7/7 by Codex
**Status:** v2, returning for independent framing review. **No RED opens on this acceptance.**
**Layer served: 3 (models) — presenting, and deliberately source-agnostic.**

**Layers 1-2 dependency check.**
- *Check performed:* read `docs/agent-ledger/2026-05-24.md:994-1004`; the committed artifact
  `app/data/backtest/phase20/phase20_bakeoff_20260524T183807Z_db568d44.json` `positions.QB`;
  `scripts/run_phase20_bakeoff.py:118-150`; `scripts/run_head_a_bakeoff.py:134`.
- *Result:* the QB arm was blocked because its four candidate columns fell below the registered
  `min_coverage_pct = 50.0` (measured 25.4%). The **cause** was a layers-1/2 ingest defect, repaired
  in `968321a`.
- *Conclusion:* **proceed at layer 3.** The ingest cause is repaired *in code*; the reporting defect
  is independent of it and would recur with any source. This is genuinely a layer-3 problem.

---

## 0. What v1 got wrong, kept rather than deleted

v1 claimed the record read as *"we tested QB college passing and it did not help."* **False.** The
2026-05-24 ledger recorded `BLOCKED/SKIP`, the exact 25.4% coverage, and the required next step. The
durable record was honest; Codex caught the error and it is corrected in the disposition. A framing
that survives by quietly dropping its falsified premise is worse than one that carries the
correction, so this section stays.

## 1. The concrete situation

David asks *"have we tried X?"* and reads a bakeoff summary to answer it. The Phase-20 run had
**three arms**: WR executed and failed (−1.4%, −5.7%), RB executed and failed (+5.6% below gate,
−7.4%), QB **never executed** — its candidate columns were dropped below the coverage threshold, so
the enriched feature set collapsed to the baseline set and both models were skipped.

All three were summarised as **"null result."** Two of those arms earned that label. One did not.

**The moment served:** a summary that cannot make "we tried it and it didn't help" and "we couldn't
try it" look the same. The ledger body already distinguishes them; the headline does not, and the
headline is what gets read six weeks later.

**Honest scale:** this is a reader-ergonomics and aggregation defect, not a buried finding. It cost
this session real time re-deriving a distinction the ledger already recorded. It is worth fixing
because that cost recurs every time, silently.

## 2. Mislead / nudge risks

- **Flattening remains the core risk.** A run-level label that averages over a blocked arm implies
  coverage of a question that was never asked.
- **A status must never imply a counterfactual.** `BLOCKED` says the arm did not run. It must not
  hint the feature would have helped — that would be a verdict smuggled in as a status.
- **Alarm fatigue.** A status that fires on a legitimately no-op configuration would train the reader
  to ignore it, leaving the surface worse than silence.
- **Rewriting history to improve it.** Mutating the 2026-05-24 artifact to add a status would destroy
  the immutable evidence that makes this classification checkable at all.

## 3. Falsification seeds for the RED

Mechanically pinned to the runner's real semantics — `enriched_differs = set(available_features) !=
set(BASELINE_FEATURES)` (`run_phase20_bakeoff.py:137`) compares **feature-name sets**, not values:

1. Declared candidate delta **non-empty**, surviving candidate delta **empty** → `BLOCKED`
   (unexecuted). This is the Phase-20 QB case.
2. Declared candidate delta **empty** → `no_candidate_features_declared`: an invalid/no-op
   configuration, a *distinct* refusal, never `BLOCKED`.
3. Surviving distinct columns carrying duplicate **values** → a separate duplicate/collinearity
   diagnostic; must **not** trip the execution-status branch (the false-positive boundary).
4. A declared family at **0.0** coverage (`qb_sack_rate_final`) → louder than "low coverage".
5. Baseline itself degenerate or empty → its own refusal, not this signal.
6. Mixed run: some arms executed, ≥1 blocked → run-level status must be `PARTIAL`, and **the
   artifact is still written** with completed arms preserved.
7. Derived assessment over a **historical** artifact must cite and hash its immutable input, and must
   reproduce byte-identically on re-run.
8. Source-agnosticism: an arm blocked for a non-CFBD reason classifies identically.
9. Status vocabulary is closed — `NOT_RUN`, `BLOCKED`, `EXECUTED_FAIL`, `EXECUTED_PASS` — and no
   other value may be emitted.

**Deliberately absent:** any `n_eligible_rows` power floor. `n_eligible_rows` is *reported*; inventing
a pass/fail floor would be a gate-threshold change and is out of scope (v1's seed 6, removed).

## 4. Overclaim check against the No-Verdict Line

The reader is running-software output, so it carries **`decision_supported=False` recursively** —
root and every nested model — per `00` §Descriptive Tools Issue No Verdicts. It reports **execution
status of a test**, never a football claim, never a ranking of feature families, and never a
counterfactual. Banned-language discipline applies to every string it emits. No `decision_supported`
value anywhere else in the system changes.

## 5. Shape

Two surfaces, no history mutation:

1. **Future runner + artifact schema** — explicit per-arm execution status plus a run-level status
   that cannot flatten blocked and executed-negative arms into one label.
2. **Historical reader/linter** — derives the same taxonomy from `spec_features`,
   `baseline_features`, `available_features`, `dropped_features`, `coverage_pct` and `gate_results`,
   emitting a new, **source-hashed**, `decision_supported=False` assessment. The 2026-05-24 artifact
   already contains enough evidence to classify its QB arm: **no rerun, no rewrite.**

## 6. Named open design decision, not an unanswered item

**Exit-code semantics** when a required arm is blocked. Constraint fixed by the disposition: durable
evidence is written **first**, and a non-zero exit may not pre-empt it. Whether the command then
exits non-zero is a v2 design choice I am deliberately leaving to the review round rather than
settling unilaterally.

## 7. Out of scope — each needs a separate David word

Gate-threshold changes (including any coverage-threshold change), bakeoff reruns, re-testing QB
features against the repaired ingest, any feature promotion, any model change.
