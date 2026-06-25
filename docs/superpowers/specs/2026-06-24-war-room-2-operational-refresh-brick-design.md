# War Room #2 — Operational Refresh Brick — Design Spec (DRAFT v1 for cockpit dual-CLEAR)

**Status:** DRAFT v1. Makes the War Room #2 backend LIVE: a scheduled producer that runs the T2 report emitter daily so the read-only API (`GET /api/league/what-changed`, shipped PR #80 `a28ea42`) serves a real report instead of 503. Mirrors the WR#1 capture bricks (a `scripts/run_*.py` entrypoint + an `ops/launchd` LaunchAgent). Backend/ops only — **frontend HOLD intact.** Governance: `02-agent-operating-loop.md` → Compounding-product lens.

> **Banned-language note:** this spec does not spell forbidden David-facing verdict/action terms; the literal-list contract test governs the emitted report (already enforced in T2/T3).

## 0. Compounding-product lens
- **Daily-login value:** the digest only exists if something writes it daily; this brick is what turns the WR#2 backend into a living daily surface.
- **Refresh cadence:** once per day, AFTER the WR#1 captures land (FC 09:00, model 09:30) so the diff compares the freshest captured PIT rows.
- **Compounding:** as the capture series lengthens, the same producer yields richer day-over-day context for free.

## 1. Scope (backend/ops only)
A cwd-independent **CLI** that runs the existing `emit_daily_what_changed_report(...)` over the real production inputs and writes the overwrite-latest report, plus a **LaunchAgent** to run it daily. **No new analysis logic** — it is a thin operational driver over the shipped T2 emitter. No model/market/feature/PVO mutation; the report is the only output.

## 2. Prerequisite gap to close (FIRST)
`app/data/what_changed/` is **NOT yet gitignored** (WR#2 spec §6 required it; T2 shipped without it). The generated report is operational data and must never enter source control. **T1 adds `app/data/what_changed/` to `.gitignore` before any report is generated** (verified with `git check-ignore`).

## 3. Inputs / sources (all read-only; resolved from repo root)
- Market PIT: `app/data/fc_forward_capture.db`
- Model PIT: `app/data/model_forward_capture.db`
- Current Sleeper snapshot: `app/data/league_snapshots/sleeper_universe_snapshot_latest.json`
- Structural artifacts: `app/data/valuation/{team_posture,team_value_matrix,league_opportunity,roster_cut_report}_latest.json`
- Output (the ONLY write): `app/data/what_changed/what_changed_latest_report.json` (gitignored, overwrite-latest)
- Clock: injected `now_fn = lambda: datetime.now(timezone.utc)` (the emitter already requires an injected clock).

## 4. CLI contract (`scripts/run_what_changed_report.py`)
- Cwd-independent: `ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))` BEFORE the `from ...` imports (the WR#1 launchd `ModuleNotFoundError` lesson; covered by an out-of-repo standalone load test).
- `main(argv) -> int`; resolves the §3 paths from `ROOT`; calls `emit_daily_what_changed_report(...)` with `now_fn` injected; prints a concise summary (overall_status + per-source status) to stdout.
- `--preflight`: a **readiness check ONLY** (Codex) — report which inputs exist / are missing and the resolved report path. It must **NOT** call the emitter or attempt any dry-run write. Exit non-zero ONLY on a readiness failure (a *required* input missing, or the report parent dir unwritable); it never reflects ordinary degraded-data semantics. Writes nothing.
- **Honest exit codes:** exit 0 when the report is written — **including a degraded/unavailable report** (degraded is honest, not a failure). Exit non-zero ONLY on a real failure (unwritable path, unhandled exception). A degraded report must still be written + served.
- Read-only over all inputs; writes ONLY the report; **never** mutates the capture stores, PVO, or any model/feature path; **never** auto-commits (the report is gitignored operational data — the no-scheduler-commits rule).

## 5. LaunchAgent (`ops/launchd/com.davidleess.dynasty-what-changed-report.plist`)
- Daily **09:45 ET** (after FC 09:00 + model 09:30 captures so the diff sees the freshest rows), `RunAtLoad=false`, runs the project interpreter on the T1 CLI; stdout/stderr to `app/data/logs/what_changed_report.out.log` / `.err.log`.
- A scheduler-contract test asserts the plist runs the committed CLI path with the project interpreter and is not RunAtLoad.
- **Operational go-live (launchctl install/load) is David-gated, separate per-step authorization** (mirrors the WR#1 brick go-lives). This brick SHIPS the code; David runs the install.

## 6. Guardrails
Read-only producer: reads capture stores + structural artifacts, writes only the gitignored report; `decision_supported=false` is inherited from the emitted report (the API DTO already enforces it recursively); market stays a descriptive overlay and never enters a model path; divergence UNVALIDATED; honest degraded/insufficient states are written, never suppressed; no banned tokens (report governed by the existing literal-list test); **no auto-commit** of the operational report; legacy stores untouched.

## 7. Build sequence (cockpit TDD: Codex RED → Claude GREEN → dual-CLEAR → David-authorized commit)
1. **T1** — `.gitignore` adds `app/data/what_changed/` (verified) + the `scripts/run_what_changed_report.py` CLI (path resolution, injected `now_fn`, `--preflight`, `main(argv)->int`, honest exit codes, out-of-repo standalone load test, read-only/no-commit assertions).
2. **T2** — the LaunchAgent plist + scheduler-contract test + docs (ARTIFACTS / quick-reference). Then David-gated launchctl go-live (separate).

## 8. Falsification matrix seeds
Missing a capture db / structural artifact → the relevant section degrades, report still written, exit 0 (honest degraded) — never a crash; report path unwritable → non-zero exit + clear error, no partial/corrupt file; `--preflight` with no inputs → non-zero, no write; CLI run from outside the repo → imports resolve (standalone load test); the produced report path is gitignored (`git check-ignore` passes); the CLI writes NOTHING but the report (no PVO/store mutation, no commit); plist is `RunAtLoad=false` and points at the committed CLI + project interpreter.

## 9. Decisions — CLOSED (David-confirmed + cockpit-settled)
- **D1 — schedule time = 09:45 ET** (after both captures).
- **D2 — brick size = 2 tasks** (T1 CLI+gitignore, T2 plist+docs).
- **D3 — log path = `app/data/logs/what_changed_report.out.log` / `.err.log`.**
