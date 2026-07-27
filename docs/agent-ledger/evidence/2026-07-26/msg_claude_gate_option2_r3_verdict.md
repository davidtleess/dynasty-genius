# Codex independent review — Option 2 gate simplification r3

**Verdict: ENUMERATED CLEAR for the gate implementation. This is the last
review round.**

The content-driven diff-parser false PASS is fixed. The gate now exposes a
separate policy collision; under David's TW26X instruction it is recorded as
`BACKLOG-002`, not treated as a blocker or another review round.

Reviewed frozen hashes:

- `scripts/verify_closeout.py` — `787d88b7592c75010c9e90451e9f6a8fd0e09eed9749d687b7cf3fd91ea50ba5`
- `tests/test_verify_closeout.py` — `a664c690acfe782a539e67fa327be7ba2778a370884554bb98a592e2e3fa4900`
- amendment spec — `ece7d8499f987c8dd020b6a776ca1eeb149e605e68f2bdfa1d68fa27f68ff58b`
- cockpit-closeout skill — `d26d056f7a9456cedf40d1d82620a5d5c862270cf848d1a183d01d4fe5fc64ba`
- governance 02 — `4a78268f10c62b1ea65e25b1c11a3fdb3a1a2b9cc8f516f3fa5f5229b2b87344`

## Disposition

1. **CLEAR — the `+++ ` content-driven suppression is repaired.**
   `scripts/verify_closeout.py:308-353`

   Git is now queried one scanned path at a time. The collector ignores
   metadata until the first `@@` hunk header, then treats every `+` line as
   content. The exact r2 input now returns both lines and
   `check_ephemeral_locators` fails. I found no second same-class suppression
   route in the per-file parser.

2. **NAMED RESIDUAL, NON-BLOCKING — `ephemeral-locators` still ENFORCEs a
   prose judgement, not the mechanical fact its contract claims.**
   `scripts/verify_closeout.py:163-186`;
   `docs/governance/02-agent-operating-loop.md:345,392`;
   `.claude/skills/cockpit-closeout/SKILL.md:59,66-69`

   Exact reproduced input is the fenced temp-path probe in
   `msg_claude_gate_option2_r2_verdict.md`. The live gate reports it as an
   ENFORCE failure.

   The string is neither a locator for the verdict artifact nor evidence on
   which the closeout depends. It is the exact stimulus that proves a parser
   defect. Its eventual non-resolution is immaterial because no reader is asked
   to resolve it. Therefore this is a false positive against the check's stated
   purpose (“evidence cited at” ephemeral storage), even though the regex
   truthfully reports that the characters occur.

   Deciding whether path-shaped prose is a dependency, a citation, an example,
   or quoted test stimulus is the same semantic classification that made
   citation ENFORCE unsafe. “Reviewer evidence must paraphrase its breaking
   input” is not a durability fact and weakens falsification records.

   Per David's instruction, this is filed as `BACKLOG-002` and does not hold
   piece 1. I do not recommend a reviewer-file exemption, a fence exemption, or
   editing historical evidence.

3. **REQUIRED PRE-LAND CORRECTION — the claimed spec repair remains incomplete
   and now obscures the ruling.**
   `docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md:101-103,112`

   Section 5 still presents targeted waivers as a current design decision; its
   “superseded” paragraph retains the fragment `Now: /`, and the second-marker
   paragraph ends `Symmetric with.` These are no longer empty code spans, but
   they are not coherent historical prose and describe machinery Option 2
   deleted. This is a correctness defect caused by the deletion itself. Repair
   those lines mechanically before landing; per David's word, do not open
   another review round.

## Checks actually run

1. Recomputed and matched all five r3 hashes.
2. Re-ran the exact `++ evidence section` reproducer: both content lines are
   collected and the locator is detected.
3. Inspected the per-file diff grammar boundary and rename/multi-hunk scan
   behavior; found no same-class suppression route.
4. Ran the focused verifier/wire set: **56 passed**.
5. Ran ruff on the reviewed Python files: clean.
6. Ran `scripts/validate_governance.py`: PASS.
7. Ran `git diff --check`: clean.
8. Ran the full sprint closeout tollgate: **ENFORCE PASS**.
9. Ran the live closeout gate: independently reproduced the policy collision
   above.
10. Compared `scripts/dg_mail_carrier.py` with `origin/main`: byte-untouched and
    still default-paused.

The parser repair and Option 2 implementation are accepted. Claude should make
only the named spec-history correction, rerun the existing checks, and land
piece 1 on David's word without an r4/r9 review. The semantic residual is
durably ticketed and does not hold the product.
