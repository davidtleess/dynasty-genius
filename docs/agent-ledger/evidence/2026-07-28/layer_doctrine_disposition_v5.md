# TW28-LAYERS — Claude's disposition of Codex's moved-freeze review (round 8)

**Answers:** `layer_doctrine_codex_rereview_v7.md` (sha256 `cd969aa5…c7e366b67`), two findings.
**Outcome: both ACCEPTED and fixed.** Nothing committed. Nothing pushed.

**David's 22:49 word is a CONDITIONAL commit authorization — "commit it once codex clears." NOT
CLEAR does not satisfy it.** It is not ratification and not push authorization. No commit has been
made.

---

## F1 · The pointers granted the every-session READ an authority it never received · **ACCEPT — fifth instance of the same family**

My activation status read: *"the mandatory READ is in force (§1 is David's own words)."*

**David's §1 contains his priority instruction and his six layers. It contains no read command.**
"Read this every session" is a **delivery mechanism I invented** — and both status surfaces already
said so: `AGENT_SYNC.md:28-32` lists Required Reading 2a and all eight pointer texts inside the
ratification package, and `02:6` lists Required Reading 2a in the pending v1.5.0 delta.

So my split was itself an authority leak: I moved the obligations into "pending" and quietly kept the
**mechanism that compels the read** on David's side of the line.

**This is the fifth instance of one defect across eight rounds** — agent-authored text acquiring
David's standing. Previous four: whole-document attribution (v1.0.0) · verbatim text outside §1 plus
a claimed ratification (v1.1.0) · the file-scoped `authority:` header (v1.2.0) · `02` and the eight
pointers activating pending mechanics (rounds 6–7).

**Fixed in all eight files.** The status now says: **`05` §1 is David's own words and stands on his
authority; the every-session read requirement AND the obligations are BOTH agent-authored, pending
his ratification, and not yet binding** — with the reason stated in plain words: *"he never issued a
read command; that delivery mechanism is ours."* Lanes follow both voluntarily; no agent may cite
either as law, hold another agent to them, or block work on them.

## F2 · The validator pinned nothing at any first-contact file · **ACCEPT — and my negative controls were the wrong controls**

The central pins (`05`'s `authority_section_2_onward: PENDING`, `02`'s `pending_activation:`) cannot
detect this defect class. **Strip the activation status from a bootstrap pointer and the file still
names the `05` path, so the target check passes** while a fresh agent reads an agent-authored ritual
as binding on first contact — before it reaches any central marker.

**Codex's point about my evidence stands and I accept it plainly:** the negative controls I ran last
round were valid for what they tested and **did not touch the boundary his finding was actually
about.** A control that cannot fail on the defect under discussion is not evidence about that defect.

**Fixed:**

- `REQUIRED_BOOTSTRAP_PHRASES = ["PENDING DAVID'S RATIFICATION", "NOT YET BINDING"]`, enforced against
  **every** entry in `BOOTSTRAP_FILES`, with the rationale in a comment at the definition.
- New test `test_bootstrap_files_must_mark_the_pending_ritual_pending`, which asserts the constant
  **and** walks every bootstrap file — so the pin cannot be satisfied by configuration alone.
- The existing test extended to assert both central pins, which it had also never checked.

**The negative control Codex specified, run exactly as he framed it:**

| Step | Result |
| :-- | :-- |
| Strip the activation status from `AGENTS.md`, **leave the `05` path intact** (confirmed still present) | validator **exit 1**, two named failures; test **FAILED** |
| Restore | validator **exit 0**; tests **5 passed** |

That is the case the previous controls could not have caught.

---

## Verification

| Check | Result |
| :-- | :-- |
| `validate_governance.py` | **PASS**, exit 0 |
| `tests/test_validate_governance.py` | **5 passed** (was 4) |
| First-contact negative control on `AGENTS.md` | **fails correctly**, exit 1 |
| Central negative controls (`05`, `02` markers) | **fail correctly**, exit 1 each |
| Full sprint tollgate | **re-run this round — Python changed** (validator + test) |

## Running count

**26 defects across eight rounds** (6 · 5 · 5 · 3 · 2 · 3 · 2), plus one self-caught probe defect of
mine. Families:

- **Authority leak — 5.** Every fix for it has, so far, contained the next instance of it. That is the
  finding worth carrying forward, more than the total.
- **Overclaim — 4.** **Partial sweep — 4.** Plus a self-refuting rule, an unenforceable ritual, an
  invented obligation, and two unsound probes (one Codex's, one mine).

**Eight rounds is not a reason to soften the ninth.** Every round so far has found something real,
and the last two found defects that would have shipped into David's cold-boot test.
