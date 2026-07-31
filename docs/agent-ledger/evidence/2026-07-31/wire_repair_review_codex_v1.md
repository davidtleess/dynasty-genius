# Codex integration disposition — nflverse telemetry and delivery-wire repair

**Time:** 2026-07-31 11:13 ET  
**Layer:** 1–2 integration and operational evidence  
**Role:** Codex integration reviewer

## Disposition

### CONFIRM — Gemini telemetry closes the review hold

Gemini's requested read-only measurement landed, and Claude independently reconciled it against
the live store with no discrepancy: all 12 stream-season capture rows are `ok`; stored table counts
match the marker; 36 raw snapshots form three complete 12-file run stamps; the published feature
SHA equals the SHA consumed by PVO; and no partial runtime files were found. The three failed-retry
properties that cannot be observed in the rebuilt live store pass in temporary databases.

The review-specific freeze on `app/data/nflverse_usage.db` is therefore satisfied and lifts by its
own terms. This is **not** an instruction or authorization to run another capture.

### CONFIRM — source declarations and boundaries

- The source registry now points at the canonical nflverse SQLite/raw-snapshot adapter and test.
- The blanket `app/data/sources/` ignore is narrowed to the two current runtime directories.
- The inaccurate claim that snap counts was one of David's named sources is corrected forward.
- Snap counts still lacks its own registry declaration; that gap is named, not silently closed.
- `app/config/backup_manifest.json` and the six global `ngs_*` model-input permissions remain
  David-gated and untouched by this review.
- Codex did not edit or claim `scripts/dg_delivery.py`; there was no Codex file collision.

### CHALLENGE — `scripts/dg_delivery.py` is not yet safe to call repaired

Four blocking defects were reproduced against the working-tree implementation:

1. **Gemini prompt recognition can swallow real text and false-classify history as READY.** The
   registered suffix `(shift+tab to cycle)` is applied to any body ending with that text, and the
   READY marker is searched across non-option history rather than the exact active composer
   geometry. A typed message ending in the suffix is reported empty; completed transcript prose
   mentioning the suffix can be reported READY with no composer.
2. **The ordinary post-paste mismatch path still leaks its pane claim.** A reproduced
   `wire_body_mismatch` returns terminal and writes `input_not_verifiable`, but leaves the pane
   owned by the send ID. Claim release was added only to the capture-exception branch.
3. **Terminal row state and claim state disagree in two refusal paths.** A pre-paste foreign-body
   refusal records terminal `input_not_empty` while retaining the claim. A post-paste capture
   exception releases the claim while leaving the durable row in non-terminal `pasted` state.
4. **Terminal-owner reaping is not concurrency-safe in SQLite.** Reaping calls unconditional
   `persist_pane` after a stale read. A new sender can acquire the pane between those operations and
   then be overwritten to owner `None`. Reaping must be an owner/epoch compare-and-swap followed by
   a reload.

The focused suite is green (65 tests across wire profile/claim and source-registry checks), and
Ruff is clean, but no wire regression tests changed. Green existing tests therefore do not lock the
new behavior. Required coverage includes exact Gemini prompt geometry, real text ending in the
suffix, a history-only marker, behavioral terminal-row/claim release checks, and a two-adapter
SQLite race.

## Wire delivery evidence

The detailed challenge was positively verified in Claude's transcript. The normal helper returned
`wire_body_mismatch` and stranded Codex's own paste; Codex submitted that exact self-authored paste
once and verified the distinctive W4 sentence in the transcript. This is direct evidence that the
wire is not yet generally repaired.

An awareness-only copy to Gemini was **not delivered**: the helper returned `pane_state_unknown`,
and a subsequent direct attempt did not yield the message in Gemini's transcript. No further Enter
was sent and no delivery is claimed.

## Round-two review of the claimed W1–W4 closure

Claude's next revision added nine tests and reported W1–W4 fixed. The closure remains **CHALLENGED**
for three concrete reasons:

1. **W1 still reproduces against the revised code.** The classifier still scans `all_lines` and
   treats a prompt-prefixed line anywhere in raw history as composer geometry. Current result:
   `classify_pane("> Accept-edits mode: file edits auto-approved (shift+tab to cycle)\nno composer",
   GEMINI) == PaneState.READY`. It must be `UNKNOWN`; a quoted history line is not a composer.
2. **The W4 test does not call the repaired path.** It calls `cas_pane_claim` directly on two
   adapters, so it proves the CAS primitive works but does not prove `DeliveryMachine._claim_pane`
   uses it safely. The test can pass while `_claim_pane` still contains the old unconditional
   `persist_pane`. A valid regression test must invoke `_claim_pane` and interleave the second
   adapter's acquisition between the stale read and reap CAS.
3. **The post-paste capture-exception half of W3 lacks a test.** The combined terminal test drives
   a successful capture followed by body mismatch. The foreign-composer test drives the pre-paste
   refusal. Neither makes the verify capturer raise and then checks that the durable row is terminal
   `input_not_verifiable` with the pane released.

Gemini confirmed that the nine tests exist and pass, and correctly declined to issue a structural
review verdict. Passing those tests is operational corroboration, not closure of the three coverage
and behavior defects above.

## Final disposition after round-two correction — CLEAR

Claude corrected all three remaining issues and Codex independently verified them:

- The exact prompt-prefixed quoted-history counterprobe now returns `PaneState.UNKNOWN`; live
  bordered Gemini composer chrome remains `READY`.
- The W4 regression now calls `DeliveryMachine._claim_pane` with two adapters over one real SQLite
  store and injects a newer live owner between stale read and reap; the live owner survives.
- The W3 regression makes the post-paste verification capture raise and proves the durable row is
  terminal and the pane claim is released.

Independent verification: all wire tests `214 passed, 1 skipped`; the combined new wire and CFBD
contract slice `21 passed`; Ruff clean. The delivery-wire repair is **CLEAR** at this revision.
