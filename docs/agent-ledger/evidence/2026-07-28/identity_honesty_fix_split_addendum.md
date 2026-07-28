# TW28-IDENTITY-9 — Split addendum to framing v4

**Authority:** David to Tower, verbatim — **"split it"**.
**Governs:** `identity_honesty_fix_framing_v4.md`. This addendum changes **no** substance in v4; it
partitions v4 into two independently-advancing threads so a RED can target one without touching the
other. Where this addendum and v4 differ on scope boundaries, **this addendum governs**.

## The two threads

**THREAD 1 — PROTECTIVE (Units A, B, D). Proceeds NOW.**
RED → GREEN → enumerated CLEAR → full-suite tollgate → commit. Does not wait on Thread 2.

**THREAD 2 — WORDING (Unit C, plus the §0.1 finding). Continues on its own timing.**
Not cancelled, not deprioritised, not rushed. **It does not gate Thread 1.**

**Neither thread's work may appear in the other's commit.** That separation is the point of the split.

## Why the seeds needed partitioning

v4 §8 interleaves 23 seeds across all four units. Handed to a RED author as-is, Thread 1's contract
would either pull in Unit C rows or leave Thread 1 rows behind. Explicit partition, exhaustive:

| Thread | v4 §8 seeds | Count |
| :-- | :-- | --: |
| **1 — A/B/D** | MEASURED-LIVE 10, 11 · PROSPECTIVE 15, 16, 17, 18, 19, 20, 21, 22 | **10** |
| **2 — C** | MEASURED-LIVE 1–9, 12 · PROSPECTIVE 13, 14, 23 | **13** |

10 + 13 = 23. Every seed is assigned to exactly one thread; none is dropped, none is shared.

## Thread 1's scope, stated tightly

- **Unit A** — fail closed on a **missing or malformed** crosswalk, and on **conflicting** duplicate
  mappings (never last-write-wins). Abort emits at
  `app/data/model_capture/pvo_refresh_latest_report.json` with `status=aborted`, the failed stage, and
  the named reason (v4 §7).
- **Unit B** — count and name every skipped player: crosswalk orphans **and** the prediction-side
  `seen_sleepers` skips. Deterministic order by `gsis_id`; `orphan_count == len(orphan_records)`;
  block present-and-empty when none.
- **Unit D** — the payload becomes the tracked dependency the loader actually reads: the path
  `build_universe_pvo_batch.py:31` resolves is git-tracked, present in a clean-checkout-equivalent
  state, and hashes to `8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`. Pattern B
  (`_runs/*` then negate the child) — proven; a bare file negation cannot re-include a child under an
  excluded directory. Bytes only; no upstream revision exists to pin.

**Still escalated and NOT resolved by "split it": v4 §0.2, the publication-coverage policy.** Thread 1
ships only the unambiguous fail-closed cases; an orphan-bearing run behaves **exactly as it does
today** except the orphans are now named. **No coverage threshold is asserted in either direction.**
This is what lets Unit A proceed without me inventing product policy — the risk David named (an app
that publishes an empty board with no error) is closed by the missing/malformed/conflicting cases,
which need no coverage rule.

## Thread 2's scope

v4 §0.1 (the 113 `MODEL_UNCERTAIN` rows presented as "Modeled" — David's call, no behaviour changed),
§3 (the eight-branch mapping and manager-voice copy), §3.5 (composition rules), and its 13 seeds.

## Two consequences of the split, named rather than discovered later

1. **The FE gate moves to Thread 2.** Thread 1 touches no frontend file — it is `scripts/`,
   `app/config`-adjacent, and `.gitignore`. Thread 2 owns `players.py`, `PlayerDetailCard.tsx`, and
   `PlayerInspector.tsx`, so the frontend half of the tollgate belongs to it. Thread 1's tollgate is the
   full Python suite plus ruff; claiming an FE gate it never exercised would be false green.
2. **Thread 1 commits a 3.77 MB payload and a `.gitignore` change.** That is the largest single tracked
   addition in this ticket and it is Unit D's whole point. It is not a code change and must not be
   described as one.

## Commit word

Thread 1 runs under David's existing authorisation — *"ship the honesty fix and commit the file."*
Per his instruction: **if at commit time I judge that what I am about to commit is not what he
authorised — because scope moved again — I ask through Tower rather than stretch the old word.** The
two things I will check against the word at that moment are (i) whether §0.2 has moved, and (ii)
whether Unit B's named-orphan output grew beyond reporting. **A push is a separate word either way.**

## Unchanged

Route 2, row targeting, name matching, I-5, sentinel population filtering, the canonical key, the
Compliance Audit workflow, and DG2-S0-01 (d) remain unauthorised and untouched. No RED is open yet. No
code written.
