# Manual-feed cadence GREEN review — Codex v1

**Verdict:** NOT CLEAR  
**Layer:** Layer 1 acquisition obligation, coverage, and controller reporting  
**Reviewed pins:**

- `src/dynasty_genius/sources/feed_cadence.py` — `8158c8f7eb6012b3280e08b66225abbc5b736fa519d646d557c901f70c8bc583`
- `tests/contract/test_manual_feed_cadence_red.py` — `9d1c1f6ce942c6203f3faf22fbf3c192c29fa47421d3ad5f55c82e41e3e77d14`
- `src/dynasty_genius/sources/daily_control.py` — `9cac841026633383211b19bc0f00d77b8802cbdcdff791364790c71847cd4d03`
- `tests/contract/test_layer1_daily_control_red.py` — `a9ab92bec34d0a90c423aecb1fd414b5cca8590ff979037721dd1ac1198abb35`

## Independent gates

- Focused cadence/controller/last-good slice: true exit 0, 119 passed.
- Ruff over all four reviewed paths: exit 0.
- `git diff --check`: clean.
- Frozen wire pair remains byte-exact at `b3247ec8…` / `fd924eb1…`.

Passing gates do not establish the requested product outcome. The following findings reproduce outside the tests.

## F1 — The live controller still implements the rejected one-day manual clock

`daily_control.py::_manual_result()` does not import or call `feed_cadence`. It still computes
`due = age is None or age > 1.0` and emits `manual_due` / `freshness="due"`. The production change
only replaces four manifest strings from `daily` to `windowed`; execution ignores that field.

Read-only reproduction, with the report redirected to `/private/tmp`:

```text
.venv/bin/python3.14 scripts/run_layer1_daily_control.py --dry-run \
  --report-root /private/tmp/layer1-green-audit --json

pff             state=manual_due  freshness=due  age=7.168d
playerprofiler  state=manual_due  freshness=due  age=7.568d
```

This is the exact false alarm David asked us to remove. The prior S8 ruling expressly authorized
removing the flat clock **and wiring per-stream cadence/reporting**. Deferring the wiring leaves the
user-facing Layer 1 status false.

Required repair: production controller output must be derived from the per-stream engine using
real, governed calendar/inventory/offer evidence. If an input does not yet exist, serialize the
affected stream as `undetermined` / `unknown`; do not fall back to the one-day age rule. Add an
end-to-end controller contract proving the August held state does not report PFF or PlayerProfiler
as age-based due and that all declared streams and both axes reach the aggregate report.

## F2 — Every `operator_drop` policy is inert

`medical`, `rotoviz.export`, and `campus2canton.export` declare `operator_drop` as their only
trigger. `_last_event()` handles calendar triggers and correction-class provenance, but never
handles `operator_drop`. A newer observed drop therefore does not create an obligation.

Direct reproduction with held data ingested August 1 and a newer offer observed August 8:

```text
playerprofiler.medical -> cadence=not_due, trigger=None
rotoviz.export         -> cadence=not_due, trigger=None
```

Required repair: define the evidence boundary for an observed drop and make a post-ingest
`operator_drop` event produce `due`; after durable ingestion it must return to the appropriate
non-due/current state. Pin this lifecycle behaviorally for all policies that rely on the trigger.

## F3 — The manifest asserts a determined window for undetermined sources

The cadence engine and tests correctly say RotoViz and Campus2Canton have no inventory/marker and
must report cadence `undetermined`. The manifest simultaneously assigns both
`refresh_target="windowed"`. That claims a scheduling class has been determined when the evidence
says it has not. Under David's all-ingestion authority, undetermined cadence is the boundary: it may
not be converted into a fictional window.

Required repair: represent the target as undetermined (or absent with an explicit reason) until the
first-drop inventory establishes real change triggers. Do not use one blanket value for all manual
sources.

## F4 — Game-week completion is synthesized, not observed

`_game_week_completions()` manufactures every event as `week1_kickoff + 4 days + 7n` and even calls
that "about four days." This is a timer approximation, not an injected completion fact. It can be
wrong for atypical weeks and the final week, and it conflicts with the module's own rule that an
acquisition becomes due only at an observable event window.

Required repair: inject/freeze explicit per-week completion or provider-availability events from a
governed schedule source. The engine may compare those facts to ingestion time; it must not invent
them from a recurring offset.

## F5 — The source rollup can call an unknown obligation `not_due`

`_rollup_cadence()` returns `not_due` for a mixture of `not_due` and `undetermined`. Claude's own
live example contains three undetermined PlayerProfiler streams but rolls the source up to
`not_due`. That repeats the false certainty the `undetermined` state was introduced to prevent.

Required repair: unless a higher-priority due/current fact governs under an explicitly pinned rule,
an unsatisfied `undetermined` child must remain visible in the source cadence rollup. Add the mixed
`not_due + undetermined` counter-case.

## Scope held

No production source was executed, no scheduler installed, no paid route used, no provider
contacted, and nothing was committed or pushed. The diagnostic controller run was dry-run and wrote
only beneath `/private/tmp`.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
