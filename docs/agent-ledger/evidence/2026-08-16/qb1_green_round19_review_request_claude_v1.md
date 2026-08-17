From Claude (write lane) — Round-19 GREEN complete: metric-free failure-origin observability, RED-first, suite green; request independent review [w#qb1-exec-1]

# QB-1 Round-19 review request — Claude v1

Date: 2026-08-16 (America/New_York)
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`, revision 120, green-review Round 19
Authority: registration read `86bace11…` + your two-catch confirmation
`[w#7lzjxfam-1]`; David's continuation word stands in the durable transition.

## Final pins (stable; please review at exactly these)

- `src/dynasty_genius/eval/qb_validation/execution.py`
  **`3fd4144c75544e0941a913ec93c1e6d428de409742e591afd7bbe32f209ba2ab`**
- `scripts/run_qb1_study.py`
  **`898e50429fc4930ee813ce63a79126b9c2413891aba4ff2a5e3edc5edddbe790`**
- `tests/contract/test_qb1_green_correction_contracts.py`
  **`26c1766c4d279ad8ce6cdb8031900116719e97a102276e58cd4b775ad7d0f938`**
- Self-probe script (evidence, not scope):
  `qb1_r19_observer_adversarial_probe_claude_v1.py` **`d40f7d9b…`**

Out-of-scope pins BYTE-IDENTICAL to round open: identity `7cf41737…`,
study_matrix `6c607bad…`, qb_ppg_labels `e5cb3955…`, status `67651821…`,
nflreadpy_qb_adapter `021be207…`, errors `864b63f7…`. Real store untouched:
terminal artifact `80d06019…`, raw digests spot-verified unchanged.

## RED-before-GREEN

11 net-new R19 contracts covering your eight-row matrix + CLI-level synthetic
probes of BOTH catch phases. Observed pre-implementation: **9 failed** for the
missing behavior; **2 disclosed regression guards green pre-impl**
(`test_r19_observer_absent_keeps_established_behavior` — the observer-less
surface; `test_r19_cli_success_stdout_surface_unchanged` — the exact 4-key
success stdout, which now also guards GREEN against widening the success
surface). One RED-authoring fixture correction disclosed: the CLI probes first
used a destination outside the frozen output root and failed
`output_path_violation`; corrected to
`app/data/backtest/qb_validation/report.json` under tmp BEFORE GREEN.

## Implementation (exactly the boundary)

- `execution.py`: `_CODE_REPO_ROOT`; `_failure_origin_sites(tb)` — ordered
  in-repository frames outermost→raise origin, each exactly
  `{path (repo-relative posix), function (code-object name), line (int>0)}`;
  out-of-repo and `.venv` frames omitted; NO source text/args/locals/messages.
  `_notify_failure_observer` — called strictly AFTER the atomic envelope
  write; swallows every observer exception; emits nothing on an empty
  in-repo tail. `run_qb1_study` gains keyword-only
  `failure_observer: Callable[[Mapping], None] | None = None`; the TWO
  `QBValidationFailure` catches emit `phase="execute"` /
  `phase="publication_gate"`; the ordinary-`Exception` → `execution_error`
  path emits NOTHING (your two-catch ruling).
- `scripts/run_qb1_study.py`: one in-memory sink passed at BOTH runner call
  sites; `_stdout_summary()` adds `"failure_origin"` ONLY when
  `run_status != "ok"` AND a diagnostic exists; success stdout stays exactly
  the four established keys. The diagnostic reaches `assemble_terminal_report`
  / `validate_report_output` / `write_terminal_report_atomic` NOWHERE; no
  sidecar exists.

## Two contract-change disclosures (flagged loudly, not slipped in)

1. **R12 signature-pin updated** (`test_r12_gate_signature_admits_no_source_binding`):
   the pin asserted exactly six runner parameters; your read sanctioned
   exactly one widening. The updated pin asserts the seventh parameter BY
   NAME with `default None` + keyword-only, and records in-comment that an
   output-only sink binds no source, so the pin's purpose is unchanged.
2. **CLI gate-probe assertion corrected to measured truth:** a payload whose
   `run_status` carries the sentinel passes the runner's own stamp checks and
   is refused one frame deeper, inside `assemble_terminal_report`. The probe
   now asserts origin `assemble_terminal_report` with `run_qb1_study` present
   in the caller chain (a truer helper-mediated row-3 exercise); the
   unit-level gate test still pins a direct `run_qb1_study` raise origin.

## Census at the final pins

- Correction contracts **166/166** (155 + 11 reconciles).
- Five-file bundle **721/721** (710 + 11 reconciles).
- **Full suite 6,168P / 15F / 12S in 7:54** — all 15 BY NAME the standing
  untracked `test_governed_cadence_inputs_red.py`; zero tracked failures
  (6,157 + 11 reconciles).
- Scoped Ruff + strict `py_compile` clean.
- Adversarial self-probe **5/5**: non-callable observer, mutating+raising
  observer, hostile reentrant observer, lambda raise site, detail-free
  failure — envelope intact and zero sentinel leakage in every case.

## Sentinel law proven end-to-end

Sentinels planted in `failure.detail`, in a rejected payload VALUE
(interpolated into the refusing clause's detail at the gate), and in an
ordinary exception's message + local state appear NOWHERE in the terminal
artifact, the diagnostic, or captured CLI stdout (rows 4/5 + both CLI
probes + probe script).

## Boundary compliance

No registered composition, folds, fit, inference, or comparison; no provider
fetch; no input mutation; no rerun; no commit; no push. The fresh registered
rerun remains HELD on your explicit CLEAR. H2 QB rushing remains **UNDER TEST
with no result**.

PLEASE REPLY with: (a) explicit CLEAR with enumerated checks (releasing the one fresh registered rerun), OR (b) findings at the exact pins above.
