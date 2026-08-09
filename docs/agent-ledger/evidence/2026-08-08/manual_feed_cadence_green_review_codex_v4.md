# Manual-feed cadence GREEN fourth review — Codex v4

**Verdict:** NOT CLEAR  
**Layer:** Layer 1 governed cadence-input integrity  
**Reviewed pins:** `ffe85416…`, `6ef0e894…`, `92c64ac5…`, `8df129ef…`

The operational failure axis, stream-enumerating fallback, and report-instant implementation now
hold on direct reproduction. Focused tests pass 134 and Ruff is clean. Three residuals remain at the
same evidence boundary.

## W1 — Nested input shapes and one calendar timestamp remain unvalidated

The boundary now validates top-level JSON shape and several calendar timestamps, but still returns
`INPUTS_OK` for all of these:

```text
calendar.combine_complete = "not-a-time"
held = ["not-a-map"]
held.pff = ["not-a-map"]
offer = ["not-a-map"]
availability = "not-a-map"
```

`combine_complete` is consumed by the PlayerProfiler `player_season` policy but is omitted from
`_REQUIRED_CALENDAR_TIMES`. Held, offer, and availability are traversed as nested mappings during
evaluation but their container/record shapes and evidence timestamps are not validated. The same
artifact can therefore still fail only when incidental source data reaches a bad branch—the exact
source-dependent guard defect this repair was meant to eliminate.

Required repair: validate every calendar key the engine consumes, plus every supplied top-level,
source-level, and stream-level held/offer/availability record and its required evidence fields and
timezone-aware timestamps. Add wrong-shape cases at each nesting level.

## W2 — The controller does not use one immutable input snapshot

Each `_manual_result()` calls `_load_cadence_inputs()` independently. A two-source controller run
loads twice; direct instrumentation returned `load-1` for PlayerProfiler and `load-2` for PFF. If
the file changes mid-run, one aggregate report can combine different control-plane vintages.

Required repair: load and validate once in `execute()`, then pass the same status/payload/detail to
every manual source. Pin loader call count == 1 and identical input identity/metadata across all
manual results.

## W3 — Two new regression tests do not behaviorally prove their claims

- The ABSENT test calls `_manual_result(inputs=None)`, which reads the real production path. It
  passes only because the artifact does not exist today; the next slice is explicitly meant to add
  that artifact. Monkeypatch the loader to return ABSENT so the counter-test stays hermetic.
- The same-instant test greps `inspect.getsource()` for two strings. It can pass while a helper
  re-reads the clock or while the implementation otherwise computes at the wrong instant. This is
  the source-proxy class previously rejected. Exercise an event boundary behaviorally with a pinned
  checked-at instant and a deliberately conflicting wall clock.

No source execution, scheduler, paid action, provider contact, commit, or push occurred.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
