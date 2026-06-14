---
title: Governed Sprint-Closeout Verifier — Design Spec
status: DESIGN SPEC v2 — round-1 cockpit findings integrated. Form/scope = three-lane consensus + David-accepted 2026-06-14 (script + 02 amendment, NO separate skill, scope B). v2 integrates Gemini governance CLEAR + Codex technical findings: Q1 collection-error premise was STALE (live `pytest --collect-only` clean at 1961 tests, verified 2026-06-14) → no --ignore/baseline; Q2 ruff invoked at CI scope `ruff check src app` (pinned 0.15.12), NOT `python -m ruff` (not installed) and NOT pre-commit `--all-files` (53 out-of-CI-scope legacy issues); surface detection covers staged/unstaged/untracked; standalone-script-check semantics tightened; --phase dropped; text-only; artifact diff REPORT-only.
date: 2026-06-14
author: Claude Code (impl), via cockpit consensus with David, Codex, Gemini
governance_hold: This is a process/verification tool — NOT a model/analytics change. No Engine A/B feature/training/threshold change; no market data; no decision_supported semantics; no banned David-facing output. The verifier is read-only over the repo + runs existing test/gate commands; it never mutates source, artifacts, or git state.
scope_guard: New file scripts/verify_sprint_closeout.py + a surgical amendment to docs/governance/02-agent-operating-loop.md. No other production code touched. 02 remains the single source of truth for cockpit philosophy; this spec adds the "how" (deterministic ship-time enforcement), never re-codifies the "why".
related:
  - docs/governance/02-agent-operating-loop.md (cockpit process, falsification discipline, close-the-loop — the WHY; this verifier is the WHEN/HOW tollgate it will reference)
  - The 2026-06-13/14 Step 0.5 build, whose T8 full-suite reconciliation caught 3 latent issues that motivated this tool
---

# Governed Sprint-Closeout Verifier

> "Sprint-closeout" = the final ship/PR tollgate of a multi-task build or phase, not a per-task gate. This is run ONCE before claiming a build verified/complete or before push/PR — never after every small task.

## 0. Why this exists

In the Step 0.5 build, per-task verification used **focused test slices** (`pytest tests/test_x.py`) to keep cadence fast. That deferred the full Python suite, the full FE gate (vitest), the inviolate audits, and the OpenAPI drift guard to the final task (T8) — where **three latent issues surfaced at once**: a new module broke the Subsystem-4 exact-set eval-allowlist audit (latent ~6 tasks); a required-field schema change broke FE vitest mocks (T6 ran typecheck but not vitest); the OpenAPI snapshot drifted red T1→T5.

`02-agent-operating-loop.md` already establishes the *theory* (falsification discipline, cockpit TDD, close-the-loop) but relies on the agent's memory to manually assemble the full ship-time test matrix. **The net-new value here is deterministic enforcement**: a single repo-resident, agent-agnostic command that runs the full matrix and emits the non-automatable human-judgment reminders — so the "focused-slice deferral" class of miss becomes hard to skip.

## 1. Scope (consensus + David-accepted)

- **In:** a pre-ship verification guard (Option B). A deterministic script + a surgical `02` amendment mandating it at the ship/PR tollgate.
- **Out (rejected unanimously):** an end-to-end cockpit-TDD "build driver" (Option A) — it would flatten the deliberate human adversarial loop + David authorization gates that make the discipline work.
- **Form:** `scripts/verify_sprint_closeout.py`, agent-agnostic (Claude / Codex / Gemini / human all run it), **no separate skill** (a skill would duplicate `02` and, as an Antigravity-bound `SKILL.md`, be lane-mismatched).

## 2. Three-tier model (ENFORCE / REPORT / REMIND)

Not everything can be deterministically enforced generically; pretending otherwise would be false confidence. The verifier classifies every check into one of three tiers, and says which is which in its output:

- **ENFORCE** — deterministic pass/fail; a failure sets a non-zero exit code.
- **REPORT** — surfaces a changed surface that needs a human/agent audit the script cannot generically adjudicate (e.g., "these tracked data artifacts changed — audit the allowed-path diff").
- **REMIND** — non-automatable human-judgment gates printed to stdout regardless of pass/fail (e.g., "commit/push/merge and inviolate-surface amendments require David's explicit authorization; route decisions through the cockpit; close the loop after hard-to-reverse ops").

## 3. The verifier — design

### 3.1 Invocation
```
.venv/bin/python3.14 scripts/verify_sprint_closeout.py [--base <ref>]
```
- `--base` (default `origin/main`): the ref to diff against for **surface detection**.
- Read-only: never mutates source, artifacts, or git state. Text-only output (the consumer is the agent's context window; no `--json` in v1).
- PR/merge mechanics are deliberately OUT — this is a local verification tollgate, not a GitHub CLI wrapper (`--phase ship` dropped per Q4).

### 3.2 Surface detection (principle-level, repo-general)
Detect which surfaces changed — never hardcode Step-0.5 paths. The change set is the UNION of committed (`git diff --name-status <base>...HEAD`), **staged** (`--cached`), **unstaged** (working tree), and **untracked** (`git ls-files --others --exclude-standard`) — a pre-ship verifier must catch uncommitted work, not just committed diffs (Codex F4):
- **Frontend touched** = any path under `frontend/`.
- **Executable scripts touched** = any changed `scripts/**.py` (or other entrypoints).
- **Tracked data artifacts touched** = changed files under data/artifact dirs (e.g., `app/data/**`).
- **New files added** = added paths across the union (candidates for a guarded-directory audit).

### 3.3 ENFORCE checks (deterministic pass/fail → exit code)
- **Full Python suite** — `.venv/bin/python3.14 -m pytest` over the whole suite (NOT focused slices). This **subsumes** the inviolate audits (e.g., the S4 exact-set eval-allowlist audit) and any pytest-based OpenAPI drift guard, so a new file in a guarded directory is caught here. **No exclusion list / baseline (Codex F1):** live `pytest --collect-only` is clean at 1961 tests (verified 2026-06-14) — the CLAUDE.md "2 collection-error files" note is stale; the verifier runs the full suite plainly and fails on ANY failure or collection error (which preserves Gemini's intent: fail loudly on a NEW collection error, since none are baselined).
- **Ruff** at CI scope (the CI hard gate): assert `.venv/bin/ruff --version` equals the CI/pre-commit pin (`0.15.12`), then run `.venv/bin/ruff check src app` (Codex R1; verified present + passing 2026-06-14 — `.venv/bin/ruff` is a console-script binary even though `python -m ruff` is absent). Do NOT use `python -m ruff` (not importable in the venv), `uvx ruff@0.15.12` (attempts user-cache setup, which failed in-env), or pre-commit `ruff-check --all-files` (surfaces legacy `tests/`+`scripts/` findings OUT of the CI gate's `src app` scope). The verifier NEVER installs/downloads ruff; if the pinned binary is absent or the wrong version, ENFORCE fails loudly with an actionable install/update message.
- **Full FE gate** — *only if frontend touched*: `npm --prefix frontend run typecheck`, `lint`, `test` (vitest), `banned-language`, `build`. Discovered from `frontend/package.json` scripts (use ACTUAL script names — `typecheck`/`lint`, not assumed `tsc`/`biome`), never hardcoded command strings.
- **Standalone-invocation check** — *only if executable scripts touched*: for each changed `scripts/**.py`, verify it loads under direct-execution import semantics — a fresh subprocess whose `sys.path[0]` is the script's own directory (repo root NOT auto-added, replicating `python scripts/foo.py`), importing the module body only via `importlib` so module-level imports/`sys.path` bootstraps execute but `if __name__ == "__main__"` / `main()` side effects do NOT run. PASS iff no `ModuleNotFoundError`/`ImportError`/`NameError` at module load (the `No module named 'src'` class pytest masks); the check asserts loadability, not behavior (Codex F3).

### 3.4 REPORT checks (surface for human/agent audit, no pass/fail verdict)
- **Tracked data-artifact changes** — list changed `app/data/**` files + a per-file path-level diff summary vs `<base>`, so the operator audits the allowed-path invariance (the verifier cannot know the task-specific allowed-path set). 
- **New files in candidate guarded directories** — list added files + flag "confirm the directory's inviolate/allowlist audit (run in the full suite above) is green and, if it amends an audit allowlist, that the amendment is David-authorized."
- **Generated-artifact staleness hints** — if an input to a known generator changed (e.g., a backend contract feeding `openapi.json`), REPORT "regen + drift-check may be required."

### 3.5 REMIND checklist (stdout, always printed — human-judgment gates)
Printed at the END of the run (so it is the last thing read), regardless of exit code:
- Commits, pushes, merges, branch deletes, and inviolate-surface amendments require **David's explicit authorization** — never self-authorized.
- Decisions (spec/plan/contract/merge-strategy) route through the **cockpit** (Codex technical + Gemini governance) before David.
- After any hard-to-reverse op (commit/push/merge/delete) send the **close-the-loop** post-action confirmation to both reviewers.
- Treat **CI** (not local-green) as the push gate; this verifier is local pre-flight, not a CI substitute.
See `02-agent-operating-loop.md` for the binding doctrine — this is a reminder, not a restatement.

### 3.6 Exit semantics
- Exit `0` only if every ENFORCE check passed.
- Exit non-zero if any ENFORCE check failed (prints which).
- REPORT and REMIND output is informational and never alters the exit code.

## 4. The `02-agent-operating-loop.md` amendment (surgical)
Add a short subsection under the Postflight / Git-and-PR area, principle-level:

> **Sprint-closeout tollgate.** Before claiming a multi-task build or phase is verified/complete, and before any push or PR, run `scripts/verify_sprint_closeout.py`. All ENFORCE checks must pass; the REPORT items must be audited; the REMIND human-judgment gates (David authorization, cockpit routing, close-the-loop, CI-as-gate) must be satisfied. Focused per-task test slices are acceptable mid-build, but the full suite + full FE gate run here is the binding closeout verification. This tollgate does not replace cockpit review or David's authorization — it ensures the deterministic matrix is not skipped.

No other `02` content changes; the philosophy stays as-is.

## 5. Anti-staleness / repo-general design
- Discover commands from the repo (FE scripts from `package.json`; the test runner from the venv), never hardcode tool names that drift (`typecheck` not `tsc`).
- Surface detection is git-diff-based, not a maintained path map.
- No Step-0.5-specific paths, SHAs, thresholds, or module names anywhere.
- The inviolate audits are enforced *transitively* by running the full suite, so the verifier needs no guarded-dir→audit map to maintain.

## 6. Testing strategy (cockpit TDD)
Codex RED → Claude GREEN, on synthetic fixtures (a temp git repo / monkeypatched diff + stubbed subprocess runners) so tests are fast and deterministic:
- surface detection classifies FE / script / artifact / new-file changes correctly from a synthetic diff;
- ENFORCE orchestration runs the right checks for the detected surfaces and aggregates pass/fail into the exit code (stub the heavy runners — assert *which* commands would run, not re-run the real suite);
- a failing ENFORCE check → non-zero exit; all-pass → exit 0;
- REPORT lists changed artifacts/new-files; REMIND checklist always prints.
Falsification rows: no-change diff, FE-only change, script-only change, artifact-only change, mixed; a stubbed-failing suite; missing `package.json` script; a script with a standalone-import failure.

## 7. Exclusions (anti-bloat — unanimous)
- Engine A/B model thresholds, the Step 0.5 status logic, any analytics.
- Cockpit role prose, the generic RED→GREEN TDD loop, David-authorization doctrine (all live in `02`; the verifier REMINDS, never restates).
- "Run the full suite after every small task" — this is a ship/phase-CLEAR gate only.
- A separate skill / SKILL.md.

## 8. Q1–Q5 — RESOLVED (round-1 cockpit)
- **Q1 (collection errors): RESOLVED — no ignore/baseline.** Premise was stale; live `pytest --collect-only` is clean at 1961 tests (verified 2026-06-14). Run the full suite plainly; fail on any failure or NEW collection error (Codex F1; supersedes Gemini's stale-premise `--ignore` answer — Gemini's fail-loud intent preserved).
- **Q2 (ruff): RESOLVED — `.venv/bin/ruff check src app`, version-asserted.** Assert `.venv/bin/ruff --version == 0.15.12` then run `.venv/bin/ruff check src app` (Codex R1, evidence-verified). NOT `python -m ruff` (absent), NOT `uvx` (failing user-cache step), NOT pre-commit `--all-files` (out-of-scope legacy). No install/download in the verifier; fail loud on absent/wrong-version.
- **Q3 (artifact diff): RESOLVED — REPORT-only.** The allowable diff is task-contextual (cannot be generically enforced); operator/agent audits it (Gemini + Codex concur).
- **Q4 (phases): RESOLVED — dropped.** Local verification tollgate only; PR/merge mechanics stay a separate interactive concern (Gemini + Codex concur).
- **Q5 (format): RESOLVED — text-only.** Agent reads stdout; no `--json` in v1 (Gemini + Codex concur).

## 9. Round-2 residuals — RESOLVED
- **R1 (ruff invocation): RESOLVED** — `.venv/bin/ruff check src app` after a `--version == 0.15.12` assertion; no uvx, no install/download; fail loud on absent/wrong-version (Codex R1, evidence-verified 2026-06-14).
- **R2 (Q1 cross-lane): RESOLVED** — Gemini concurs the stale-premise correction holds (suite collects clean; fail-loud-on-any-collection-error preserves the governance intent).

## 10. Cockpit status
Spec v2: Gemini governance CLEAR (firm through v2) + Codex technical CLEAR (after the R1 text fix in §3.3/§8, now applied). DUAL-CLEAR. Pending David's spec review → writing-plans → cockpit-TDD build.
