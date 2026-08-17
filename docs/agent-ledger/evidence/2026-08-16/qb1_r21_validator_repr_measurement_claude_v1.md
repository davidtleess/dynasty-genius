From Claude (write lane) — STOP per your instruction: RED measurement PROVES the unchanged validator invokes hostile __repr__; publication path escapes ARTIFACT-LESS; routed as scope/registration-read conflict [w#qb1-exec-1]

# QB-1 Round-21 validator-repr measurement — Claude v1

Date: 2026-08-16/17 (America/New_York)
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`, revision 129, Round 21 open
Status: **STOPPED before GREEN** per `[w#88asmhoo-1]` — nothing masked in the
adapter, no scope widened, `execution.py` untouched, the repr-era adapter
still at the opening pin (runner `ec19067c…`).

## RED census at the opening pins (contracts now at the R21 RED state)

- 3 failed / 2 passed on the new rows: pass-through re-specification FAILS
  (current adapter still reprs), adapter-level hostile-repr FAILS (current
  adapter reprs) — both the expected pre-GREEN REDs — and the e2e
  hostile-repr row FAILS with the MEASUREMENT below. The 2 passes are the
  disclosed regression guards (plain-string unreadable shapes refuse at the
  gate e2e with the required name; unrelated-metadata token passes through).

## The measurement (exact, from the observed traceback)

Test `test_r21_hostile_repr_end_to_end_named_failure` — a Mapping exclusion
entry whose `reasons` value raises in `__repr__`, submitted through the
PUBLIC runner (`_run` → `qb.run_qb1_study`, publication path; the adapter is
NOT in this path):

```
tests/.../test_qb1_green_correction_contracts.py:4319  (the e2e row)
tests/.../test_qb1_green_correction_contracts.py:223   (_run)
src/.../execution.py:2413   run_qb1_study — the ok-path gate call
                            validate_registered_report_blocks(report, ...)
src/.../execution.py:1301   the exclusion clause's refusal —
                            _refuse(f"comparison {row.get('id')}: an
                            exclusion row needs test_season and non-empty
                            registered reasons, got {entry!r}")
RuntimeError: r21-hostile-repr-sentinel   (raised inside {entry!r})
```

**Measured consequences:**

1. The unchanged validator's eager `{entry!r}` interpolation invokes the
   hostile `__repr__` BEFORE `QBValidationFailure` is constructed, so the
   named refusal never comes into being.
2. On the PUBLICATION path the RuntimeError escapes `run_qb1_study`
   entirely — the surrounding catch accepts `QBValidationFailure` only — so
   the runner raises with **NO terminal artifact written**: an artifact-less
   escape, in tension with the R2-G1 every-invocation-terminal-artifact
   guarantee. (Not merely `execution_error`.)
3. Code-read inference, labeled as such (not separately measured): on the
   REAL registered path the same interpolation fires inside `compose_study`'s
   defense-in-depth call (execute phase), where the generic `except
   Exception` converts it to `execution_error` — artifact written, R19
   diagnostic lost.

## Scope facts for your registration read (no lean)

- The required Round-21 e2e proof ("failure_reason=report_schema_invalid and
  never execution_error" under hostile `__repr__`) is UNACHIEVABLE within
  the two-file scope: the failing surface is `execution.py:1298-1302` (and
  every sibling `_refuse(f"... {value!r}")` interpolation in the validator
  family is the same class), which the current round forbids touching.
- The adapter-side correction (remove repr inspection; structural token
  inspection only; unreadable shapes pass through) remains implementable and
  correct regardless of the validator question — it is written as RED and
  awaiting your ruling before GREEN proceeds.
- Robustness-boundary framing (02 §Falsification #8): the real producer
  emits plain str/int reasons; a raising `__repr__` is API-misuse-class
  input. Whether the validator must be hardened (an `execution.py` change =
  new bounded scope), or the hostile-repr e2e requirement re-specifies to
  the adapter-level + plain-shape gate rows, is exactly your
  scope/registration-read call.

H2 QB rushing remains **UNDER TEST with no result**.

PLEASE REPLY with: (a) the ruled path (re-specified Round-21 proof matrix OR a widened/staged validator-hardening scope) so GREEN can proceed, OR (b) further read-only measurements you require first.
