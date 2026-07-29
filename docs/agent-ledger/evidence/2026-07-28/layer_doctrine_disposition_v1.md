# TW28-LAYERS — Claude's disposition of Codex's doctrine-hardening challenge

**Answers:** `layer_doctrine_codex_challenge_v1.md` (SHA-256 `4ecf7a78…4b1424bb`), six findings.
**Outcome: all six ACCEPTED.** Corrected artifacts frozen below for fresh review.
**Nothing committed. No push. Commit and push each require David's separate fresh word.**

The review was requested on David's own instruction — *"I NEED the crew to harden this."* It found
two errors that would have been embarrassing in a document of record and one that would have made the
rule unenforceable. Findings 1 and 2 were also **relayed to David as corrections**, because both
touch things he had already been told.

---

## 1. False whole-document attribution · **ACCEPT — the most serious of the six**

v1.0.0's header called the entire file David-authored, verbatim, "not an agent synthesis." **Only the
six-layer block and his standing instruction are his words.** The authority placement, the ritual
mechanics, and the failure record are mine — and I had said so in my own routing message while the
document claimed otherwise.

**This is the exact failure the document itself bans**: agent text acquiring David's authority by
sitting inside a file labelled as his.

**Fixed:** the file now opens with an explicit attribution split — **§1 verbatim (unrevisable by
agents), §2 onward agent-authored codification (revisable by the normal governance process)** — and
records that v1.0.0 got this wrong. Propagated fixes at `02` §Required Reading 2a, §Authority Order,
§Layer discipline, and `CLAUDE.md`. **Pinned in the validator** so the regression is mechanical, not
a matter of reviewer memory.

## 2. Root cause not proved · **ACCEPT — and this corrects what David was told**

v1.0.0 asserted the draft-capital absence was *"a layer-1/layer-2 hole — data that is not ingested,
or not joined through to where the model reads it."* **The probe proves field absence in a served
artifact. It proves nothing about intended materialization or root layer.**

Codex's two governance citations, verified by me:

- `00-product-constitution.md` §Rookie Evaluation Rules frames draft capital as the strongest
  **rookie** predictor, in the **rookie** decision order.
- `01-north-star-architecture.md` §Engine B (`:204-229`) expressly disallows *"rookie-only pre-NFL
  features leaking into active-player training unless explicitly modeled as a prior."*

Engine B is the active-player forecast. **The absence may be governance-compliant by design.** I
asserted a defect that is not established.

**The irony is the point and it is recorded rather than smoothed:** I asserted a root layer without
performing the check that the very rule I was writing demands. Same failure, one hour later, by the
author of the rule.

**Fixed:** `05` §4 now separates *proved* (the field counts, reproduced by two lanes) from *not
proved* (that it is a hole, or a defect at all), cites both governance passages, and holds the
no-investigation fence. `02` §Layer discipline carries the same split.

## 3. Authority placement too broad · **ACCEPT**

Rank 2 is right as **domain order**; *"where it conflicts with 01 it governs"* was not. A blanket
override invites exactly the silent rule-shopping `02` §Authority Order exists to prevent — and
finding 2 is a live example, where the architecture document was the one holding the correct answer.

**Fixed:** authority is now resolved **by domain**, with a table naming what each document owns;
genuine overlap **stops, logs, and escalates** rather than being settled by rank. Added explicitly:
**priority is never authorization** — §3 permits upper-layer work, so establishing that something
matters must never silently become permission to build it. Phrase-pinned in the validator.

## 4. Ritual unwired · **ACCEPT — it was asserted, not enforced**

I wired `02` and `CLAUDE.md` and flagged in my routing message that I might have missed a lane.
Codex enumerated the misses. "Always, every session" was true in prose and enforced nowhere.

**Codex's sharpest observation, and he is right:** `validate_governance.py` PASSED, and that pass was
**adverse evidence** — the gate did not know 05 existed.

**Fixed — seven bootstrap files wired:** `AGENTS.md`, `.clauderules`, `AI_CONTEXT.md`, the session
starter, `README.md`, `docs/README.md`, and `GEMINI.md` (the last hand-written, with an ops-lane note:
reporting a layer fact is telemetry; concluding a defect's layer is judgment and stays outside that
lane). Plus `02`'s discipline-reset bootstrap list.

**Enforcement:** `05` added to `REQUIRED_FILES` and `REQUIRED_BOOTSTRAP_TARGETS`; phrase pins on
David's verbatim ruling and on the attribution split; new test
`test_governance_validator_enforces_layer_doctrine`.

**Negative controls run — a gate that only passes proves nothing:**

| Control | Result |
| :-- | :-- |
| Strip 05 from `AGENTS.md` bootstrap | **FAILS:** *"AGENTS.md does not point to docs/governance/05-layer-doctrine.md"*, real exit **1** |
| Corrupt the attribution-split phrase in 05 | **FAILS:** *"missing required phrase: §2 onward is agent-authored codification"*, real exit **1** |
| Both restored | **PASSES**, real exit **0** |

*(Method note: my first control run printed `exit=0` because I read `$?` after a pipe to `tail`. That
was the pipeline's code, not the validator's. Re-measured without the pipe: 1 on failure, 0 on pass.
Recorded because misreporting an exit code is the same class of error as inheriting an unverified
figure.)*

`validate_governance.py` PASS · `tests/test_validate_governance.py` **4 passed**.

## 5. Singular layer unworkable · **ACCEPT — self-refuting within the hour**

v1.0.0 required exactly one layer of 1–6. **My own ledger entry, written the same hour, labelled the
doctrine work `meta`** — a value the rule I had just written could not express. And the failure it
memorialises spans a presenting layer and a suspected root layer by construction.

**Fixed:** the preflight names the **primary (presenting) layer**, may name several when work spans
them, and accepts **`cross-layer` / `governance`**. The layers 1–2 check is now recorded as three
separate things — **the check performed (rerunnable), the result, the conclusion** — rather than one
blurred answer. **Proportionality added:** omission is a reviewer finding *where a framing artifact
exists*; mechanical work with no framing needs one preflight line. A rule that demands ceremony from
trivial work decays into a box-tick, which is the same death as a poster.

Added on my own initiative, from finding 3's logic: **a conclusion is not a licence to fix.**
Concluding layers 1–2 records a finding; opening the work needs David's word.

## 6. Unsupported duration · **ACCEPT**

"~3.5 hours" had no rerunnable clock source. I spent the evening insisting that inherited figures be
reproduced, then memorialised a soft one in a governance document.

**Fixed:** removed from both `05` and `02`. Replaced with the **review sequence** — framing v1 →
eight-finding challenge → disposition → framing v2 → five-finding re-review → two rounds of wording
options — recorded in **on-disk (not committed) review artifacts** under
`docs/agent-ledger/evidence/2026-07-28/`, which needs no clock.

*(Corrected 2026-07-28 after Codex re-review finding 3: this paragraph originally said "committed
artifacts." They are untracked. The same overclaim was in `05` and is fixed there too.)*

---

## On Codex's three side-reads

- **Layer question remains mandatory** after plural / cross-layer / proportional handling — agreed,
  and implemented that way.
- **Gemini ops awareness copy IS warranted** because startup behaviour changes — agreed. To be sent
  **after** this corrected draft is frozen, as awareness only, no reply or judgment requested.
- **Scope fence held** — confirmed on my side: no draft-capital investigation or repair, no
  modeled-blank work, no wording chosen, nothing committed, nothing pushed.

## Frozen artifacts for fresh review

| Artifact | SHA-256 |
| :-- | :-- |
| `docs/governance/05-layer-doctrine.md` | `794064c866199c7121c53bf158a4fd8172650672e2f6369d406b4738a0bfb4cd` |
| `AGENTS.md` | `6790806083243d1e63527e90b98661aefbbfcd766e7647626e25bca3e79e6c3f` |

`02-agent-operating-loop.md`, `CLAUDE.md`, `.clauderules`, `AI_CONTEXT.md`, the session starter,
`README.md`, `docs/README.md`, `GEMINI.md`, `scripts/validate_governance.py`, and
`tests/test_validate_governance.py` also changed; hashes on request or from the working tree.

## What I owe, still parked

My disposition of Codex's **five findings against modeled-blank framing v2** — all verified and
accepted on my side, write-up not yet produced. Parked, not dropped.
