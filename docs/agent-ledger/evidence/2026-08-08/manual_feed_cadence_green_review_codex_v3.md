# Manual-feed cadence GREEN re-review — Codex v3

**Verdict:** NOT CLEAR  
**Layer:** Layer 1 acquisition obligation and controller integrity  
**Reviewed pins:** `ffe85416…`, `6ef0e894…`, `62a1d4ba…`, `2a5426e3…`

The prior no-input visibility and single-clock mechanisms now reproduce correctly on the live
dry-run surface: PFF has 15 declared streams, PlayerProfiler 5, and RotoViz/Campus2Canton 1 each;
every absent-evidence stream reports `undetermined` / `unknown`. Focused tests still pass 119 and
Ruff is clean.

## V1 — Invalid governed inputs fail open

Malformed JSON now produces `manual_inputs_invalid`, but the result carries `failed=False`; the
aggregate controller exits 0. A corrupt control-plane artifact therefore looks successful to a
scheduler or monitor even though the controller cannot determine any manual acquisition
obligation. Coverage gaps are not run failures, but unreadable/invalid governed configuration is an
operational failure and must be distinguished from both coverage and cadence.

Direct reproduction over all manual entries:

```text
malformed JSON -> controller exit 0
pff/playerprofiler -> manual_inputs_invalid, failed=False
```

Required repair: invalid governed inputs set the operational failure axis and aggregate exit
nonzero while isolation still permits independent automatic sources to run and report.

## V2 — Boundary validation does not validate the declared schema or timestamps

`_validate_inputs()` checks only that `calendar` is an object and that three keys are present. It
does not validate their types/timestamps, nor the optional held/offer/availability shapes. A
calendar with `week1_kickoff="not-a-time"` passes the boundary. With that same global artifact:

```text
playerprofiler -> manual_undetermined, streams=5
pff            -> manual_inputs_invalid, streams=0, CadenceError
controller     -> exit 0
```

The artifact is globally invalid, but the error appears only when one source happens to traverse
the bad value. This contradicts the claim that schema/timestamps are validated at the evidence
boundary and yields source-dependent truth from one artifact.

Required repair: validate calendar values and all supplied mapping/record shapes before source
evaluation. One validated immutable input snapshot should govern the whole controller run. Invalid
global evidence must be identified consistently without depending on which streams happen to be
held.

## V3 — The exception-isolation fallback drops the stream contract

The manual exception guard preserves process isolation, but serializes `streams={}`. Any unexpected
evaluation error therefore reintroduces the exact omission R1 repaired. The invalid timestamp
reproduction above demonstrates it on PFF.

Required repair: isolation fallbacks must enumerate every declared source stream as
`undetermined` / `unknown`, retain the explicit operational failure, and name the error.

## V4 — No controller regression tests were added for R1–R3

The focused count remains 119. Searches of the controller contract find no tests for
`manual_inputs_invalid`, malformed/partial inputs, stream enumeration on the execute surface, or
the single checked-at evaluation instant. The production changes are therefore unguarded and the
suite passes the fail-open behavior above.

Required repair: add behavioral controller tests for absent, malformed, wrong-shape, invalid-time,
route-incomplete, same-instant, and isolation-with-later-healthy-route cases. Mutate each guard to
prove its test fails for the intended mechanism.

No source was executed; diagnostic runs wrote only beneath `/private/tmp`. No scheduler, paid
action, provider contact, commit, or push occurred.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
