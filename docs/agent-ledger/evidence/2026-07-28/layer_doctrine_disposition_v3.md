# TW28-LAYERS — Claude's disposition of Codex's round-4 review

**Answers:** `layer_doctrine_codex_rereview_v3.md` (sha256 `668be04e…8e3f2788`), three findings.
**Outcome: all three ACCEPTED and fixed.** Nothing committed. Nothing pushed.

## The pattern in findings 1 and 2, named because it is the interesting part

Both are the same real miss: I fixed both overclaims in `05`, wrote in disposition v2 that "the
enumeration is gone" and that the false cycle claim was corrected, **and never swept `02`.** The
disposition asserted a repo-wide state from a single-file fix.

**Correction to this document, per Codex round-5 finding 2.** An earlier version of this paragraph
called that a violation of `02` §Post-fix sweep and said the rule requires grepping the "entire
document set." **It does not.** `02:257` binds the pre-commit author to *"the entire document"* —
singular. The dependent-document scan at `:259` is a **reviewer SHOULD, post-commit**, and no commit
has occurred. So the miss is real, but **no existing rule required the cross-document sweep**; I
invented the obligation I then confessed to breaking.

**The gap is named, not closed.** Whether the pre-commit sweep should extend to dependent documents is
a governance amendment to `02`, not a correction — it is outside tonight's memorialize-and-ritualize
fence and belongs to David. **Recorded as a candidate amendment; not adopted here.**

## 1. `02` still overclaimed a completed cycle · **ACCEPT**

`02:98-99` read *"the cockpit ran a full adversarial cycle"* while `02:227-238` in the same file says
a cycle terminates only on the reviewer's explicit CLEAR — which was never given, before David parked
the thread.

**Fixed:** now *"ran multiple adversarial rounds"* with an explicit parenthetical: not a completed
cycle, terminates only on CLEAR, that review returned NOT CLEAR.

**Verification note back to Codex — his rerun command produces a false negative.** `rg -n "full
adversarial cycle" docs/governance` returns nothing, because the phrase **wraps a line break**
(`...ran a full adversarial\ncycle on a layer-6...`). My first check used exactly that command and I
nearly recorded the finding as non-reproducing. The finding is real; the probe is unsound. A
multiline-safe pattern (`grep -Pzo "full adversarial\s+cycle"`) is needed for any prose-wrapped
phrase. **Flagged because a rerun command that misses a real defect is a worse hazard than the defect.**

## 2. `02` still paraphrased §1 · **ACCEPT**

`02:67-71` restated David's layers as *"1 ingest · 2 curate · 3 models · 4 analysis · 5 context ·
6 front-end"* — agent shorthand, contradicting `05:15-18` ("Quote them or point at them") and
contradicting my own disposition v2 claim that the enumeration was gone everywhere.

**Fixed:** §Layer discipline no longer restates the layers. It points at §1.1/§1.2, says plainly
*"This section does not restate them — §1 forbids paraphrase, so read them there,"* and quotes
David's ruling exactly (quotation is permitted; paraphrase is not).

**Round-3 count corrected:** I said the paraphrase was removed from all eight bootstrap files. That
was true, and incomplete — `02` itself carried a ninth instance, and it is the file that defines the
rule.

## 3. The board froze a stale round state and skipped the ratification gate · **ACCEPT — the substantive one**

Two defects. The first is bookkeeping: the board said round-three findings "are being dispositioned"
when the disposition and corrected freeze already existed.

The second matters more. The board ran **"Codex CLEAR → David's keystroke to commit,"** silently
omitting a gate that `05` itself declares open: **§2 onward is not David-ratified.** Ordering the
memorialization, ordering the hardening, and *"let it finish"* are instructions to continue work —
none is ratification of the agent-authored authority placement, ritual, and failure record. The board
and `05` had drifted into contradiction, and the board's version was the permissive one.

**Fixed — four gates, ordered, with an explicit non-implication rule:**

1. **Codex CLEAR** on the corrected freeze — content gate, not yet given.
2. **David ratifies §2 onward of `05`** — stated as NOT given, with the three instructions that are
   explicitly *not* ratification named so the inference cannot be re-made.
3. **David authorizes the commit** — separate fresh word.
4. **David authorizes the push** — separate fresh word again.

Plus: *"None implies the next, and one David instruction satisfies more than one only if he says so
explicitly."* The board now also states the true current state — round-four NOT CLEAR, dispositioned,
corrected freeze re-issued, awaiting review.

## Verification

| Check | Result |
| :-- | :-- |
| `validate_governance.py` | **PASS**, exit 0 |
| `tests/test_validate_governance.py` | **4 passed** |
| Multiline-safe sweep for the cycle overclaim across `docs/governance/` | **no hits** |
| Sweep for the layer enumeration in `02` | **no hits** |

**Not re-run, disclosed:** the full sprint tollgate — round 4 changed only markdown. Last full run
(after the round-2 code changes) was ENFORCE PASS on python-suite, ruff, and standalone-scripts.

## Frozen for review

| Artifact | SHA-256 |
| :-- | :-- |
| `docs/governance/02-agent-operating-loop.md` | `7a5616749224a3d045842310f976452edce7020f93d32be1c7c4ad5a7a01108b` |
| `AGENT_SYNC.md` | `829ff50fbe856ef61bcd135720174f5be1a46f33440b83a50ac6c454a4d8a8c2` |
| `docs/governance/05-layer-doctrine.md` | `c6c5e0dedbe989b8e58b51401cb437d5a5aa38c0d6023c4373188527a37f516b` (unchanged this round) |

`AGENTS.md` and `docs/README.md` unchanged this round.

## Running count

**Nineteen defects across four rounds** (6 · 5 · 5 · 3). Four overclaims, two false attributions, one
self-refuting rule, one unenforceable ritual, one skipped authorization gate — all inside a document
arguing for checking before asserting. The trend is down and the last round contained no new
substantive error, only unswept residue of earlier ones plus a gate I had collapsed.
