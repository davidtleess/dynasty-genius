# TW28-IDENTITY-12 — Codex independent A/B/D GREEN review round 1

**Reviewed scope:** `.gitignore`, `scripts/build_universe_pvo_batch.py`,
`tests/contract/test_identity_crosswalk_hardening_red.py`, and the exact frozen
crosswalk bytes.

**Disposition:** **NOT CLEAR — two loader-integrity findings.**

## What passed independently

- Focused + sibling contract surface: **41 passed**.
- Ruff on the touched producer and RED: clean.
- Governed Ruff scope `src app`: clean.
- `git diff --check`: clean.
- Exact crosswalk SHA-256:
  `8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`.
- Production payload parses to 7,952 GSIS keys / 6,117 Sleeper keys / zero
  duplicate rows.
- Actual Engine-B inference path, read-only: 503 predictions → 501 joins + two
  deterministic orphans, Nick Kallerup then Ke'Shawn Williams; duplicate counts
  both zero.
- Missing/malformed shape, repeated-entry conflicts, repeated-prediction
  conflicts, zero-prediction, zero-join, scheduled abort preservation, tracking,
  and sibling-ignore rows all pass.

Claude's reported full suite also exited 0. That report is corroborating
evidence, not the basis of this review disposition.

## Finding 1 — duplicate JSON keys still resolve by last-write-wins

The loader calls ordinary `json.loads(path.read_text())`. Python's standard
decoder accepts duplicate keys inside one object and silently keeps the last
value:

```text
input:
{"gsis_id":"00-good","gsis_id":"00-wrong","sleeper_id":"101"}

parsed:
{"gsis_id":"00-wrong","sleeper_id":"101"}
```

The new duplicate-entry checks run **after** that information has already been
destroyed, so they cannot detect it. A single crosswalk row can therefore
redirect a Sleeper mapping by duplicate-key order while the loader reports no
duplicate and no conflict. This is the exact last-write-wins class Unit A says
must fail closed.

Required contract: reject any duplicate key in any JSON object in the
crosswalk payload with a stable named reason such as
`ff_playerids_duplicate_json_key`. Detection must happen during decoding via an
`object_pairs_hook` or equivalent, before a dict is constructed. Do not try to
grep serialized text for keys.

## Finding 2 — non-UTF-8 corruption does not receive the named invalid-JSON reason

`path.read_text()` can raise `UnicodeDecodeError` before `json.loads` runs. The
current `except json.JSONDecodeError` does not catch it. The scheduled runner
will still abort, but `aborted_reason` becomes raw codec prose rather than the
stable machine token promised by the truth surface.

Required contract: invalidly encoded bytes fail with the same stable
`ff_playerids_crosswalk_invalid_json` reason (or another explicitly pinned
machine reason). The production file is ordinary UTF-8; this is a corruption
probe, not an encoding migration.

## Boundaries

These findings do not alter the partial-coverage policy, the zero/nonzero join
boundary, orphan/duplicate arithmetic, Unit C, player targeting, name matching,
I-5, sentinel filtering, or the frozen payload bytes. They add no production
refresh and no model change.

Claude should challenge either finding before changing the RED if it believes
the behavior is intentionally outside Unit A. If accepted, Codex will add the
two failing rows to the RED, Claude will make the narrow decoder fix, and Codex
will rerun the independent matrix.
