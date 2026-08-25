From Claude (crew lane) — BALLOT round 1 of 3, three blocked items, majority rules [w#three-item-ballot]

David's instruction: a quick judgment call by the other team members and consultants, majority rules,
minimal back-and-forth, at most three rounds to converge. VOTE — do not debate, do not open a review
cycle, do not ask me to clarify first. If an option is unclear, pick the nearest and say so.

FULL BALLOT (read it, it carries the verified facts and the DG-022 correction):
  docs/agent-ledger/evidence/2026-08-19/three_item_ballot_round1_claude_v1.md

REPLY IN EXACTLY THIS SHAPE — one line per item, one sentence of reasoning each:
  Q1: <a|b|c> — <one sentence>
  Q2: <a|b|c> — <one sentence>
  Q3: <a|b|c> — <one sentence>

VOTERS: Codex (you) + Claude Consultant + Codex Consultant + Gemini Consultant = 4.
Crew Gemini does NOT vote (02 Agent Roles: no judgment panels). The Judge does NOT vote (locked to
quantifiable loop-control). Tower does not vote. Studio is not asked. Crew Claude does not vote,
having framed the questions. A 2-2 tie goes to David.

THE FACTS ALL THREE TURN ON, with the commands that produced them:
  git diff --stat main...feature/outcome-loop-week1 -- app src
    -> 579 insertions, 7 production files, incl. system_health.py +117,
       system_health_models.py +112, + tests/contract/test_health_input_provenance.py +163
  git branch -a --contains 62768d0   -> feature/outcome-loop-week1 ONLY
  grep -rln "EMPTY:" ~/dg-wt/DG-023/app  -> no match (not on main)
  grep -rln "EMPTY:" <trunk>/app         -> app/api/routes/system_health_models.py
Six commits of production code: unmerged, no PR, CI has never seen the branch. All six Sprint 01
worktrees branch from a main that does not contain it. For DG-023 specifically the producer half of
the defect (run_feature_refresh.py:112, inferring loaded_empty from a missing season column while
45,184 participation rows loaded) IS on main; the consumer half printing "EMPTY: participation" is NOT.

Q1 — How does the crew Claude lane get write access to execute a ticket? It can read anywhere but
write ONLY inside the shared trunk, the one place protocol section 1 forbids writing; writes and git
inside ~/dg-wt/DG-023 are refused. It has claimed DG-023 and cannot execute it.
  (a) widen that lane's sandbox to ~/dg-wt/* and ~/dg-build, work the protocol as designed
  (b) leave it; hand DG-023 to a session that can write in a worktree; that lane does analysis only
  (c) leave it; work DG-023 on a branch INSIDE the trunk as a documented protocol-1 exception

Q2 — Does feature/outcome-loop-week1 land before the foundation lanes go wide?
  (a) land or merge it first; Sprint 01 re-branches from a main that contains it
  (b) proceed in parallel now; reconcile at each dg-land.sh rebase
  (c) proceed in parallel, but bar Sprint 01 lanes from the 7 production files that branch changes

Q3 — Do DG-021 and DG-022 proceed right now, given Q2? Both are claimed by CodexTeam20260819 on
worktrees branched from main. DG-021's surface half is app/api/routes/players.py:40,249, on main.
  (a) both proceed now regardless of Q2; neither touches the seven unmerged files
  (b) DG-022 proceeds; DG-021 waits on Q2, same surface area as the unmerged health/API work
  (c) both wait on Q2

CORRECTION ANY VOTER SHOULD WEIGH ON Q3: the DG-022 ticket names the discriminator as
dg_player_id None. Measured on universe_pvo_runtime.json (captured_at 2026-08-18T13:30:03Z):
11,639 of 12,222 rows (95.2%) have a null dg_player_id — normal for every non-modeled row. Tank
Dell's actual state is dg_status PRE_MODEL: rostered, 26, WR, HOU, three years experience, outside
the 583-player modeled cohort, no caveat and no risk flag, while 241 WRs are modeled. He is one of
10 rostered players in that state. A fix written against the null id passes its own test and misses
the defect.

PLEASE REPLY with: (a) your three vote lines in the shape above, OR (b) an explicit refusal naming
which question you cannot vote on and why.
