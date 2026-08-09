# Governed cadence inputs RED review — Codex v1

Date: 2026-08-08
Layer: Layer 1 ingestion control
Verdict: **NOT CLEAR**

Reviewed artifact:

- `tests/contract/test_governed_cadence_inputs_red.py`
- SHA-256: `c6ca249f990b1eb97f83044744f9d0ee95bce8fd48afae7cc35d19b6d5e96609`
- Independent RED: 15 failed, 0 passed, 0 skipped, zero collection errors; all failures arise at the missing module boundary.
- Independent Ruff: clean.

## Blocking findings

1. **The asserted controller integration bypasses the production load path.** X1 calls
   `build_artifact(...).as_controller_inputs()` and hands the flattened payload directly to
   `daily_control._validate_inputs`. The shipped controller instead reads
   `app/config/manual_feed_cadence_inputs.json` as JSON and validates it directly. If the file
   retains the provenance wrappers, the shipped loader rejects it; if the file contains only the
   flattened view, the provenance the new module exists to govern has been discarded. The RED must
   drive the real loader/controller from the persisted provenance-bearing representation.

2. **No production artifact can result from this contract.** The RED explicitly excludes writing
   `app/config/manual_feed_cadence_inputs.json`; it has no stable-path, atomic-write, crash-preserves-
   previous-good, schema-version, or artifact-identity contract. A GREEN can therefore remain an
   in-memory library while PFF and PlayerProfiler continue to report `undetermined`, reproducing the
   exact incomplete state this slice is meant to close.

3. **The calendar contract is route-agnostic after the route was technically resolved as hybrid.**
   The RED accepts an all-declared calendar. Game-derived facts (season, Week 1, final game and
   declared game-week completions) should be derived from the canonical B21 schedules capture;
   non-game anchors (league-year open, combine, draft) and vendor availability require a versioned
   declared/observed registry. B21 cannot supply the latter, while hand-declaring the former retains
   annual rot. The RED should pin the origin class per fact and may encode B21 as an unmet prerequisite.

4. **Origin evidence is incomplete.** O3 requires only `declared_by` for declared facts although the
   prose promises who/when, and only `observed_at` for observed facts although the prose promises
   when/from-what. It does not require timezone-aware, non-future `declared_at`/`observed_at`, source
   provenance, or any re-affirmation/review-due behavior for declared facts. Consequently a declared
   fact can still rot silently—the defect the contract says it prevents.

5. **Derived facts self-certify.** A free-form `derivation` string plus a caller-supplied `actual`
   value is not re-derivation. The contract must use a closed derivation registry that executes the
   registered derivation against an injected source snapshot/store and binds the result to source
   identity (dataset/table and capture/hash). Otherwise the caller can supply any matching value and
   mark a fiction fresh.

6. **The measured inventory scope is not pinned.** The preamble claims derivability for all 14 PFF
   lanes and four/five PlayerProfiler streams, but tests exercise only a generic season parser and a
   `pff.grades` example. Pin exact equality against `feed_cadence.streams_for`, prove each derivable
   stream is populated from synthetic source fixtures, retain the underivable stream visibly, and
   prove the real controller no longer reports the derivable sources as wholly `undetermined`.

7. **Calendar tests can pass for the wrong reason and admit impossible calendars.** C1 accepts any
   `InputProvenanceError`, so a validator rejecting a partial calendar for missing other anchors
   satisfies the test without checking the named anchor's origin. C1b assigns one timestamp to every
   required anchor and asserts only non-null acceptance. Build one complete valid calendar, remove
   origin one fact at a time, assert the exact diagnostic, and pin chronological/season consistency
   with realistic distinct values and invalid counter-cases.

## Required end-to-end acceptance

A complete RED should prove: a provenance-rich, versioned artifact is written atomically to the
configured path; the shipped loader reads that exact representation (or a single explicit loader
adapter preserves its governance envelope); all declared streams remain visible; derivable PFF and
PlayerProfiler streams receive evidence-backed cadence/coverage states; invalid/drifted evidence
fails closed without replacing the last good artifact; and CI uses only injected synthetic stores,
never gitignored private data.

No source execution, scheduler, provider contact, paid action, production artifact write, commit or
push occurred during this review.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
