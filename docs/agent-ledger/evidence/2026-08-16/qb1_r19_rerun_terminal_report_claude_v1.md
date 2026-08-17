From Claude (write lane) — R19 rerun terminal report: failed closed at the SAME wall, NOW MEASURED — exclusion-row law at execution.py:1288-1302, execute-phase composition self-check; observability worked first fire [w#qb1-exec-1]

# QB-1 Round-19 CLEAR-authorized registered rerun — terminal report (Claude v1)

Date: 2026-08-16 (America/New_York)
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`

## 1. Exact one-run accounting

- Fired ONCE on the machinery resume wake after durable verification
  (revision 123, Round-19 CLEAR `0cd53b74…`, on-disk files at the reviewed
  pins); your CLEAR wire was matched to the same process (ACK
  `qb1_round19_clear_ack_claude_v1.md`, delivery verified).
- **Exactly one runner process:** PID 24181, 19:48:21 → ~20:16:34 ET
  (~28 minutes; the R18 fire took ~70 — recorded, not interpreted). Zero
  runner processes remain. No second run. No repair. No input mutation.

## 2. Terminal state

- `run_status` = **failed**; `failure_reason` = **`report_schema_invalid`**;
  `decision_supported` = **false**; runner exit **1**.
- Atomic six-key metric-free artifact:
  `app/data/backtest/qb_validation/qb_validation_report.json` SHA-256
  **`0c0cd6308a14dc44a177335ddafc2876f65e2010d3ae1748e8e912e197540956`**
  (296 bytes; `generated_at` 2026-08-16T23:48:21Z = fire minute, per the
  designed process-start stamp).
- Stdout receipt WITH the R19 diagnostic:
  `qb1_registered_rerun_r19_stdout_claude_v1.txt` SHA-256
  **`ceb2fba7a8c18b9b48380de5037e0e8b00c09f80681bc297a23e02700109bb7f`**
  (981 bytes).
- **No registered result was produced, read, or published. The grant is
  consumed.**

## 3. The R19 `failure_origin` — verbatim from the receipt

```json
{"phase": "execute", "sites": [
  {"path": "src/dynasty_genius/eval/qb_validation/execution.py", "function": "run_qb1_study",  "line": 2358},
  {"path": "scripts/run_qb1_study.py",                            "function": "execute",        "line": 1283},
  {"path": "scripts/run_qb1_study.py",                            "function": "compose_study",  "line": 1199},
  {"path": "src/dynasty_genius/eval/qb_validation/execution.py", "function": "validate_registered_report_blocks", "line": 1298},
  {"path": "src/dynasty_genius/eval/qb_validation/execution.py", "function": "_refuse",        "line": 965}
]}
```

The observability shipped in Round 19 did exactly its job on its first real
fire: no clause detail or registered value disclosed, the six-key envelope
unchanged, and the wall named to the line.

## 4. Clause identification (read-only, from the cited lines)

- **Phase `execute` is truthful and significant:** the refusal comes from
  `compose_study`'s DEFENSE-IN-DEPTH self-check
  (`scripts/run_qb1_study.py:1199` — "the runner re-runs this gate
  unconditionally at publication; this call is defense in depth at the
  composition seam"), so the composed success blocks refuse INSIDE the
  composition, before the publication gate is ever reached.
- **The refusing clause** (`execution.py:1288-1302`, the `_refuse` at
  `:1298`): every entry of a comparison row's `excluded_folds` must be a
  Mapping carrying a non-negative-int `test_season` AND a non-empty
  `reasons` list whose every member is in the registered
  `_FOLD_FLAG_VOCABULARY`. The REAL composed report carries at least one
  exclusion row violating this conjunction.
- **UNMEASURED and deliberately undisclosed by the receipt:** which
  comparison row, which conjunct (shape vs test_season vs empty vs
  out-of-vocabulary reason), and any offending value. Naming them needs your
  staged read-only measurement.
- Context for your read (cited, no lean): the gate's synthetic hardening
  (rounds 2–12) validated this law against fixture payloads; this is the
  first time the REAL producer's exclusion rows met it. Producer-side
  exclusion rows are assembled in the runner script's fold/status path
  (e.g. the `excluded_folds` producer around `contrast_status`); whether the
  correction is producer alignment (implementation) or vocabulary change
  (amendment) is exactly the registration-read question.

## 5. Standing authority

David's continuation word remains in the durable transition: *"ok lets
continue until we get throught h5"*, then *"go"*. Requested next step per the
sanctioned machinery: record the failed real-surface receipt, then stage the
continuation — presumably one read-only exclusion-row census bounded to
SHAPES and VOCABULARY WORDS (no metric values), routed for your registration
read. H2 QB rushing remains **UNDER TEST with no result**.

PLEASE REPLY with: (a) failed-receipt recorded + the staged continuation boundary, OR (b) named corrections to any fact above.
