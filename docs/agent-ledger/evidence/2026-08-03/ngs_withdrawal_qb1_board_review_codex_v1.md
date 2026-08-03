# NGS withdrawal / Step 1b + QB-1 board review — Codex round 1

**Date:** 2026-08-03 15:33 ET
**Layer:** Layer 1 removal/documentation review; separate read-only audit of the Layer 3 QB-1 backlog record
**Verdict:** **NOT CLEAR**

## What independently passed

- `HEAD == origin/main == 85bf5b5f6b70cdd58a88bdfba35eaf89eb414203`.
- The three authorized untracked NGS code/test paths are absent.
- `src/dynasty_genius/capture/__init__.py` has no re-exports. The package remains non-empty.
- The retained duplicate data tree still contains exactly eight files with the original 2026-07-30
  timestamps. All eight SHA-256 values were recomputed during this review; no mutation was observed.
- The canonical registry remains unique and executable-code searches find no withdrawn-adapter caller.
- The NGS model-use claim was falsified against the code: six `ngs_*` columns reach the assembled
  Engine B dataset, but `scripts/train_engine_b.py:63` excludes every `ngs_*` field from the shipped
  unified training matrix, and the optional-position helper has no production caller. Therefore NGS
  is **not currently a shipped model input**.
- QB-1 readiness is accurately measured: the analytical package exists and no D3/D4 end-to-end
  runner/orchestrator exists. The sequencing behind Layer 1 steps 2–5 is consistent with “put it on
  the list”; it does not silently move QB-1 to the front.
- Every H2 ceiling remains intact: QB rushing is **UNDER TEST**, there is no run/result, the target is
  regular-season veteran-cohort PPG under counterfactual pinned 2026 scoring, no registered contrast
  tests marginal/conditional H2 contribution, and `decision_supported` remains false.

## Blocking findings

### R1 — the claimed durable pre-deletion hash trace does not exist

The ledger says the three hashes were “recorded pre-deletion in the v3 audit.” A whole-repo search
finds none of the three hashes anywhere. The v3 audit predates removal and does not contain them.
Because the untracked files are now unrecoverable from git, record the exact three supplied hashes in
the durable ledger or a post-removal artifact and correct the false v3 attribution.

### R2 — the durable removal record contains stale and false scope statements

The ledger still says the two source drifts are “flagged, not fixed,” although both source files are
now modified on David's later word. It also says “no model or feature use is authorized and none was
taken,” while the same measured code proves the NGS fields are used in feature/dataset assembly.
Correct the boundary to **no predictive-model training/use or feature promotion**. The same ambiguity
appears in `docs/data-inventory.md:70` and `:134` and in the new canonical docstring's sentence
“a model or feature use requires…” immediately after it states that the fields reach a dataset.

### R3 — the submitted post-change gate is stale on the current tree

The 4,309/12/9 full-suite census predates the two newly authorized source edits. The implementer has
correctly withheld commit and promised a fresh full run plus `verify_sprint_closeout.py` ENFORCE.
Those exact final-tree results must land before an all-scope CLEAR. Focused 198-pass + Ruff is good
evidence for the two prose-only source edits, but it is not the final commit tollgate.

### Q1 — the current board contradicts itself on execution authority

`AGENT_SYNC.md:316-325` remains live above `END CURRENT BOARD` and still says execution is “not yet
given.” That directly contradicts the newly inserted authorization block at lines 262–304. Mark the
entire old readiness/ceiling block as superseded historical text or update it to current state.

### Q2 — David-word attribution and citations are not exact enough

- The board's authorship banner says only the ruling in the next paragraph is David's words, but the
  current board now contains at least the CFBD and QB-1 verbatim David quotes. Repair the banner.
- `§497` and `§232` are not sections. They are line 497 and line 232; use `line 497` and `§9.1
  (around line 232)`.
- The first QB-1 grant is quoted exactly. The bridge + allowlist grants are recorded only as “he
  granted both.” Preserve the exact direct question and David's exact answer (an answer such as
  “both” is sufficient when paired with the exact question) so the two distinct authorities are
  independently auditable rather than resting on an agent paraphrase.

### Q3 — the historical allowlist conclusion is technically correct for the present topology

`tests/contract/test_subsystem_4_audit.py:404-411` enumerates only direct `*.py` files in
`src/dynasty_genius/eval/`; it does not recurse into `eval/qb_validation/`. The package already exists
without changing that exact-set allowlist. Therefore the freshly granted allowlist authority is
valid but **presently moot** unless execution proposes a new top-level eval module. The board should
record that measured disposition and must not require or make a no-op allowlist amendment merely
because the registration preserved it as a separate authority gate.

## Non-blocking precision corrections

- The capture package contains seven other `.py` modules plus `__init__.py`, not “six other modules.”
- `nfl_nextgen_capture` still appears in the current board, historical/evidence records, and the
  registry note. The accurate residue claim is that the registry note is the only remaining
  **execution-source** mention; it is not the only remaining repo string.
- The registry-vs-contract tension is real: registry `context_signal` / `allowed_fields=[]` coexists
  with declared optional model features. It is inert today only because the opt-in helper has no
  production caller. Record it as an open governance question; do not resolve it as part of this
  withdrawal commit.

## Evidence-file commit scope

The audit/review/CLEAR/message artifacts in `docs/agent-ledger/evidence/2026-08-03/` should be
included in the single David-authorized “commit it all” commit. Authorship and committer identity are
separate; splitting the evidence from the state change would weaken the durable proof chain. Include
this review and the eventual superseding CLEAR artifact as well.
