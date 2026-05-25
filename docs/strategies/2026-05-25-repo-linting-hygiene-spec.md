# Dynasty Genius Repo Lint Hygiene Policy And Plan

Version: 0.2.0
Last updated: 2026-05-25
Status: DRAFT FOR CLAUDE REVIEW, THEN DAVID APPROVAL
Authority: Proposed code-quality policy; not binding until David approves and governance/bootstrap references are updated.

## 1. Problem Statement

The repository currently has Python lint debt that is visible in local IDEs but not enforced by the repo:

- Ruff reports 226 findings across the repo.
- Most findings are in `tests/` and `scripts/`; only a small minority are in `src/` and `app/`.
- No Ruff configuration is committed.
- Pre-commit currently enforces only the training CSV market-leakage guard.
- CI Python checks run pytest, not lint.

This is not a model-quality or football-evaluation defect by itself. It is an engineering-process gap: lint hygiene was not part of the repo's definition of done, so low-risk import/style debt accumulated during fast phase work.

## 2. Policy Goals

The policy should make future lint drift difficult without creating noisy churn or semantic risk.

Required outcomes:

1. Establish one committed Ruff ruleset for all agents.
2. Keep lint cleanup isolated from feature/model work.
3. Clear production code paths first: `src/` and `app/`.
4. Ratchet tests and scripts so new or modified files cannot add avoidable lint debt.
5. Protect pandas, Polars, NumPy, and script bootstrap semantics from unsafe autofixes.
6. Keep PM and David approval explicit before any full-repo hygiene campaign.
7. Add bootstrap references so future agents cannot miss the policy.

Out of scope:

- mypy or broader type-checking adoption
- formatting-only churn unrelated to selected Ruff rules
- model feature, valuation, artifact, or decision-surface behavior changes
- CI full-repo lint enforcement before the repo is clean

## 3. Standing Rules

These rules apply once David approves the policy.

### 3.1 Lint Work Must Be Scoped

Lint cleanup must run on a dedicated branch unless it is a tiny local fix in files already being changed for an approved task.

Dedicated branch naming:

```text
hygiene/ruff-lint-ratchet
```

Lint-only commits must not include:

- model pickle files
- generated valuation artifacts
- source snapshots or caches
- unrelated feature work
- semantic formula changes
- API response-contract changes

### 3.2 Production Code Has The Highest Bar

`src/` and `app/` should be driven to zero selected Ruff findings first.

Any remaining exception in production code must have a file-local `noqa` with a reason, not a silent global ignore, unless David explicitly approves a rule-level carve-out.

### 3.3 Tests And Scripts Are Ratcheted

`tests/` and `scripts/` should not block the initial policy rollout if legacy debt remains.

The ratchet rule:

- New Python files must pass Ruff.
- Modified Python files must pass Ruff as whole files under the selected rule set.
- Legacy unmodified files may remain dirty until touched or until David approves a thorough cleanup sprint.

This is intentionally a touched-file ratchet, not an added-lines-only rule. Ruff and the standard Ruff pre-commit hook lint whole files. The policy should be honest about that behavior instead of promising a diff-only mode Ruff does not provide.

### 3.4 Unsafe Autofixes Are Forbidden

Agents must never run Ruff with `--unsafe-fixes` unless David explicitly approves that command for a narrowly reviewed cleanup. The default allowed autofix mode is plain `ruff check --fix` under the selected rule set.

Manual fixes require review for:

- `E712` where pandas, Polars, NumPy, or other vectorized boolean masks may be involved.
- `E402` where late imports follow environment setup, monkeypatch setup, path setup, Databricks/Sleeper configuration, or test fixture initialization.
- `F821` where the correct fix may be a guarded import, `TYPE_CHECKING` import, string annotation, or local model/schema import.
- broad exception cleanup (`E722`) without checking the intended error boundary.

Verified locally on 2026-05-25: among these guarded examples, Ruff reports an autofix only for `E712`, and marks that fix unsafe. `E402`, `F821`, and `E722` have no default Ruff autofix, but they still require human review because the manual fix can change runtime behavior.

### 3.5 PM Is In The Loop

Gemini/PM owns policy synthesis and approval routing, not implementation.

Before implementation begins:

- Gemini or another PM-designated process should review the proposed policy for governance alignment.
- David must explicitly approve the policy and choose the strategy: pragmatic ratchet or full zero-drive.
- Claude Code/Codex may implement only after that approval is recorded in the ledger or `AGENT_SYNC.md`.

PM must not be left out of future lint-policy changes. Any change to selected rules, ignored rules, enforcement surface, or CI gating must be treated as a policy change and routed through PM review plus David approval.

## 4. Recommended Ruff Baseline

The initial ruleset must be conservative. It should capture the existing 226-style Ruff debt that agents already diagnosed, not expand the repo into a formatting or modernization campaign.

Do not begin with broad `E`, `W`, `UP`, `B`, or `RUF` selection. In the current repo, broad selection expands the surface from the known default-style lint debt into thousands of findings dominated by line length, whitespace, annotation-modernization, and advisory modernization rules. That would turn a hygiene ratchet into a churn project.

Proposed config location:

```text
pyproject.toml
```

Proposed baseline:

```toml
[tool.ruff]
target-version = "py314"
line-length = 88

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I"]

# Keep E712 visible for manual review, but never run Ruff with --unsafe-fixes
# until all vectorized boolean masks have been reviewed. Ruff marks the E712
# fix as unsafe because operator-overloaded libraries can change semantics.

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
"tests/**/*" = ["E402"]
"scripts/**/*" = ["E402"]
```

This baseline intentionally keeps `E712` selected. Production `src/` and `app/` should be driven to zero selected findings by either making a behavior-preserving fix or adding a narrow `noqa` with a reason. A permanent global `E712` ignore would contradict the production-zero goal and should require a separate David approval.

`I` is included in the selected set because import order should be part of the go-forward hygiene contract. It is not baseline-neutral: verified on 2026-05-25, `E4,E7,E9,F` reports 226 findings; adding `I` reports 351 findings because it adds 125 `I001` import-order findings. To keep review clean, handle those 125 import-order fixes in a dedicated mechanical `P1b` commit, separate from the dead-code/unused-import cleanup.

Verified locally on 2026-05-25:

- `.venv/bin/ruff --version` -> `ruff 0.15.12`
- Ruff 0.15.12 accepts `--target-version py314`
- Ruff validates target versions rather than silently accepting invalid values

Deferred rule families:

- `UP` should be a separate modernization initiative. Current repo impact is 392 findings.
- `B` should start as a read-only bug-class audit and triage, not an immediate cleanup gate. Current repo impact is 29 findings.
- `RUF` should be deferred except for a later narrow `RUF100` unused-`noqa` pass if useful. Current repo impact is 136 findings.
- Broad `E`/`W` should stay out of the initial gate because it pulls in `E501`, `W291`, and `W293` formatting debt.

## 5. Implementation Plan

### P0: Config And Baseline Measurement

Actions:

- Pin Ruff through the pre-commit hook `rev`; that is the source of truth for enforcement.
- Keep the local `.venv/bin/ruff` version aligned with the pinned hook version when practical.
- Add `pyproject.toml` Ruff configuration.
- Run Ruff without fixes and capture the baseline count by rule and directory.
- Commit config and baseline notes only.

Required checks:

```bash
.venv/bin/ruff check .
.venv/bin/python3.14 scripts/validate_governance.py
```

Exit criteria:

- Config exists.
- Baseline is documented.
- No source files are changed except config/docs/ledger.

### P1: Safe Autofix Batch

Actions:

- Run Ruff autofix only for rule families selected as safe after dry-run review.
- Split P1 into two commits:
  - P1a: dead-code/default hygiene fixes such as `F401`, `F541`, `F811`, and `E731` where safe.
  - P1b: import sorting only (`I001`), as a dedicated mechanical commit.
- Review every changed file before committing.

Candidate safe fixes:

- unused imports where they are not public re-exports
- f-string-without-interpolation
- duplicate imports
- simple import sorting in the dedicated P1b commit

Forbidden in P1:

- `--unsafe-fixes`
- broad `UP`, `B`, or `RUF` autofixes
- full formatting/line-length cleanup

Mandatory import-diff review:

- Hand-review every `F401` and `I001` diff that touches adapters, registries, package `__init__.py` files, route mounting, plugin/module discovery, or source registration.
- Preserve side-effect imports, public re-exports, `__all__` contracts, and import-time registration semantics.
- If an import exists only for side effects, keep it and add a narrow explanatory `noqa` rather than letting Ruff remove it.
- Do not rely only on the test suite for this guardrail; tests catch the break only if they exercise the affected import path.

Required checks:

```bash
.venv/bin/python3.14 -m pytest -q
.venv/bin/python3.14 scripts/validate_governance.py
.venv/bin/ruff check .
```

Exit criteria:

- Test suite green or any pre-existing exclusions documented from `AGENT_SYNC.md`.
- Governance validator green.
- No model/artifact files touched.

### P2: Production Manual Clearance

Actions:

- Hand-clear selected Ruff findings under `src/` and `app/`.
- Add targeted `noqa` comments with reasons where lint clarity conflicts with runtime semantics.
- Do not change formulas, feature contracts, model routing, PVO semantics, or API response meanings.

Required checks:

```bash
.venv/bin/python3.14 -m pytest -q
.venv/bin/python3.14 scripts/validate_governance.py
.venv/bin/ruff check src app
```

Exit criteria:

- `src/` and `app/` pass selected Ruff rules, except explicitly justified `noqa`.
- No market-derived data enters Engine A/B features.
- No valuation artifacts are regenerated.

### P3: Ratchet Enforcement

Actions:

- Add Ruff to pre-commit.
- Use the standard Ruff pre-commit behavior as the first ratchet: staged Python files are linted as whole files.
- Decide whether CI runs changed-files lint only or a production-scope lint check.

Recommended first enforcement:

- Pre-commit: run Ruff on staged Python files as whole files.
- CI: run Ruff on `src/` and `app/`; optionally add a PR changed-files wrapper only if the team wants server-side enforcement for touched files outside production.
- Do not require full-repo `tests/` and `scripts/` zero until P4 is approved.

Required checks:

```bash
pre-commit run --all-files
.venv/bin/python3.14 -m pytest -q
.venv/bin/python3.14 scripts/validate_governance.py
```

Exit criteria:

- New production lint debt is blocked.
- Modified-file debt is blocked or explicitly documented.
- Legacy debt remains visible but not silently growing.

### P4: Optional Full Zero-Drive

This requires a separate David approval.

Actions:

- Drive `tests/` and `scripts/` to zero selected Ruff findings.
- Split commits by directory or rule family.
- Flip CI from production-scope/changed-file lint to full-repo lint.

Required checks:

```bash
.venv/bin/python3.14 -m pytest -q
.venv/bin/python3.14 scripts/validate_governance.py
.venv/bin/ruff check .
```

Exit criteria:

- Full repo passes Ruff.
- CI enforces full repo.

## 6. Required Governance And Bootstrap Placement

If David approves this policy, it should not live only in `docs/strategies/`. The durable placement should be:

1. New authoritative policy doc:

```text
docs/governance/03-code-hygiene-policy.md
```

Purpose: permanent code-quality doctrine, rule-change process, lint scope, PM/David approval boundary, and unsafe-autofix guardrails.

2. Update agent operating loop:

```text
docs/governance/02-agent-operating-loop.md
```

Add code-hygiene requirements to execution/postflight:

- add `docs/governance/03-code-hygiene-policy.md` to the required reading order after `01-north-star-architecture.md` for implementation, review, CI, or Python-editing sessions
- add `docs/governance/03-code-hygiene-policy.md` to the authority order below `02-agent-operating-loop.md`; it governs code-hygiene mechanics, while the constitution and architecture continue to govern product and technical semantics
- agents must respect the committed lint policy
- lint cleanup must not be bundled with unrelated feature work
- lint-policy changes require PM review and David approval
- relevant lint checks must be listed in ledger closeouts when code changes touch Python

3. Update bootstrap entrypoints:

```text
AGENTS.md
CLAUDE.md
.clauderules
GEMINI.md
AI_CONTEXT.md
README.md
docs/README.md
# DYNASTY GENIUS — SESSION STARTER.md
```

Each should point agents to `docs/governance/03-code-hygiene-policy.md` after the existing governance reads. Gemini's file should explicitly say PM reviews policy and specs but does not run lint cleanup unless David explicitly authorizes runtime actions.

4. Update governance validator:

```text
scripts/validate_governance.py
```

Add the new policy doc to `REQUIRED_FILES`, require bootstrap references to it, and add required phrases covering:

- the policy doc path appears in every bootstrap entrypoint
- `02-agent-operating-loop.md` includes the policy doc in the required reading order for relevant sessions

Do not gate on exact policy sentences. Literal phrase gates are too brittle for this policy because harmless wording edits would break every commit. Path/reference validation is the right level for `validate_governance.py`; detailed policy content should be reviewed through PM/David approval and normal code review.

5. Update `AGENT_SYNC.md`:

Record policy status, selected strategy, current lint baseline, and current enforcement mode.

6. Update PR template:

```text
.github/pull_request_template.md
```

Add a checkbox for Python-touching PRs:

```text
- [ ] Ruff policy considered; relevant lint checks run or explicitly deferred.
```

7. Add implementation artifacts:

```text
pyproject.toml
.pre-commit-config.yaml
.github/workflows/*
```

Only after the policy is approved and implementation begins.

## 7. Claude/Codex Convergence

Claude and Codex converged on these implementation positions:

1. Selected baseline should be `E4,E7,E9,F,I`, not broad `E/F/W/I/UP/B/RUF`.
2. Import sorting (`I001`) should be included now, but isolated into a dedicated P1b mechanical commit.
3. `UP`, `B`, and `RUF` are deferred; `B` starts as read-only audit/triage before any gate.
4. Ratchet semantics are whole touched files, not added lines.
5. Default autofix is plain `ruff check --fix`; `--unsafe-fixes` is forbidden without explicit approval.
6. `E712` remains selected and is hand-reviewed; no global ignore.
7. Ruff is invoked as `.venv/bin/ruff`; `python -m ruff` is not valid in this environment.
8. Ruff pin source of truth is pre-commit `rev`; keep local `.venv/bin/ruff` aligned when practical.
9. Governance validation should check required policy paths/references, not brittle literal phrases.
10. `docs/governance/03-code-hygiene-policy.md` belongs in both required reading and authority order in `02-agent-operating-loop.md`.

## 8. Decision Needed From David

David needs to approve one strategy before execution:

- Recommended pragmatic ratchet: clean `src/` and `app/`, include import sorting now via a dedicated P1b bulk-sort commit, enforce production and touched-file gates, clean remaining tests/scripts on touch.
- Full zero-drive: clean every Python file and then enforce full-repo Ruff in CI.

Recommendation: approve the pragmatic ratchet with P1b bulk import sorting now. It is deterministic, one-time, and avoids months of drip import-order churn while keeping the diff reviewable.
