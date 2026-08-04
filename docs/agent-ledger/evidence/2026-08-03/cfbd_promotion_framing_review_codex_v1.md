# CFBD DATA promotion framing — Codex written challenge v1

**Reviewer:** Codex (independent lane)
**Reviewed:** 2026-08-03 17:16 EDT
**Target artifact:** `cfbd_promotion_framing_claude_v1.md`
**Target SHA-256:** `95f8abe60ee13d7e2cbfa32fa11ff5d266648dbe2773e3754c7d9ebb7edbb5e3`
**Verdict:** **NOT CLEAR — seven dispositions required before RED.**

This is a read-only framing review. No promotion, refresh, bakeoff, model write, RED, GREEN, or
data mutation was performed. The authority remains David's exact DATA-scoped word: *"yea make the
fresh data live!"* H2 QB rushing remains **UNDER TEST** with no result; none of the promoted fields
is a rushing field and this review supplies no evidence about rushing.

## Independent controls reproduced

- `HEAD == origin/main == 111c26deddac080d8d443c118ddc3d047a297983`, divergence `0/0`.
- Active SHA-256: `b3c28e4206ea347919daf3f895a0475f125dae27138e243f4dbe4b0e40649f38`.
- Candidate SHA-256: `15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0`.
- The framing's 874-row, 173-column, 117-row, 1,123-cell, 12-column measurements are accepted for
  framing. They still need executable RED contracts.
- A canonical keyed projection over `gsis_id` plus the 12 promoted columns distinguishes the two
  current states: active `32ea9f233b9ec3f45ef7bf7b9f855b89dfaee4b1d7ba9ef91e395a1fb8682db2`,
  candidate `567581517a463ae6e31e738974c31c3a9f37d36dd04ecaa3fa7fa98272496387`.

## F1 — the central three-writer claim is false

The framing says any later run of any of three scripts silently reverts the promotion. The scripts
are not equivalent:

1. `build_head_b_targets.py` reads the older `prospects_with_outcomes.csv`, reconstructs rows, and
   writes V3. It can erase later enrichment and is a destructive producer for this promotion.
2. `build_w2b_cfbd.py` reads V3, recomputes the QB triplets through the legacy
   `app/data/cfbd_cache` path, `row.update(feats)`, and writes V3. It can overwrite the promoted
   projection and is a destructive producer for this promotion.
3. `build_w2_features.py` reads V3 itself, updates other enrichment, and adds CFBD stubs only when a
   key is absent (`if k not in row`). On the 173-column promoted artifact the 12 keys already exist,
   so this path can change the file's bytes without reverting those fields.

Disposition required: replace "three reverters" with this classified topology. Retain all three as
whole-file writers, but do not call `build_w2_features.py` a CFBD reverter without a failing probe.

## F2 — a whole-file hash detector answers the wrong durability question

The promoted whole-file SHA belongs in the receipt and is the correct post-swap byte check. It is
not, by itself, a durable CFBD-state detector: `build_w2_features.py` can legitimately change
unrelated fields and therefore the whole-file SHA while preserving every promoted CFBD cell.

The receipt/check contract needs both:

- whole-file before/candidate/after SHA values for CAS and byte provenance; and
- a versioned, canonical digest over stable row identity plus the 12 promoted columns, with the
  serialization recipe recorded, for the statement "the promoted CFBD payload is still present."

Unknown whole-file drift must still surface, but it must not be mislabeled "CFBD reverted" when the
projection digest is intact.

## F3 — durability belongs in this scope, but only at the destructive boundaries

A detector that can be run later is insufficient if the two destructive producers remain free to
silently overwrite the active projection before a model/evaluator reads it. Either this increment:

- guards/repoints `build_head_b_targets.py` and `build_w2b_cfbd.py` so they refuse to overwrite an
  active promoted projection without an explicit governed replacement path; or
- places the same projection-state admission guard on every permitted consumer before it reads the
  active file.

If neither is included, the honest closeout is "promotion applied but not durable; silent reversion
remains possible," not a completed durable promotion. `build_w2_features.py` needs whole-file-drift
handling, not the same destructive-producer accusation.

## F4 — the exact counts remain hard gates for this promotion

The full SHAs are primary byte identities, but `117` changed rows and `1,123` changed cells must
remain independently recomputed, fatal semantic gates alongside the 12-column/QB-only invariants.
They are not merely receipt annotations. A SHA proves which bytes were selected; the semantic
checks prove why those bytes satisfy this authorized change.

Do not hard-code the counts as eternal CFBD schema constants. Put the two SHAs and expected semantic
delta in a reviewed one-time promotion specification. A regenerated candidate is a new promotion
spec/review cycle, not a reason for this pinned promotion to accept different counts.

## F5 — disposition is `existing_consumer`, with narrower prose

Use:

`existing_consumer — scripts/run_phase20_bakeoff.py; permitted only as a separately authorized,
non-promoting QB evaluation; not invoked by this DATA promotion.`

The script reads V3 and explicitly places the four corrected values in its QB candidate feature
contract. Human gating does not make the reader nonexistent. Conversely, the framing's generic
"the next Engine A training run would consume" is too broad: the concrete reader is the Phase-20
non-promoting evaluator, while `promote_head_a_te_v3.py` is TE-only and must not be implied to use
these QB fields. Name the exact consumer and permitted use.

## F6 — no new paid-refresh interlock; make promotion offline by construction

`run_cfbd_foundation_refresh.py` already stages into the isolated CFBD source tree and binds the
builder's output path away from the active V3 file. It is a paid candidate producer, not part of the
promotion command. Do not widen this increment by changing it merely to enforce "do not run."

The promotion entrypoint itself must have an executable side-effect allowlist and be offline by
construction: no import/call of the refresh entrypoint, no CFBD/network operation, no subprocess,
and no model/bakeoff command. Tests should make those side effects fatal. Documentation alone is
not a sufficient boundary for the promotion code.

## F7 — missing RED seeds

The ten listed seeds are useful but incomplete. Add at least these independently fatal cases:

1. **Manifest-chain mismatch:** candidate SHA matches a supplied pin but `manifest_latest.json`
   does not bind the expected schema/run, `input_sha256`, `curated_sha256`, raw-content SHA, and
   immutable run manifest. The board requires source-manifest/hash binding, not candidate hash only.
2. **TOCTOU after validation:** active or candidate changes between validation and replacement.
   Acquire the lock first, bind one candidate byte buffer, re-CAS active immediately before a
   same-directory atomic replace, and never promote bytes different from those validated.
3. **Post-replace readback:** the active file must be re-read and match both the candidate
   whole-file SHA and promoted projection digest before success/receipt completion.
4. **Idempotent rerun:** active already equals the promoted candidate with a matching receipt must
   return an explicit `already_promoted`/no-op; it must not overwrite the original preimage or emit
   a contradictory second success.
5. **Rollback CAS:** rollback may replace active only when active still equals the promoted SHA (and
   projection). Unknown intervening bytes must refuse; rollback must not erase later work.
6. **Complete recovery matrix:** test active old/new/unknown against receipt absent/valid/corrupt,
   including preimage present without receipt and receipt claiming new while active is old/unknown.
7. **Stale lock behavior:** contention is covered, but abandoned/stale lock handling must neither
   deadlock forever nor break a demonstrably live owner.
8. **Durability failures:** temp/preimage/receipt short write, fsync failure, and parent-directory
   sync failure leave either the verified old active or a recoverable named split state. Atomic
   rename alone is not durable storage.
9. **Projection-specific clobber:** unrelated-column rewrite changes full SHA while projection
   digest stays equal; legacy QB overwrite changes projection digest. The detector must distinguish
   these outcomes.
10. **Identity ambiguity:** duplicate/blank `gsis_id`, duplicate/blank secondary identity, or a
    one-sided key must fail separately from a simple row permutation.
11. **Path/alias safety:** active, candidate, preimage, temp, and receipt paths must not alias the
    same file/inode or escape their governed roots; replacement temp must share the active file's
    filesystem for atomicity.
12. **Receipt/preimage immutability:** run-id/path collision or an existing differently hashed
    artifact refuses instead of overwriting audit history.

## Review boundary

No objection to the framing's DATA-only authority, no-model-write boundary, receipt-not-validation
language, or explicit statement that H2 QB rushing remains under test and untouched. The CFBD skill's
promotion gates reinforce that no feature/model promotion can be inferred from this data movement.
