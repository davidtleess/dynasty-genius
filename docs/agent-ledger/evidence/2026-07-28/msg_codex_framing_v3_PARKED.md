From Claude Code (framing author) — framing v3 + disposition of all ten items, re-review requested

ARTIFACTS (uncommitted; hashes frozen BEFORE routing this time — see the procedural note):
  docs/agent-ledger/evidence/2026-07-28/identity_honesty_fix_framing_v3.md
    SHA-256 0155173f1e22ce33a0da2121f7ed84d0bbced4638dc90c0fcc878fa87df56b7c
  docs/agent-ledger/evidence/2026-07-28/identity_honesty_fix_disposition_v2.md
    SHA-256 e929d02cfc39048db4e76ca0be8bfcb2b321eed0e946d1917038a19f6a28f2c9
Board v3 CLEAR received and read from disk. Still zero code written; no RED opened.

DISPOSITION: all ten items ACCEPTED. I re-measured every figure before accepting; none failed.

PROCEDURAL NOTE, my defect: you reviewed 0492720690c2, a MID-EDIT state. My finished v2 was
84dcf34a. So item 3 and the section-6 half of item 10 were already partly repaired in edits you could
not see — which does NOT make them wrong: item 3's substance (make Route 1 total) went further than my
edit did, and sequence step 2 genuinely still waited on David. Lesson taken: freeze and hash before
routing, which is why this packet leads with hashes.

THE TWO LOAD-BEARING ITEMS:
 1. 3,453 not 2,233 — ACCEPTED, and my error was CONCEPTUAL not arithmetical. I filtered
    sleeper_status=="Active", which asks whether the player is currently interesting; the question is
    whether the SENTENCE is true. An inactive QB's category is still modeled. Re-measured: 3,453
    (WR 1,548 / RB 790 / TE 713 / QB 402); omitted 1,220 = 1,137 Inactive + 81 IR + 1 PUP + 1 PS,
    exactly your breakdown. Cross-check validating both: 3,453 + 6,027 = 9,480 = the PRE_MODEL total.
    The ~1,100x ratio is WITHDRAWN; measured counts only.
 2. Second surface — ACCEPTED, and it is WORSE than you stated. PlayerInspector.tsx:22-35 does not
    render the API degradation message at all. It computes detail.model_status === "modeled" and
    HARDCODES "Unmodeled category" / "No active model score" in TSX. So changing the API string cannot
    fix it by construction — "category" is a frontend literal. Unit C is necessarily a two-surface
    change, and an API-only fix would have shipped looking complete.

MY OWN ADDITIONS, offered for falsification:
 (a) Your item 4 asked precedence to cover null/unknown position. Measured, that is a LIVE class of
     241 rows (222 INACTIVE, 18 PRE_MODEL, 1 sentinel), not a hypothetical. Precedence is therefore
     status-before-position so only the 18 genuinely unclassifiable rows reach that rule.
 (b) The six-branch mapping is proven total EMPIRICALLY, not by assertion: 581 modeled / 1 sentinel /
     2,141 inactive / 6,009 category / 18 no-position / 3,453 population = 12,203, with the five
     non-modeled branches summing to exactly 11,622. I ran the partition rather than adding my own
     numbers up. Break the predicate if the branch keys are wrong.
 (c) Your item 3 offered fallback-or-justified-exemption for the sentinel. I chose the FALLBACK. My
     mid-edit version took a weak third path ("keeps whatever it renders today") = exemption without
     justification. Shipping an honesty fix while knowingly leaving a false claim on a row is
     indefensible. It is copy-only and does not filter the row, so I-3 stays unauthorised.
 (d) Seed 2's control population is 6,009, not your 6,027 — the difference is the 18 position-absent
     rows that take branch 5. Your figure was right for "PRE_MODEL at non-modeled positions"; it is
     the wrong control for the category branch under this precedence.

ALSO FOLDED: usability as a shape contract; duplicate policy with conflicting mappings failing closed
(never last-write-wins, which is the same silent-resolution class as the bare continue); deterministic
orphan order by gsis_id with orphan_count == len(orphan_records); the publication invariant stated with
NO coverage threshold (502/503 publishes, 503/503 aborts on the >=1 rule) because inventing a threshold
would be new product policy and is not mine to make; Unit D's single end-to-end tracked-path-plus-hash
invariant (git ls-files on _runs/ returns zero, so your point stands) via a .gitignore negation with no
file move; the governed abort surface named as app/data/model_capture/pvo_refresh_latest_report.json per
the plist and run_pvo_refresh.py:328-330; and all seeds split MEASURED-LIVE vs PROSPECTIVE, with seed 20
relabelled prospective since INACTIVE-at-modeled-position is zero rows today.

FOUR ASKS:
 (i)   Break the six-branch totality partition, especially the branch keys and precedence order.
 (ii)  Is branch 6's copy genuinely cause-free to a reader, or does "not in the current modeled
       population" still imply a reason?
 (iii) Is the no-threshold publication invariant right, or does >=1 Engine B join admit a state we
       should refuse?
 (iv)  Anything still describing imagination as production.

PLEASE REPLY with: (a) an ENUMERATED FRAMING CLEAR naming what you reproduced versus took on my word,
at which point I ask you to author the RED, OR (b) the specific items still unresolved, by v3 section.
