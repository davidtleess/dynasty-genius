# Loop Control — Script-Enforced Severity Budget, Round Caps, and Diminishing-Returns Detector

- **Date:** 2026-08-12
- **Status:** `JOINT-SYNTHESIS DRAFT — Codex delta dispositioned by Claude (§7: 10 accepts, 0 rejects, 2 raised items R1/R2, 1 David flag on D5) — awaiting Codex final CLEAR review, then David authorization` (per David's 2026-08-12 direction; see §5)
- **Authoring lane:** Claude authored the spec and framing · **Codex** independently proposed the same control plane, performed the diff, and integrated the synthesis corrections recorded here; Codex remains the sole binding reviewer and RED author, so this draft is **not CLEAR** until Claude has dispositioned the synthesis changes and Codex has reviewed that resulting artifact · **Gemini** is Operations & Telemetry — awareness copy only, telemetry facts on request, no judgment
- **Scope:** Cockpit **process layer** across two repos — a governance amendment to `dynasty-genius/docs/governance/02-agent-operating-loop.md` (authority) and a contract-tested extension to `dg-cockpit/autonomy/core` plus host hooks (enforcement). It is explicitly **not** a product change: no model, feature, surface, or David-facing output is touched; the No-Verdict Line and frozen-model constitution are untouched by construction.

---

## 1. Problem (measured, not inferred)

Cockpit adversarial review has no mechanical ceiling. The rules in `02-agent-operating-loop.md` §Adversarial review pattern say "repeat until the independent reviewer replies with an explicit CLEAR" with no round cap, no severity floor on what keeps a cycle open, and no objective stall signal. The autonomy layer that could enforce a ceiling has no concept of a review round. One host hook actively pushes the other way: the Antigravity Stop hook forces continuation without bound.

**David's directive (verbatim, 2026-08-12):** "Cap each review phase at 5 rounds and the whole run at 10. At a cap, never manufacture CLEAR—either advance with zero blockers or stop for my decision. […] Diminishing returns requires repeated unresolved blocker fingerprints plus low scoped churn across three rounds. A small diff alone must not halt a legitimate two-line fix. […] Enforce the shared result through host Stop hooks, including the currently unbounded Antigravity stop hook."

**Reproduced (not asserted).**

The observed failure — last night's overnight arc, from `docs/agent-ledger/2026-08-12.md` (02:55 ET entry):

> Session arc: RED v20 → v26 (seven frozen RED generations, two withdrawn on RED-side defects this lane proved mechanically)

and from `AGENT_SYNC.md`: a Codex CLEAR at v26 was retracted by one lane and then restored by another in the same morning — three stacked correction blocks fighting over whether the loop had legitimately terminated.

No mechanical cap or severity vocabulary exists in governance:

```
$ grep -cin "round cap|cap each|round limit|maximum round|round 5|10 round" docs/governance/02-agent-operating-loop.md
0
$ grep -n "BLOCKER|severity" docs/governance/02-agent-operating-loop.md | wc -l
0
```

The autonomy run state has no round concept to enforce against:

```
$ grep -n "round" dg-cockpit/autonomy/core/lib/run-state.mjs | wc -l
0
```

The Antigravity Stop hook is unbounded — `dg-cockpit/autonomy/antigravity/dg-autonomy/scripts/asw-stop-check.mjs:18-22` emits `continue` whenever background work is not idle, with no cap and no consult of run state:

```js
} else if (payload.fullyIdle === false) {
  process.stdout.write(JSON.stringify({
    decision: "continue",
    reason: "Antigravity Swarm detected active background work. Continue until spawned work is idle, verified, and cleaned up.",
  }));
```

**Root cause.** Three gaps compound: (a) `02` §Adversarial review pattern defines the win condition as "finding defects" with no severity floor, so a STYLE-weight finding legitimately opens another round; (b) `run-state.mjs` records checks and failures but not rounds, findings, or churn, so no script can observe a stall; (c) `asw-stop-check.mjs:18` can force continuation forever while (a) supplies it new rounds.

**Consequence.** Reviewer-lane wall-clock and tokens burn on non-blocking findings (v20→v26 in one night); worse, loop-termination itself became contested — the retraction/restoration fight consumed a morning and put two agent-authored correction blocks into `AGENT_SYNC.md` that David had to adjudicate. Unbounded loops are also the direct risk the two-week kill criterion measures Tower's lane against.

---

## 2. Design

One script-enforced design in `dg-cockpit/autonomy/core`, with `02` amended to carry the authority the scripts enforce. Detection and enforcement read **structured round records only** — never `AGENT_SYNC.md` prose, never inferred git history. `AGENT_SYNC.md` may carry a human-readable mirror of the verdict, written by agents, parsed by no one.

### 2.1 Contract extension — `core/contract.json`

```json
"loopControl": {
  "severities": ["BLOCKER", "WARN", "STYLE"],
  "phaseRoundCap": 5,
  "runRoundCap": 10,
  "diminishingWindow": 3,
  "diminishingWindowMaxCombinedLinesExclusive": 10,
  "phases": ["framing", "red", "green-review"]
}
```

Caps are contract data, not scattered code constants. Retuning them is still a governed contract/config change: it requires David's word, tests, and adapter regeneration rather than an ad hoc runtime override.

### 2.2 Run-state schema v3 — `core/lib/run-state.mjs` (additive)

`schemaVersion: 3` adds loop state plus a monotonic `revision` to the run record; v2 runs stay readable (absent fields ⇒ loop control reports `CONTINUE`, never a spurious halt). Every mutating verb supplies the revision it read; the atomic writer rejects a stale revision rather than silently losing a concurrent finding or round:

```js
reviewRounds: [{
  phase,            // one of contract.loopControl.phases — fail closed on unknown
  index,            // 1-based within phase
  openedAt, closedAt,
  reviewerVerdict,  // null or explicit "CLEAR"; the script never invents this word
  findings: [{
    id, severity, criterionId,
    summary, file, evidence,
    fingerprint,    // script-computed hash of normalized phase + criterionId + file + summary
    resolvedInRound // null until resolved; set to the round index that resolved it
  }],
  scope: [relativePath, ...],              // explicit, validated, worktree-relative artifact scope
  churn: {
    filesChanged, linesChanged,
    openSnapshotHash, closeSnapshotHash    // script-generated evidence, never caller assertions
  }
}],
backlog: []         // run-local WARN/STYLE parking lot, carried in the run record
```

The CLI renders `backlog` deterministically to `.git/dg-autonomy/backlog.md` for the human gate. That Markdown file is a view, not a second source of truth and not a tracked product artifact.

At `openRound`, the script snapshots the explicit artifact scope beneath the run-state directory. At `closeRound`, it snapshots the same scope and computes added/deleted line churn itself, including uncommitted state, with a bounded no-index diff. Scope validation rejects absolute paths, traversal, paths outside the authorized worktree, binaries, oversized files, and governance-noise paths (`AGENT_SYNC.md`, `docs/agent-ledger/**`, wire evidence, and the generated backlog) unless a future contract explicitly opts one in. The lane cannot type its own churn number.

### 2.3 Loop-control module — `core/lib/loop-control.mjs` (new)

Verbs (each validates fail-closed, writes through the existing atomic `writeRun` path):

- `openRound(run, {phase})` — rejects if phase unknown, run terminal, or opening would exceed either cap.
- `recordFinding(run, roundIndex, finding)` — rejects missing/invalid `severity`, `criterionId`, `file`, or reproducible `evidence`; computes the fingerprint itself from controlled normalized fields. **`WARN`/`STYLE` route to `run.backlog` at round close; only `BLOCKER` findings can hold a phase open.**
- `resolveFinding(run, findingId, {round})` — marks the blocker resolved in the named round.
- `recordReviewerVerdict(run, roundIndex, {verdict: "CLEAR", evidence})` — accepts only the independent reviewer's explicit, evidence-cited CLEAR and rejects CLEAR while any BLOCKER remains.
- `closeRound(run, roundIndex)` — computes scoped churn from script-owned snapshots and stamps `closedAt`; it accepts no caller-supplied churn.
- `loopVerdict(run, contract)` — **pure function of the run object** (no I/O, no git, no file reads), returning:

```js
{ status: "CONTINUE" | "CLEAR_ELIGIBLE" | "ADVANCE_PHASE" | "HUMAN_GATE_REQUIRED", reasons: [ ... ] }
```

Verdict rules, in David's words made mechanical:

1. **Severity budget.** Zero unresolved BLOCKERs with no recorded CLEAR ⇒ `CLEAR_ELIGIBLE`: no remediation round is allowed, but the phase does not advance until the independent reviewer records its explicit evidence-cited CLEAR. WARN/STYLE items remain in the backlog.
2. **Explicit CLEAR.** Zero unresolved BLOCKERs plus the independent reviewer's recorded CLEAR ⇒ `ADVANCE_PHASE`. This preserves `02`'s termination authority and prevents the script from manufacturing the word.
3. **Phase cap.** Round `phaseRoundCap` closes with unresolved BLOCKERs ⇒ `HUMAN_GATE_REQUIRED`; opening round 6 is rejected.
4. **Run cap.** At `runRoundCap`, unresolved BLOCKERs ⇒ `HUMAN_GATE_REQUIRED`; zero BLOCKERs follows rules 1–2 rather than forcing a false halt.
5. **Diminishing returns (conjunction, per David).** The same blocker fingerprint remains unresolved in all of the last `diminishingWindow` consecutive closed rounds of the phase **AND the sum of those rounds' script-measured `churn.linesChanged` is less than 10** ⇒ `HUMAN_GATE_REQUIRED` with reason `DIMINISHING_RETURNS`. A small diff alone never halts: a two-line round that resolves its blocker removes the repeated-open fingerprint and no rule fires.

`HUMAN_GATE_REQUIRED` is a verdict, not a third terminal state. Applying it transitions the existing run to **`BLOCKED`** with structured `reasonCode` (`PHASE_ROUND_CAP`, `RUN_ROUND_CAP`, and/or `DIMINISHING_RETURNS`) plus evidence and the smallest resume action. This preserves the autonomy layer's approved two-state terminal contract (`READY_FOR_GATE` / `BLOCKED`) while letting status surfaces render “human gate required” distinctly.

CLI verbs surface on the existing `core/bin/dg-autonomy.mjs` (`round-open`, `finding`, `resolve`, `round-close`, `verdict`) so every lane records rounds the same way. Round verbs reject `role: "tower"` runs — Tower's contract stays `health-verify` only.

### 2.4 Enforcement — host hooks (the shared result, applied)

- **Antigravity Stop hook bounded** (`asw-stop-check.mjs`): before ever emitting `continue`, load the run via the existing `resolveStatePath()`/`DG_AUTONOMY_STATE` seam and compute `loopVerdict`. Terminal run or `HUMAN_GATE_REQUIRED` ⇒ **never** `continue` (emit the empty decision plus the verdict reason). Unreadable/absent state in an autonomy-run context ⇒ fail closed to no-continue. Outside an autonomy run (no state file expected), current behavior is preserved.
- **Claude and Codex adapters gain Stop hooks** that surface the verdict at stop time (`BLOCKED — HUMAN_GATE_REQUIRED: <reasons>` becomes the visible last word of the lane) and never emit a continue past a cap. Codex behavior follows the current official Stop-hook contract, including `stop_hook_active`, so the adapter cannot create its own continuation loop.
- **Hard backstop — PreToolUse:** the existing per-host PreToolUse policy hooks additionally deny mutating tool calls when the run is terminal. Stop hooks can decline to force continuation, but only PreToolUse can stop a lane that keeps editing mid-turn; without it the cap is advisory against an agent that never tries to stop. Read-only status/evidence inspection remains allowed so the human-gate packet can be produced.

### 2.5 Governance amendment — `02-agent-operating-loop.md` (authority)

A new subsection **"Loop-control budget"** in §Cockpit Process stating: the severity vocabulary and its budget rule; the 5/10 caps — explicitly covering the framing challenge phase, which today has a protocol shape but **no mechanical cap** (grep above); the at-cap rule verbatim ("never manufacture CLEAR — advance with zero blockers or stop for David"); the duty to record rounds/findings/churn via the autonomy verbs before sending cycle messages; and that `AGENT_SYNC.md` mirrors verdicts for humans only and is never parsed. Gemini's telemetry-only seat and Tower's non-orchestrator charter are restated as untouched.

---

## 3. Out of scope (named, not hidden)

- **Gemini binding stop power (proposal's fix 4).** David ruled it out 2026-08-12; the 2026-07-16 telemetry-only ratification stands. Its route remains the observable-fact report.
- **`tmux_msg.py` send-path linting** (severity-tag validation on cockpit messages). Real defense-in-depth, but a second enforcement surface belongs in its own spec once round recording exists; will surface by name as a follow-up.
- **Hygiene-tripwire extension** flagging CLEAR claims that lack run-state round records (the recording-bypass detector). Named follow-up in §6 — not in this increment.
- **Retroactive backfill** of past runs/ledgers into round records. The detector starts observing from adoption forward.
- **Cross-worktree/run aggregation.** Run state is per-worktree by design (`.git/dg-autonomy/run.json`); a fleet view is a later, separate concern.
- **Retuning David's numbers.** 5/5/10/3/10-lines are his stated values, carried as contract data; changing them is a one-line contract edit under his word, not this spec.

## 4. Falsification seeds — the RED matrix

**Test path:** `dg-cockpit/autonomy/tests/loop-control.test.mjs` and `stop-hook-bounds.test.mjs` — the target repo's existing `node:test` `.mjs` contract pattern (deviation from the product repo's `tests/contract/test_<slug>_red.py` convention, stated openly: the code under test is Node, in dg-cockpit). All hermetic: state path injected via the existing `statePath`/`DG_AUTONOMY_STATE` seam into temp dirs; stop-hook scripts driven via stdin payload + env; `loopVerdict` tested as a pure function; no git, no network, no live `AGENT_SYNC.md`.

| # | Seed (inputs / state) | Required behavior |
|---|---|---|
| F1 | `recordFinding` with severity missing/lowercase/outside vocabulary, or missing `criterionId`/file/evidence | Throws; run file unchanged (fail closed) |
| F2 | Round with only WARN/STYLE findings, then `closeRound`, but no reviewer CLEAR | Verdict `CLEAR_ELIGIBLE`; items appear in `run.backlog` and rendered `backlog.md`; no remediation round opens and phase does not silently advance |
| F3 | One unresolved BLOCKER, rounds under both caps | Verdict `CONTINUE`; no halt |
| F4 | 5th round of a phase closes with an unresolved BLOCKER | `HUMAN_GATE_REQUIRED`; applying verdict produces terminal `BLOCKED` with `PHASE_ROUND_CAP`; `openRound` for round 6 throws |
| F5 | 5th round closes with all BLOCKERs resolved | Without recorded CLEAR: `CLEAR_ELIGIBLE`; with evidence-cited reviewer CLEAR: `ADVANCE_PHASE` |
| F6 | 10th round total across phases | Unresolved BLOCKER ⇒ `HUMAN_GATE_REQUIRED`; zero BLOCKERs follows the F5 CLEAR rule rather than forcing a halt |
| F7 | Same fingerprint unresolved across 3 consecutive closed rounds whose **combined** measured churn is 9 lines | `HUMAN_GATE_REQUIRED`, reason `DIMINISHING_RETURNS` |
| F8 | 2-line round whose diff **resolves** its blocker (fingerprint marked resolved) | No halt — the two-line-fix protection holds |
| F9 | Repeated fingerprint across 3 rounds whose combined measured churn is exactly 10 lines | No `DIMINISHING_RETURNS` (exclusive threshold) |
| F10 | Controlled fingerprint fields differ only in case/whitespace across rounds | Script computes the same identity; caller-supplied fingerprint is rejected/ignored |
| F11 | Cap reached AND diminishing simultaneously true | `reasons` contains both — one failure must not mask another |
| F12 | v2 run record (no `reviewRounds`) fed to `loopVerdict` | `CONTINUE`, no throw, no spurious halt (additive migration) |
| F13 | `openRound` on a `role: "tower"` run; unknown phase string | Throws both times (role and phase fail closed) |
| F14 | Antigravity stop payload `fullyIdle:false` + run `BLOCKED` for a loop-control reason | Output contains **no** `"decision":"continue"` |
| F15 | Same payload + state file unreadable/corrupt JSON in an autonomy-run context | Fail closed: no `continue` emitted |
| F16 | Same payload + no autonomy run in scope (legitimately absent state) | Current upstream behavior preserved (`continue` allowed) — bounding, not breaking, ASW |
| F17 | Two `closeRound` calls start from the same run revision | One succeeds; the stale writer receives a named conflict and must reload/retry; no finding or round is silently lost |
| F18 | PreToolUse policy: mutating tool call while run terminal (`BLOCKED` for loop control) | Denied; read-only/status calls still permitted |
| F19 | `round-open` scope contains absolute path, `..`, symlink escape, excluded governance-noise path, binary, or oversized file | Reject before snapshot; state unchanged |
| F20 | Caller attempts to pass `linesChanged` to `round-close` | Reject the caller assertion; churn comes only from script-owned open/close snapshots |
| F21 | Open/close snapshots include an uncommitted two-line edit | Measured churn is 2 with reproducible snapshot hashes; real git index/staging state is byte-for-byte unchanged |
| F22 | Codex Stop receives `stop_hook_active:true` without a state transition since its prior continuation | It does not create another continuation loop; terminal and human-gate precedence remain fail closed |

## 5. Sequence (cockpit-TDD, adapted to David's stated flow)

1. **Codex diff + joint synthesis (David's explicit instruction):** Codex diffs this draft against its independent proposal; Claude and Codex synthesize one final spec version. Divergences neither lane will yield on go to David.
2. **Cockpit CLEAR on the synthesized spec:** Claude framing → Codex written challenge → Claude written disposition on every item → Codex CLEAR (Gemini: awareness copy).
3. **David authorizes the RED.**
4. Codex authors the RED (F1–F22) in `autonomy/tests/`, demonstrably red against current `dg-cockpit` main.
5. Claude implements GREEN (schema v3, `loop-control.mjs`, hook changes, `02` amendment text); runs the full `autonomy/tests` suite + `verify.sh --isolated`; self-probes the matrix.
6. Codex independent review → CLEAR.
7. **Only then, each on David's separate word:** commit; `install.sh --activate` (live hook changes are host-config mutations — his call); the fresh-session Codex `/hooks` trust review the installer intentionally does not bypass; the `02` governance commit in the product repo.

## 6. Risks

| Risk | Honest assessment · mitigation |
|---|---|
| **Recording bypass** — lanes simply don't call the round verbs; detector observes nothing | The known-largest hole. `02` makes recording a duty before cycle messages; the named follow-up (out of scope §3) extends the hygiene tripwire to flag CLEAR claims with no round records. Until then this is procedural — said plainly. |
| **Severity gaming** — a real defect labeled WARN to end a loop | Every finding names the violated criterion and reproducible evidence; the independent reviewer owns its severity, the implementer dispositions it, and a disputed label escalates like any disagreement. The script cannot solve dishonest classification, but it makes the claim auditable. |
| **False halts** — caps interrupt a legitimately hard review (last night needed 7 rounds and *converged*) | By design the halt is a David decision point, not a verdict; his release valve is one word, and cap values are contract data he can retune. |
| **Stop hooks can't stop a lane that never stops** | True — Stop fires only at stop attempts. That is exactly why §2.4 adds the PreToolUse terminal-state deny; if the cockpit rejects that addition in challenge, the caps degrade to advisory and the spec should say so in its final version. |
| **ASW vendor drift** — bounding a vendored, pinned hook | ASW is pinned at audited `a949cb8…`; the bound wraps the adapter copy, not upstream; F16 proves non-autonomy behavior is preserved. |
| **Schema migration false-positives** | F12 pins v2-tolerance; loop control never halts a run that predates it. |
| **What this does not prove** | It cannot prove review *quality* — a capped loop can still be a wrong loop. It bounds cost and forces the stall to a human decision; it does not make the decision. |

---

## 7. Claude disposition of the Codex synthesis delta (2026-08-12)

Per `02` §Strategy/UX framing first (the no-broker duty): every synthesis change dispositioned in writing, accept/reject with reasons. Layer named per the pending `05` codification, voluntarily: `governance / cross-layer` — no layers 1–6 product artifact is touched. **Except where a disposition item says otherwise, this section is the only change since Codex's integration — the CLEAR-review delta is this section plus the two status-line edits it describes.**

**D1 — Explicit-CLEAR preservation (`reviewerVerdict`, `recordReviewerVerdict`, `CLEAR_ELIGIBLE`/`ADVANCE_PHASE` split). ACCEPT — the strongest correction in the delta.** My draft's rule 1 let the script advance a phase on zero open BLOCKERs alone; that manufactures the termination `02` reserves for the independent reviewer's explicit CLEAR. The split closes it, and rejecting a CLEAR while any BLOCKER is open is the correct fail-closed guard.

**D2 — Two-terminal-state ruling (`HUMAN_GATE_REQUIRED` as a verdict that lands as `BLOCKED` + structured `reasonCode`). ACCEPT; my `HALT_FOR_DAVID` recommendation is withdrawn.** The `reasonCode` achieves the render-it-distinctly semantics I wanted without widening a terminal contract every existing consumer (hooks, status surfaces, installer checks) already honors.

**D3 — Script-owned churn (open/close snapshots, no caller-supplied numbers, scope validation, governance-noise exclusion). ACCEPT.** My caller-supplied `churn` was an integrity hole: a lane could type the number that decides its own halt. Excluding `AGENT_SYNC.md`/ledger churn from "progress" is a catch I had missed — state-doc motion is not remediation.

**D4 — Script-computed fingerprint. ACCEPT the principle; RAISE R1 on composition.** Caller-supplied identity was evadable, so computing it from controlled fields is right. But including free-text `summary` in the hash re-opens the same evasion one level up: the identical defect re-worded each round yields a fresh fingerprint and `DIMINISHING_RETURNS` never trips. The counter-tradeoff is real too — dropping `summary` merges genuinely distinct defects sharing `criterionId`+`file`, which can false-trigger the window. **R1 for the CLEAR pass:** pick the identity semantics deliberately — my proposal is normalized `phase`+`criterionId`+`file` with the repeat window keyed on finding lineage (a fingerprint that resolves and later reappears as a *new* finding restarts the window, so a resolved-then-recurring defect is not counted as one continuous stall) — and pin the chosen semantics in a dedicated F-seed either way.

**D5 — Combined-window exclusive churn threshold (per-round floor → sum across the 3-round window `< 10`, key renamed). ACCEPT as the conservative reading — WITH A DAVID FLAG.** His words, "low scoped churn across three rounds," support both readings. The combined-sum form triggers far less often (near-zero total motion) and biases against false halts, with the round-5 phase cap still backstopping cost. But this changed the *semantics of David's stated number* between drafts, so the choice is surfaced for his authorization word rather than settled between lanes: per-round floor (my draft — halts a lane grinding ~9 lines/round against the same blocker) vs. combined window (this draft — halts only near-total stall).

**D6 — Optimistic concurrency (monotonic `revision`, stale writes rejected by name; F17 rewritten). ACCEPT.** My "last atomic write wins" silently dropped concurrent findings — in a multi-lane cockpit that is data loss at exactly the moment two lanes disagree.

**D7 — Codex Stop-hook loop-guard (`stop_hook_active`, F22). ACCEPT.** Bounding the bounder: without it the enforcement hook could itself become the unbounded continuation loop this spec exists to remove.

**D8 — Deterministic `backlog.md` render as a view, never a second source of truth. ACCEPT.** Matches David's run-local-backlog instruction while keeping the run record authoritative.

**D9 — Evidence discipline (`criterionId` + reproducible `evidence` required on findings; CLEAR must cite evidence; F1 extended). ACCEPT.** This is `02`'s enumerated-checks CLEAR definition made mechanical.

**D10 — Retuning language tightened (§2.1: governed change, never ad hoc runtime override). ACCEPT.**

**R2 (raised, minor — wording only, left unedited so the CLEAR delta stays clean).** §2.3 rule 1's "no remediation round is allowed" could read as barring *any* new round in `CLEAR_ELIGIBLE`. A reviewer who discovers a genuinely new, evidence-cited BLOCKER after a zero-blocker state must still be able to open a round under the caps — otherwise the state deadlocks against honest late discovery. Proposed: one clarifying sentence in the final text distinguishing "no round may open on WARN/STYLE grounds" from "a new BLOCKER finding may open a round, caps permitting."

*Summary: 10 accepts, 0 rejects, 2 raised items (R1 fingerprint composition, R2 CLEAR_ELIGIBLE wording), 1 David flag (D5 threshold semantics). Nothing in the Codex delta is reverted or modified.*

---

*Joint-synthesis draft — Claude-authored 2026-08-12 per David's direction; Codex diff integrated the script-owned evidence, explicit-CLEAR, combined-window, concurrency, and two-terminal-state corrections; Claude disposition recorded in §7.*

---

## 8. As-built notes (2026-08-12 — David's word: "build it yourself"; Codex lane was frozen)

David collapsed the lanes for this build. Implementation lives in `dg-cockpit/autonomy/` (uncommitted), test-first against F1–F22 (RED verified failing, then GREEN). Decisions made during the build, recorded for the after-the-fact review:

- **R1 resolved as proposed:** fingerprint = SHA-256 of normalized `phase`+`criterionId`+`file`; `summary` excluded (reword-evasion closed). The false-merge tradeoff is accepted and mitigated by lineage: the diminishing window counts only fingerprints recorded at-or-before the window start, so a resolved-then-recurring defect restarts its window (pinned by F7/F8).
- **R2 resolved as clarified:** `CLEAR_ELIGIBLE` bars nothing mechanically at round-open; new rounds (for genuinely new BLOCKERs) may open under the caps. The severity budget binds through the verdict, not through a round-open bar — no deadlock against honest late discovery.
- **D5 built as-written** (combined-window exclusive threshold, contract key `diminishingWindowMaxCombinedLinesExclusive`). One-line contract retune if David rules for per-round.
- **Hook-hang defense added everywhere** (motivated by the 2026-08-12 Codex freeze inside a PreToolUse hook): all hook-side state reads are synchronous, bounded (`git rev-parse` capped at 2s, snapshot diff at 5s), and never throw; a hook can fail closed but cannot hang its lane on loop-control's account.
- **F21 test fixture corrected during GREEN:** run state in the fixture moved outside the measured worktree (mirroring production `.git/dg-autonomy`), after the first run caught the fixture polluting `git status`.
- **Known pre-existing failure, not mine to fix here:** `tests/cockpit.test.mjs` "flight deck loads only the approved role adapters" fails on current main — the committed flight deck uses absolute paths where the test expects `$HOME`-relative. Untouched by this build; surfaced to David.

*No commit has been made; `install.sh --activate` has NOT been run — live hooks are unchanged until David's word. Next actor: Codex after-the-fact CLEAR review of spec + implementation, then David's commit/activation words.*

---

## 9. The Judge lane (2026-08-12, David-directed — write · review · judge)

David's design intent, stated after the build: a **three-agent system — write, review, judge** — with a standing, binding judge seat. His words: *"enforce a limit to the number of reviews — if it reaches that number it goes to the judge. it can go to the judge before then. the judge rules and we ship what the judge rules — the judge can consult Tower."* Seat-holder decision: **new dedicated lane** (not a Gemini re-role), placed in the Studio–Tower window.

**What changed (built TDD, seeds J1–J8 in `autonomy/tests/judge-adjudication.test.mjs`):**

- The gate verdict renamed `HUMAN_GATE_REQUIRED` → **`ADJUDICATION_REQUIRED`**: caps and the diminishing-returns detector — the only routes — send the case to the Judge, not directly to David.
- ~~Early referral~~ **REMOVED — David's word, 2026-08-12 evening ("lock it to a quantifiable loop"):** routing to the Judge is purely counter-driven (phase cap 5, run cap 10, diminishing returns). The discretionary referral verb was built, then deleted the same evening on his ruling; J1/J1b now pin its absence, and legacy referral fields in run records carry no weight. This supersedes the morning's "it can go to the judge before then."
- **Binding ruling** (`adjudicateRun` / CLI `adjudicate`): `SHIP` resolves the gate to `READY_FOR_GATE`, records evidence + content pins, and is itself the commit authorization — the Claude/Codex hooks then permit **exactly `git commit`**: no edits, no push (J2, J7, J8). `STOP` keeps the run `BLOCKED` with `JUDGE_STOP`, parked for David (J3). One gate, one ruling (J6). The Judge can never override a verification-failure block (J4); malformed rulings fail closed (J5).
- **The Judge lane itself:** agent charter at `~/.claude/agents/judge.md` (rules only on loop-control gates; enumerated-evidence standard; bootstraps from source per ruling; may consult Tower for VERIFIED facts — Tower does not co-rule; Studio wall TW29-WALL-35 binds it; No-Verdict Line not waivable by ruling). Pane 2.3 in the Studio–Tower window, spawned live and wired into `dynasty_flight_deck.sh` §7b.

**THE AUTHORITY TRANSFER — ratify knowingly.** This reverses part of the morning directive ("at a cap … stop for my decision"). As built, a capped or referred review dispute is settled **finally by the Judge**, and a SHIP ruling **ships without a further David content-gate**: David's landing word for review-dispute ships is delegated to the ruling. David retains: push, activation, scheduling, everything outward-facing, all verification-failure blocks, disputes about a ruling itself, and an unconditional override at any time. **Status: RATIFIED — David's word, 2026-08-12 evening ("ratified"), given with the delegation explicitly flagged.** The Judge's SHIP rulings ship without a further David content-gate; his override and the outward-facing gates (push, activation, scheduling) remain his. Reversal, should he ever rule it, is one hook-guard flip in each of two hooks.

**Honest limits:** seat identity is procedural, not cryptographic (any lane could physically run `adjudicate`; the charter, evidence standard, and audit trail are the control — named, not hidden). The Antigravity tool policy carries the terminal-deny but not the SHIP-commit allowance (implementer lanes are Claude/Codex). Judge model vendor overlaps with the writer lane; mitigation is the per-ruling fresh bootstrap, and the seat can be re-pointed at a different vendor later without mechanism changes.
