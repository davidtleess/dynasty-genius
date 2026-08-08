# Layer 1 daily-control CI portability fix — Codex CLEAR v1

Date: 2026-08-08 ET  
Layer: Layer 1 ingestion  
Reviewer: Codex  
Status: **CONTENT CLEAR; landing and exact-SHA CI verification still required**

## Scope

This review covers only the correction to the Layer 1 daily-control code and its contract tests after
GitHub Actions run `31240289595` failed on pushed SHA
`c55e645ff031207dffffe7f6d9a9ee1f559032ab`.

Reviewed blobs:

- `src/dynasty_genius/sources/daily_control.py`
  - SHA-256 `eaf2091a30964811d7e72124c351ba5cec2ab91b0c71b6f91e2716c972f670e7`
  - Git blob `b31564a92c31297fd46d4b99ee1560e321ae0ab2`
- `tests/contract/test_layer1_daily_control_red.py`
  - SHA-256 `1f33f8c768841ac4d374c244b9c6549e9706b1a855e0cf55086fe81b5637c323`
  - Git blob `dd3e6d22e208640d7e630199b1c768345197be18`

## Failure reproduced and bounded

The exact failed GitHub run had ten failures, all in the daily-control contract file. Frontend checks
passed. Two local-state assumptions caused the Python failures:

1. `_py()` hard-coded the gitignored local `.venv/bin/python3.14`; that path does not exist on a
   clean CI runner.
2. A manual PlayerProfiler assertion required a non-null age even when its private, gitignored
   marker/data are absent. The honest no-marker state is `age_days=None`, `freshness=unknown`.

No failure outside the daily-control contract file was attributed to this change.

## Findings and dispositions

### F1 — interpreter validation failed open

The first repair used `sys.executable` but still accepted an empty interpreter and a directory because
it checked only path existence. Direct reproduction showed both cases returning `ok=True`.

Resolved at the evidence boundary:

- an empty component is rejected;
- every command component must be a real file;
- the interpreter must additionally be executable;
- runner scripts remain interpreter arguments and are not incorrectly required to carry an execute
  bit;
- the existing `command_not_found:` token remains compatible.

Boundary, missing-path, directory, non-executable, and valid-interpreter counter-cases are pinned.

### F2 — stale CI date

The regression-test docstring called the c55e645 CI failure a 2026-08-07 event. The commit timestamp is
2026-08-08 ET. The docstring and its claim-class sweep were repaired.

### Self-found — vacuous portability guard

The first new assertion compared `_py()` with `sys.executable`; locally those were already the same
string, so restoring the hard-coded path did not kill the test. The final test monkeypatches
`sys.executable`, and mutation testing proves that a restored hard-coded path is rejected.

## Falsification matrix

- Nominal: the real executable and pinned manifest routes pass.
- Boundary: empty, directory, and non-executable interpreter cases fail with specific reasons.
- Missing: a missing interpreter is rejected even when the runner script exists.
- Null/empty command: the existing command-absence contract remains enforced.
- Cross-component: interpreter validity is tested independently of runner-script validity.
- Synthetic override: a monkeypatched `sys.executable` proves the implementation follows runtime
  state rather than this laptop's path.
- Clean checkout: the focused three-file slice passed `90/90` in a tracked-files-only archive.
- Private-marker absence: manual freshness remains honest and non-failing in a clean environment.
- Mutation: each interpreter guard and the dynamic-interpreter guard was individually killed by its
  corresponding test.

## Gates

- Final controller contract file: `67 passed`.
- Focused tracked-files-only archive: `90 passed`.
- Claude's unmasked full local suite: `4,779 passed`, `12 skipped`, `9 xfailed`, true exit `0`.
- Ruff on the touched files: pass.
- Mandatory `scripts/verify_sprint_closeout.py`: true exit `0`; Python suite PASS, Ruff PASS,
  standalone scripts PASS; **ENFORCE verdict PASS**.

An archive-only whole-suite harness produced nine unrelated failures because `git archive` has no
`.git` metadata and no installed frontend dependencies. The same nine occurred against unmodified
HEAD, while the focused tracked-files-only slice reproduced all ten real Layer 1 CI failures before
the repair and zero afterward. This is supporting evidence, not a substitute for exact-SHA GitHub CI.

## Ruling

**CLEAR on the two reviewed blobs.** The correction is bounded to clean-runner portability and honest
manual-marker absence. It does not authorize scheduler installation, a paid source call, provider
contact, subscriber-data access, or changes to the frozen wire pair. Commit and fast-forward push are
authorized by David's standing instruction once the reviewed blobs and this durable record are pinned
unchanged. Exact pushed-SHA GitHub CI remains the final landing gate.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result.
