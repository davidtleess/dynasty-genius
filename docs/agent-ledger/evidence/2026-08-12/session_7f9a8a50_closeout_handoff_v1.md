# Working state notes — Claude session `7f9a8a50` (the surviving lane)

**SUPERSEDED PREMISE — read this first.** An earlier draft of this file assumed session `7f9a8a50`
would be killed and session `c43d74ea` would land the pair. **David ruled the opposite.** The
`claude-v21` tmux window (`dynasty:3`, pid 8810, session `c43d74ea`) was killed on his word at
~03:4x on 2026-08-12; `7f9a8a50` is the surviving and only Claude lane in this repo. Its work was
explicitly kept: the v21–v26 GREEN/RED pins were verified byte-identical after the kill
(`a419930b…` / `9e0a861f…`) and live in the working tree. Nothing of that session's output was
discarded — only its pane.

Read `night_cleanup_plan_v1.md` (committed at `fa90ced`) for the full ticket board; this file is
only what that plan does not already carry.

## Things only this session knows

1. **A retraction-withdrawal is IN FLIGHT to Codex** (`w#3w6wh9ps-1`,
   `footballguys_retraction_withdrawn_claude_wire_v1.md`). This session wrongly accused Codex of
   fabricating "Claude received and acknowledged the CLEAR" — it was TRUE and referred to session
   `c43d74ea`. Codex had already issued a retraction of a true statement
   (`footballguys_v26_clear_retraction_codex_v1.md`); it is being asked to restore the original and
   annotate why, WITHOUT deleting the retraction doc. **Confirm Codex completed this before
   landing** so the record is correct at the moment of the commit. Track as **DG-15**.

2. **`scripts/run_realized_outcome_scoring.py` is MODIFIED and UNCOMMITTED** — David's approved
   realized-outcome scorer wiring, done by this session, unrelated to Phase A:
   - `_default_prediction_loader` now joins `model_forward_prediction_snapshot` to
     `model_forward_capture_joinable` on the 5-part key and returns **501 real predictions**
     (`sleeper_id`, `capture_date`, `projection_2y`, `position`); verified against the live
     `app/data/model_forward_capture.db` (22,569 `captured` rows across 45 capture dates).
   - Closes the "September trap": an undeclared/empty frozen set now RAISES
     `FrozenPredictionSetUndeclared` → `status: failed`, exit 1, instead of `noop` — which is a
     SUCCESS status on this artifact's `auxiliary` tier and would have reported the loop healthy
     all season while grading nothing.
   - **Consequence David has been told about: the job exits 1 today.** It stays red until he
     declares the frozen capture in `app/config/realized_outcome_frozen_predictions.json`
     (ticket **DG-09**; recommended value `2026-06-28`, the pre-season capture, immune to
     hindsight). Do not "fix" the red by reverting to noop — the red is the honest state.
   - 64 realized-outcome contract tests pass. Ruff and strict compile clean.
   - **This is unreviewed by any other lane.** Route it to Codex separately; do NOT fold it into
     the Phase A landing commit.

3. **Do not `ruff --fix` anything under `docs/agent-ledger/evidence/`** — ticket **DG-14**. Five
   `footballguys_identity_census_generator_v3–v7.py` files are hash-referenced by the framing
   documents; 15 of their 25 lint errors are auto-fixable, which makes the trap inviting.
   Reformatting silently invalidates the audit chain. Commit evidence with
   `git add docs/agent-ledger/ && git diff --cached --name-only | grep '\.py$' | xargs -r git reset -q --`.

4. **Orphan forensics are preserved** at `~/.claude/jobs-quarantine/9a73fbe9-orphan-2026-08-11`.
   Do not delete until DG-05 and OPS-05 close. That agent ran unsupervised ~08-10 → 08-11 with
   auto-permissions and computer-use, wrote production code, keyed panes, and committed `87362f1`
   (whose message claims code the commit does not contain — ticket **DG-06**).

5. **`caffeinate -dimsu -t 43200` is running** from ~23:5x on 08-11 (12h). It will expire on its
   own; kill it if the machine should be allowed to sleep sooner.

6. **Gemini's pane cannot be reached by `scripts/tmux_msg.py`** (`pane_state_unknown` /
   `wire_body_mismatch` on long pastes) — ticket **OPS-02**. Its five OPS tickets are already
   merged into the plan verbatim, so nothing is pending from it.

## State at closeout — measured, not recalled

| Item | Value |
| :-- | :-- |
| HEAD | `fa90ced` (evidence chain, 107 files, 13,492 insertions) |
| Remote | `3722ff5` — **nothing pushed all night** |
| GREEN (frozen, uncommitted) | `a419930b3a0871d3bb2477475699ef2dcc76317125b544b0c2caac12ccd7790d` |
| RED (frozen, uncommitted) | `9e0a861facd1e1502d66f9bc4672c2055ca7c1719483f387014b5d3453aa76e3` |
| Strict module | 660 passed, exit 0 |
| Live `receipts.db` | legacy **v1** store — the migration path is real, not hypothetical |

## Landing reminders

RED and GREEN **must land together** — the 660 contracts would red CI without their GREEN. Commit
immediately on landing (**DG-03**, the night's most expensive lesson). Push, first capture, the
monthly-notice wiring, scheduler, provider contact, and Phases B/C/D each remain separate David
words. **H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
