# TW28 Identity Units A/B/D — Post-Commit Divergence Audit

**Disposition: DIVERGENCE-VERIFY CLEAR. Zero drift from the content Codex
cleared.**

Audited commit:
`89757413e4f81b6ca2406e167455d29f434c2bf3`

## Enumerated checks

1. **Commit identity and ancestry — CLEAR.** The object exists as a commit. `HEAD`
   is exactly `89757413e4f81b6ca2406e167455d29f434c2bf3`; its parent is exactly
   `67bd75fb89788d0caed5b38453ca9db2cef6dd25`, which is also `origin/main`.
   Local `main` is ahead by one. Nothing was pushed.

2. **Authorized path boundary — CLEAR.** The commit changes exactly four paths:
   `.gitignore`, `scripts/build_universe_pvo_batch.py`,
   `tests/contract/test_identity_crosswalk_hardening_red.py`, and
   `app/data/identity/_runs/ff_playerids_20260516.json`. The stat is exactly
   136,016 insertions and 26 deletions. No Unit C, frontend, player-detail API,
   shared batch-module, ledger, or evidence path entered the commit.

3. **Producer bytes — CLEAR.** The committed producer blob is
   `617e5cfcb2d24477862d4b27d94fc535837fcff6`, exactly the destination blob
   Codex inspected before issuing the implementation CLEAR. The actual
   parent-to-commit diff retains all named fail-closed reasons, collision
   behavior, orphan accounting, zero-join refusal, positive-partial boundary,
   and compatibility behavior as cleared.

4. **Tracking-rule bytes — CLEAR.** The committed `.gitignore` blob is
   `6dc2f6d24de4e5168312a0d0b660de1966cee39e`, exactly the destination blob
   Codex inspected before CLEAR. The frozen child is tracked and an arbitrary
   sibling under `_runs/` remains ignored.

5. **RED-contract bytes — CLEAR.** SHA-256 of the test file read from the
   committed tree is
   `39eee2340ace49f411558e8cf725b3bf235a313ff4be8638d01eb561c359afcd`,
   exactly the pre-commit reviewed hash. The commit did not edit the RED after
   its final review.

6. **Frozen dependency bytes — CLEAR.** SHA-256 of the crosswalk read from the
   committed tree is
   `8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`,
   exactly the pre-commit reviewed hash.

7. **Post-commit contracts — CLEAR.** Codex independently reran the focused,
   refresh-runner sibling, and universe-batch sibling tests against the clean
   committed execution paths: **43 passed**. Ruff passed on the touched producer
   and test; the commit diff passes `git diff --check`.

8. **Real-path positive control — CLEAR.** Independent execution after commit
   reproduced 7,952 GSIS mappings, 6,117 Sleeper mappings, zero crosswalk
   duplicates, 503 predictions, 501 joins, zero prediction duplicates, and the
   exact two sorted `sleeper_id_missing` orphan records for Nick Kallerup and
   Ke'Shawn Williams.

9. **Commit-message fidelity — CLEAR.** Reading the raw commit object, the frozen
   proposal is an exact byte prefix (SHA-256
   `cc61cf1c2fdd51db2b5d3b08e0c3ca3d0e78f74dd6769d23cb29fb123deb2791`).
   The only remainder is one blank line plus the disclosed
   `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` trailer
   and its terminating newline. No reviewed substantive wording drifted.

10. **Post-commit dependency sweep — CLEAR.** No additional production caller
    depends on the prior fail-open return. The similarly named loader in
    `scripts/run_identity_audit.py` is a separate function and path. Historical
    framing/evidence correctly preserves descriptions of the pre-fix state.
    The known generic `_load_json` decoder gap remains separately recorded and
    was not silently absorbed.

## Close-loop state

The A/B/D implementation cycle is closed for local commit divergence. The state
documentation remains outside this implementation commit as intended. A push is
still separately unauthorized, and CI—not this local CLEAR—is the push gate.
Unit C remains a separate thread.

