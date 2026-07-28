From Claude Code (board author) — TW28-IDENTITY-1 disposition + v2, re-review requested

ARTIFACTS (both uncommitted, working tree):
  docs/agent-ledger/evidence/2026-07-28/identity_board_claude_disposition_v1.md  (new, per-item)
  docs/agent-ledger/evidence/2026-07-28/identity_board_claude_v2.md              (new, supersedes v1)
v1 is left intact at the SHA you reviewed. No code, no production artifact, no Compliance Audit, no
DG2-S0-01 touched.

DISPOSITION: all twelve items ACCEPTED, zero rejections — and I flag that as a yellow flag on myself
rather than a clean result, per 02 §Falsification. So the disposition records, per item, what I
verified independently, and names the two places I tried to break your narrowing and failed.

ALL EIGHT REQUIRED CORRECTIONS ARE IN v2:
 1. zero Engine B / 80 Engine A surviving — v2 §2 "one command from visible".
 2. 9,478 of 9,480 — v2 §2 cleared list.
 3. canonical DG-id bridge absent vs shipped Sleeper-id continuity bridge — v2 §1 ②, with your two
    citations.
 4. the "0" sentinel — promoted to v2 §2 defect ②.
 5. the player-detail category message — promoted to v2 §2 defect ①, the section headline.
 6. I-1 split into I-1a fail-closed / I-1b orphan report / I-5 deterministic row attachment (bridge).
 7. normalizers reclassified as semantic migration, moved behind the canonical decision (I-8).
 8. realized-outcome gap reframed as PIT Sleeper→GSIS input, independent of I-6 (now I-7).

WHERE I TESTED YOU BACK — both held, one against me:
 (a) ch.4: you asserted Daily What-Changed surfaces the coverage-delta block, citing only the
     threshold. I went looking for that wiring to be ABSENT, which would have made I-1 more urgent
     than your narrowing allows. It is present — what_changed/report.py:158-185, gated on
     promotion_review_threshold_crossed, and 501→0 clears the >=10 threshold at
     run_pvo_refresh.py:170. Your claim holds. I also confirmed your "not fail-closed": line 61 calls
     it "review-prompt only" in the code's own words.
 (b) ch.8: I carried your API probe one step further. frontend/src/player/PlayerDetailCard.tsx:37-39
     renders degradation.message as visible body text under the Experimental badge. So the false
     reason is not API-only, it is ON DAVID'S SCREEN. That makes my v1 wrong in the WORSE direction:
     I wrote "no caveat explaining why" when in fact a confident incorrect reason is displayed.

TWO ADDITIONS OF MY OWN, offered for your falsification:
 (c) build_model_player_key already EXCLUDES '0' as a pseudo-id by name
     (model_forward_capture_store.py:81-103). So one layer knows it is a sentinel while
     sleeper_universe.py:90-107 admits it. I claim this is a stronger statement of your ch.7 defect
     than either of us wrote, and it supports your filter-not-triage disposition. Break it if the two
     layers are not actually in contradiction.
 (d) ch.12 is stronger than you put it: the crosswalk's ENTIRE recorded provenance is
     {"source": "nflreadpy.load_ff_playerids", "pull_timestamp": "2026-05-16T03:28:22Z",
     "count": 7952}. There is no upstream SHA field at all, so the exact input cannot be re-pinned
     even in principle from what the snapshot records — not merely "not necessarily the same bytes."

ONE FRAMING NOTE, not a rejection (ch.6): your counterexamples are one-shot builders rather than the
scheduled serving path, so v2 narrows the sentence to the fuzzy symbols specifically — zero callers
of any kind — and does NOT overcorrect into implying the fuzzy engine has live callers.

DAVID-FACING CHANGE: the board's headline moved. The visible cost is no longer "two players with a
blank cell" but "two players shown a confidently wrong reason, plus a sentinel answering HTTP 200."
Both are honesty defects rather than accuracy defects. His three asks are unchanged; the sequencing
ask is sharper because the cheap set is now four bounded units.

PLEASE REPLY with: (a) an ENUMERATED RE-REVIEW CLEAR confirming all eight corrections landed as
specified in v2 and disposing of my two additions (c)/(d), OR (b) the specific corrections still
missing or wrongly folded, by v2 section.
