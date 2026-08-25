From Claude (write lane) — FRAMING CHALLENGE ROUND requested, pre-RED [w#r1-r2-group]

David's word this morning: "lets tackle the tickets as a group - everything coordinated". Scope
confirmed with him: R1 + R2 first, A7 and the descriptive cluster after. He has also added three
outside consultants in their own terminal windows (Claude/Gemini/Codex Consultant) — they are OFF
the tmux wire, advisory only, and cannot CLEAR. You remain the binding independent reviewer.

ARTIFACT UNDER REVIEW:
  docs/agent-ledger/evidence/2026-08-19/r1_r2_group_framing_claude_v1.md
  (new, uncommitted; zero product paths touched this session)

Per 02 Strategy/UX framing first, this is the mandatory adversarial challenge round. No RED opens
until you challenge in writing and I answer every item in a written disposition.

WHAT I MEASURED MYSELF — re-derived from the served artifact and source, not relayed:
- 115 rows: dynasty_value_score None AND projection_2y present.
- 114 of those carry dvs_engine="A" plus the caveat "Insufficient professional season data —
  Engine A prospect score used as prior", and ZERO of the 114 have an nfl_draft_round. No prior
  existed. The row asserts a mechanism that did not run. pvo_assembler.py:458-465.
- players.py:40,249 derive `modeled` from engine_path ALONE. Garrett Wilson (ENGINE_B, projection
  11.255, score None) is therefore served as model_status="modeled" with degradation=None, inside
  a PlayerModelLane whose dynasty_value_score is None. players.py:265-284.
- The other branch (players.py:286-291) tells Tank Dell — 26, WR, HOU, 3 yrs exp, ON DAVID'S
  ROSTER — "No active model score for this player category", while 241 WRs are modeled.
- David's own 27-man roster has 3 blank cells with 3 different causes. A7 adds a 4th class
  (Jeanty 75.3, Ali 20.7 — score exists, deliberately withheld).

MY CENTRAL CLAIM, WHICH IS WHAT I WANT ATTACKED: model_status has two values and is being asked to
carry at least four truths, so R1 and R2 are one defect at two sites and should share one state
vocabulary rather than being fixed as separate tickets.

I ALSO CORRECTED THE TICKET TEXT and want that checked: R2 was carried as "Tank Dell's
dg_player_id is None". True but not the finding — 11,639 of 12,222 rows (95.2%) have a null
dg_player_id and it is normal for every non-modeled row. The real statement is cohort exclusion
with no caveat and no risk flag.

FIND CONCRETE DEFECTS. Specifically:
1. Is the four-state count wrong — too few, too many, or wrongly bounded?
2. Is my layers 1-2 dependency check (framing section 0) adequate, or did I assert a layer without
   earning it? That exact error was made on this thread on 2026-07-28 and again on 2026-08-18.
3. Section 4.2 flags an R1/A7 conflict — surfacing PPG for players whose score is deliberately
   withheld may route around an intentional gate. Is that real, and is leaving it to David correct?
4. Are the falsification seeds in section 5 adequate to open a RED, and what is missing?
5. Overclaim check in section 6 against 00 No-Verdict Line — anything smuggled?

NOTHING IS AUTHORIZED. No RED, no code, no rebuild. Severity per 02 loop-control: BLOCKER / WARN /
STYLE with the violated criterion and reproducible evidence.

PLEASE REPLY with: (a) your written challenge, findings ranked most severe first with file:line or
reproduced counts, OR (b) an explicit statement that the framing is adequate to open a RED, with
the checks you ran enumerated.
