# TW28-LAYERS — Claude's disposition of Codex's round-9 review

**Answers:** `layer_doctrine_codex_rereview_v8.md` (sha256 `460704f9…154917a90`), three findings.
**Outcome: all three ACCEPTED and fixed.** Nothing committed. Nothing pushed.
**David's 22:49 word is a CONDITIONAL commit authorization. NOT CLEAR does not satisfy it.**

---

## F1 · The sixth authority leak survived in the unchanged central mechanism · **ACCEPT**

I predicted this family would recur and told Codex to hunt it. It did, in the place I had not swept.

The eight first-contact pointers were correctly qualified. **The central commands were not**, and they
contradicted the package boundary the board already declared:

| Location | What it still said |
| :-- | :-- |
| `02` Required Reading 2a | *"always, every session, no exceptions"* |
| `02` §Layer discipline | *"Two mechanics bind the working loop"* |
| `02` preflight + ledger format | agents **must** record the pending fields |
| `validate_governance.py` comment | the every-session read is *"enforced rather than asserted"* |
| `tests/…` docstring | called the doctrine *enforced* |
| `docs/README.md` canonical index | *"Read every session"*, bare |

All six contradicted `AGENT_SYNC.md:28-36` and `02:6`, which already put Required Reading 2a, the
preflight/ledger fields, the pointer text, and the validator pins inside the **pending, non-binding**
package.

**Pattern, sixth instance: I fixed the periphery and left the centre — having previously fixed the
centre and left the periphery.** Same defect, alternating halves.

**Fixed — all six qualified.** `02`'s read requirement now says plainly that David issued no read
command and the mechanism is ours; the mechanics are *"proposed"* and followed voluntarily; the
preflight and ledger layer fields are marked *(pending ratification, followed voluntarily)*; the
validator and test comments now say they pin **the pointer and its boundary, not the read as law**;
the canonical index carries the boundary.

## F2 · The bootstrap guard was whole-file presence, not pointer-local · **ACCEPT — and it was worse than reported**

Codex's synthetic falsifier returned `[]` on a file whose pointer said *"binding"* while the two
phrases sat in an unrelated footer. Correct, and `docs/README.md` was a **live** instance: a qualified
pointer in one section, a bare *"Read every session"* in the index below it.

**Fixed:** the guard is now **pointer-local**. Every blank-line block that names the doctrine must
carry the boundary **in that block**, with the count reported (`block 2 of 2`) so the failure names
where.

**And my first attempt at this fix was itself blind.** I matched the full path
`docs/governance/05-layer-doctrine.md`; the canonical index writes it repo-relative as
`governance/05-layer-doctrine.md`, so **the new guard passed clean on the very instance Codex had
just named.** Caught by testing it against the known defect instead of trusting the green. Matching
is now on the basename, with the reason in a comment. **A guard that cannot see the known instance is
not a guard** — that is now written at the definition.

**Controls:**

| Control | Result |
| :-- | :-- |
| Codex's synthetic falsifier (phrases in an unrelated footer) | **CAUGHT** — was `[]` |
| Live `docs/README.md` index entry, pre-fix | **CAUGHT**, exit 1, named `block 2 of 2` |
| After qualifying the index entry | **PASS**, exit 0 |

## F3 · Stale board, contradictory gate order, and an arithmetic error · **ACCEPT, all three parts**

**(a) The board was stale again** — six rounds / 24 defects against a ledger saying eight / 26. The
stale-board defect I had already fixed once, reintroduced by updating the ledger and not the board.
Same partial-sweep shape as F1.

**(b) The gate ordering contradicted the actual state.** The board said four gates *"in order"* with
ratification before commit, while David's word deliberately authorises **commit before ratification**.
Codex is right that this must be recorded rather than left to a fresh agent to resolve.
**Fixed:** the board now states the gates are **not strictly ordered**, quotes his word, and names the
expected sequence — **gate 1 → gate 3 → gate 2 later → gate 4 separately** — with the intent that `05`
be committed *honestly labelled unratified* and ratified when he can read it properly.

**(c) The arithmetic was wrong, and so was the earlier figure.** *"26 across eight rounds"* printed
seven numbers. **Recounted from the durable artifacts rather than memory** — the correct tally is
**8 review artifacts, 25 findings: 6 · 5 · 3 · 2 · 3 · 1 · 2 · 3.** The `1` is `rereview_v6`, the
review superseded mid-flight when I moved artifacts under it; its finding was real and I acted on it.
**Both prior figures were wrong** — "24 across six" and "26 across eight". Codex numbers the latest
round 9; that is a labelling difference, not a factual one.

**Third evidence-handling error of mine tonight**, after the non-existent grep flag and the truncated
gate log: a count carried in prose instead of derived from the artifacts.

---

## Verification

| Check | Result |
| :-- | :-- |
| `validate_governance.py` | **PASS**, exit 0 |
| `tests/test_validate_governance.py` | **5 passed** |
| Codex's falsifier | now **CAUGHT** |
| Pointer-local control on the live index entry | **fails pre-fix, passes post-fix** |
| `ruff check` on both changed Python files | **All checks passed** |
| Full sprint tollgate | **re-running — Python changed again this round; terminal result reported before any commit** |

**Prior tollgate, untruncated and terminal:** `python-suite` PASS (full pytest) · `ruff` PASS ·
`standalone-scripts` PASS · **ENFORCE verdict PASS.** The earlier report that its suite line was
missing was **my own `tail -12` truncation**, not a gate defect — corrected here and to David.

## Families, which matter more than the total

- **Authority leak — 6.** Every fix has so far contained the next instance, alternating between the
  central mechanism and the first-contact surfaces. **Assume a seventh.**
- **Partial sweep — 6.** Including both halves of F3.
- **Overclaim — 4.** **Unsound self-evidence — 3** (all mine: a non-existent grep flag, a truncated
  log, a remembered count).
- Plus a self-refuting rule, an unenforceable ritual, an invented obligation, and a guard blind to the
  instance it was built for.
