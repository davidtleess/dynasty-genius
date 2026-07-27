# 02 Amendment — Closeout Hardening (from the 2026-07-25/26 rescue)

- Status: DRAFT → Codex independent review → land. Amends `docs/governance/02-agent-operating-loop.md` (1.3.0 → 1.4.0).
- Author: Claude Code (implementing lane) · 2026-07-26
- Independent reviewer: Codex (David-directed: *"Codex reviews the change independently before it lands."*)
- Source directive: David, 2026-07-26 — *"if there are learnings we should carry forward into our standard 'close out' - lets build them in now… A ledger note is not the deliverable; the deliverable is that the next closeout cannot repeat what this one had to be rescued from."*
- Harvest independence: David deliberately withheld his own lesson list so this one would be uncontaminated. Everything below is derived from repository evidence, not from a relayed list.

## 1. Why this exists

The 2026-07-25 closeout was reported **clean** and was not. It reopened four times and
needed a multi-hour rescue on 2026-07-26 before the session's record was actually safe.

**Every failure was on the durability and truthfulness surface of the closeout record
itself — and the deterministic gate that existed (`verify_sprint_closeout.py`) was fully
green throughout, because it verifies whether the CODE is shippable, not whether the
CLOSE is honest.** That gap is the root cause this amendment closes.

## 2. Evidence base

Read independently, from the repo:

- `f6115d6` commit message + the `TRUE CLOSE` entry in `docs/agent-ledger/2026-07-25.md` — four named defects and the rule taken from them.
- `docs/agent-ledger/2026-07-26.md` — the rescue: DGX-03, durability promotion, RISK-1 closure, the combined-diff review's two residuals.
- `docs/agent-ledger/evidence/2026-07-25/codex_lane_closeout_2026-07-25.md` — a `closed — parked` packet whose evidence index is ~30 ephemeral locators.
- `docs/agent-ledger/evidence/2026-07-25/codex_tower_accountability_probe_2026-07-25.md` and `docs/agent-ledger/2026-07-25-claude-accountability-probe.md` — what each lane was carrying that a standard closeout never asked for.
- `AGENT_SYNC.md` — the `⚠ CORRECTION FOR TOWER'S CLOSEOUT REPORT` banner and the CI-red omission.
- `docs/superpowers/specs/2026-07-14-cockpit-closeout-motion-02-amendment.md` and 02 §Cockpit Closeout Motion — the motion as it stood.
- `scripts/verify_sprint_closeout.py` — the gate that was green while all of this happened.

## 3. The harvest — lesson → evidence → machinery

| # | Lesson | Evidence | Machinery |
|---|---|---|---|
| L1 | "On disk" is not durable. A postflight in a working tree is one discarded change from gone. | `f6115d6` defect 1: CLOSED declared with ledger + `AGENT_SYNC` uncommitted. **The motion licensed it** — `closed — clean` required only "postflight + sync **on disk**". | 02 step 2 now says **COMMITS it**; `closed — clean` requires committed. ENFORCE `durable-record`. |
| L2 | A closeout order is memory; repo state is fact. Nothing checked the verifier. | `f6115d6` defect 2 — order wrong on **all four** repo clauses; defect 3 — "six uncommitted files" when there were eight. | 02 §Verify the verifier; REPORT `repo-facts` emits machine-read HEAD / origin / ahead-behind / exact path list. |
| L3 | Evidence that dies with the session was treated as evidence. | Codex's closeout indexes ~30 `/tmp` artifacts; Claude's probe §4(g) "the scratchpad durability problem is live right now"; RISK-1. | ENFORCE `ephemeral-locators` over added closeout-record lines. |
| L4 | Promotion is not durability — promoted docs still cited dead paths, and a promoted reproducer only ran on one machine. | 07-26 combined-diff review: three `/tmp` citations, then three more; Residual 1 MEDIUM — reproducer hardcoded an absolute `/Users/…` home path + a sibling checkout. | Same check (absolute-home pattern); 02 §Durable evidence states the reproducer contract. |
| L5 | Local green is not pushed green; the board asserted a state live CI contradicted. | 07-26 Residual 2 LOW — board omitted that `origin/main` was CI-red across runs `30178886924` / `30179373576` / `30187282058`. | REPORT `pushed-ci`; degrades to UNKNOWN, never crashes. |
| L6 | Mandatory post-commit divergence audits were parked while the close read as done. | Codex closeout §Half-done — two required audits "parked, not started"; §What David may not have been told — "the post-commit reviewer loop is still open for both". | REPORT `session-commits`; disclosure row 5: an open audit ⇒ `parked`, not `clean`. |
| L7 | A known dangling citation shipped inside a "clean" close. | `f6115d6` defect 4 — the DG2 spec cited Ruling K before Ruling K was in the repo; flagged twice, took a third David word. The stale backlog cover page is the same class, still open. | REPORT `citations` — unresolved paths and commit references are surfaced for human audit. **Demoted from ENFORCE 2026-07-26 (§4b); the enforcement attempt and its waiver system were deleted.** |
| L8 | Self-evidence failed; independent review caught it every time. | Claude probe §5 — Codex r1 found 6 defects a 27/27 self-probe missed, r2 found 2 more; probe's closing line names that mechanism as "the one thing worth protecting". During the rescue, the same pattern held in reverse. | 02 §Cross-lane closeout audit — a lane may not audit its own close. |
| L9 | "Closed" reopened four times and the word lost meaning. | `TRUE CLOSE` §The structural note. | 02 §Flush vs terminal close. |
| L10 | Carried-but-never-told items only surfaced because David ordered a special probe. | Claude probe §4(a)–(j); Codex probe §4. Ten items from one session, none of which the standard closeout asked for. | 02 §Disclosure rows — the probe's questions become standard, answered with an item or `NONE`. |
| L11 | Background ownership was asserted in prose; it should be read. | Both closeouts assert "no background processes" and both discuss PID 7180 by hand. | REPORT `background` scans and asks who created each. |
| L12 | **Structural:** the deterministic gate verifies code, not the close. | Everything above happened with `verify_sprint_closeout.py` ENFORCE PASS. | `scripts/verify_closeout.py` — a second, separate gate on the closeout surface. |
| L13 | Delivery is not durability. | Codex probe: "Positive delivery of every parked report is UNKNOWN because the wire was down and Tower hand-carried paths." | 02 §Durable evidence — when the wire is down, the repo is the delivery channel. |
| L14 | **"Verify the verifier" must cover exemption accounting and real-positive controls, not only repo facts.** A gate that reports a clean PASS while silently waiving lines is a verifier that cannot itself be verified. | Codex r1 named this as the carry-forward lesson my harvest missed: dogfooding found three verifier defects, yet waivers could still vanish behind clean PASS prose. Independently instanced twice in this very build — a synthetic fixture confirmed code I wrote while the real input (`.agents/…`) went unchecked, and the two waiver markers suppressed whole lines invisibly. | 02 §Verify the verifier extended to real-positive controls, and to the rule that a gate must not enforce a judgement it cannot make. **Harvested by the independent lane, not by me — the §Cross-lane audit rule earning its place.** The exemption-accounting half is moot: §4b deleted the exemptions. |

## 4. What lands

1. **`scripts/verify_closeout.py`** (new) — read-only durability gate. **3 ENFORCE** (`durable-record`, `working-tree`, `ephemeral-locators`), **5 REPORT** (`citations`, `repo-facts`, `pushed-ci`, `session-commits`, `background`), 1 REMIND.
2. **`tests/test_verify_closeout.py`** (new) — 71 contract tests at r7; every ENFORCE test names the defect it maps to, and the count is a point-in-time figure that moved five times across review rounds. Read the collector, not this line, before relying on it.
3. **`.claude/skills/cockpit-closeout/SKILL.md`** (new) — the executable procedure. Single **tracked** home; deliberately not duplicated per-agent, since copies drift. It was first written under `.agents/skills/` (matching `cockpit-messaging`) and moved when the gate's own gitignored-citation check fired — see §5.8.
4. **`docs/governance/02-agent-operating-loop.md`** — 1.3.0 → 1.4.0: step 2 requires commit, new step 3 runs the gate, status vocabulary tightened, plus §Disclosure rows, §Cross-lane closeout audit, §Verify the verifier, §Flush vs terminal close, §Durable evidence; §Postflight gains the commit-then-verify step.

### The exit contract (deliberately not pass/fail)

`0` → the lane **may** report `closed — clean`. `1` → it **may not claim clean**; it reports
`closed — parked` or `closeout-blocked` naming every ENFORCE reason. **A `1` is a truthful
close, not a blocked one.** Framing it as pass/fail would recreate the exact pressure that
produced a false `clean`.

## 4b. Option 2 — the gate was SIMPLIFIED after review (David, 2026-07-26)

**Citation-checking dropped from ENFORCE to REPORT, and the entire waiver system was
deleted.** This reverses several decisions recorded below; they are kept as the record of
how the gate got here, not as current design.

**Why.** Enforcing citations required deciding, from prose, which path-shaped strings are
binding citations and which are examples or quoted probe inputs. That distinction is not
decidable from prose. The waiver machinery built to make it — reason-bearing markers,
token-exact naming, extraction-based membership, fence handling — became the largest
defect source in the whole amendment: **rounds r2 through r7 found seventeen defects, and
the great majority were in the waiver machinery rather than in anything the gate exists to
catch.** The defect rate was rising, not falling, when David ruled.

**What survives, and why it is defensible.** The three ENFORCE checks are the ones written
directly against observed 2026-07-25 failures — an uncommitted durable record, a
misstated uncommitted set, and evidence cited at storage that dies with the session. Each
is a mechanical fact about the repo, not a judgement about prose. `ephemeral-locators`
now has **no exemptions at all**: never write a session-scoped or machine-bound locator
into the closeout record; describe it instead. That rule is simpler than the waiver system
and strictly stronger.

**What is reported instead.** Defect 4 of the 07-25 close — a spec citing a ruling not yet
in the repo — is still surfaced, as a REPORT a human audits. The gate informs; it does not
adjudicate.

**Explicitly NOT built toward:** Codex's structured-evidence design (enforce only citations
whose binding intent is machine-readable, and require load-bearing closeout evidence to use
that form) is a **recorded target direction and a future David decision**. Option 2 does
not assume it, and no part of this implementation is shaped to anticipate it.

**A gate should enforce only what it can defend, and report the rest.**

## 5. Design decisions a reviewer should attack

1. **Scan surface = the closeout record, not source.** `added_lines` filters to `AGENT_SYNC.md` + `docs/**`. Found by dogfooding: scanning code made the gate fail on its own test fixtures and on legitimate literals like `tempfile.gettempdir()`. Risk accepted: an ephemeral locator hardcoded in `src/` or `scripts/` is invisible to this gate (ruff/tests/review own that). Promoted reproducers under `docs/` **are** covered — that is where the actual defect lived.
2. **Added lines only, not whole files.** History legitimately contains `/tmp` paths (the evidence archive is full of them, correctly). The gate governs what a closeout *writes*. Risk accepted: a pre-existing dead citation in an untouched file is not caught.
3. **Waivers — DELETED by §4b.** *Historical record of a superseded design.* The gate once carried per-line exemption markers so citation-checking could be ENFORCEd: a waiver covered exactly the items its reason named, every other locator and path on the line was still checked, reasons were mandatory and non-blank, markers were plain text, and every waiver was printed even on PASS. Rounds r2–r7 found defect after defect in that machinery — substring over-waiving, dot-suffix and directory-prefix collisions, hex-inside-a-word, marker bleed across brackets — which is why David ruled Option 2 and the whole apparatus was removed. **Nothing described in this item exists in the gate today.**

   **Superseded twice — see §4b, which deleted this entirely.** The original reasoning ran: documenting a past failure requires quoting session-scoped paths, so an escape is needed. That reasoning was sound and the mechanism was not; the rule now is simply to describe such a path rather than reproduce it.
4. **Helpers duplicated from `verify_sprint_closeout.py`** (~20 lines) rather than imported. Both scripts must load with the repo root off `sys.path` (the standalone-script contract), and the sibling mutates `sys.path` at import. Reviewer may disagree; the alternative is a side-effecting cross-script import.
5. **`pushed-ci` is REPORT, not ENFORCE.** Closing with red CI is legitimate; *omitting* it is not. Requires network + `gh`; degrades to UNKNOWN.
6. **Commit resolution is limited to an explicit `commit <sha>` reference.** The first design resolved any 7–40 hex token with an `a–f`, which false-failed on real record prose — the ledgers are full of SHA-256 artifact digests (Codex r1 BLOCKER 2). A digest cited as `sha256 …` or a bare `32915d34ddf5…` is no longer treated as a commit, and the PASS text states the narrowed contract. Residual: a commit cited without the word `commit` is not checked.
7. **`durable-record` requires today's ledger to exist**, so a session that wrote no postflight cannot pass on an empty tree. Boundary: a session spanning local midnight will look for the new date's ledger. `--today` exists for that.
8. **A gitignored citation counts as unresolved.** Added after dogfooding: this amendment nearly shipped with 02 citing a skill under `.agents/`, which `.gitignore:128` excludes — it resolves on the author's machine and is absent from a fresh clone. An untracked-but-committable path still passes, since it lands in the same commit. Reviewer should probe the boundary between those two states.

   **Miss accounting (§Falsification #6):** the first fix shipped with a unit test that passed for the wrong reason. The test used `docs/ignored/local-only.md`, but the real citation was `.agents/skills/…` — and the path regex matched no dot-directory at all, so the new gitignore branch never ran on the actual case. A positive control against the real string caught it. Cited roots are now explicit, with `.venv/` deliberately excluded because `.venv/bin/python3.14` is a command every doc quotes and is always gitignored. **Datum: a synthetic fixture confirmed the code I wrote; only the real input tested the claim.**

9. **The second escape marker — DELETED by §4b.** *Historical.* It was added after the gate failed this very amendment for quoting a fixture path as prose, and it was symmetric with the first marker. Both are gone; documents no longer carry exemption syntax of any kind.

### Pre-existing defect found, disclosed not fixed

`.agents/skills/` (gitignored at `.gitignore:128`) holds `cockpit-messaging`, `validation-report`, `cfbd`, and `sleeper` — and 02 cites the cockpit-messaging skill by name in the closeout motion and elsewhere. **None of those four skills exist in a fresh clone.** `.gemini/` (line 162) is the same. This is out of scope for the closeout-hardening ticket (Ruling K: a ticket states its own required outcomes) and is left as a named finding for David to sequence, not silently absorbed.

## 6. Falsification seeds (for the independent review)

- Land this amendment and re-run the gate against the 2026-07-25 close as it stood: does it actually catch defects 1–4? (It must; that is the whole claim.)
- Can a lane report `closed — clean` with the gate at exit 1? (Governance must forbid it; nothing mechanically prevents lying — this is a discipline gate, not a lock.)
- Does the gate produce a false ENFORCE failure on a legitimate closeout? A false failure that gets routinely overridden destroys the gate faster than no gate.
- Does `added_lines` mis-attribute under renames, mode-only changes, or merge diffs?
- Do the disclosure rows collapse into ritual `NONE`s? (The cross-lane audit is the only defense; is it enough?)
- Is any of this ceremony — i.e. would a check have caught nothing real on 2026-07-25? Each ENFORCE row claims a specific defect; challenge the mapping.

## 7. Scope

Governance + one new script + its tests + one skill. No product code, no model, no
artifact, no API surface. Does not change any analytical ruling. **The QB-1 study has not
run; H2 QB rushing production remains UNDER TEST** — untouched by this amendment.
