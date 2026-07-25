# PROPOSAL for David — where "necessary constraint" ends and "prescribing the HOW" begins

**Date:** 2026-07-25 · **Status:** PROPOSAL. **Not adopted. Not settled between lanes.** David ratifies; the lanes made it precise enough to rule on in one sentence.
**Authors:** Claude (drafted) · Codex (binding review). Neither lane may adopt its own definition — that divergence is the measured cause of the problem below.

---

## Why this needs you

Three independent fresh engineers reviewed the same 41 tickets against the same standard and returned **5, 9 and 26 FAILs**. The counts are not a quality signal — they are a *definition* signal. The reviewers disagreed about one thing, and it drove almost the entire spread.

**The two contested tickets, and how each reviewer called them:**

| Ticket | The disputed text | Claude's reviewer | Gemini's reviewer | Codex's reviewer |
|---|---|---|---|---|
| **DGX-03** SciPy | *"pin SciPy"* | **PASS** ("the cleanest ticket in the backlog") | **FAIL** ("dictating the fix") | **FAIL** ("textbook HOW and package-management design") |
| **DGX-04** CI hardening | *"produces a named unavailable state … the promotion gate refuses on that state"* | **PASS** | **FAIL** ("dictating the exact error handling mechanism") | **PASS** ("leaves representation and implementation open") |

**Both other lanes pushed back on their own reviewers here, independently and without coordinating.** Gemini: *"we think this is overly pedantic — for dependency hardening and fail-secure logic, the pin itself **is** the constraint."* Codex defended DGX-04's fail-closed requirement as behaviour, not mechanism. That two lanes independently rejected their own reviewer on the same axis is the strongest evidence that the standard is under-specified rather than that anyone applied it badly.

**The stakes are not cosmetic.** Under Codex's reviewer's reading, 26 of 41 tickets fail and the backlog is unusable. Under Gemini's reviewer's, 9 fail and it is nearly ready. **The same document is either broken or nearly done depending on one undrawn line.**

---

## What everyone already agrees on

Recorded so you are only ruling on the genuinely contested part.

**Agreed HOW — all three reviewers, no dissent:**
- `"computed in exactly one module"` (S5-03) — module granularity is a design choice; one package, one service, or one memoised function all satisfy the actual requirement.
- `"reproducible from a pinned seed"` (S3-01a) — a closed-form estimator has no seed and would fail this while meeting the requirement.
- `"reproduced by a second lane"` (S0-01) — staffing, not a property of the work.
- Naming a library outright (already removed in v2: `pydfs-lineup-optimizer`, `nflreadpy`).

**Agreed CONSTRAINT — no reviewer objected:**
- `"no ceiling artifact may reach any downstream consumer"` (S3-03) — an outcome, mechanism explicitly left open.
- `"deterministic for a given roster … league-legal … within the refresh budget"` (S3-04) — properties the solution must have.
- `"the discount is never FIT"` (S1-03) — a methodological prohibition with a stated reason.
- `"nfl_data_py is archived — the library choice is the developer's"` (S2-01a) — context that saves a day without taking the decision.

---

## The proposed rule — three candidates, in ascending permissiveness

Each is one sentence. Each is tested against the contested cases below.

### Candidate A — the strict behavioural rule
> **A ticket may state only properties verifiable from the artifact's observable behaviour or externally visible state; any requirement that can only be checked by inspecting how the code is built belongs to the developer.**

Yields: DGX-03 **HOW** (a pin is checked by reading a file, not by observing behaviour — the observable property is "a fresh clone resolves the version the study registered"). DGX-04 **CONSTRAINT** (feed a degenerate input, observe a named state and a refusal — no internals read). S5-03 **HOW**. Contract tests **HOW**.
**Cost:** it invalidates this repo's cockpit-TDD convention, where tickets routinely name a RED contract test. Roughly ten tickets would lose language everyone considers normal here.

### Candidate B — behavioural, with a governed-mechanism exception *(the lanes' joint recommendation)*
> **A ticket states the observable property, not the mechanism — except where a governance document already mandates that mechanism, in which case naming it is citing a house rule rather than choosing a design.**

Yields: DGX-04 **CONSTRAINT** (behavioural). S5-03 **HOW** (no governance doc mandates module granularity). Contract tests **CONSTRAINT** (cockpit-TDD in `02` mandates RED-first). Backup manifest coverage **CONSTRAINT** (`02`'s manifest-coverage law). **DGX-03 becomes a question about `03-code-hygiene-policy`** — if dependency pinning is a governed mechanism there, it is a constraint; if not, it is HOW. That is a checkable fact, not a judgement call, which is why we prefer this candidate: **it converts the contested case into a lookup.**
**Cost:** it makes the boundary depend on what governance currently says, so a governance gap silently reclassifies tickets.

### Candidate C — the intent rule
> **Naming a mechanism is acceptable when the mechanism is the requirement (safety, reproducibility, governance) and unacceptable when it is merely one way to meet the requirement.**

Yields: DGX-03 **CONSTRAINT** (reproducibility *is* the requirement — Gemini's position). DGX-04 **CONSTRAINT**. S5-03 **HOW**.
**Cost:** "is the requirement" is a judgement, so it reproduces the disagreement it is meant to end. We record it because it is the most permissive reading and it is what one lane argued for; we do not recommend it.

---

## Worked examples on both sides, under Candidate B

| Text | Verdict | Why |
|---|---|---|
| "no ceiling artifact may reach any downstream consumer" | **CONSTRAINT** | Observable at the consumer boundary |
| "a degenerate input produces a named unavailable state; the gate refuses on it" | **CONSTRAINT** | Observable: feed it, watch it |
| "an unjoinable row goes to triage, never silently dropped" | **CONSTRAINT** | Observable outcome; "triage" names a governed destination (`01` identity law) |
| "fails a contract test" | **CONSTRAINT** | Cockpit-TDD is mandated by `02` |
| "computed in exactly one module" | **HOW** | Internal structure; no governance mandates granularity |
| "reproducible from a pinned seed" | **HOW** | Mechanism; the property is bit-identical rerun |
| "reproduced by a second lane" | **HOW** | Staffing |
| "calibration error reported by decile" | **HOW** | One demonstration method; the property is "tails meet the same bar as the middle" |
| "pin SciPy" | **DEPENDS** | Constraint iff `03-code-hygiene-policy` governs dependency declaration; otherwise HOW, and the ticket should say "a fresh clone resolves the version the study registered" |

---

## What we are asking you to rule

**One sentence: A, B, or C** — or your own. Our joint recommendation is **B**, because it is the only candidate that turns the contested case into a fact-check rather than an argument, and because it preserves the cockpit-TDD convention that the rest of the governance already depends on.

**A second, smaller question that follows from B:** does `03-code-hygiene-policy` govern dependency declaration? If yes, DGX-03 is clean as written. If no, it needs one sentence rewritten. **We did not answer this ourselves because under B it decides a contested verdict, and the whole point of this proposal is that we do not draw that line.**

---

## Honest note on our own incentives

Claude authored the backlog under review. A permissive rule flatters that work; a strict one condemns 26 tickets of it. **We recommend B, which is stricter than the reading Claude's own reviewer applied** — under B, several tickets Claude's reviewer PASSed become HOW and need rewriting. We name the incentive so you can discount for it.
