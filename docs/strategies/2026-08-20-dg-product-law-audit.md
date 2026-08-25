# Dynasty Genius — Product Law Audit

**Date:** 2026-08-20
**Question asked (David):** are we over-governing, and are there rules that stop us doing valuable
analysis, experimentation, or modeling?

**Scope:** PRODUCT law only — what the software may say and do. Process governance was settled at
near-zero on 2026-08-18 and is not the subject.

**Method:** seven parallel sweeps of the rule surface (127 rules catalogued),
one max-effort adjudication, then two opposing challenges — a guardian arguing every loosening is
dangerous, and a researcher arguing the adjudication was too timid. 10 agents, ~1.43M tokens, zero
errors. Every number below was re-run against the live repo.

---

## HEADLINE

Your product law spends almost all of its enforcement budget on LANGUAGE while the defects that actually ship are ARITHMETIC and PROVENANCE. I ran the runtime filter that guards your counter-arguments: it suppressed 10 of 12 honest bear cases ("buried on the depth chart", "historical bust rate is 42%") and passed all 17 real verdicts I threw at it — including "Sell him.", "Priority: cut", and "Likely_Favors_You", which your trade endpoint ships today through the one route with no schema governance. Meanwhile the market-leakage guard you correctly call non-negotiable has zero production callers, its CI test skips because the file it checks is gitignored, and its regex blocks `value_over_replacement` and `market_share_yds` while passing `sleeper_adp` and `fantasycalc_value`.

---

## THE ADJUDICATION

# Where You Are Paying a Tax and Getting Nothing

**Scope note:** this is PRODUCT law only — what the software may say and do. Process governance is settled (near zero, 2026-08-18) and is not my subject, except where a process-shaped gate has taken up residence inside product law.

**Method:** I did not take the seven sweeps on trust. Everything below with a number in it, I re-ran against the running system with `.venv/bin/python3.14`. Where I disagree with a sweep, I say so.

---

## The one measurement that explains everything

I loaded `frontend/src/shell/banned_vocabulary.json` and ran the exact matching logic from `app/api/routes/players.py:164-191` — the filter that decides whether your counter-argument reaches your screen — against two sets of strings.

**Twelve honest, purely descriptive bear cases. Ten were suppressed:**

| Counter-argument | Verdict |
|---|---|
| "He is buried on the depth chart behind two veterans." | **SUPPRESSED** (`depth`) |
| "He is not a starter in this offense." | **SUPPRESSED** (`starter`) |
| "Athletic testing is not elite." | **SUPPRESSED** (`elite`) |
| "Historical bust rate for this archetype is 42% (n=57)." | **SUPPRESSED** (`bust`) |
| "This is not a confidence score; it is an RMSE-proxied band." | **SUPPRESSED** (`confidence score`) |
| "The model has no dynasty tier for this player." | **SUPPRESSED** (`dynasty tier`) |
| "Nothing here says you should accept this trade." | **SUPPRESSED** (`accept this trade`) |
| "He is a net winner in snap share but a net loser in routes." | **SUPPRESSED** (`net win`) |
| "Coaches must start him for the projection to hold." | **SUPPRESSED** (`must start`) |
| "Target share fell from 24% to 17%." | passes |

**Seventeen actual verdicts. All seventeen passed:**

> "Sell him." · "Buy him." · "Hold." · "Cut him." · "Keep him." · "Safe to start." · "We recommend this trade." · "Recommended." · "Avoid." · "Target him." · "Strong buy." · "You win this trade." · "This trade favors you." · "Do not draft this player." · "Priority: cut" · "Advice: move on." · **"Likely_Favors_You"**

That last string is not hypothetical. `app/services/trade_analyzer.py:229-232` returns `"Likely_Favors_You"` / `"Likely_Favors_Opponent"` today, served by `POST /api/trade/analyze`, which is the only route in the app declared `-> dict` with no `response_model` — so it bypasses every `extra='forbid'` and recursive-`decision_supported` invariant governing the other seventeen routers. `delta_status` has **zero** occurrences in `frontend/openapi.json` because there is no schema for it to appear in. Neither scanner touches `app/services/`.

**So: a two-language AST scanner runs in CI checking that no surface says "buy", while a live endpoint returns a directional trade verdict as an enum at the root, and the runtime filter deletes your bear case for saying "depth chart."**

Constitution `00:264` makes the counter-argument **mandatory**. One product law silently deletes what another product law compels — and you cannot tell the difference, because suppression and absence both render as the same caveat token.

---

# 1. Rules that block valuable work

### 1.1 The leakage regex blocks your own core quantities and passes real market columns

`src/dynasty_genius/models/engine_a_contract.py:71`:
```
LEAKAGE_REGEX = r"^ktc_|^adp|_rank$|^expert|^market_|^value_|^consensus"
```

I ran it. It fails on both sides simultaneously:

| Column | Blocked? | What it actually is |
|---|---|---|
| `value_over_replacement` | **BLOCKED** | your own core product quantity |
| `market_share_yds` | **BLOCKED** | THE canonical prospect metric |
| `recruiting_rank`, `dominator_rank` | **BLOCKED** | pre-NFL, non-market |
| `sleeper_adp` | passes | market ADP |
| `fp_ecr` | passes | market consensus rank |
| `fantasycalc_value` | passes | **enumerated in your own PROHIBITED_COLUMNS** |
| `dynastydatalab_adp` | passes | **enumerated in your own PROHIBITED_COLUMNS** |
| `crowd_price`, `dn_val`, `sf_value` | passes | market, plausibly named |

Two of the six market columns the same file lists by name are missed by the regex meant to generalise it. `market_share_yds` survives in the repo today only because someone happened to spell it `wr_market_share_yds`. The exact enumerated set is doing all the real work; the regex mostly generates false positives.

The `_rank$` clause is worse than useless — it's *inconsistent*. `leakage.py:52` uses `regex.match` (anchored at position 0, so `_rank$` can literally never fire); `scripts/validate_training_csv.py:57` uses `.search` (where it fires on everything). Same constant, two behaviours. And `tests/test_market_leakage_gate.py` tests the *permissive* one with `re.search`, asserting `expert_rank` is caught — which passes only because `^expert` fires. The test gives false confidence in a clause that is dead in the module named `leakage.py`.

### 1.2 The calibrated-tier amendment shipped its prohibition and not its permission

You ratified this on 2026-07-14, in your own words: *"the use of prose tiering is fine on the front end and frankly even the backend so long as it is backed by statistical evidence."*

I grepped `tier_calibration` and `CalibratedTier` across `src/`, `app/`, `frontend/src/` and `tests/`. **Zero hits.** Step 2 of the amendment's own binding sequence — build the calibration producer — was never done.

The prohibition half shipped completely, and it now reaches *further* than the ban it replaced: fail-closed across compute, serialize, emit, persist and render, front end and back end, where the old vocabulary ban only touched visible JSX. **The net effect of an amendment you ratified in order to relax a ban is a stricter ban that has now stood for five weeks.** The prohibition was cheap. The calibration model was the real work.

This is the corpus's signature failure mode in its purest form, and it repeats: `_PROMOTION_ABOVE_C_GATED_UNTIL_STEP_0_5`, the frozen constants, the composite gate. **Cheap half ships; expensive half doesn't; the temporary catch hardens into a permanent ceiling.**

### 1.3 The filesystem, not statistics, is what stops experiments

I walked three concrete experiments. In every case the blocker was structural, not scientific.

**Try one extra usage feature on the TE model.** `tests/test_engine_b_contract.py:228-231` pins the TE feature set by exact set equality. To fit one Ridge with one extra column you must edit the frozen contract *and rewrite the test that asserts the contract is frozen* — a promotion-shaped edit to answer a question that is not yet a promotion. Compounding it, `tests/contract/test_feature_engineering_extraction.py:267` pins `ENGINE_B_OUTPUT_COLUMNS` as an exact ordered list, so an exploratory column cannot exist in the assembled dataset **at all**. There is no diagnostic lane.

That second pin is the damaging one. The assembler is the only code that knows how to build a leakage-correct T/T-1/T-2 frame with the outcome joined at T+1/T+2. Forbidding an extra column there means every exploratory feature gets recomputed by hand *outside* that machinery — and hand-recomputing season alignment is exactly how temporal leakage gets introduced. **The rule written to protect data integrity relocates feature construction to the least safe place in the system.**

**Bench a gradient-boosted tree against the Ridge baseline.** `tests/contract/test_subsystem_4_audit.py:114-132` allows exactly 18 files in `src/dynasty_genius/eval/`. A GBT bakeoff is an eval module by every structural criterion — identical in shape to `te_regularization_bakeoff.py`, already on the list. It fails a contract test **on file creation**, before it contains a line of logic. Nothing pins Ridge as the estimator; scikit-learn is already a dependency. *The rule that stops this experiment is not a modelling rule. It is a filesystem rule.*

**Test whether analyst sentiment leads market price.** `tests/test_source_registry.py:22-34` pins the registry to exactly 21 sources, and it cannot distinguish "a new market-adjacent feature source" from "a read-only study source." Register it even as `validation_study` — a role that by construction can never reach a model — and `docs/data-source-contracts.md:27-50` then demands a four-method production adapter with provenance columns, a pure parser and a cadence registration, before you can compute one lead-lag correlation.

**And here is the part that should worry you most.** The bypass discards the one thing in that list genuinely worth protecting. Pre-registration is what makes a positive result trustworthy; it is bundled with adapter ceremony that has nothing to do with inferential honesty, so it is thrown out together with the ceremony.

### 1.4 The two closeout rules that manufacture the bypass

Neither author could have seen this alone.

`scripts/verify_closeout.py:144-153` — no uncommitted paths at close. I checked: **there is no gitignored scratch location.** `driver-scratch/` exists at the repo root, created 10 August, empty, untracked, and *not* gitignored — so anything you put in it makes closeout dirty.

`scripts/verify_closeout.py:156-186` — no `/tmp`, `/private/tmp`, `/var/folders` or `/Users/<name>/` path in the record. No waivers.

Together: **the first makes out-of-repo experimentation necessary; the second makes it uncitable.** The rule's own docstring instructs the writer to "describe the path instead of reproducing it" — that is, to write a citation nobody can follow. Meanwhile `AGENTS.md` rule 10 demands "every claim about the repo carries the command that produced it," and this check forbids the one part of that command a reader would need.

The joint output is exactly what you should fear: **ungoverned work that looks governed** — a prose paragraph with numbers in a 10.6MB ledger, formatted identically to work that passed every contract test.

And the gate has already stopped being read. Your working tree carries **60 dirty paths right now**; `AGENT_SYNC`'s own 2026-08-18 close reports the durability gate red for "30+ paths, mostly other lanes' parked work."

The fix costs one `.gitignore` line. **A governed place to be messy is the cheapest anti-bypass mechanism available.**

### 1.5 The entry toll: ~98K tokens of mandatory reading, charged flat

Six governance documents plus `AGENT_SYNC.md` to the END CURRENT BOARD marker — roughly 390KB — before touching anything, levied per session, identical whether the task is "restructure the PVO" or "try one extra column on TE."

`02-agent-operating-loop.md` is 70KB of mostly *process* governance — cockpit lanes, closeout vocabulary, agent authority history — the thing you turned to near zero. It remains the largest single mandatory read for a purely analytical task.

Its enforcement is the tell: `scripts/validate_governance.py:76-135` pins **~30 exact prose sentences** in CI. So CI mechanically verifies the documents still *say* the right sentences and can never verify anyone read them. It will block a change that improves a sentence in `DESIGN.md`, and it will pass a change shipping a tight-end multiplier that values every TE 7.8% low.

---

# 2. Rules that are theatre — the expensive ones

These buy false confidence, which is worse than buying nothing.

### 2.1 The market wall: one real guard, three decorations, one skipped test

You named this as non-negotiable and you are right. Here is its actual state.

**`check_leakage` / `find_leaking_columns` (`models/leakage.py`) has ZERO production callers.** Verified by repo-wide grep: the only importers are `tests/test_leakage_scanner.py` and one retirement contract test. Its own docstring says it "keeps KTC/ADP-derived columns out of Engine A training rows." It keeps nothing out of anything. It was extracted from a retired script in August 2026 and never re-wired.

**The CI leakage test cannot run.** `tests/test_market_leakage_gate.py` points at `app/data/training/prospects_with_outcomes_v2.csv`. `git check-ignore -v` reports **`.gitignore:48`**. On CI and any fresh clone the file is absent, both real-enforcement assertions `skipif` away, the suite reports green. What actually executes under that filename is eight regex self-tests asserting that `re.search(r'^ktc_', 'ktc_value')` is truthy. *Your most-protected law, guarded by tests that assert a regex library works.* The live artifact is `_v3.csv`, referenced by no gate. And `04-strategic-execution-charter.md:74` already names this exact anti-pattern as a lesson learned.

**The CI "market feature" scan looks at the wrong files.** I resolved `MODEL_FEATURE_GLOBS` from `scripts/validate_governance.py:144-151`. It matches **5 files**, all under `src/dynasty_genius/features/`. Out of scope: `models/engine_b_contract.py`, `models/engine_a_contract.py`, `scoring/engine_a.py`, `pvo_assembler.py` — *every file where the per-position feature matrices actually live*. Within the five, `\badp\b` cannot match `adp_sleeper` (underscore is a word character) and a variable rename defeats it entirely.

**`MARKET_FIELD_PATTERNS` is a dead constant.** `scripts/build_head_b_targets.py:99` defines it, `:12` claims the ban is "enforced by" it, and grep confirms it is never used in the script. Its only consumer is a test asserting that six hand-written literals don't match — a test that cannot fail. It is also the *fourth* divergent copy of the market rule, and the only copy that catches `fantasycalc` and `dynastynerds`: someone hit the canonical regex's gap and patched it in a dead constant instead of fixing `engine_a_contract.py:71`.

**What actually protects the wall** is three things, all structural: the closed-world `ENGINE_B_ALLOWED_FEATURES` checked against real column lists at training time; the nine-line import-time assertion at `source_registry.py:462-469`; and the pre-commit hook on real CSV bytes. Note the contrast: **the strongest enforcement of your most important law is nine lines with no CI step and no ceremony**, while the decorations around it run to hundreds.

### 2.2 The banned-fields gate guards five names that cannot exist

I counted occurrences in `frontend/openapi.json`:

| Banned field | In contract | | Directional field that IS in contract | Occurrences |
|---|---|---|---|---|
| `verdict` | **0** | | `favors` | 2 |
| `dynasty_tier` | **0** | | `adjusted_favors` | 2 |
| `confidence` | **0** | | `partner_score` | 3 |
| `recommended_action` | **0** | | `cut_priority` | 3 |
| `roster_action` | **0** | | `sort_value` | 4 |
| | | | `posture_label` | 3 |

The gate is *structurally incapable of firing*. It is one of three gates in a 264-line scanner with a 406-line contract test and a 30-row falsification matrix, aimed at a vocabulary that was retired. The six names it should be watching are absent from the list.

### 2.3 The scanner has two one-character bypasses and has never fired

`frontend/scripts/check-banned-language.mjs:138-143` extracts text only from `ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)`.

- `<p>Sell now</p>` → trips.
- ``<p>{`Sell ${name} now`}</p>`` → **passes**. Any interpolated template evades entirely — and interpolation is the normal React idiom for dynamic copy.
- `<p>Sell&nbsp;now</p>` → **passes**. Entities are never decoded.

The scanner is green today with zero suppression markers anywhere in real source. It has never once fired on production code, so these holes have never been tested by an actual violation.

### 2.4 One "single source of truth," two opposite semantics

`banned_vocabulary.json` calls itself the single source of truth. The Python contract test is literally named `test_t6_vocabulary_artifact_is_single_source_of_truth`.

| | Standalone words | Phrases |
|---|---|---|
| **Frontend** (`check-banned-language.mjs`) | exact whole-node match | `\b…\b` regex |
| **Backend** (`players.py`) | `\b…\b` anywhere in text | plain substring `in` |

Opposite on both axes. `"depth chart"` is **explicitly asserted safe** by the JS contract test and is **suppressed** by the Python one. `"net winner"` has an explicit JS falsification row saying it must pass; Python suppresses it. It is a single source of *data* with two incompatible semantics — and whichever one you have reasoned about, the other is doing something else.

There are at least **nine live banned-word lists** across the repo, no two identical. `target` is banned in three and legal in the rest. Bare `buy`/`sell` are banned in five and legal in the artifact that calls itself canonical. **The dispersion is itself the over-governance.**

### 2.5 `decision_supported` — 3,685 lines to police a field with one possible value

Measured: **468 of 468** scored rows are `False`. No code path anywhere can produce `True`. A boolean whose True branch has never executed is not a guarantee; it is an untested decoration.

Three compounding defects:

**(a) The lock is missing exactly where the danger is.** I constructed it:
```
PlayerValueObject(player_id='x', full_name='y', position='QB',
                  signal_completeness=1.0, decision_supported=True)
→ CONSTRUCTED, decision_supported = True
```
`player_value_object.py:119` is plain `bool = False`. Its own docstring says *"Every decision surface (Roster Audit, Trade Lab, Rookie Board) reads from this object."* Meanwhile `system_capture_health_models.py`, `system_health_models.py` and `system_tier_readiness_models.py` — internal ops dashboards nobody could mistake for advice — are hard-locked with `Literal[False]` four times each. **Enforcement went where it was easy (new DTOs written after the rule existed), not where the danger is (the central legacy object every surface reads).**

**(b) Fifteen validators suppress the alarm they exist to raise.** The `mode='before'` validators run *ahead* of type validation. On those 15 surfaces a genuine bug setting `True` is **swallowed silently**; on the other 40 it raises. Two mechanisms with opposite failure semantics on one nominal law — and several fields carry both, where the validator wins and the `Literal` is dead decoration. *A no-verdict law whose enforcement mechanism suppresses its own violations is anti-safety.*

**(c) The apparatus certifies the label and never inspects the content.** `roster_cut_engine.py:355-380` emits `cut_priority: 1..N` — a scalar rank of **actions**, the precise thing the narrowed xVAR ruling calls illegitimate. That object carries `decision_supported=False` and passes every verifier.

**And it blocks the one honest promotion available.** WR has cleared every gate the system defines — `g1_rank_correlation_pass=True`, `g2_rmse_stability_pass=True`, `g3_market_superiority_pass=True`, `overall_grade=ACTIVE_B_VALIDATED`, `model_status=VALIDATED`, `leakage_clean=True`, `null_coverage_min=1.0`. It is the one position that has earned a claim, and the product cannot express it, because the field is a compile-time constant in 40 places. **The apparatus does not encode "not yet earned." It encodes "unearnable."**

The whole thing terminates in a hardcoded string: `DisclosureLine.tsx` renders a constant and never reads the field; `TrustTruthPanel.tsx:20` renders the literal `decision_supported = false` as UI text — finding F10 from `docs/product-assessment-2026-07-04.md:30`, still shipping six weeks later, because the energy went into locking the field's type rather than into what you actually see.

---

# 3. What is right, and what it protects

Defend these. They are short, structural, and aimed at the thing that can actually be wrong.

1. **`ENGINE_B_ALLOWED_FEATURES` closed-world allowlist**, checked against real column lists at training time. This — not the prose, not the regex — is what makes "do we beat the market?" answerable. Closed-world beats denylist because a denylist can never enumerate future column names.
2. **`source_registry.py:462-469`** — nine lines, import-time, structural (roles, not words), unbypassable without deliberately editing the registry. **This is the template every other rule should copy.**
3. **The pre-commit CSV guard** — right artifact, right moment, checks substance not vocabulary. Point it at files that aren't gitignored and it becomes the whole wall.
4. **`OUTCOME_SEASON_COLUMNS`** exact set — the highest-consequence defect in the system, guarded by an enumerated list with zero false-positive surface.
5. **The composite gate's hard floors** (`leakage_clean`, `null_coverage >= 0.90`, fail-closed, dominating everything). Correct ordering, auditable denominator, ~10 lines. Note the contrast in effort: this protects the moat in 10 lines; `decision_supported` protects nothing in 3,685.
6. **Silent substitution forbidden + the fail-closed/503/staleness machinery.** Genuinely running. The point-in-time capture DBs are written daily. **The append-only archive you call the moat is the one place where doctrine and the running system agree completely.**
7. **The morning-tape 503 guard** — fail-closed on a real danger, at the serve layer where the claim reaches you, checking *structure*. This is what the vocabulary scanner would look like if it were aimed correctly.
8. **The `favors` render guard** — the only mechanism in the corpus asserting on rendered output for a field that actually exists and actually carries direction. Widen this; shrink the scanner.
9. **"The model is the anchor" (`00:150`).** The best-argued rule you have, and the only one with the right *shape*: it explicitly permits in-season monitors to detect, report, alert and queue candidate changes. **It gates promotion without blocking experimentation. Use it as the pattern for narrowing everything else.**
10. **The 05 attribution rule.** Do not weaken it — propagate it.
11. **The codex_audit SQL workflow.** Deliberately non-blocking, exits 1 today, and its own comment forbids citing a green run as evidence — it even records that a previous version reported "passed for 0 SQL files" daily for months. *This is the healthy shape for a check that is not yet a gate.*

---

# 4. Rules nobody enforces — enforce or delete

A dead law teaches agents that laws are optional.

| Rule | Reality |
|---|---|
| `test_no_unvalidated_in_production.py`, `test_no_silent_substitution.py`, `test_ratchet.py`, `test_ktc_not_in_features.py` (`docs/validation-gates.md`) | **All four return zero hits repo-wide.** Never written. They are cited as the mechanical gates closing phases 0, 3, 8, 9 — covering three of the four doctrines that genuinely matter. |
| `check_leakage` | Zero production callers. |
| `tier_calibration` producer | Zero occurrences. |
| axe accessibility = 0 (`PRODUCT.md:56`) | **Fully built, never run.** `@axe-core/playwright` and `@playwright/test` installed, `playwright.config.ts` exists, `visual:smoke` script exists — absent from the `gate` script and from CI. One line to fix. |
| No system-nominated hero / MoverHero (`PRODUCT.md:46`) | Grep across `frontend/src`, `src`, `app`, `tests` returns only the two doc mentions. A lexical scanner cannot see a structural nomination anyway. |
| Counter-argument required (`00:264`) | **254 of 468** populated. No gate, no floor, no caveat. |
| Uncertainty required (`00:268`) | **Zero** interval/sigma/CI/lower/upper fields on any of 468 rows. `projection_3y` null on 468/468. `DESIGN.md:58` names the σ bar as your signature differentiator against Sleeper/DN/KTC. It does not exist — and the field name you'd naturally give it, `confidence`, is on the banned list. **You banned the word for false certainty and never built the mechanism for honest uncertainty. This is the highest-value unbuilt item in the audit, and it is already mandated.** |
| "Surface the arithmetic honestly, unclamped" (`00:166`) | Enforced by nothing. See §5. |
| Feature provenance MUST (`01:140-159`) | `engine_b_features_v2.csv`: 33 columns, **none** of source / source_timestamp / parser_version / metric_version. Engine A's `_v3.csv` *does* carry it. Satisfied on the engine that scores rookies; unsatisfied on the engine that scores every player you trade. |
| P90/λ freeze "recompute when the distribution materially changes" | **Nothing measures whether it changed.** See §5. |
| Phase 17.5 exit criteria | Two hardcoded Python `True` literals, asserted by a test, **persisted into shipped artifacts as a governance guarantee you can read.** A criterion that cannot fail is a false receipt — worse than absent, because it occupies the slot where a real check would go. |

---

# 5. Contradictions the code already ships

### 5.1 The clamp is flattening the top of your board — and I found the real cause

`00:166` (David-ratified): *"Surface the arithmetic honestly, unclamped… Tightening, clamping, banding… is the failure mode this line prevents."*

The code clamps `dynasty_value_score` to `[0,100]` at `pvo_assembler.py:409,424`, `scoring/engine_a.py:113,217`, `trade_lab/draft_pick_valuation.py:47`.

Measured on the served artifact: **23 of 468** scored players sit at exactly 100.0. Because xVAR derives from clamped DVS, ordering dies at the top of every position:

- **11 tight ends** all report `xvar = 2.85`
- **6 wide receivers** all report `xvar = 39.40`
- **5 running backs** all report `xvar = 58.05`

The best player at a position and the eleventh are numerically indistinguishable — for exactly the players you most need to tell apart.

**Correction to the sweeps.** They attribute TE compression mainly to the stale multiplier. I checked the arithmetic; that is not right. `ENGINE_B_REPLACEMENT_DVS['TE'] = 95.6` against a ceiling of 100, so max TE xVAR is `(100 − 95.6) × 0.648 = 2.85`. **Fixing the multiplier to 0.703 only moves it to 3.09.** Compare RB at 58.05. **The clamp is the binding constraint for TE, not the multiplier.** Fix the clamp first; the multiplier second.

And note what the corpus did on discovering this: `tests/contract/test_dvs_clamp_disclosure_red.py` (2026-08-18) — a test that the clamp is **disclosed**. There is a test that it is disclosed. **There is no test that forbids it.** A constitutional prohibition you ratified was answered with a disclosure field instead of a fix.

### 5.2 The frozen constants are stale and nothing was listening

I recomputed P90 of `avg_ppg_t1_t2` from the live `app/data/training/engine_b_features_v2.csv` (2,741 rows; identical on the `training_eligible` subset):

| Pos | Recomputed P90 | λ vs WR | **Shipped λ** | Error |
|---|---|---|---|---|
| QB | 20.445 | 1.398 | 1.386 | −0.9% |
| RB | 15.691 | 1.073 | 1.083 | +0.9% |
| WR | 14.628 | 1.000 | 1.000 | — |
| **TE** | **10.284** | **0.703** | **0.648** | **−7.8%** |

The shipped multipliers reproduce the shipped P90s to three decimals — **the arithmetic is honest and jointly stale.** Every tight end is understated in every cross-positional comparison the product makes, and that flows into `starter_weighted_xvar` (`team_value_matrix.py:268`), which carries 0.60 weight in every posture label.

Why no test caught it: **every** test touching `XVAR_LAMBDA` computes its expected value *from* the constant (`test_phase15_xvar.py:36,73,80,95`; `test_phase15_rookie_rank_refresh.py:45,56`). Tautological. Not one derives λ from `ENGINE_B_P90_PPG`.

The rule says recompute "when the training distribution materially changes," and nothing measures whether it changed. `AGENT_SYNC`'s own 2026-08-18 board records that PPG now includes postseason and that "P90/replacement/xVAR/calibration need rerun." **The trigger fired. Nothing was listening — because the rule gated the measurement behind an approval instead of gating the publication.**

Two cheap fixes, both absent: one test asserting `XVAR_LAMBDA[pos] == round(P90[pos]/P90['WR'], 3)`, and a recompute-and-diff on every training assembly that *reports* drift.

### 5.3 The rule change, not the evidence, demoted QB

Live artifacts under `app/data/backtest/trust_surface/latest/`:

**QB — every fold passes the original two-part rule** at `docs/validation-gates.md:125` (point ≥ 0.55 **and** lower bound ≥ 0.40):

| Fold | n | ρ | 95% BCa lower | CI width |
|---|---|---|---|---|
| 1 | 43 | 0.678 | 0.415 ✓ | 0.405 |
| 2 | 46 | 0.721 | 0.543 ✓ | 0.290 |
| 3 | 46 | 0.693 | 0.426 ✓ | **0.413** |
| 4 | 49 | 0.755 | 0.608 ✓ | 0.252 |

QB is `PROVISIONAL` solely because fold 3's CI is 0.413 wide. The composite gate kept the point estimate and **silently swapped the lower-bound half for a CI-width half** — substituting a *precision* requirement for an *effect-size* requirement. Those are not interchangeable. And it's a hidden raising of its own published bar: ρ ≥ 0.55 **and** width ≤ 0.30 at n=46 implies an effective ρ ≥ ~0.71 — 0.16 above the number the spec, the code comment and `validation-gates.md` all publish.

**And the excuse machinery inverts.** TE fold 1: ρ = 0.436 (below threshold), lower bound 0.244, on **n = 206** — a large sample measuring genuine weakness. It is excused as cold-start on *both* rank and CI, and TE ships `VALIDATED`. QB fold 3: ρ = 0.693 on n = 46 — a small sample measuring genuinely strong rank skill. Not excused; QB ships `PROVISIONAL`.

**The gate forgives a well-measured weak result and punishes a noisily-measured strong one.** That is backwards from what a sample-adequacy criterion is for — and it is hardest exactly where Superflex makes the decisions matter most.

Restore the lower bound and drop `CI_WIDTH_MAX`: QB passes on its own evidence, and TE fold 1 correctly fails on effect size without any excuse being invoked. The codebase already contained the better-reasoned rule; a later spec replaced it with a worse one that reads as more rigorous.

### 5.4 Five guards on which columns the TE model sees; none on whether it is any good

`scripts/train_engine_b.py:121-176`. Trace it: `:143` calls `_fit_position_ridge(train_df, features, alpha)`, which fits imputer and Ridge on `train_df` and returns that same `X`; `:145` does `model.predict(X)` on it. **The shipped TE artifact's `metrics_model` and `metrics_baseline` are both in-sample.** And `:171` hardcodes `promotion_warranted: None` — `_gate()` is never called, so the ≥2-of-3 composite gate governing every other position is skipped entirely for TE. The `v2_stratified` path at `:264-274` does it correctly.

So the TE *feature list* is defended by five mechanical guards — exact-equality contract test, closed-world allowlist, leakage validator, prohibited-feature validator, position-contract validator — while the number saying whether the model works is computed on its own training rows and no gate reads it. **The scanners check membership; the defect is arithmetic.** Same position whose multiplier ships 7.8% low.

### 5.5 The rest

- **`_safe_source_status`** (`market_reconciler.py:693-707`) collapses any status containing `pass`/`fail`/`block`/`reject` to `None`. Its own docstring names the case: `gates_passed` contains "pass." So `blocked_stale_market` and `rejected_low_coverage` are silently erased and the surface reports *no reason at all* — while `00:166` requires the exact opposite. **It deletes the receipt to satisfy a word list.**
- **`PartnerRankings.tsx`** renders `partner_score` to three decimals as, per its own source comment, *"the who-to-target context"* — a descending rank of **actions** whose DTO stamps `market_influenced=True`. Under the narrowed xVAR rule this is the *illegitimate* case, and it passes every gate. Cross-positional xVAR — single-lane, disclosed, market-free, describing a *player* — got interrogated under the letter of the law. **The law never looked at this one.**
- **`cut_priority: 1..N`** ships on the What-Changed DTO (3 occurrences in openapi.json) while `LeaguePulseCapacityCandidatePool` went to real trouble to avoid exactly that, substituting `capacity_conflict_status` with a docstring explaining it "never selects one." Same law, same repo, two answers. The ordering is honest; the *name* is not. Rename to `capacity_order`.
- **`head_b_contract.py:77-82`** bans seven "market-overlay columns" — `nfl_yards`, `nfl_tds`, `nfl_targets`… — none of which is market data, and none of which exists anywhere in the repo. Because the ban is filed under "market," the genuinely dangerous columns of the same class were never enumerated: `y2_points`, `total_points`, `y24_ppg`, `best3of4_ppg` and `residual_ppg` — **Head B's own target** — are all admissible as features. *The constant name is lying, and the lie cost you the real rule.*
- **`qb_rookie_risk_filter`** rejects `height`, `ras_composite`, `college_ypa`, `early_declare`, `season` as "NFL usage leakage." All five are pre-NFL; the message is false for every one. Meanwhile `classify_rookie_qb_risk` branches on `draft_number` **alone** — `age_at_entry` is required, validated, echoed to output, and influences nothing. **The whitelist mandates a column the model ignores and forbids every column that might improve it.**
- **"Frontend polish comes last"** (`00:131`) vs `PRODUCT.md:28` ("an honest developer diagnostics console wearing a fantasy skin" is the failure mode to kill). An agent reading in the mandated order hits the first *before* the second and can cite it to defer visual work indefinitely. The Phase Sequence is already dead: phases 10 and 12 shipped, phase 11 didn't, nobody logged the exception `01:352` requires.
- **H2 QB rushing.** The conclusion still holds; the stated *premise* is false. Both bootstrap files say "The study has not run. There is no result." `docs/agent-ledger/2026-08-17.md:25` records the study finished `READY_FOR_GATE` with all five receipts passed. Every agent reads the stale line first, every session. **A standing rule with a stale premise is how a false claim reaches you in good faith** — which your own memory record shows has already happened once on a different stale line.
- **Non-goals.** "Mock draft simulator" shadows your RULING F scenario builder; "mobile app" shadows `PRODUCT.md:51`. Two entries the constitution never updated after your own later rulings.
- **The green/red ban.** `tokens.css` has **no** directional token at all. A +2.3% and a −2.3% render in identical ink, glyph-only, on a 32px row at 0.8125rem — in a product whose daily job is "what changed overnight." `DESIGN.md` concedes "direction is data, not judgment" and then bans the encoding that would make direction legible.
- **The Sleeper palette gate.** `tokens.css:37-40` ships QB as purple (doc says pink/red), WR as pink (doc says blue), TE as cyan (doc says orange). The gate requiring screenshot-sampling plus cross-review has not been paid, so a *known-wrong* palette ships instead. The ceremony costs more than the error it prevents.

---

# 6. What I would do first

**This week, ~1 day of work, all mechanical:**

1. Delete the standalone-word gate from the runtime counter-argument filter. It suppresses 83% of your honest bear cases and catches 0% of real verdicts.
2. Give `POST /api/trade/analyze` a `response_model` and rename `delta_status` to describe interval overlap rather than a winner.
3. Remove the DVS upper clamp. Let values exceed 100 and print them — an out-of-band number is a legible signal that the P90 reference needs recomputing.
4. Add `npm run visual:smoke` to the `gate` script. One line, and the accessibility law starts existing.
5. Add one `.gitignore` line for a declared scratch path, and make `check_working_tree` ignore it by name. This is the single highest-leverage anti-bypass change available.
6. Point `tests/test_market_leakage_gate.py` at `_v3.csv` and add `scripts/validate_training_csv.py --all` to CI. I ran it read-only: it exits 0 clean across all 8 CSVs today, so wiring it costs nothing and gives you real coverage for the first time.

**Next, ~1 week:**

7. Recompute the P90s, fix `XVAR_LAMBDA['TE']` to 0.703, and add the two cheap guards: the derivation test and the drift report. **Gate the publication, never the measurement.**
8. Fix `train_te_deployment_model` to hold out seasons and call `_gate()`.
9. Restore the two-part Spearman criterion; drop `CI_WIDTH_MAX`.
10. Delete `MARKET_FIELD_PATTERNS`, the `MARKET_FEATURE_RE` CI scan, `_safe_source_status`, the `banned_fields` gate, and 27 of the 30 prose pins. **Every one of these is pure cost.**

**Then the two things that actually make the product better, both already mandated:**

11. **Build the uncertainty interval.** `00:268` requires it, `DESIGN.md:58` calls it your signature differentiator against Sleeper/DN/KTC, and it does not exist on any of 468 rows. Building it is also what earns you the word "confidence" back.
12. **Build the tier calibration producer** — step 2 of the amendment you ratified five weeks ago — so the permission half of your own ruling finally ships.

**And one structural change worth more than any single fix:** put `05`'s section-scoped attribution header on `00` through `04`. Right now the highest-authority document in the corpus is agent codification of an AI-authored framework, with four ratified islands, presented uniformly as binding doctrine. **That one change tells every future reader which rules the crew may narrow on its own and which need you — which is precisely the question this audit had to reconstruct by hand.**

---

## The pattern, stated once

Language is easy to check. Arithmetic is not. So the enforcement went where it was easy, and then — this is the expensive part — **the presence of enforcement was mistaken for the presence of safety.**

Nine banned-word lists, a two-language AST scanner, a 406-line contract test with a 30-row falsification matrix, and 3,685 lines policing a boolean with one possible value. Underneath it: a leakage guard with no callers, a CI test that skips, a frozen constant 7.8% wrong, a TE model scored on its own training rows, and a live endpoint returning `Likely_Favors_You`.

You are not over-governed because you have too many rules. **You are over-governed because the rules are pointed at the wrong layer, and the ones pointed at the right layer are the short ones nobody notices.** The nine-line import-time assertion at `source_registry.py:462-469` protects more than everything in §2 combined.

---

## RECOMMENDED CHANGES (52)

### [NARROW] Runtime banned-vocabulary filter applied to counter_argument and evidence strings (app/api/routes/players.py:164-191)

**Why:** I executed it against 12 honest, purely descriptive bear cases and 17 real verdicts. It suppressed 10 of the 12 honest ones ('he is buried on the depth chart', 'historical bust rate is 42% (n=57)', 'he is not a starter in this offense', 'nothing here says you should accept this trade') and passed all 17 verdicts including 'Sell him.', 'Recommended.', 'Priority: cut' and 'Likely_Favors_You'. The constitution MANDATES the counter-argument (00:264) and this filter silently deletes it, replacing it with a token David cannot distinguish from 'none was generated'. Perfectly inverted: it deletes the most valuable honest content the product makes and passes every actual verdict.

**Replacement:** Scan for imperative mood directed at David — a transaction verb phrase addressed to the reader — not for domain nouns. Keep the phrase gate, drop the standalone-word gate on generated prose entirely. DANGER ACCEPTED: an imperative phrased in words nobody listed could reach the bear case. STAYS VISIBLE: the counter-argument is 254/468 populated today and read by one person; a bad one is immediately obvious to him, and today's filter provides zero protection against 'Sell him.' anyway.

### [NARROW] LEAKAGE_REGEX = ^ktc_|^adp|_rank$|^expert|^market_|^value_|^consensus (src/dynasty_genius/models/engine_a_contract.py:71)

**Why:** Verified by execution, it fails on both sides at once. BLOCKS: value_over_replacement (the product's own core quantity), market_share_yds (the canonical prospect metric — it survives today only because it was spelled wr_market_share_yds), recruiting_rank, dominator_rank, any percentile transform. PASSES: sleeper_adp, fp_ecr, fantasycalc_value, dynastydatalab_adp, crowd_price, dn_val, sf_value. Two of the six market columns the same file enumerates by name are missed by the regex that is supposed to generalise it.

**Replacement:** Delete the ^value_ and _rank$ clauses. Match market TOKENS anywhere in the name (adp, ecr, ktc, keeptradecut, trade_value, auction, consensus_rank, fantasycalc, dynastynerds) and let SOURCE_REGISTRY roles adjudicate the rest. DANGER ACCEPTED: a market rank named with no market token slips the regex. STAYS VISIBLE: the enumerated PROHIBITED_COLUMNS set and the import-time source_registry role check are the two mechanisms doing the actual work today and are unaffected.

### [ENFORCE_PROPERLY] check_leakage / find_leaking_columns fail-closed frame guard (src/dynasty_genius/models/leakage.py:42-80)

**Why:** Zero production callers — verified by repo-wide grep, the only importers are tests/test_leakage_scanner.py and one retirement contract test. The module docstring says it 'keeps KTC/ADP-derived columns out of Engine A training rows'. It keeps nothing out of anything. It also uses regex.match where its sibling validator uses regex.search, silently disabling the _rank$ clause. This is the load-bearing law with the largest gap between claim and reality.

**Replacement:** Wire scripts/validate_training_csv.py --all into CI as one step (I ran it read-only: exits 0 clean across all 8 CSVs today, so it costs nothing to add), and delete leakage.py or call it. Pick one of match/search and test the one production runs.

### [ENFORCE_PROPERLY] tests/test_market_leakage_gate.py real-enforcement assertions, guarded by @pytest.mark.skipif(not ENRICHED_CSV.exists())

**Why:** ENRICHED_CSV is app/data/training/prospects_with_outcomes_v2.csv, gitignored at .gitignore:48 (verified with git check-ignore). On CI and any fresh clone it is absent, both tests SKIP, the suite reports green. The live artifact is _v3.csv, referenced by no gate. What actually runs in CI under this filename is eight regex self-tests asserting that re.search(r'^ktc_','ktc_value') is truthy. The pre-commit hook meant to be the real gate only fires on STAGED files under app/data/training/*.csv, so it can never see a gitignored file either. There is currently no automated path that inspects the live training artifact for market leakage. 04-strategic-execution-charter.md:74 already names this exact anti-pattern as a lesson learned.

**Replacement:** Point the gate at the artifact that exists (_v3.csv) and run validate_training_csv.py --all in CI so it cannot skip.

### [NARROW] Calibrated-tier fail-closed gate — no named tier label may be computed, serialized, emitted, persisted or rendered until a David-ratified tier_calibration artifact authorizes it (00-product-constitution.md:170)

**Why:** Verified: tier_calibration and CalibratedTier return ZERO hits across src/, app/, frontend/src/ and tests/. Step 2 of the amendment's own binding sequence — build the calibration producer — was never done. David ratified this on 2026-07-14 to RELAX a ban ('the use of prose tiering is fine on the front end and frankly even the backend so long as it is backed by statistical evidence'). The prohibition half shipped completely and reaches further than the old ban ever did (into backend computation and persistence); the permission half shipped not at all. Five weeks on, the net effect of a relaxation is a stricter ban.

**Replacement:** Permit a disclosed-basis band label carrying its metric, percentile and population denominator NOW — which 00:168 already independently requires and DESIGN.md:50 already calls legal. Reserve the fail-closed gate for the named lexicon only. DANGER ACCEPTED: a band label reads as more authoritative than its basis. STAYS VISIBLE: the disclosed basis travels with the label by construction; if it cannot be disclosed the label cannot be drawn.

### [NARROW] banned_standalone_words = elite, starter, depth, bust (frontend/src/shell/banned_vocabulary.json:36)

**Why:** 'Starter' and 'Depth' carry no verdict content — they are positional facts, and 00:209 names 'Superflex starter stability' as a core QB signal while David's RULING C creates 'Starter Strength'. A column header reading 'Starter' trips the linter. The contract test concedes this ('Accepted v1 tradeoff'). Meanwhile the frontend matches on exact whole node and the backend matches on \b anywhere in the string, so one artifact calling itself 'the single source of truth' gives opposite answers: 'depth chart' is explicitly asserted SAFE by the JS contract test and is SUPPRESSED by the Python one.

**Replacement:** Keep 'bust' (a pejorative with no calibrated meaning). Release 'starter', 'depth', 'elite' behind the disclosed-basis rule above. Share one matcher between the two enforcers or stop calling the file a single source of truth.

### [DROP] banned_fields = verdict, dynasty_tier, confidence, recommended_action, roster_action (banned_vocabulary.json:29-35)

**Why:** Verified against frontend/openapi.json: all five have ZERO occurrences. Not one exists in the API contract or the generated client, so this gate is structurally incapable of firing. The fields that DO exist and DO carry direction are absent from the list: favors (2), adjusted_favors (2), partner_score (3), cut_priority (3), sort_value (4), posture_label (3). This is one of three gates in a 264-line scanner with a 406-line contract test, aimed at a vocabulary that was retired. Separately, banning the bare name 'confidence' blocks the field you would naturally use for the honest interval that 00:268 mandates and DESIGN.md:58 calls the product's signature asset.

**Replacement:** Generate the field check from the live openapi.json field set so it can only name fields that actually exist, and seed it with the six directional names above.

### [ENFORCE_PROPERLY] Frontend banned-language scanner text extraction — StringLiteral || NoSubstitutionTemplateLiteral only (frontend/scripts/check-banned-language.mjs:138-143)

**Why:** Any template literal with a ${} substitution is invisible to the scanner, and interpolation is the normal React idiom for dynamic copy. `<p>Sell now</p>` trips; `` <p>{`Sell ${name} now`}</p> `` does not. HTML entities are never decoded, so `Sell&nbsp;now` also passes. The gate receiving the most engineering investment on this surface is green today with zero suppression markers anywhere in real source — it has never fired on production code, so these holes have never been tested by an actual violation.

**Replacement:** If the scanner is kept, handle TemplateExpression spans and decode entities. Better: move the check to serialized API responses, where the danger actually is.

### [ENFORCE_PROPERLY] banned_phrases — 25 fixed phrases (banned_vocabulary.json:2-28)

**Why:** Constitution 00:164 bans buy/sell/hold, keep/cut, must/do not, 'safe to', 'recommended'. The artifact bans 'buy now' and 'sell high' — none of the bare words. Executed against 17 unambiguous verdicts, exactly zero tripped. It cannot enforce the law it cites. It is also negation-blind in the other direction: 'This is not a confidence score', 'The model has no dynasty tier for this player', and 'Nothing here says you should accept this trade' all FAIL. The honest disclaimer is blocked and the verdict is not.

**Replacement:** Replace the phrase list with an imperative-mood check on serialized responses, and add the constitution's own bare words to whatever list survives.

### [ENFORCE_PROPERLY] POST /api/trade/analyze returns compute_delta_status() -> 'Likely_Favors_You' / 'Likely_Favors_Opponent' (app/services/trade_analyzer.py:229-232; app/api/routes/trade.py:83-86)

**Why:** The single largest No-Verdict violation in the product ships through the one endpoint with no DTO governance. Verified: /analyze is declared `-> dict` with no response_model, so it bypasses every extra='forbid' and recursive decision_supported invariant that governs the other routers, and delta_status has 0 occurrences in openapi.json because there is no schema for it to appear in. Neither scanner touches app/services/. A cross-language AST scanner checks that no surface says 'buy' while a live endpoint returns a directional trade verdict as an enum at the root.

**Replacement:** Give /analyze a response_model like every other route. Rename the field to a disclosed interval-overlap description ('intervals_overlap' / 'left_interval_above_right') or surface the two side intervals and let David read them. DANGER ACCEPTED: none — the arithmetic (interval overlap ratio) is honest and stays; only the verdict-shaped label goes.

### [ENFORCE_PROPERLY] DVS clamp to [0,100] (pvo_assembler.py:409,424; scoring/engine_a.py:113,217; trade_lab/draft_pick_valuation.py:47) vs 00-product-constitution.md:166 'Surface the arithmetic honestly, unclamped'

**Why:** Measured on the served artifact: 23 of 468 scored players sit at exactly 100.0. Because xVAR derives from the clamped DVS, ordering is destroyed at the top of every position — 11 tight ends all report xvar 2.85, 6 wide receivers all report 39.40, 5 running backs all report 58.05. The best player at a position and the eleventh are numerically indistinguishable, for exactly the players David most needs to tell apart. CORRECTION TO THE SWEEPS: the TE compression is caused mainly by the clamp, not the stale multiplier. TE replacement DVS is 95.6 against a ceiling of 100, so max TE xVAR is (100-95.6)x0.648 = 2.85; fixing the multiplier to 0.703 only moves it to 3.09. The clamp is the binding constraint. The corpus's response to discovering this was tests/contract/test_dvs_clamp_disclosure_red.py — a test that the clamp is DISCLOSED. There is no test that forbids it. A constitutional prohibition David ratified was met with a disclosure field instead of a fix.

**Replacement:** Remove the upper clamp; let DVS run above 100 and print the value. Keep the disclosure. DANGER ACCEPTED: a number above 100 looks odd on a 0-100 scale. STAYS VISIBLE: that is exactly the point — 00:166 says show wide ranges as wide ranges, and an out-of-band value is a legible signal that the P90 reference needs recomputing.

### [ENFORCE_PROPERLY] ENGINE_B_P90_PPG and XVAR_LAMBDA frozen at May 2026 values, recompute requires 'a new diagnostic run and David approval' (engine_b_contract.py:20-31, 44-59)

**Why:** A freeze with no drift detector is not a freeze, it is a slow silent failure. I recomputed P90 of avg_ppg_t1_t2 from the live app/data/training/engine_b_features_v2.csv (2,741 rows, identical on the training_eligible subset): QB 20.445 / RB 15.691 / WR 14.628 / TE 10.284, giving lambdas of QB 1.398, RB 1.073, WR 1.000, TE 0.703. Shipped: 1.386 / 1.083 / 1.000 / 0.648. The shipped multipliers reproduce the shipped P90s to three decimals — the arithmetic is honest and jointly stale. TE ships 7.8% low. Every test that touches XVAR_LAMBDA computes its expected value FROM the constant, so no test can ever detect this. The rule says recompute 'when the training distribution materially changes' and nothing anywhere measures whether it changed. AGENT_SYNC's own 2026-08-18 board records that PPG now includes postseason and 'P90/replacement/xVAR/calibration need rerun'. The trigger fired; nothing was listening.

**Replacement:** Keep the freeze on PUBLISHING. Add two cheap things: one test asserting XVAR_LAMBDA[pos] == round(P90[pos]/P90['WR'], 3), and a recompute-and-diff on every training assembly that REPORTS drift rather than requiring permission to measure. Gate the change, never the measurement.

### [RELOCATE] ENGINE_B_PROHIBITED_FEATURES — 19 Engine A pre-NFL columns banned from Engine B (engine_b_contract.py:250-258)

**Why:** None of these is a leakage danger — every one is strictly pre-NFL and strictly historical relative to season T. This is an ARCHITECTURE preference (keep the engines separable so the Bayesian blend stays interpretable) filed under leakage vocabulary and raised by a function called validate_no_prohibited_features. Because feature_validation.py intersects the prohibited set against ALL dataframe columns, you cannot even carry pick/round/draft_year as METADATA. So 'do Engine B residuals correlate with draft capital?' and 'does college dominator add signal for players with under 2 NFL seasons?' are un-runnable without editing product law — and the sanctioned answer, DVS_BLEND_K, is an assumed architecture that has never been measured.

**Replacement:** Move out of the leakage guard into a per-spec admissibility declaration that constrains the X matrix only. Columns ride in the artifact for diagnostics; an explicit experiment opts in. DANGER ACCEPTED: someone trains a production Engine B on draft capital. STAYS VISIBLE: the X-matrix declaration is the thing the training run records, so the artifact says which columns were fitted.

### [NARROW] AUTHORIZED_EVAL_FILES — src/dynasty_genius/eval/ may contain exactly 18 named .py files (tests/contract/test_subsystem_4_audit.py:114-132)

**Why:** A gradient-boosted-tree bakeoff against the Ridge baseline is an eval module by every structural criterion — it is exactly the shape of te_regularization_bakeoff.py, already on the list. Creating it fails a contract test on FILE CREATION, before it contains a line of logic. Nothing pins Ridge as the estimator and scikit-learn is already a dependency, so the rule that stops the experiment is not a modelling rule at all: it is a filesystem rule. PREDICTED BYPASS, and I would bet on it: the bakeoff is written as an uncommitted one-off, run once, numbers pasted into docs/agent-ledger/, deleted before closeout so the working-tree check passes. The comparison that decides whether the product's core estimator is right leaves no reproducible artifact.

**Replacement:** The allowlist governs what production may IMPORT from eval/ — the reverse-import guard at :448-473 already does that properly and is the real protection. Add a declared eval/experiments/ subdirectory excluded from the exact-set assertion and from the import guard.

### [NARROW] verify_closeout check_working_tree (no uncommitted paths) + check_ephemeral_locators (no /tmp, /Users/<name>/ path in the record), both ENFORCE tier, no waivers (scripts/verify_closeout.py:144-186)

**Why:** These two compose into the most damaging interaction in the audit and neither author could have seen it alone. There is NO gitignored scratch location — verified: driver-scratch/ exists at the repo root, is empty, is untracked and is NOT gitignored, so anything placed in it makes closeout dirty. So check_working_tree makes out-of-repo experimentation NECESSARY, and check_ephemeral_locators then makes it UNCITEABLE — its own docstring instructs the writer to 'describe the path instead of reproducing it', i.e. write a citation nobody can follow. The joint output is precisely the failure mode to fear: ungoverned work that LOOKS governed, appearing in a 10.6MB ledger in the same voice as gated work. The gate is also routinely red for unrelated reasons — the working tree carries 60 dirty paths right now — which is how a gate stops being read.

**Replacement:** Add one .gitignore line for a declared experiments/ or scratch/ path that check_working_tree ignores by name, and allow an explicitly-labelled external locator when the closeout also names what was promoted into the repo from it. A governed place to be messy is the cheapest anti-bypass mechanism available. DANGER ACCEPTED: scratch work is not reproducible. STAYS VISIBLE: it already isn't — this makes it visible instead of invisible.

### [NARROW] Mandatory bootstrap read — six governance documents plus AGENT_SYNC.md to the END CURRENT BOARD marker, before executing any command (AGENTS.md:41-72, CLAUDE.md:9-24)

**Why:** ~390KB, roughly 98K tokens, levied per session and identical whether the task is 'restructure the PVO' or 'try one extra column on TE'. 02-agent-operating-loop.md is 70KB of mostly PROCESS governance — cockpit lanes, closeout vocabulary, agent authority history — which David turned to near zero on 2026-08-18, and it remains the largest single mandatory read for a purely analytical task. Its enforcement is instructive: scripts/validate_governance.py runs in CI pinning ~30 EXACT PROSE STRINGS inside the markdown, so CI mechanically verifies the documents still SAY the right sentences and can never verify anyone read them. That also means rewording any pinned sentence for clarity turns CI red on the whole repo — the documents can only accrete, never be cleaned.

**Replacement:** Split the mandatory read by task type: a modelling experiment needs 00-constitution and the current board. Keep two or three prose pins with a named recurrence behind them and delete the other twenty-seven.

### [ENFORCE_PROPERLY] _PROMOTION_ABOVE_C_GATED_UNTIL_STEP_0_5 = True — no Engine A position may exceed model_grade C until app/data/pipeline/validation/composite.py ships (app/data/pipeline/train_models.py:153)

**Why:** The stated release condition has been met, in a different place, and nobody re-evaluated the flag. Verified: app/data/pipeline/validation/composite.py DOES NOT EXIST, while src/dynasty_genius/eval/composite_gate.py DOES, is on the eval allowlist, and is consumed by backtest_harness.py and republish_step05_trust_surface.py. So the ceiling is held against a path that will never be written while the implementation it waits for has been shipped and wired elsewhere for months. The live grader is now a sign test — `if r2<0 or spearman<0: 'D'; if r2>=0 and spearman>=0: 'C'` — so every position is permanently C or D, and two tests assert the ceiling stays down while none asserts it can ever come up. docs/validation-gates.md publishes a seven-component gate taxonomy; the shipped grader checks two signs.

**Replacement:** Point _model_grade at src/dynasty_genius/eval/composite_gate.py, or state plainly in validation-gates.md that grade is a sign test. Either is honest; the current state is neither.

### [ENFORCE_PROPERLY] CI_WIDTH_MAX = 0.30 per-fold Spearman BCa CI width (src/dynasty_genius/eval/composite_gate.py:19)

**Why:** It is a raw-n cutoff in disguise, and the spec's own section 10.1 says it was chosen to avoid being one. Measured on the live artifacts: every QB fold passes the ORIGINAL two-part rule at docs/validation-gates.md:125 (point >= 0.55 AND lower bound >= 0.40) — fold1 rho=0.678 lb=0.415, fold2 0.721/0.543, fold3 0.693/0.426, fold4 0.755/0.608. QB is demoted to PROVISIONAL solely because fold 3's CI is 0.413 wide on n=46. The rule change, not the evidence, demoted QB — the highest-stakes position in a Superflex league. And the excuse machinery inverts: TE fold 1 is rho=0.436 with lb=0.244 on n=206 — a large sample measuring genuine weakness — and it is excused as cold-start, so TE ships VALIDATED. The gate forgives a well-measured weak result and punishes a noisily-measured strong one.

**Replacement:** Restore the two-part criterion (point >= 0.55 AND BCa lower bound >= 0.40) and drop CI_WIDTH_MAX. The lower bound answers the question the gate is for and is scale-anchored. Under it, QB passes on its own evidence and TE fold 1 correctly fails on effect size without any excuse being invoked.

### [RELOCATE] decision_supported hard-locked to Literal[False] in ~40 DTOs, plus 15 mode='before' validators that silently coerce, plus ~8 publish-time verifiers

**Why:** Verified: 468/468 scored rows are False; no code path anywhere can produce True. A boolean whose True branch has never executed is not a guarantee, it is an untested decoration. Meanwhile WR has cleared every gate the system defines — g1, g2 AND g3 market superiority all pass, overall_grade ACTIVE_B_VALIDATED, model_status VALIDATED, leakage_clean, null coverage 1.0 — and the product cannot express that. Two compounding defects: (a) the 15 mode='before' validators run AHEAD of type validation, so a genuine bug setting True is SWALLOWED on those surfaces and RAISES on the other 40 — a no-verdict law whose enforcement suppresses its own violations; (b) the lock is absent exactly where the danger is. I constructed PlayerValueObject(..., decision_supported=True) successfully — the object whose own docstring says 'Every decision surface reads from this object' is typed plain `bool = False`, while internal ops dashboards nobody could mistake for advice are hard-locked four times each.

**Replacement:** Define ONE ordered claim_level in one module (the repo has four competing ladders today: model_grade, model_status, gate4 claim_level, decision_supported — QB simultaneously reports ACTIVE_B, PROVISIONAL and false). Derive decision_supported as a read-only projection, claim_level >= DECISION_GRADE. Delete the coercing validators and 7 of 8 verifiers. Put a real lock on PlayerValueObject and RosterAuditSignals. DANGER ACCEPTED: the claim becomes data-driven rather than compile-time. STAYS VISIBLE: that is the point — today the honesty guarantee is unfalsifiable because it has one possible value.

### [DROP] _safe_source_status collapses any status containing buy/sell/target/block/approve/reject/pass/fail to None (src/dynasty_genius/trade_lab/market_reconciler.py:693-707)

**Why:** 'pass', 'fail', 'block', 'approve', 'reject' are gate-status words, not normative verdicts, and no governance document bans any of them. The function's own docstring names the case: 'gates_passed' contains 'pass', so it collapses to None. Any honest degraded reason ('blocked_stale_market', 'rejected_low_coverage') is silently erased and the surface reports no reason at all. 00:166 requires the exact opposite: when inputs cannot be trusted, report unavailable or block. This rule deletes the report to satisfy a word list.

**Replacement:** Delete the function. If a normative claim is the worry, check whether the surface asserts an ACTION, and let status strings say what happened.

### [RELOCATE] MARKET_FEATURE_RE line-local scan over app/**/*feature*.py and src/**/*feature*.py (scripts/validate_governance.py:144-151, run in CI)

**Why:** Textbook theatre. I resolved the globs: they match exactly 5 files, all under src/dynasty_genius/features/. Every file where the per-position feature matrices actually live — models/engine_b_contract.py, models/engine_a_contract.py, scoring/engine_a.py, pvo_assembler.py — is OUT OF SCOPE. Within the 5 it scans, the regex \badp\b cannot match adp_sleeper because underscore is a word character, and any variable rename defeats it. Its only real effect is that an honest comment in a feature module explaining WHY ADP is excluded fails CI unless the author happens to put an incantation on the same line. Its existence is worse than neutral: it makes the market wall LOOK guarded at source level and buys false confidence.

**Replacement:** Delete it. The wall is genuinely enforced three other ways — the closed-world ENGINE_B_ALLOWED_FEATURES checked against real column lists at training time, the import-time source_registry role assertion, and the pre-commit validate_training_csv.py on actual CSV bytes. Those are dataflow checks; this is a word check.

### [DROP] MARKET_FIELD_PATTERNS in scripts/build_head_b_targets.py:99, docstring at :12 claims the ban is 'enforced by' it

**Why:** The purest theatre found and I confirmed it: the constant is defined and never used anywhere in the script. Its only consumer is tests/test_head_b_targets.py:195, which asserts that six string literals hand-written in the test body do not match market patterns — a test that cannot fail. It is also the FOURTH divergent copy of the market rule, and the only copy that catches fantasycalc and dynastynerds: someone hit the canonical regex's gap and patched it locally in a dead constant instead of fixing engine_a_contract.py:71.

**Replacement:** Delete the constant and the test; fold its patterns into the single canonical market token list.

### [ENFORCE_PROPERLY] PRODUCT.md:56 axe accessibility violations = 0 on shipped surfaces

**Why:** Fully built and simply not run. Verified: @axe-core/playwright 4.12.1 and @playwright/test 1.61.1 are installed, frontend/playwright.config.ts exists, and the visual:smoke script exists — but visual:smoke appears in neither the `gate` npm script nor .github/workflows/ci.yml. One of the two most concrete, most mechanically checkable product laws is the one nothing executes, while the hardest-to-check law (vocabulary) gets a cross-language AST scanner in CI.

**Replacement:** Add `npm run visual:smoke` to the gate script. One line.

### [ENFORCE_PROPERLY] docs/validation-gates.md:80,118,174,181 — phases 0, 3, 8, 9 close when test_no_unvalidated_in_production.py, test_no_silent_substitution.py, test_ratchet.py and test_ktc_not_in_features.py pass

**Why:** Verified by repo-wide find: all four filenames return zero hits — not renamed, not moved, never written. Only test_pvo_schema.py is real. These four are cited as the mechanical gates keeping unvalidated cards out of production, keeping silent source substitution out of ingestion, keeping removed fields removed, and keeping KTC out of features — three of the four doctrines that genuinely matter. A reader of the most authority-carrying validation document in the repo would reasonably conclude four gates stand where none do.

**Replacement:** Write the four tests or delete the four names. A dead law teaches agents that laws are optional.

### [ENFORCE_PROPERLY] train_te_deployment_model reports in-sample metrics and hardcodes promotion_warranted: None (scripts/train_engine_b.py:121-176)

**Why:** Not a governance rule — an enforcement hole sitting directly beneath the heaviest enforcement in the repo, and it belongs in this report because it is the same failure. Trace it: :143 calls _fit_position_ridge(train_df, features, alpha) which fits on train_df and returns that same X; :145 does model.predict(X) on it. The shipped TE artifact's metrics_model and metrics_baseline are BOTH in-sample, and :171 hardcodes promotion_warranted: None so the >=2-of-3 composite gate governing every other position is skipped entirely for TE. The v2_stratified path at :264-274 does it correctly. So the TE feature LIST is defended by five mechanical guards — exact-equality contract test, closed-world allowlist, leakage validator, prohibited-feature validator, position-contract validator — while the number saying whether the model is any good is computed on its own training rows and no gate reads it. And it is the same position whose scarcity multiplier ships 7.8% low.

**Replacement:** Hold out HOLDOUT_SEASONS as the v2_stratified path already does, and call _gate().

### [NARROW] PRODUCT.md:46 no system-nominated single-player hero (the banned MoverHero pattern)

**Why:** The rule conflates EMPHASIS with ADVICE, and it blocks the single most useful thing a daily-login product can say. David's stated daily context is 'the morning check of what changed overnight'; 'the largest absolute model-value change in the last 24h was X, +N' is a disclosed, reproducible arithmetic fact about the model's own output — the exact shape the 2026-08-20 xVAR narrowing declared legitimate. It ranks no action. Forbidding it does not remove the judgement, it relocates it into David scanning 468 rows by eye with worse recall and no receipt. It is also enforced by nobody: grep for MoverHero across frontend/src, src, app and tests returns only the two doc mentions, and a lexical scanner cannot see a structural nomination anyway.

**Replacement:** A system-nominated hero must state the disclosed metric and window that selected it, must be lane-symmetric (a model mover AND a market mover, never market-only), and must carry no action verb. DANGER ACCEPTED: emphasis is persuasive. STAYS VISIBLE: the selecting metric is printed on the card, so David can always ask 'why this player' and read the answer.

### [ENFORCE_PROPERLY] PartnerRankings renders partner_score to 3 decimals as 'the who-to-target context' (frontend/src/league-pulse/PartnerRankings.tsx:5-6,39-41)

**Why:** This is the asymmetry that proves the point. Under the narrowed xVAR rule — a composite describing a PLAYER is legitimate, ranking ACTIONS by a scalar is not — this is the illegitimate case: a descending list of trade counterparties ordered by a single composite scalar whose DTO forcibly stamps market_influenced=True because divergence_density_score is market-derived. It passes every gate, because 'rank' is not a banned word, 'partner_score' is not a banned field, and the file is not in the cordon's pinned list. Cross-positional xVAR — a single-lane disclosed composite describing a player, touching no market — was interrogated under the letter of the law. A market-influenced composite ranking ACTIONS ships with a source comment calling it 'who-to-target'.

**Replacement:** Not necessarily delete it — a Superflex manager genuinely needs to know who to talk to, and the components ARE disclosed and market influence IS labelled. Decide it on the merits and write the decision down. The point is that the law never looked.

### [NARROW] cut_priority = 1..N surfaced on the David-facing What-Changed DTO (roster_cut_engine.py:375; league_what_changed_models.py:384-390)

**Why:** Same law, same repo, two answers. LeaguePulseCapacityCandidatePool went to real trouble to avoid this — it drops cut_priority and substitutes capacity_conflict_status with a docstring explaining it 'never selects one'. The What-Changed DTO exposes cut_priority unchanged, 3 occurrences in openapi.json. The engine's ordering is defensible and disclosed (ascending xVAR percentile within data-availability tier). The word 'priority' is not.

**Replacement:** Rename to capacity_order. This is the mirror image of the xVAR case: an honest ordering carrying a normative name, where the fix is a rename, not a ban.

### [NARROW] scan_league_opportunity_no_verdict.py — any identifier containing 'opportunity_score', 'recommend', 'tool_nominated', or an ALL-CAPS 'CANDIDATE' (scripts/scan_league_opportunity_no_verdict.py:44-127)

**Why:** Two problems. 'Weighted opportunity' is a constitutionally REQUIRED Engine B feature class (00:216, 01:217), so a mandated football metric cannot be named after itself on ten pinned files including model-side producer code. And the scanner's own docstring claims the cordon is 'FULLY ENFORCING across the entire live surface' when it is pinned to exactly 10 files — a false claim restated in AGENT_SYNC and 04:67. Widening it, the obvious next 'improvement', would immediately outlaw the vocabulary of modelling: candidate feature sets, candidate model heads, bakeoff candidates, identity-match candidates, the standard model-card 'Recommendations' heading — and would fail on every docstring that PLEDGES compliance and on the enforcement code itself.

**Replacement:** Narrow to David-FACING field names — keys present in frontend/openapi.json — not identifiers in Python source. Apply the discipline the same file already gets right elsewhere, where it distinguishes drop_candidate (an action) from cut_candidates (a descriptive pool). And correct the docstring.

### [NARROW] DESIGN.md:60-66 — two independent unanchored fresh-agent visual audits at mean >= 8/10, no dimension < 7, zero P0/P1, plus a mandatory pre-code composition artifact, before any surface ships

**Why:** A four-artifact tax on every surface change including small ones, on the layer David most wants to be exceptional. The corpus has no proportionality carve-out here, while 05-layer-doctrine.md:151-153 explicitly has one and states the reason: 'a rule that demands ceremony from trivial work decays into a box-tick, which is the same death as a poster on a wall.'

**Replacement:** Keep the standard and the unanchored-fresh-agent instrument — the bar is David's and the instrument genuinely resists rubber-stamping. Narrow the trigger: full double-audit for a new surface or a material visual-direction change; a single diff-scoped check for an increment on an already-passed surface. Import 05's proportionality sentence verbatim.

### [NARROW] DESIGN.md:21,37 — no green/red anywhere, no verdict hues

**Why:** Verified: frontend/src/styles/tokens.css defines --dg-model, --dg-market, --dg-caveat, --dg-cliff, --dg-pos-* and NO directional token at all. A +2.3% and a -2.3% render in identical ink, distinguished only by a glyph, on a 32px row at 0.8125rem, in a product whose entire daily job is 'what changed overnight'. DESIGN.md itself concedes the distinction — 'Direction is data (signed, neutral), not judgment' — then bans the encoding that makes direction legible at a glance. The danger is semantic (hue meaning ACTION), not chromatic.

**Replacement:** No hue may encode a recommended action; a hue may encode the sign of a measured delta provided sign and glyph redundantly carry the same information. Use the CVD-safe blue/orange divergent pair, not red/green. DANGER ACCEPTED: any two-colour split invites a buy/sell reading. STAYS VISIBLE: the number and its sign are printed next to the colour, so the colour is never the only carrier.

### [DROP] 00-product-constitution.md:83 — default evidence weighting is 65% quantitative, 35% qualitative

**Why:** Asserted with no rationale, no derivation and no provenance; verified unenforced — no such weight exists in src/, app/ or tests/. It is not David-attributed and traces to an AI-authored source document. It reads as a binding quantitative mandate and is a qualitative posture. The risk is the reverse of blocking: a future agent implements the literal number and defends it by citing the constitution — which is precisely the unearned precision the same document bans elsewhere.

**Replacement:** 'Quantitative evidence leads; qualitative signal is admitted only when verifiable and only when it explains something the box score cannot.' Keep the qualitative guardrails at 00:87-94, which do all the actual work.

### [NARROW] 00-product-constitution.md:131 'Frontend polish comes last' + the twelve-step Phase Sequence gate (01:335-352)

**Why:** Flatly contradicted by later ratified law: PRODUCT.md:28 names the failure mode to kill as 'an honest developer diagnostics console wearing a fantasy skin' and DESIGN.md:66 sets a 'truly exceptional' bar per David's standing directive. An agent reading 00 in the mandated bootstrap order reaches 'polish comes last' BEFORE it reaches PRODUCT.md and can legitimately cite it to defer visual work indefinitely. The Phase Sequence is already a dead letter — market overlay (phase 10) and frontend (phase 12) have shipped while the backtest harness (phase 11) has not, and nobody logged the exception 01:352 requires.

**Replacement:** Keep 'no surface implies decision-grade confidence before validation justifies it' — that is the real rule. Drop the sequencing half and the Phase Sequence gate. A rule the whole team has quietly stepped over is worse than no rule.

### [NARROW] CLAUDE.md:34-46 and AGENTS.md:123-135 — 'The study has not run. There is no result.' (H2 QB rushing)

**Why:** The rule's CONCLUSION still holds — H2 remains under test until David rules on the registered result. But its stated PREMISE is now false: docs/agent-ledger/2026-08-17.md records dg-autonomy finishing READY_FOR_GATE with all five receipts passed and David's reproducibility condition satisfied. Both bootstrap files still say the study has not run, and every agent reads them first, every session, in the mandated order. A standing rule whose factual premise is stale is exactly how a false claim reaches David in good faith — which the memory record shows has already happened once on a different stale line.

**Replacement:** Restate on the true premise — 'executed; awaiting David's ruling on the registered result' — without weakening a single one of the five clauses. Adopt the general habit: when a ruling supersedes constitutional text, amend the text in the same session.

### [RELOCATE] 05-layer-doctrine.md attribution discipline (section 1 is David verbatim; section 2 onward is agent codification pending ratification and may not be cited as law or used to block work)

**Why:** This is the single most valuable governance idea in the repo and it is applied in exactly one file. 00-product-constitution.md carries [David-ratified] stamps on four bullets and nothing on the other forty, and its declared source document reads as AI-authored framework prose — so the highest-authority document in the corpus is agent codification of an AI document with four ratified islands, presented uniformly as binding doctrine. 01, 02 and 03 are wholly agent-authored with no attribution field at all; 04 is explicitly 'DRAFT pending David authorization' and is cited as if standing.

**Replacement:** Do not weaken the rule — propagate it. Put 05's section-scoped attribution header on 00, 01, 02, 03 and 04. That one change tells every future reader which rules the crew may narrow on its own and which need David — precisely the question this audit had to reconstruct by hand.

### [NARROW] 00-product-constitution.md:276-291 standing non-goals — 'mock draft simulator' and 'mobile app'

**Why:** Ten of the twelve are obviously correct and cost nothing. Two have been overtaken by David's own later rulings and the constitution was never updated: RULING F asks for a contention-window analysis 'almost like a scenario builder or a simulator', and PRODUCT.md:51 / DESIGN.md:43 make mobile a first-class layout. A literal reader can cite the constitution to refuse work David has since asked for.

**Replacement:** 'A public or generic mock-draft product' and 'a native mobile application'. Keep the other ten.

### [NARROW] 01-north-star-architecture.md:305-315 banned output patterns — 'trade side totals before validated uncertainty bands' and 'confidence'

**Why:** The side-totals clause is a conditional ban whose condition can never clear: verified, there is no uncertainty band anywhere in the shipped product and nothing is building one. A permanently-blocking clause is written as a temporary one. And the entry says 'confidence mapped from pick bucket' while what propagated into banned_vocabulary.json's banned_fields is the bare word — so the frontend linter inherited a broader ban than the constitution wrote, and it now blocks the honest interval.

**Replacement:** Keep the four specific historical defects — they name real regressions and are precisely scoped. Narrow the confidence entry back to 'mapped from pick bucket'. Either build the uncertainty bands or convert the side-totals clause into a plain prohibition so it stops pretending to be temporary.

### [ENFORCE_PROPERLY] 00-product-constitution.md:264 'Every strong recommendation must include a real counter-argument' and :268 'Use confidence ranges'

**Why:** Both are MUSTs in the highest-authority document with zero enforcement, and both are the highest-value UNBUILT items in the audit. Measured on the shipped artifact: counter_argument present on 254 of 468 scored players (54%), no gate, no coverage floor, no caveat saying it is missing. And there is no uncertainty anywhere — the valuation object's twelve keys contain not one interval, sigma, CI, lower or upper field on any of 468 rows, and projection_3y is null on all 468. DESIGN.md:58 names the per-row sigma bar as the product's signature differentiator against Sleeper, DynastyNerds and KTC; it does not exist. The corpus banned the word for false certainty and never built the mechanism for honest uncertainty.

**Replacement:** Wire a counter_argument coverage floor into the PVO batch ready-gate — universe_pvo_batch.py:248 already computes recursive counters, the machinery is right there. And build the interval: it is mandated, it is the stated differentiator, and it is what would let 'confidence' be released as an honest word.

### [RELOCATE] Head B MARKET_PROHIBITED_COLUMNS = nfl_yards, nfl_tds, nfl_targets, nfl_carries, nfl_receptions, nfl_air_yards, nfl_yprr, raised as 'a prohibited market-overlay column' (head_b_contract.py:77-82, 277-280)

**Why:** The constant name and the error message both state something false — none of these is market data, they are NFL production, i.e. the outcome side for a pre-NFL model. The intended rule is 'Head B is pre-NFL and may not see NFL production.' The lie has a cost beyond tidiness: because the ban is filed under 'market', the actually-dangerous columns of the same class were never enumerated. The outcome columns sitting in the very CSV Head B trains from — y2_points, y3_points, total_points, y24_ppg, best3of4_ppg and residual_ppg, which IS Head B's own target — are all admissible as features. The guard bans seven names that exist nowhere in the repo while the real target column passes one row away.

**Replacement:** Keep the market names in the single shared market set. Create an explicit pre-NFL-only admissibility rule seeded from the outcome columns that actually exist in the frame.

### [NARROW] Head B draft-capital regex ^expected_|^curve_|^round_|^pick_ (head_b_contract.py:65-73)

**Why:** The ^expected_ clause bans the whole modern football-analytics vocabulary, all pre-NFL-safe and none of it draft capital: expected_points_added, expected_completion_pct, expected_yards_after_catch, expected_dominator. DG already ingests this family — engine_b_contract lists ppa and wepa, CFBD predicted points added — so naming the same quantity expected_points_added makes it draft capital. The clause exists to catch one target-side column, expected_ppg_at_pick, which HEAD_B_PROHIBITED_COLUMNS already names explicitly. Meanwhile draft_position, selection_number, overall_selection, projected_pick, first_round_flag, big_board_rank, consensus_board and mock_draft_avg all pass — the last four are pre-draft consensus proxies that would contaminate Head B's orthogonality just as badly as the pick number.

**Replacement:** Drop ^expected_ and ^curve_, keep the enumerated names, and add a numeric orthogonality check — correlation of the fitted Head B feature matrix against nfl_pick. That is the property actually being claimed, and no name scanner can establish it.

### [NARROW] qb_rookie_risk_filter accepts exactly four input columns, anything else rejected as 'NFL usage / non-pre-NFL columns ... leakage' (features/qb_rookie_risk_filter.py:27,146-154)

**Why:** The strongest cost-to-benefit inversion in the sweep, and the guard's benefit is smaller than it looks. It rejects height, ras_composite, college_ypa, early_declare and season — every one pre-NFL — and reports each as NFL-usage leakage, which is factually false for all five. Meanwhile classify_rookie_qb_risk branches on draft_number ALONE; age_at_entry is required, type-validated, echoed into the output and never influences any classification. The whitelist MANDATES a column the model ignores while FORBIDDING every column that might improve it, and blocks the ablation that would show which.

**Replacement:** Replace the whitelist with a denylist of NFL-usage provenance or a source-tagged admissibility check. Keep the fail-closed behaviour. Fix the message so a rejection names what was actually wrong.

### [ENFORCE_PROPERLY] 01-north-star-architecture.md:140-159 — every computed feature must carry source, source timestamp, parser version, metric version and completeness flags

**Why:** Verified against the substrate: app/data/training/engine_b_features_v2.csv carries 33 columns and NOT ONE of source, source_timestamp, parser_version or metric_version. prospects_with_outcomes_v3.csv (Engine A) DOES carry per-field provenance. So the MUST is satisfied on the engine that scores rookies and unsatisfied on the engine that scores every player David actually trades. This is the missing substrate for a real provenance-based leakage guard — fixing this rule is what would let the market rule be enforced on SUBSTANCE instead of on column-name spelling.

**Replacement:** Add provenance columns to the Engine B assembly. Then re-express the market rule as 'every training column resolves to a registry source whose roles include model_input' — strictly stricter than the regex, and it stops blocking honestly-named non-market columns.

### [NARROW] scripts/validate_governance.py:76-135 — CI fails unless ~30 exact prose sentences appear verbatim in 00, 02, 05, GEMINI.md, PRODUCT.md and DESIGN.md

**Why:** The misdirection pattern at its clearest. CI will block a change that improves a sentence in DESIGN.md and will pass a change shipping a tight-end multiplier that values every TE 7.8% low. It enforces the PRESENCE OF WORDS ABOUT rules and can never enforce a rule. The pins also make the documents brittle to their own amendment process: a ratified change to a pinned sentence turns main red unless a code change lands in the same commit, so the docs carrying the product's thinking can only accrete, never be cleaned.

**Replacement:** Keep the two or three pins with a named recurrence behind them — the 05 pending-ratification boundary, the KTC overlay-only sentence. Delete the rest.

### [NARROW] TE Engine B feature set pinned by exact set equality (tests/test_engine_b_contract.py:228-231) and ENGINE_B_OUTPUT_COLUMNS pinned as an exact ordered list (tests/contract/test_feature_engineering_extraction.py:267)

**Why:** To fit ONE Ridge with one extra column, an experimenter must edit the frozen contract AND rewrite the test that asserts the contract is frozen — a promotion-shaped edit to answer a question that is not yet a promotion. The honest experimenter refuses, so the cheap correct-feeling move is to copy the assembled CSV outside the repo and fit sklearn by hand. PREDICTED BYPASS: pandas.read_csv on the assembled Engine B dataset in a scratch directory, Ridge fitted by hand, result reported in prose in docs/agent-ledger/ — ungoverned, but written in the same voice as gated work. The column pin is worse still: it forbids even LOOKING, so every exploratory feature must be recomputed by hand outside the only machinery that knows how to build a leakage-correct T/T-1/T-2 frame with the outcome joined at T+1. The rule intended to protect data integrity actively relocates feature construction to the least safe place in the system.

**Replacement:** Keep exact-equality on what the DEPLOYED artifact trains on; give the measurement path an explicit candidate-set parameter. Make the pinned tuple a required SUBSET plus a declared dx_ prefix namespace that the publisher strips before writing runtime. One parameter and one prefix separate 'measure' from 'promote' and remove the incentive to edit the guard.

### [NARROW] ENGINE_B feature contract sets are all-or-nothing REQUIRED (engine_b_contract.py:336-342)

**Why:** The repo wrote its own confession at engine_b_contract.py:182-206: adding NGS features to the required sets broke the QB-1 walk-forward and TE deployment training, so a SECOND parallel optional mapping was built beside the contract rather than inside it — and the relocation is incomplete. train_engine_b.py:257 wires optional features into the research path, but train_te_deployment_model at :127 reads sorted(ENGINE_B_FEATURES_BY_POSITION['TE']) and never calls optional_features_present. The shipped TE model therefore receives zero NGS features. The workaround built to unblock the experiment does not reach the artifact David actually uses.

**Replacement:** A three-way contract — required / optional / forbidden — inside the single mapping, so the escape hatch cannot drift out of sync with the deployment path.

### [NARROW] tests/test_source_registry.py:22-34 — SOURCE_REGISTRY must contain exactly 21 named sources

**Why:** It cannot tell 'a new market-adjacent feature source' from 'a new read-only study source'. An analyst-sentiment feed cannot be registered even as validation_study — a role that by construction can never reach a model — without editing the pin, and then docs/data-source-contracts.md:27-50 demands a full four-method production adapter with provenance columns and a cadence registration before you can compute a single lead-lag correlation. That is disproportionate by an order of magnitude, and the bypass discards the ONE thing here genuinely worth protecting: the pre-registration seal, which gets thrown out because it is bundled with adapter ceremony that has nothing to do with inferential honesty.

**Replacement:** Make adapter-contract weight proportional to role. A validation_study-only source needs a named provenance record and a frozen input snapshot — not fetch_automated, not ingest_manual_export, not a freshness report. Keep pre-registration mandatory and make it cheap enough to survive.

### [NARROW] verify_sprint_closeout ENFORCE — full Python suite (6,287 tests) plus npm ci before any push

**Why:** Right for a LANDING, wrong for an ITERATION, and it does not distinguish them. For an experiment whose whole point is trying five variants of one feature, this is the per-iteration cost. It compounds with the working-tree rule: because there is no sanctioned scratch lane, an experimenter iterating in-repo pays a full-suite run per loop while one working outside pays nothing and is also invisible. The gate's cost lands entirely on the compliant path.

**Replacement:** Full suite gates landing and push. A declared experiments lane runs the contract subset per iteration — tests/contract/ plus the leakage and market-wall tests. That keeps the guards that matter for an experiment on every loop and defers the frontend-and-ops tail to when it is relevant.

### [NARROW] RULING A pick-value floor max(0.0, ...) (draft_pick_valuation.py:47; team_value_matrix.py:131)

**Why:** David is right about the economics — a pick's worth is the MAX of three always-available options and today's curve, built solely from realized production, cannot price optionality. But the clamp is the wrong instrument for that truth: it deletes the information instead of labelling it, and it is in direct textual conflict with 00:166. It also floors negative xVAR to zero in team aggregates, erasing genuine roster liabilities from every team-strength comparison. This is a real constitution-vs-ruling conflict that 00:293-296 says must be logged rather than silently resolved.

**Replacement:** The constitution's own remedy at 00:166 is better: report negative-computing picks as UNPRICED with the reason (optionality not modelled), not as 0.0 — which is itself a confident tidy number that reads as a verdict. DANGER ACCEPTED: David sees 'unpriced' where he used to see a number. STAYS VISIBLE: the reason travels with the label, which is more than 0.0 ever told him.

### [NARROW] 02-agent-operating-loop.md:397 'Inseparable guardrail' — trend data never folded into a buy/sell OR a composite score

**Why:** The clause bundles two very different prohibitions under one 'or'. 'Never folded into a buy/sell' is correct. 'Never folded into a composite score' is over-broad and already falsified by the shipped product — this is the sentence that made cross-positional xVAR illegal on paper while it ran in production, and it equally bans summarising a realized-outcome track record into a single calibration number, which is the only way to ever answer 'does the model beat the market?'. Note the attribution: David's contribution to this section is the three compounding questions; the guardrail paragraph is agent-authored.

**Replacement:** Apply the 2026-08-20 xVAR narrowing here too, since this is the sentence that actually does the banning while 00:168 only requires disclosure: a composite of one lane's own outputs with disclosed construction and a stated interval, describing a PLAYER or a MODEL'S TRACK RECORD, is legitimate; ranking ACTIONS by any scalar is not.

### [NARROW] qb_validation/guards.py:40-55 — buy/sell/hold/verdict/recommended/keep/cut banned in any key OR string value of a validation report

**Why:** Right rule, wrong surface. The recursive decision_supported check in the same function is the strongest 'no unearned claim' enforcement in the repo and should not change. But the lexicon half blocks the honest scientific vocabulary of the artifact it guards: a validation report cannot say 'the promotion gate verdict is FAIL', cannot describe a holdout decision, cannot carry the standard model-card 'Recommendations' section that eval/model_card.py:98 already has. The constitution is explicit that the No-Verdict Line 'governs running-software outputs' and 'does not restrict design specs, roadmap plans, or strategy briefs' — a validation study is exactly the class of artifact it exempts.

**Replacement:** Keep the decision_supported recursion and the field-NAME scan. Drop the scan over string VALUES so the study can describe its own method.

### [DROP] DESIGN.md:26 — exact Sleeper position hexes may not enter the token spec without direct screenshot sampling and Codex cross-review

**Why:** The ceremony is attached to a preference David already stated in words, and while it stands a known-wrong palette ships. Verified in frontend/src/styles/tokens.css:37-40: QB is hue 300 (purple) where the doc says pink/red, WR is hue 340 (pink) where the doc says blue, TE is hue 205 (cyan) where the doc says orange. The cost of a slightly-off hue is that a chip is a slightly different pink; the cost of the gate is that the chips are the wrong colours entirely and have been for weeks.

**Replacement:** Drop the gate. Keep the note that these are approximations of Sleeper's family, and set them from the stated preference now.

### [NARROW] league_opportunity_map / universe_market_divergence no_imperative_language exit criterion (banning buy, sell, target, fade)

**Why:** Simultaneously too broad in vocabulary and structurally unable to fire — the worst combination. It bans 'target', the single most important receiving metric in the sport, by plain substring, so target_share would trip it. And it cannot currently fire because the scanned language_surface is narrowed to closed enums containing none of the four words: it is a substring test of a constant against a constant. The recorded banned_language_present: [] in every shipped artifact therefore reads as evidence of cleanliness that was never tested. Alongside it, phase17-5 exit criteria assert two hardcoded Python `True` literals — a criterion that cannot fail, persisted in shipped artifacts as a governance guarantee David can read.

**Replacement:** Drop 'target' and 'fade', scan the real payload, and delete the two hardcoded-True criteria. A false receipt is worse than an absent one because it occupies the slot where a real check would go.


---

## RULES THAT EARN THEIR KEEP (13)

- Closed-world ENGINE_B_ALLOWED_FEATURES checked against real column lists at training time (engine_b_contract.py:126-146, 312-342) — the mechanism that actually makes 'do we beat the market?' answerable. Closed-world beats denylist because a denylist can never enumerate future column names.
- Import-time source-registry assertion: no model_input source may list a PROHIBITED_COLUMN (source_registry.py:462-469). Nine lines, structural rather than lexical, fails at import so it cannot be skipped, unbypassable without deliberately editing the registry. The strongest enforcement of the most important law, with no CI step and no ceremony. This is the template.
- Pre-commit validate_training_csv.py on actual training-CSV bytes (.pre-commit-config.yaml:14-21) — fires on the artifact where the danger lives, at the moment it is introduced, checking which columns are PRESENT rather than which words appear. Point it at the files that are not gitignored and it becomes the whole market wall.
- OUTCOME_SEASON_COLUMNS exact set — ppg_t1/ppg_t2/games_t1/games_t2 may never be features (engine_b_contract.py:16, checked at :286). Exact, enumerated, zero false-positive surface, guards the highest-consequence defect in the system.
- Temporal-leakage name scanner on Engine B (engine_b_contract.py:268-297), wired at six real call sites and failing loud. Cheap tripwire — but understand its residual honestly: it is a NAME check, `ppg_t_plus_1` passes it, and no value-level temporal check exists anywhere in the repo.
- Hard safety floors in the composite gate: leakage_clean must be True and null_coverage >= 0.90, fail-closed, dominating everything else (composite_gate.py:20, 126-135). Ordered correctly, auditable denominator, ~10 lines. R2_FLOOR = 0.0 belongs here too — 'beats a naive mean' is a floor with an actual meaning.
- Silent substitution forbidden; unresolved identity rows rejected to triage; 26-hour staleness law; the fail-closed 503 / capture-health machinery (01:85, 126-138). Genuinely running, and the point-in-time capture databases are being written daily. The append-only archive you call the moat is the one place where doctrine and the running system agree completely.
- Morning-tape route 503s unless decision_supported is structurally False at root, row and nested bundle (morning_tape.py:65-95). A fail-closed guard on a real danger, at the serve layer where the claim actually reaches you, checking structure rather than vocabulary. This is what the banned-language scanner would look like if it were aimed correctly.
- The favors / adjusted_favors render guard (frontend/src/trade/favors_guard.test.jsx) — the one mechanism in the whole corpus aimed at the right target: an assertion on RENDERED OUTPUT for a field that actually exists in openapi.json and actually carries direction. Widen this pattern; shrink the vocabulary scanner.
- No binary age cliff in predictive models; hardcoded cliff ages are display warnings only (00:100-111). Right rule, right rationale, correctly separates display layer from model layer, cheap to honour.
- 'The model is the anchor' — no in-season auto-adjustment; promotion is human-gated and pre-registered (00:150). The best-argued rule in the corpus, and the only one with the right SHAPE: it explicitly permits in-season monitors to detect, report, alert and queue candidate changes, so it gates PROMOTION without blocking EXPERIMENTATION. Use it as the template for narrowing everything else.
- The 05-layer-doctrine attribution rule (section 1 David verbatim, section 2 onward agent codification pending ratification, not citable as law). Do not weaken it — propagate it to 00 through 04.
- The codex_audit SQL workflow (.github/workflows/codex_audit.yml:27-95) — deliberately non-blocking, exits 1 today, and its own comment forbids citing a green run as evidence, recording that a previous version reported 'passed for 0 SQL files' daily for months. This is the healthy shape for a check that is not yet a gate. Every unenforced rule should either become this honest or become real.

---

## CHALLENGE 1: GUARDIAN — where loosening produces a false claim

**Verdict:** MIXED

# GUARDIAN REVIEW — where the loosening produces a false claim

I re-ran the load-bearing numbers against the live repo with `.venv/bin/python3.14`. Roughly two-thirds of the recommended loosenings are safe or overdue. Four are dangerous. One is dangerous *and* delivers none of its stated benefit, and that is the one to refuse.

---

## THE SINGLE MOST-LIKELY-REGRETTED LOOSENING

**Dropping `CI_WIDTH_MAX` from the composite gate (`src/dynasty_genius/eval/composite_gate.py:19`).**

The adjudication's case is that CI width is a precision requirement masquerading as an effect-size requirement, that restoring the two-part Spearman rule promotes QB on its own evidence, and that TE fold 1 would then "correctly fail on effect size without any excuse being invoked."

I read the shipped artifacts under `app/data/backtest/trust_surface/latest/`. **Both halves of that claim are false.**

### The claimed benefit does not exist

TE fold 1: ρ = 0.436, BCa lower bound 0.244, CI width 0.344, n_test = 206. It fails the rank gate, the proposed lower-bound gate, and the CI gate — all three. But `backtest_result_TE.json` records `cold_start_fold_index: 1` and `cold_start_tolerated: true`, and fold 1 is uniquely min-`test_year` (2020) and uniquely min-train (237), so `identify_cold_start_fold` grants the excuse mechanically. `effective_rank_gate_pass` then passes it, and TE already ships `model_status: VALIDATED` **today, with fold 1 failing both gates**.

Restoring the lower bound does not change this. The lower bound lives inside the rank gate, and the rank gate is exactly what the cold-start clause excuses. **TE ships VALIDATED before the change and VALIDATED after it.** The stated benefit is zero.

### The cost is a false claim on the position that matters most

QB's `promotion_gate` block reads `failed_ci_folds: [1, 3]`, `cold_start_fold_index: 1`. Fold 1 is excused; fold 3 (width 0.413, not cold-start) is the sole reason QB is `PROVISIONAL`. Delete `CI_WIDTH_MAX` and `failed_ci_folds` empties — QB flips to `VALIDATED`.

Here is what QB would be certifying:

| Fold | n_test | ρ | r²_oos | nDCG diff vs market |
|---|---|---|---|---|
| 1 | 43 | 0.678 | **0.141** (`metric_caveats: ["r2_oos_small_sample"]`) | **−0.052** |
| 2 | 46 | 0.721 | 0.298 | **−0.041** |
| 3 | 46 | 0.693 | 0.287 | +0.001 |
| 4 | 49 | 0.755 | 0.286 | **−0.005** |

`g3_market_superiority_pass: false`. `promotion_justification: "Promotion blocked by G3."` **The QB model loses to `dynastyprocess_ecr_2qb` on three of four folds.**

And `compute_model_status`'s own docstring says: *"Pure: no I/O, no market/G3 coupling. G3 market-superiority never enters here."* So the promotion would put QB in exactly the state TE occupies right now — `overall_grade: ACTIVE_B` ("blocked by G3") sitting beside `model_status: VALIDATED` — for the position where Superflex makes every roster decision.

**The concrete false claim:** David opens the Trust Surface, sees QB marked VALIDATED for the first time, and reads it as "the QB model is good enough to lean on." The evidence underneath is ~46 quarterbacks per fold, an r² of 0.14 on the earliest fold with the model's own caveat attached, and a model that ranks QBs *worse than the free consensus ECR* on three folds out of four. **The one thing the brief names as non-negotiable — not claiming a decision is supported when no evidence supports it — is breached directly, by deleting the only gate currently preventing it.**

CI width at n≈46 is not theatre here. It is the only thing in the gate that notices QB's sample is thin. The lower bound does not substitute for it: QB's lower bounds are 0.415/0.543/0.426/0.608 — all pass — precisely because a wide interval on a high point estimate can still clear a lower-bound floor. The two criteria fail in opposite regimes, which is why keeping both is not redundancy.

**Verdict: refuse. If the excuse machinery is genuinely inverted, the defect is `identify_cold_start_fold` granting TE a pass on n=206 — a fold that is "cold start" by year and train-length but not by sample size. Fix that. Do not delete the gate that is holding QB honest.**

---

## ALSO DANGEROUS

### 2. Narrowing `LEAKAGE_REGEX` — the cheap half of this lands and opens the wall

The adjudication tested the regex **in isolation** and reported the result as the wall's behaviour. I ran the actual guard — `_violations_in_header` in `scripts/validate_training_csv.py`, which is what the pre-commit hook executes:

- `fantasycalc_value` — **blocked** (in `PROHIBITED_COLUMNS`). Reported as passing.
- `dynastydatalab_adp` — **blocked** (in `PROHIBITED_COLUMNS`). Reported as passing.
- `market_share_yds` — the repo column is `wr_market_share_yds`, which already passes. The false positive is hypothetical.
- `value_over_replacement` — never appears as a training column in any of the 8 CSVs. Also hypothetical.

What is *not* hypothetical: `validate_training_csv.py:57` uses `_LEAKAGE_RE.search`, on the **shared** `LEAKAGE_REGEX` constant, in the pre-commit hook the KEEP list calls "the whole market wall." I simulated the recommended edit (delete `^value_` and `_rank$`). Newly admitted into training CSVs:

`ecr_rank` · `sf_rank` · `superflex_rank` · `overall_rank` · `dp_consensus_rank` · `dominator_rank` · `recruiting_rank` · `value_over_replacement`

The first five are market consensus ranks. `overall_rank` is not theoretical either — `model_card_source_TE.json` names it: *"Model trained on overall_rank overweights pick number for non-fantasy TEs."*

**The scenario:** the replacement token list (`adp, ecr, ktc, trade_value, auction, consensus_rank, fantasycalc, dynastynerds`) is the expensive half. Deleting two regex clauses is the cheap half. This corpus's documented signature failure — which the adjudication itself names three times — is that the cheap half ships and the expensive half does not. Someone lands the deletion in a cleanup commit, the token list waits on a ticket, and six weeks later an Engine B assembly picks up `sf_rank` from a joined frame. Nothing catches it: `check_leakage` has no production callers, `test_market_leakage_gate.py` skips, `MARKET_FEATURE_RE` doesn't scan `models/`. `sf_rank` correlates strongly with the outcome, the backtest ρ jumps, and **"do we beat the market?" is answered yes by a model whose best feature is the market.** That question dies permanently, because the belief archive from that day forward is contaminated and you cannot tell which rows.

**Verdict: safe only if landed as a single atomic edit with the token list in the same commit and a test proving `ecr_rank`, `sf_rank`, `superflex_rank`, `overall_rank` and `dp_consensus_rank` are still rejected. Split into two commits, it is the highest-consequence loosening in the set.**

### 3. Deriving `decision_supported` from a claim ladder — this flips TE to True

The recommendation is `decision_supported = (claim_level >= DECISION_GRADE)`, with `model_status` as the natural input, justified by WR having cleared every gate.

Run it. `model_status` is `VALIDATED` for **WR and TE**. So TE flips to `decision_supported: True`.

`model_card_source_TE.json`, shipped, says verbatim:
- `intended_use`: **"EXPERIMENTAL — not for trade decisions. Diagnostic only."**
- `out_of_scope_uses`: **"Any trade decision"**, **"Dynasty value ranking"**
- caveats: **"TE model failed Phase 10/11 promotion gates (0/3). Alpha=1.0 indicates severe overfitting; model cannot beat a naive prior-PPG baseline."**

And TE is the position whose deployment training (`scripts/train_engine_b.py:143-145`) reports in-sample metrics and hardcodes `promotion_warranted: None`, skipping `_gate()` entirely.

**The scenario:** the derivation lands, TE tight ends render without the caveat token, and the first surface to change behaviour is the one whose own model card forbids the use. That is the precise failure `decision_supported` exists to prevent — and today's compile-time `Literal[False]`, decoration though it is, makes it impossible.

The WR premise is also weaker than stated. WR's `g3_market_superiority_pass: true` rests on nDCG diffs of +0.010, +0.010, +0.016, −0.039 with BCa intervals of [−0.286, 0.288], [−0.289, 0.309], [−0.193, 0.213], [−0.281, 0.238]. **Every interval spans zero, by an order of magnitude more than the point estimate.** WR has not demonstrated market superiority; it has failed to demonstrate inferiority. That is not a claim to promote on.

**Verdict: the diagnosis is right — one ladder, not four — but the wiring is dangerous. Build the single `claim_level`, publish it as a read-only field, and leave `decision_supported` locked until a position clears a gate that G3 actually enters. The `Literal[False]` lock should move ONTO `PlayerValueObject` (I confirmed `PlayerValueObject(..., decision_supported=True)` constructs today), not off the DTOs.**

### 4. The `dx_` exploratory-column namespace

The proposal exempts a `dx_`-prefixed namespace from `ENGINE_B_OUTPUT_COLUMNS` so exploratory features can ride inside the leakage-correct assembler.

The diagnosis is right and the incentive analysis is right. The hazard is that `validate_no_temporal_leakage` (`engine_b_contract.py:269-274`) is a **name** scanner — four patterns: `_t\+?\d`, `_next`, `^future_`, `_future`. A `dx_` column is exempt from the shape pin but still subject to the name scanner, so `dx_ppg_t1` is caught. What is not caught is any exploratory column *computed* from outcome-season rows under a name carrying no temporal marker — `dx_teammate_ppg`, `dx_role_share`. There is no value-level temporal check anywhere in the repo; the KEEP list concedes this.

The honest reading: today's pin does not prevent that leak either — it relocates it outside the assembler, where it is invisible. **The `dx_` namespace makes the leak visible but also makes it easy.** The mitigation that makes this safe costs almost nothing: require every `dx_` column to be declared with the `feature_season` it was computed from, and assert `feature_season <= T` before the frame is written. Without that, this is a net increase in leakage surface.

### 5. Loosening `qb_rookie_risk_filter`'s exact-set contract to a denylist

The adjudication is right that the rejection message is false for all five columns it names, and right that `age_at_entry` is required but unused. Fix both.

But the exact-set contract is what makes the module's central claim *checkable*. `RookieQbRiskFilterResult` carries `engine_b_training_integration: bool = False` and `decision_supported: bool = False` as frozen defaults, and the docstring asserts "Consumes PRE-NFL inputs ONLY." With a whitelist, that is a property of the call site, verifiable by reading four names. With a denylist of "NFL-usage provenance," it becomes a claim about a set nobody has enumerated — and there is no provenance substrate to check against, because `engine_b_features_v2.csv` carries 33 columns and none of `source`, `source_timestamp`, `parser_version` or `metric_version`.

**Verdict: the denylist is only safe AFTER the provenance columns exist. Sequenced the other way, you trade a verifiable four-name contract for an unverifiable claim. Fix the message and the dead `age_at_entry` now; hold the contract change until provenance ships.**

### 6. Renaming `cut_priority` to `capacity_order`

This one is worse than a no-op. `roster_cut_engine.py` emits `cut_priority=rank` at :375 but also `cut_priority=0` at :297 and `cut_priority=-1` at :267 and :318 — and `league_opportunity_map.py:372` reads `candidate.cut_priority == 0` as `hard_conflict`. **0 and −1 are sentinels, not ordinal positions.** Renaming to `capacity_order` tells the reader the field is a pure ordering when two of its values are status codes, and it launders the normative name without touching the normative content. The `LeaguePulseCapacityCandidatePool` precedent did the real thing: it dropped the scalar and substituted a typed `capacity_conflict_status`. Copy that, or leave the honest name alone.

---

## WHERE THE LOOSENING IS GENUINELY SAFE — and the defenders have earned it

I tried to build a false-claim scenario for each of these and could not.

- **`MARKET_FIELD_PATTERNS` (`build_head_b_targets.py:99`) — DROP is correct.** Defined, never referenced, tested only against literals in the test body. Deleting it removes nothing, and its existence actively conceals that the canonical regex misses `fantasycalc`/`dynastynerds`. Fold the patterns up first, then delete.
- **`MARKET_FEATURE_RE` CI scan — RELOCATE/DROP is correct.** The globs resolve to 5 files, none of which is `engine_a_contract.py`, `engine_b_contract.py`, `scoring/engine_a.py` or `pvo_assembler.py`. It cannot see the feature matrices. Its only measurable effect is failing honest comments.
- **`banned_fields` — DROP is correct.** All five have zero occurrences in `frontend/openapi.json`. A gate that cannot fire teaches nothing. Generating the list from the live contract is strictly better.
- **`_safe_source_status` — DROP is correct.** Erasing `blocked_stale_market` because it contains "block" is the one place in the corpus where a rule deletes the receipt. `00:166` requires the opposite.
- **`^expected_` in `HEAD_B_PROHIBITED_REGEX` — NARROW is safe.** `expected_ppg_at_pick`, `expected_ppg`, `expected_ppg_bucket`, `curve_expected_ppg` are all enumerated explicitly in `HEAD_B_PROHIBITED_COLUMNS`, and `_expected_ppg` remains in the regex. **But keep `^curve_`** — the pipeline generates a `curve_*` namespace (`curve_version` is live in `prospects_with_outcomes_v3.csv`), and the comment names `curve_pick_value` as a form the enumeration does not pre-name. Dropping `^curve_` costs a namespace guard; dropping `^expected_` costs nothing.
- **Head B `MARKET_PROHIBITED_COLUMNS` — RELOCATE is correct and urgent.** The constant name is false and the falsehood cost you the real rule: `residual_ppg` — Head B's own target — sits in the training CSV admissible as a feature, guarded by nothing.
- **The `.gitignore` scratch lane — safe, and the strongest single recommendation in the set.** I confirmed `driver-scratch/` is untracked and NOT gitignored, and the working tree carries 60 dirty paths. The archive is not at risk: the point-in-time capture DBs and training CSVs are already gitignored (`.gitignore:48`) and live in GCS. Note that `check_ephemeral_locators` is scoped to added lines and its docstring offers promotion as the first remedy — the interaction is real but softer than described.
- **`AUTHORIZED_EVAL_FILES` — NARROW is safe.** The reverse-import guard is the real protection and is untouched by an `eval/experiments/` carve-out.
- **Prose pins, bootstrap read, non-goals, the 65/35 split, "polish comes last", the Sleeper palette gate, the H2 stale premise, the 05 attribution propagation — all safe.** None of these can produce a wrong number. The H2 correction and the attribution header are net *increases* in honesty.
- **Green/red — NARROW is safe as specified**, because the sign and the number ride alongside the hue. Use the CVD-safe blue/orange pair, not red/green.

---

## CORRECTIONS THAT CHANGE WHICH LOOSENINGS ARE SAFE

These are not quibbles — each one alters a recommendation.

**1. The runtime counter-argument filter suppresses nothing in production.** `src/dynasty_genius/decision_logic/counter_arguments.py` is the sole producer: seven hardcoded template strings. I ran the exact `_contains_banned` logic against all seven — **all seven pass**. The 254/468 coverage is explained by the generator returning `None` when DVS ≤ 80 and no risk flag fires, not by suppression. The API also emits two *distinct* caveats — `evidence_suppressed_banned_term` vs `counter_argument_unavailable` (`players.py:175-183`) — so suppression and absence are distinguishable at the contract layer (the frontend renders neither, which is the real defect).

So the filter's measured cost today is zero and its measured benefit is zero. That does not make it worth keeping — but it means the loosening buys nothing now, and the gate becomes load-bearing at exactly the moment counter-arguments stop being fixed templates. **Deleting the word gate is safe today and premature; do it in the same commit that makes generation dynamic, not before.**

**2. The clamp is NOT the binding constraint on TE, and the recommended ordering is backwards.** The adjudication computes the fixed TE ceiling as `(100 − 95.6) × 0.703 = 3.09`, holding `ENGINE_B_REPLACEMENT_DVS['TE'] = 95.6` fixed while changing λ. Those both derive from the same P90. Recomputing P90 to 10.284 moves the TE replacement to `8.99 / 10.284 × 100 = 87.4`, and the ceiling becomes `(100 − 87.4) × 0.703 = 8.85` — **3.1× today's 2.85, under the clamp, with no clamp change at all.**

| Pos | shipped repl. | corrected | shipped λ | corrected λ | max xVAR now | max xVAR corrected |
|---|---|---|---|---|---|---|
| QB | 64.2 | 63.15 | 1.386 | 1.398 | 49.62 | 51.51 |
| RB | 46.4 | 46.46 | 1.083 | 1.073 | 58.05 | 57.43 |
| WR | 60.6 | 60.09 | 1.000 | 1.000 | 39.40 | 39.91 |
| **TE** | **95.6** | **87.42** | **0.648** | **0.703** | **2.85** | **8.85** |

The stale constant is the binding problem. The clamp is secondary.

Worse, the recommended order — remove the clamp this week, recompute P90 next week — is the dangerous sequence. TE's shipped P90 (9.4) is 8.6% *below* the true value (10.284), so **every TE's DVS is currently ~9% too high**. Unclamping first ships those inflated values above 100 onto David's roster screen (`RosterAuditRow.tsx:40` renders `dvs_pct` as a bare percentage, and `roster_audit_models.py:181` types it `float | None` with no upper bound), and the training-outcome maxima imply DVS up to ~212 for TE and ~188 for RB. **Recompute the constants first; then decide about the clamp.** And if only the λ half lands — the cheap half, again — TEs get an inflated DVS *and* a corrected multiplier, overstating them in both directions at once.

**3. `check_leakage`'s `_rank$` clause is not dead where it matters.** `leakage.py:52` uses `.match`, so the clause is inert *there* — but `leakage.py` has no production callers, so that module's behaviour is irrelevant. The clause is fully live under `.search` in `validate_training_csv.py`, which is the pre-commit hook. Reasoning about the dead module and editing the shared constant is how the live guard gets broken by accident.

**4. Two of the four headline "the regex passes real market columns" examples are wrong.** `fantasycalc_value` and `dynastydatalab_adp` are both blocked by `PROHIBITED_COLUMNS`, and `ktc_` and `fantasycalc_` are additionally covered by `_MARKET_OVERLAY_PREFIXES` derived from the registry (`footballguys_`, `fantasycalc_`, `mfl_rookie_adp_`, `dynasty_data_lab_`, `dynasty_nerds_`, `ktc_`). The real gaps are `sleeper_adp`, `fp_ecr`, `crowd_price`, `dn_val`, `sf_value`, `trade_value`, `auction_value`, `keeptradecut_value`. Fix those — but the wall is meaningfully stronger than the isolated-regex test suggested.

---

## THE PRINCIPLE

The adjudication's diagnosis is right: enforcement went where it was easy, and its presence was mistaken for safety. But the corrective has a symmetric failure available to it — **deleting the check is also easy, and its absence will be mistaken for freedom.**

Every dangerous item above shares one shape: *the cheap half of the recommendation can land without the expensive half.* Delete two regex clauses without the token list. Derive `decision_supported` without a G3-aware ladder. Exempt `dx_` without the `feature_season` assertion. Swap a whitelist for a denylist without the provenance columns. Fix λ without recomputing P90.

So the guardrail on the loosening is the same guardrail the codebase already gets right at `source_registry.py:462-469` — **make the permission structurally inseparable from its precondition.** Land each of these as one atomic change with a test that fails if only the deletion arrives. Where that cannot be arranged, keep the rule.

And refuse the `CI_WIDTH_MAX` deletion outright. It is the only recommendation in the set that produces a false claim on David's screen with no accompanying benefit at all: QB flips to VALIDATED on ~46 players per fold against a model that loses to free consensus ECR on three folds of four, and TE — the entire stated reason for the change — ships VALIDATED either way.

---

## CHALLENGE 2: RESEARCHER — where the audit was too timid

**Verdict:** MIXED

# THE RESEARCHER'S BRIEF — where the adjudication was too timid

I accept the four things named as worth protecting. I am going to show that the current rules do not protect three of them, and that the one they do protect is protected by a mechanism that makes the bans redundant.

Everything below was executed against the running system with `.venv/bin/python3.14`. Read-only; nothing changed.

---

## 0. The single fact that reframes the market question

**The market denylist is mathematically incapable of firing where the model is, and is load-bearing only where the model is not.**

The X matrix is built closed-world by intersection:

```
src/dynasty_genius/eval/backtest_harness.py:436-440
    contract  = ENGINE_B_FEATURES_BY_POSITION[position]
    available = contract & set(df_columns) - _METADATA_COLS
```

I then computed the intersection of every position contract with the denylists:

| Position | ∩ `ENGINE_B_PROHIBITED_FEATURES` | ∩ `MARKET_PROHIBITED` |
|---|---|---|
| QB | `[]` | `[]` |
| RB | `[]` | `[]` |
| WR | `[]` | `[]` |
| TE | `[]` | `[]` |

So `validate_no_prohibited_features(feature_cols)` at `backtest_harness.py:474` is checking a set that by construction cannot contain a market name. **It is a proven no-op in the lane that produces the "do we beat the market?" answer.**

Where the denylist *does* fire is the frame level — `scripts/assemble_engine_b_dataset.py:236-237` and `src/dynasty_genius/features/feature_validation.py:108`, both of which scan **every column of the assembled dataset**, not the X matrix. That is: the ban buys zero model safety and its entire live effect is to forbid carrying a market column, or a comparator column, or a diagnostic column, *alongside* the features — the exact thing an analyst needs and the model can never see.

**Correction to the adjudication.** KEEP #1 credits `ENGINE_B_ALLOWED_FEATURES` (`src/dynasty_genius/models/engine_b_contract.py:126-146`) as "checked against real column lists at training time." It is not. Repo-wide grep returns importers only in `tests/test_engine_b_contract.py` — **zero production callers**, same defect the adjudication correctly found in `leakage.py`. The real closed-world wall is `ENGINE_B_FEATURES_BY_POSITION` (`:178`) via `_get_feature_columns` and `validate_position_feature_contract`. The mechanism is real; the constant named is decorative. This matters because the adjudication's confidence in relaxing denylists rests on a wall it misidentified.

**And `market_overlay` is not a rule at all.** Grep across `src/`, `app/`, `scripts/`, `tests/` shows the registry role `market_overlay` (`src/dynasty_genius/sources/source_registry.py:14-16`) is never read by any code — only string literals in unrelated payload fields. The import-time assertion the adjudication rightly praised (`source_registry.py:462-469`) guards `if "model_input" in _src.roles` only. **A market source registered `roles=["training_label"]` passes it untouched.** The registry already has the vocabulary for role-scoped market use; nothing enforces it, and nothing forbids it either — the *prose* does.

---

## 1. The wall's stated purpose is not being served — measured

"Model features must not contain market data. This is the ONLY reason 'do we beat the market?' is answerable at all." Here is the answer it produces, from `app/data/backtest/trust_surface/latest/`:

| Pos | k | fold diffs (model − market NDCG@k) | 95% BCa CI (fold 1) | width | G3 | model_status |
|---|---|---|---|---|---|---|
| QB | 12 | −0.0519, −0.0409, +0.0014, −0.0046 | [−0.521, +0.376] | 0.897 | False | PROVISIONAL |
| RB | 24 | −0.0243, −0.0008, −0.0578, −0.0415 | [−0.400, +0.214] | 0.615 | False | **VALIDATED** |
| TE | 12 | −0.0158, +0.0193, +0.0462, −0.0371 | [−0.493, +0.239] | 0.731 | False | **VALIDATED** |
| WR | 24 | +0.0098, +0.0103, +0.0163, −0.0389 | [−0.286, +0.288] | 0.574 | **True** | VALIDATED |

**All sixteen confidence intervals straddle zero, by ten to fifty times the effect.** WR's `g3_market_superiority_pass=True` is a 3-of-4 sign count on three noise draws averaging +0.012 against a CI of ±0.29.

To scale it, I simulated the null (random ranking, realistic skewed PPG, same n and k, 4,000 draws):

- QB n=40 k=12: random NDCG = **0.535** (p5 0.386, p95 0.692)
- WR n=125 k=24: random NDCG = **0.474** (p5 0.373, p95 0.585)

Observed values sit at 0.86–0.98. So the metric's usable range is ≈0.5, the model-vs-market effect is 0.01–0.06 (2–12% of range), and **the reported CI is 0.57–0.90 — larger than the entire range from random to perfect.** The question the whole wall exists to make answerable is currently unanswerable, and the product ships a binary answer anyway.

### 1a. ~80% of that uncertainty is a bootstrap bug, not real noise

`src/dynasty_genius/eval/backtest_metrics.py:147-215` resamples player indices with replacement and carries the **original full-pool rank integers** into `compute_ndcg`, which does `mask = ranks <= k` (`:134`). In a resample, the count of players holding rank ≤ k is itself random (≈Binomial(n, k/n)) and duplicates are counted repeatedly. That variance has nothing to do with model-vs-market.

I ran both versions on identical synthetic data (n=125, k=24, paired, 2,000 draws):

```
as-shipped:  diff -0.0024  ci [-0.2359, +0.2185]  width 0.454
re-ranked:   diff -0.0009  ci [-0.0466, +0.0431]  width 0.090
```

**A 5× inflation.** Fix the resample to re-rank within each draw and the comparison becomes capable of resolving a ~2-point NDCG edge — which is the size of the effect that is actually there.

### 1b. The comparator is handed a nine-month information advantage

`backtest_harness.py:55-57`: `_market_snapshot_date(test_year) = f"{test_year+1}-09-08"`. Confirmed in the artifact: `{'2020': '2021-09-08', ..., '2023': '2024-09-08'}`.

The model's features stop at the end of season T. The market snapshot is Sep 8 of T+1 — after that offseason's draft, free agency, training camp and preseason. **They are not on the same information set,** and the model is roughly at parity anyway. Nothing in the corpus requires as-of alignment between a model and its comparator, because governance is aimed at column names, not at information sets.

### 1c. The status label is deliberately market-blind

`src/dynasty_genius/eval/composite_gate.py:96` — *"Pure: no I/O, no market/G3 coupling. G3 market-superiority never enters here."* And `backtest_harness.py:385` — *"DISCLOSED only; never gates model_status."*

Consequence, live today: **RB ships `VALIDATED` while losing to the market on 4 of 4 folds. TE ships `VALIDATED` while losing on 2 of 4.** The one question the constitution says credibility is earned by (`00:129`) cannot touch the label that claims credibility.

---

## 2. Legitimate uses of market data the blanket rule forbids and should not

The constitutional text (`docs/governance/00-product-constitution.md:121-123`) is narrower than the practice: *"must never enter Engine A or Engine B **as predictive model features**."* The registry prose (`source_registry.py:14-16`) widened it to *"never enters Engine A/B ... regardless of feature name."* The frame-level denylist widened it again to "may not exist in the assembled dataset." Each widening was unratified and each one costs a real analysis.

**(a) Market as the target of a residual head — already ratified in this repo, for a different prior.**
`src/dynasty_genius/models/head_b_contract.py:56-60` bans `expected_ppg_at_pick` as a *feature* while using it as the *target-side* decomposition: Head B models production orthogonal to draft capital. The prior defines the target; the fitted function contains no term for it. **That is exactly the architecture that would let you model where the market errs**, and it is banned only because the prior is spelled "market." Honest guardrail, and it is a lineage rule not a name rule: the market snapshot that defines the target must be strictly earlier than the snapshot the result is evaluated against, and the head is scored on realized PPG, never on market agreement.

**(b) Market as an evaluation cohort — the reason G3 is uninformative.**
NDCG over the whole matched pool measures *agreement*, and model and market agree on almost everyone (both ≈0.9 against a random null of ≈0.5). The decision-relevant question — "when we disagree, who is right?" — requires slicing by market rank, and a market-defined evaluation stratum never touches a feature matrix. It is not forbidden by `00:123`; it is unbuilt because `composite_gate` is required to be market-blind, so no gate rewards building it. **This is the single highest-value unbuilt analysis in the system and the rule structure actively de-prioritizes it.**

**(c) Market-implied replacement level and cross-positional scarcity.**
The stale `XVAR_LAMBDA['TE']` defect exists because P90 ratios are the only scarcity anchor available. A market-implied positional scarcity curve is an *independent second estimate* of the same quantity — and the disagreement between the two is itself a finding. Forbidden today because it would live in the model artifact.

**(d) Market as a sample weight — permit it, but I will not pretend it is free.**
There is no `sample_weight` anywhere in the repo (grep: zero hits). Weighting training toward the rosterable universe would improve the model where decisions happen. But a market-derived weight *does* leak market information into the fitted function and does contaminate the headline claim. This one belongs in a pre-registered lane evaluated against a strictly later market snapshot — not in the default path. Say so explicitly rather than banning it by name and pretending the question is settled.

**(e) The moat is accruing and is walled off from every use but display.**
Measured, live:

| Store | rows | distinct dates | span |
|---|---|---|---|
| `app/data/fc_forward_capture.db` | 27,158 | 58 | 2026-06-24 → 2026-08-20 |
| `app/data/model_forward_capture.db` | 707,941 | 57 | 2026-06-24 → 2026-08-20 |
| `app/data/market_divergence_history.db` | 476,121 | 39 | 2026-07-09 → 2026-08-20 |
| `app/data/fc_snapshots.db` | 6,790 | 14 (4 archive + 10 native) | 2021-09-08 → 2026-06-24 |

A 58-day daily **paired** panel of model value and market price, append-only, point-in-time validated (`scripts/backfill_market_archive.py:41-60`). This is the genuine moat. The only sanctioned analysis over it is a display overlay, because every analytic use routes through a model artifact and every model artifact is name-banned.

---

## 3. The temporal guard is a name regex and it is wrong in both directions

`src/dynasty_genius/models/engine_b_contract.py:266-272` — patterns `_t\+?\d`, `_next`, `^future_`, `_future`. I ran them.

**Blocks legitimate as-of-correct PAST features:**

| Column | Result |
|---|---|
| `target_share_t1` | **BLOCKED** |
| `snap_share_t1_lag` | **BLOCKED** |
| `routes_t2_prior` | **BLOCKED** |
| `rolling_t4_avg` | **BLOCKED** |
| `age_t1` | **BLOCKED** |
| `yards_t3_seasons_ago` | **BLOCKED** |

**Passes every value-level leak:**

`career_ppg` · `total_points` · `y24_ppg` · `best3of4_ppg` · **`residual_ppg`** (Head B's own target) · `final_season_rank` · `end_of_year_snap_share` · `full_career_yprr` · `injury_return_date` — all pass.

Worse, the repo carries **both conventions with opposite meanings**: `ppg_t1` is the *future* outcome (`OUTCOME_SEASON_COLUMNS`, `:16`) while `ppg_t_minus_1` is a *past* feature (`:137`). The guard enforces a convention that is itself ambiguous, and it is applied to the **entire assembled frame** — `feature_validation.py:39` excludes only `avg_ppg_t1_t2` and `training_eligible` — so a diagnostic column cannot ride along either.

### 3a. A real as-of violation the name regex cannot see

`aging_curve_value` is a **required** Engine B base feature for every position (`engine_b_contract.py:154`). It is read from `resources/fitted_aging_curves_v1.json`, whose header reads:

```
"fit_date": "2026-05-11",
"data_source": "historical_nfl_positional_ppg_consensus"
```

The walk-forward folds test **2020, 2021, 2022, 2023** (`train_years` / `test_year` in `backtest_result_WR.json`). The curve's peak ages, decline slopes and cliff ages were parameterized in May 2026 from history spanning every one of those test years, and it is applied **unchanged in every fold**. The harness is scrupulous about imputer and scaler ("fit on train only", `backtest_harness.py:448-452`) and then hands every fold a feature whose parameters encode 2026 knowledge.

Whether you judge that material or benign, note what settles it: **a lineage check — "what data produced this column, and is its as-of date ≤ this fold's train cutoff?" — answers it in one line. A name regex can never ask the question.** This is the worked specimen exactly: the scanner checks LANGUAGE, the defect is LINEAGE.

The substrate for that check is already half-built and already mandated: `01-north-star-architecture.md:140-159` requires `source`, `source_timestamp`, `parser_version`, `metric_version` on every computed feature. Engine A's `prospects_with_outcomes_v3.csv` carries them. `engine_b_features_v2.csv` carries none of them.

---

## 4. What to do, in order — sequencing matters

**Loosening is safe here, now:**

1. **Delete `_LEAKAGE_PATTERNS` as a frame-level gate.** Keep the exact-set `OUTCOME_SEASON_COLUMNS` check (`:286`) — that is the enumerated, zero-false-positive guard that actually works. Apply the name patterns to the **X matrix** only, if at all. The closed-world intersection already makes them redundant there.
2. **Fix the paired bootstrap** (`backtest_metrics.py:147-215`) to re-rank within each resample. Measured 5× CI reduction. This is the cheapest fix in the audit and it is the difference between "we cannot tell" and a real answer.
3. **Align the comparator's information set** with the model's, or disclose the nine-month gap on the surface. Today the model is beating a comparator with a year's head start and the product reports it as a loss.
4. **Let G3 inform `model_status`** — at minimum, forbid `VALIDATED` while the market point estimate wins on a majority of folds, which is RB and TE today.
5. **Build the disagreement-stratified evaluation.** Market as an evaluation cohort touches no feature matrix and is not forbidden by `00:123`.
6. **Add a declared `dx_` diagnostic namespace** exempt from the frame-level denylist and temporal regex, stripped by the publisher before runtime. One prefix separates "measure" from "promote."

**Loosening is dangerous unless sequenced:**

7. **Do not relax `MARKET_PROHIBITED` or `PROHIBITED_COLUMNS` before installing the closed-world X-matrix check everywhere.** It holds in `backtest_harness.py` and in `train_engine_b.py` via `validate_position_feature_contract` — but `train_te_deployment_model` and the unified path do not all go through it consistently, and `app/services/engine_b_service.py` imports only the denylist. Wire the closed-world check into every training and scoring path **first**; then the denylists can go and every non-feature market use becomes safe by construction rather than by vocabulary.
8. **Market as a residual target or a sample weight requires a lineage rule, not a name rule.** Permit them only in a lane where the market snapshot defining the target is strictly earlier than the snapshot the result is evaluated against, and where the head is scored on realized PPG. Without that, the headline claim genuinely dies — the adjudication is right about that, and it is the one place I would not push.

**The reframe.** "No market in features" is the correct rule and it is already enforced structurally by closed-world intersection. What is deployed is a *name denylist over the whole dataset*, which protects nothing the intersection does not already protect and forbids market as target, comparator, cohort, weight and diagnostic — none of which is a feature. Replace the name bans with a **role-and-lineage rule**: a column may enter an X matrix only if its registry role is `model_input`; any other role may appear anywhere else in the pipeline provided it carries `source_timestamp` and the as-of check passes. That is strictly stricter on the model, strictly looser on the analysis, and it is the only version that catches `aging_curve_value`.
