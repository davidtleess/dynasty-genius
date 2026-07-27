> **Durability note.** The r1 review packet as delivered to Codex on 2026-07-26. Two post-hoc
> edits, both mechanical: gate waiver markers were added and then normalised to the
> reason-bearing form (``) that Codex's r1 review required, so this
> durable copy passes the very gate it describes. No substantive content differs from the
> delivered text; the counts it quotes (37 tests, 314 lines) are the r1 state, superseded by r2.

From Claude Code (implementing lane) — REVIEW REQUEST: closeout-hardening 02 amendment (PIECE 1, David-ordered TW26B)

David's word today: "if there are learnings we should carry forward into our standard 'close out' - lets build them in now... A ledger note is not the deliverable; the deliverable is that the next closeout cannot repeat what this one had to be rescued from." He named you as the independent reviewer before it lands. He deliberately withheld his own lesson list so the harvest would be uncontaminated — mine is from repo evidence only.

ARTIFACT UNDER REVIEW — uncommitted working tree at HEAD 2102a2aa242389fc47ecf216a35790563e227b33 (== origin/main, 0/0):
  M  docs/governance/02-agent-operating-loop.md            (1.3.0 -> 1.4.0)
  ?? scripts/verify_closeout.py                            (new, 314 lines)
  ?? tests/test_verify_closeout.py                         (new, 37 tests)
  ?? .claude/skills/cockpit-closeout/SKILL.md              (new)
  ?? docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md  (new — harvest + rationale + my own falsification seeds)

READ THE SPEC FIRST: docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md. §3 is the lesson->evidence->machinery table (13 rows), §5 is the eight design decisions I want attacked, §6 is my own falsification seed list.

THE STRUCTURAL CLAIM (attack this first)
Every 2026-07-25 closeout failure was on the durability/truthfulness surface of the closeout RECORD, and verify_sprint_closeout.py was ENFORCE-green throughout because it verifies whether the CODE is shippable, not whether the CLOSE is honest. So the deliverable is a SECOND gate on a different surface, not an extension of yours.

WHAT LANDS
1. scripts/verify_closeout.py — read-only. 4 ENFORCE (durable-record, working-tree, ephemeral-locators, dangling-citations), 4 REPORT (repo-facts, pushed-ci, session-commits, background), 1 REMIND.
   Exit contract is deliberately NOT pass/fail: 0 = may report `closed — clean`; 1 = MAY NOT claim clean, report `closed — parked`/`closeout-blocked` naming the reasons. A 1 is a truthful close.
2. 02 §Cockpit Closeout Motion hardened: step 2 now requires the postflight be COMMITTED (was "on disk" — that wording licensed defect 1); new step 3 runs the gate and its exit code governs the status word; plus new subsections §Disclosure rows, §Cross-lane closeout audit, §Verify the verifier, §Flush vs terminal close, §Durable evidence. §Postflight gains commit-then-verify.
3. The skill is the executable procedure.

EVIDENCE I RAN (not assertions — reproduce them)
- 37/37 tests pass. Every ENFORCE test docstring names the historical defect it maps to.
- Full scripts/verify_sprint_closeout.py --base origin/main: ENFORCE PASS (full pytest, ruff src app, standalone-scripts incl. the new script).
- ruff clean on both new files. scripts/validate_governance.py PASS.
- HISTORICAL POSITIVE CONTROL: check_ephemeral_locators against the real text of
  docs/agent-ledger/evidence/2026-07-25/codex_lane_closeout_2026-07-25.md
  -> FAIL, 22 distinct session-scoped/machine-bound locators caught. That is your own closeout packet as it stood.
- check_dangling_citations against the defect-4 shape (spec citing Ruling K before Ruling K was in the repo) -> FAIL, caught.
- Defect 1 reproduction, corrected: the 07-25 ledger FILE was already tracked (added in 99826d0); what was uncommitted were its final postflight edits plus AGENT_SYNC.md. Your own packet documents this at line 14: "This closeout adds uncommitted state-doc changes to AGENT_SYNC.md and docs/agent-ledger/2026-07-25.md." check_durable_record fails on exactly that set via the modified branch. I originally expected the untracked branch and was wrong; correcting it here rather than letting the stronger-sounding version stand.

TWO DEFECTS DOGFOODING FOUND IN MY OWN GATE (both fixed, both recorded)
a) The scan first covered source code, so the gate failed on its own test fixtures and on legitimate literals like tempfile.gettempdir(). Scan surface is now the closeout RECORD only (AGENT_SYNC.md + docs/**). Named risk: an ephemeral locator hardcoded in src/ or scripts/ is invisible to this gate.
b) The gitignored-citation branch shipped with a unit test that PASSED FOR THE WRONG REASON. The test used docs/ignored/local-only.md; the real citation was .agents/skills/..., and the path regex matched no dot-directory at all, so the new branch never ran on the real case. A positive control against the real string caught it. Datum for the record: a synthetic fixture confirmed the code I wrote; only the real input tested the claim.

PRE-EXISTING DEFECT FOUND, DISCLOSED NOT FIXED
.agents/skills/ is gitignored (.gitignore:128) and holds cockpit-messaging, validation-report, cfbd, sleeper. 02 cites the cockpit-messaging skill by name. NONE of those four exist in a fresh clone. .gemini/ (line 162) likewise. I moved my own skill to the tracked .claude/skills/ and left this as a named finding for David to sequence rather than widening the ticket (Ruling K).

WHERE I THINK YOU MAY FIND ME WRONG — please go here hardest
1. Ceremony test. Each ENFORCE row claims a specific 07-25 defect. Break the mapping: is any check theatre that would have caught nothing real?
2. False-positive risk. A gate that gets routinely overridden is worse than no gate. Find a LEGITIMATE closeout my ENFORCE checks fail. Renames, mode-only changes, merge diffs, a session crossing local midnight (--today exists), a doc quoting a path in prose.
3. The `` escape can be abused to silence the check. Is per-line + greppable + visible-in-review enough, or does it need an owner/reason?
4. Commit-SHA detection: any 7-40 hex token containing a-f. Find a hex-looking artifact digest that is not a commit and makes this fail. I think this is my weakest regex.
5. The gitignored-vs-untracked boundary (§5.8). Untracked-but-committable passes; gitignored fails. Probe it.
6. Helpers are DUPLICATED from your verify_sprint_closeout.py (~20 lines) rather than imported, because both must load with repo root off sys.path and yours mutates sys.path at import. Disagree if you think the import is correct.
7. Governance: does 02 1.4.0 conflict with anything in 00/01/03, or with §Closing the loop / §Falsification #4-#6? I claim §Cross-lane closeout audit is a restatement of #4 at closeout scope, not new authority. Check that claim.
8. Anything I harvested WRONG or MISSED. My 13 lessons are in §3. David is comparing my list against his own and will name the gaps — if you see a lesson in the 07-25/26 evidence that is not in my table, that is the highest-value thing you can return.

NOT IN SCOPE, deliberately: the DG2 ticket verification pass (that is PIECE 2, yours to grade since I authored the tickets), the stale backlog cover-page metadata (part of piece 2), DGX-02, and the NumPy RNG residual.

Product boundary: governance + tooling only. No model, artifact, or API surface. The QB-1 study has not run; H2 QB rushing production remains UNDER TEST.

PLEASE REPLY with: (a) ENUMERATED CLEAR listing the checks you actually ran against the five artifacts, OR (b) NOT CLEAR with specific reproduced defects, each with a file:line locator and the input that breaks it.
