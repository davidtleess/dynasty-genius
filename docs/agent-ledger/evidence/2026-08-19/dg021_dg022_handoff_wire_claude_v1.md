From Claude (crew lane) — HANDOFF: measured evidence for DG-021 and DG-022 [w#r1-r2-group]

You hold both tickets as CodexTeam20260819. Everything below is re-derived at source by this lane
against app/data/valuation_runtime/universe_pvo_runtime.json (captured_at 2026-08-18T13:30:03Z,
12,222 rows). Take it or refute it — but it is measured, so please don't spend an evening
re-deriving it. Full text is in the shared ledger, docs/agent-ledger/2026-08-19.md, entry 13:4x ET.

DG-021 — reproduces exactly, and the ticket names only HALF of it.
  115 rows carry a null dynasty_value_score AND a live projection_2y.
  114 of those carry dvs_engine="A" plus "Engine A prospect score used as prior".
  0 of those 114 possess an nfl_draft_round. No prior existed; none was used; the row says one was.
  Source: pvo_assembler.py:458-465 — the branch that runs BECAUSE no Engine A result was produced is
  the branch that stamps the Engine A provenance.

  THE HALF THE TICKET DOES NOT NAME: app/api/routes/players.py:40,249 derives `modeled` from
  engine_path ALONE, never from whether a score exists. Garrett Wilson (ENGINE_B, projection 11.255,
  score None) is therefore served as model_status="modeled" with degradation=None, wrapping a
  PlayerModelLane whose dynasty_value_score is None (:265-284). Fixing the assembler alone leaves the
  API still claiming a healthy model lane over an empty one. Both halves are on main; neither is on
  the frozen branch.

DG-022 — the ticket's stated discriminator is wrong, and a fix written against it would PASS.
  The ticket names dg_player_id: None as the marker. It is not one: 11,639 of 12,222 rows (95.2%)
  carry a null dg_player_id, normal for every non-modeled row — the field is populated only for the
  583-row modeled cohort. 0 null-id rows carry a projection or a DVS.
  Tank Dell's actual state is dg_status = PRE_MODEL: 26, WR, HOU, three years experience, ROSTERED BY
  DAVID (roster_id 1), outside the modeled cohort with risk_flags: None and caveats: None, while 241
  WRs are modeled. He is one of 10 rostered players league-wide in that state.

THE FRAMING BOTH LANES MAY WANT: model_status carries two values and is asked to express at least
four truths — score present, score died downstream (Wilson), never entered the cohort (Dell), score
exists but is deliberately withheld by the A7 Roster Audit gate (Jeanty 75.3, Ali 20.7). On David's
own 27-man roster three cells are blank for three different reasons and nothing distinguishes them.
Framing, mislead risks, falsification seeds and the No-Verdict-Line check:
docs/agent-ledger/evidence/2026-08-19/r1_r2_group_framing_claude_v1.md

FLAGGED, UNRESOLVED, DAVID'S CALL: surfacing points-per-game for players whose score is deliberately
withheld may route around an intentional product gate. That is the R1/A7 conflict; no lane settles it
alone.

MY LANE'S STATE, disclosed: DG-023 claimed, defect confirmed at source from both directions, RED
written at ~/dg-wt/DG-023/tests/contract/test_stream_provenance_status_red.py and NEVER EXECUTED. The
machine is saturated — load ~11 sustained, syspolicyd 138%, codex 51%; a single-file pytest run
produced no output in 20 minutes and ps itself times out. No fix written, nothing claimed green.

PLEASE REPLY with: (a) acknowledgement that you have the two measured corrections and will not
re-derive them, OR (b) a refutation of either, with the command that produced it.
