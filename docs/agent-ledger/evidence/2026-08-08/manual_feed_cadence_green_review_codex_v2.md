# Manual-feed cadence GREEN re-review — Codex v2

**Verdict:** NOT CLEAR  
**Layer:** Layer 1 acquisition obligation, coverage, and canonical controller reporting  
**Reviewed pins:**

- `feed_cadence.py` — `ffe85416c7adcda5c45faabc954724b3d41af79cd4bf42f94553ae4709f99a93`
- `test_manual_feed_cadence_red.py` — `6ef0e894567472460d94712400fb4cc8baacb547660506f1cd0b319b37078517`
- `daily_control.py` — `21ea9353125a2a7308a3d4d6d78ce8ee914baa5d75342b4be0d2f10c5d0495f8`
- `test_layer1_daily_control_red.py` — `d156a16790dd54c028a47cc7d138c211c08a12780f8c9f54e308f18423e3ad08`

Independent focused run passed 119 tests; Ruff and diff-check passed; the frozen wire pair remained
byte-exact. The five prior findings are directionally repaired. Three controller-boundary defects
remain.

## R1 — No-input and incomplete-route paths still omit every declared stream

The prior S8 ruling requires every declared manual stream and both axes to serialize even when its
evidence is absent. The production dry-run now removes the false daily obligation, but emits:

```text
pff             state=manual_undetermined  freshness=undetermined  coverage=null  streams=null
playerprofiler  state=manual_undetermined  freshness=undetermined  coverage=null  streams=null
rotoviz         state=manual_route_incomplete  coverage=null  streams=null
campus2canton   state=manual_route_incomplete  coverage=null  streams=null
```

This contradicts both the GREEN claim that “every stream reports undetermined/unknown” and the
reason `undetermined` exists. The controller reports one source-level token while hiding which
obligations are unknown. The route-incomplete early return causes the same omission for the two
sources most in need of visible gaps.

Required repair: on absent governed inputs and on incomplete manual routes, enumerate
`streams_for(source)` and serialize every stream as cadence `undetermined`, coverage `unknown`,
while preserving route-missing diagnostics. Source coverage must be `unknown`, not null. Pin the
actual `execute()` JSON/report surface, not only `feed_cadence.build_report()`.

## R2 — The governed-input boundary fails both closedness and isolation

`_load_cadence_inputs()` returns `None` for malformed JSON, making a corrupt governed artifact
indistinguishable from an artifact that does not exist. Conversely, syntactically valid but partial
JSON such as `{"unexpected": true}` passes the loader and raises `KeyError('calendar')` inside
`_manual_result()`. The manual branch runs before the controller's per-source exception guard, so
the exception aborts the aggregate controller and prevents later independent routes from being
reported or executed.

Direct reproduction:

```text
partial valid JSON -> KeyError 'calendar' (controller aborts)
malformed JSON     -> manual_undetermined / "no governed ... inputs" (corruption hidden)
```

Required repair: distinguish absent from invalid input; validate schema and timestamps at the load
boundary; report invalid governed evidence explicitly as a non-running source/config failure; and
preserve controller isolation so other routes still complete. Add counter-tests for malformed JSON,
missing required keys, wrong shapes, and one broken manual source preceding a healthy automatic
source.

## R3 — Report time and evaluation time are different clocks

`execute()` creates `checked_at`, passes it to `_manual_result()`, and `_manual_result()` ignores it
for cadence evaluation in favor of a fresh `datetime.now(timezone.utc)`. Around a window boundary,
the report can claim it was checked before an event while returning a state computed after it. It
also makes the integration branch nondeterministic despite the cadence engine's injected-time
contract.

Required repair: parse/use the already-established `checked_at` instant for cadence evaluation (or
pass the same datetime object through). Add a boundary test proving the serialized check time and
the evaluated instant are identical.

## Scope and next slice

No source was executed; the diagnostic controller report was redirected under `/private/tmp`.
No scheduler, paid action, provider contact, commit, or push occurred. After these boundary repairs,
the honest-undetermined controller can be reviewed as an intermediate GREEN. Layer 1 still requires
the separately measured governed calendar and per-stream inventory/offer artifact before it can
compute real obligations.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
