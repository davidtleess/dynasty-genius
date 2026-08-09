# League-scoped events RED review — Codex v1

Date: 2026-08-08
Layer: Layer 1 ingestion control
Verdict: **NOT CLEAR**

Reviewed artifact:

- `tests/contract/test_league_scoped_events_red.py`
- SHA-256: `287dcc7cb8bfbf9ced6216f26a334cbc28820575c184b50f6cf468ba7ec63885`
- Independent run: 17 failed, 0 passed, 0 skipped, zero collection errors.
- Independent Ruff: **failed** with three F841 errors at lines 275, 295 and 314 (`m` assigned but
  unused). The routed “Ruff clean” claim is false.

## Findings

1. **PFF grades must split by competition.** The alternative permitted by P4—retain one `grades`
   policy but remove its game triggers—would erase the standing refresh obligation for proprietary
   grade fields. Those fields occur in both NFL and NCAA payload lanes, whose clocks differ. Replace
   the ambiguous stream with `nfl_grades` and `ncaa_grades`, each carrying the real weekly/season-
   final triggers and the matching competition. Update the pinned stream/trigger/disposition
   contracts accordingly; do not silently double-fetch, because these are cadence surfaces over
   the underlying league-family payloads.

2. **P2 is not total in both directions.** It queries only keys already present in
   `EXPECTED_COMPETITION`, so an invented additional game-triggered policy with any legal scope
   passes. Build the actual map by iterating every shipped policy that carries a game-calendar
   trigger, then assert exact map equality. Include the two grade streams in the expected map.
   Separately prove `build_policy_registry` rejects a raw game-triggered declaration with no
   competition; P3 over the assembled registry cannot prove the constructor makes it impossible.

3. **Use stable validation codes, not a loose prose substring.** The concern about V2 is valid.
   Have the production scoped-calendar validator return a stable machine-readable code such as
   `calendar_competitions_not_object`, `calendar_competition_unknown`,
   `calendar_competition_entry_not_object`, or `calendar_competition_missing_keys`, followed by
   human detail. Assert the exact code at both the pure validator and public `_validate_inputs`
   surfaces. This pins the decision path without coupling to sentence wording and prevents the old
   missing-flat-key rejection from satisfying the tests.

4. **Missing competition and malformed competition are different.** A completely absent FBS block
   must be accepted and leave FBS streams `undetermined`; requiring invented FBS facts would violate
   the evidence contract. A block that is present must be complete and valid. Add valid NFL-only and
   FBS-only counter-cases, then mutate each required field (`week1_kickoff`, `final_game`,
   `game_week_completions`) out one at a time and reject malformed completion containers/timestamps.

5. **Full-controller fail-closed isolation is untested.** Inject a malformed scoped artifact through
   `_load_cadence_inputs`, run `daily_control.execute`, and require every complete manual route to
   report `manual_inputs_invalid` with both axes/all streams, aggregate nonzero, every source still
   present, and an unrelated automatic route unaffected. Direct validator tests alone do not prove
   the controller honors the verdict.

6. **Behavioral counter-cases need tightening.** Add the positive FBS `season_final` case and its NFL
   isolation counterpart. In I4 assert the exact expected states (`nfl=not_due`,
   `fbs=undetermined` with no completion evidence), not merely “different,” so an unrelated event
   cannot satisfy the test. Pin missing scoped evidence as undetermined in both directions.

7. **The RED preamble is factually wrong.** `feed_cadence` already exists; the scoped behavior is
   absent. The tests fail through missing attributes, old global behavior and old validator shape,
   not because the module is missing. Correct the line that says “The scoped module does not exist.”

No GREEN, B21 capture, governed input, provider contact, scheduler action, commit or push occurred
during this review.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
