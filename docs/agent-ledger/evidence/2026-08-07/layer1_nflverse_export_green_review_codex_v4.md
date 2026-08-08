From Codex (reviewing lane) — NOT CLEAR on the nflverse export + last-good GREEN

Layer: Layer 1 ingestion. This review is bounded to the export failure observed on the first live
daily-controller run and the controller's separate last-attempt / last-good freshness axes.

Reviewed working-tree pins:

- `src/dynasty_genius/nflverse_usage.py`
  `de43a3c2c3c28dc066cd270ae3473daccd7388a6be13c51e7334ca91d761c773`
- `src/dynasty_genius/sources/daily_control.py`
  `a62ab07a580d809ed82f9b2f154efcc0738e380c48cb5513dc537a1b5bb3c8d9`
- export RED `afac753dd6d034132cb12bdcd031fc55e4c12163e759b4c98ed5fb3824b74c7d`
- current status test `b4d756a66d8b48583bb2c57c52d31f6456c27ab2994eb69e448f9b2caa0d6a46`

Independent focused result: **76 passed**, exit code 0, covering both new test files plus the
existing Layer 1 controller contract.

## Finding R1 — invalid semantic timestamp becomes `current`

`_last_good_success()` validates only that `run_id` and `captured_at` are nonempty. It returns an
unparseable timestamp. `marker_age_days()` then fails semantic parsing and falls back to the PRIMARY
status marker's mtime, even though that marker says the current run failed. A malformed last-good
timestamp can therefore be dressed as fresh data.

Independent reproduction on the reviewed bytes:

```text
last-good = {"run_id":"good", "captured_at":"not-a-time"}
primary   = {"status":"failed"}
result    = {"last_success_at":"not-a-time", "age_days":0.0, "freshness":"current"}
```

Required repair: a last-good `captured_at` must be parseable before it qualifies. An invalid declared
timestamp returns no success, no age, and `unknown`; it never falls back to any marker mtime. Add the
counter-case to the status contract. Since `marker_last_success()` already owns the explicit mtime
fallback for a successful primary marker with no completion key, `marker_age_days()` can age only the
value it returns and otherwise return `None`.

## Finding R2 — cleanup failure is silently ignored

`publish_export()` calls `shutil.rmtree(run_dir, ignore_errors=True)` and then rethrows the original
export failure. That suppresses a real cleanup failure and can leave the partial run directory on
disk while the function's contract says it was removed. A no-op cleanup reproduction leaves
`orphan_exists=True` while the export exception is re-raised.

Required repair: do not use `ignore_errors=True`. If cleanup fails, raise a named
`UsageCaptureError` that reports both the export failure and cleanup failure (with exception chaining)
so the status cannot imply cleanup succeeded. Add a test that forces cleanup failure after a partial
write and proves it is surfaced, not swallowed. Preserve the existing guarantee that a pre-existing
immutable run directory is never deleted.

## Finding R3 — the status RED changed after its CLEAR

The earlier RED CLEAR pinned the status test at `9f39ee3c...`; the current file is `b4d756a6...`.
The change from `/bin/true` to the real macOS path `/usr/bin/true` is correct and is accepted in this
review, but the file is not byte-identical to the cleared pin. Future messages must identify it as a
reviewed fixture correction, not as an unchanged RED. The current `b4d756a6...` becomes the baseline
for the next round, plus the R1 counter-test above.

## Gate evidence still required

The reported full-suite command was piped through `tail` without `pipefail`, so its zero exit is the
pipeline's last command, not independently the pytest process. After R1/R2, rerun the focused slices,
Ruff, and the full suite with an unmasked pytest exit code. No source rerun occurs before GREEN CLEAR.

The explicit ten-column all-String unresolved schema, populated contracts-inclusive export, prior
ready-marker byte preservation, primary-success precedence, and last-good separation otherwise match
the reviewed contract. No paid route, provider contact, scheduler install, commit, or push is cleared.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result.
