# r6 disposition — Thread A + TW26O claim release

From Claude Code (implementing lane). **All three r5 defects ACCEPTED, plus your test
defect.** Each reproduced by me before dispositioning. No disagreement. Thread B is
CLEAR per your r5 and I have not touched it.

## Frozen set (SHA-256), computed after the final gate

| Path | SHA-256 |
|---|---|
| `scripts/verify_closeout.py` | `0b447e1a3826064bfa88b8ce2ba92366158eb13836692a02e7d2c480d3813565` |
| `tests/test_verify_closeout.py` | `be1b1b47044de1123b6247622b54ef43afe50570e88a0849e6803df2ad562580` |
| `docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md` | `fbd35a218a350ad6405260dc7697eadd820d979be524092a70a3b782a7f5780d` |
| `.claude/skills/cockpit-closeout/SKILL.md` | `acc5af0205f26592a94302824a22e4913945f5842e4be99ec0c7180ec6bdbf56` |
| `docs/governance/02-agent-operating-loop.md` | `aeb4263c0759665914cf7c9b550a7ed2930847a154fbee2e5248c9396abe73d2` |
| `scripts/dg_delivery.py` | `853e64d1b96182df924ccd23ae075a4523dc4a966097648cd67b9783f8e12773` |
| `tests/test_dg_delivery_chip_profile.py` | `09087fb4246eba9dc26ec7cebb4f11e02280a0ebd6cf7c33820752c9a45f334e` |
| `tests/test_dg_delivery_claim_release.py` | `190b38e7a90dabc21e8789f53cecc8ac6cadfa467065345e5faeeca0735e3134` |

**89 focused tests.** I do not touch these eight files until your verdict.

## r5 #1 — `docs/a.md../backup/` still over-waived. ACCEPTED; approach changed.

Three successive boundary lookaheads each lost a race to you: substring containment,
then `(?!\.\w)` on `..backup`, then `(?!\.+\w)` on `../backup/`. I have stopped playing
that game and changed the mechanism.

**Naming is now decided by EXTRACTION, not by lookahead.** `_named_items()` parses the
reason with the *same* extractors used on closeout text — `cited_paths()`, the ephemeral
locator patterns, and a bare-hex pattern — and an item is named only if it appears in that
set. `docs/a.md../backup/` yields itself and never `docs/a.md`; "quoting docs/x.md." still
yields `docs/x.md`.

Two consequences I found while making the change, both now pinned by tests:
- A **bare directory root** (`.agents/`) is not matched by the bare-prose path regex, which
  requires an extension or a deeper segment. `_named_items` recognises it token-wise so a
  namespace waiver can name what it waives.
- A **space-containing path must be backticked inside a reason**, exactly as in closeout
  text — the delimiter is what makes it unambiguous. Unquoted, whitespace splitting surfaces
  its directory prefix as a separate named item. Documented in the test.

## r5 #3 — `retry_submit` attempts-exhausted retained the claim. ACCEPTED.

You asked me to attack the invariant rather than the call, and you were right that there was
a second route. `retry_submit` returned terminal `submit_attempts_exhausted` while retaining
the pane claim **and leaving the row non-terminal**, so the same `pane_claim_lost` jam stayed
reachable. It now marks the row terminal and releases owner-bound before returning.

## r5 #4 — my test asserted on source text. ACCEPTED, and this is the one worth recording.

You were exactly right: commenting out the release still satisfied both substring
assertions, because the commented line still contains the string. **The test could not fail.**
It is replaced with **behavioural** tests that drive the real paths and assert
`owner_send_id is None` afterwards.

**I ran your own probe against the repair:** with the release call commented out,
`test_unconfirmed_branch_actually_releases_the_claim` now **FAILS**. The mutation you used to
expose the defect is the proof the repair holds.

## Constraint check

`scripts/dg_mail_carrier.py` **byte-untouched** against origin, default-pause guard intact.
Held across five threads.

## Checks run

- Focused **89/89**; full wire/carrier **212 PASS, 1 skipped, zero regressions**.
- Your r5 #1 input re-run, predicate and end-to-end: both `False`.
- Mutation probe on the release call: test fails as it must.
- Ruff clean on five Python files; `validate_governance.py` PASS; `git diff --check` clean.
- Full `scripts/verify_sprint_closeout.py --base origin/main` **ENFORCE PASS**.

## The wire, one-way — a finding you should see

Your returns keep being refused `pane_claim_lost`, and it is not random. **My pane `%182` is
claimed by send `w#43zr0ym0-1` in state `manual_clear_required`, at epoch 1 — your very first
send of the day, stuck since this morning.** Every later return of yours hits it.

I did **not** clear it: it is your claim, `_release_pane` is owner-bound, and Tower's
authorisation covered only the one claim on `%183`. Escalated to Tower/David.

Note this is a *pre-existing* parked claim from before the chip fix, not a new mismatch. My
TW26O work removes the routes that *create* such jams; it cannot retroactively free a claim
parked in a human-clear state.

## Two further defects found while landing r6, both disclosed

1. **A reason could not name a backticked item.** `_waiver_reason` de-backticked the line to
   enforce plain-text markers, which also erased backticked content *inside* the reason — so
   a reason naming a space-containing path in the documented form named nothing. Code spans
   are now masked with same-length filler and the reason is sliced from the original line, so
   r3 #2 (a backticked marker is documentation) still holds. Both properties are pinned.
2. **My marking helper over-reached, and I reverted it.** A script I used to append waiver
   markers scanned WHOLE FILES rather than added lines, and appended markers to pre-existing
   governance prose in `02-agent-operating-loop.md` — a frozen artifact. I caught it on the
   next gate run, reverted all nine spurious markers, and confirmed 02 is byte-identical to
   its frozen hash `aeb4263c0759…`. Re-marking is now scoped to added lines only. **Disclosing
   because it touched a frozen file, even though the net diff is zero.**

## Where I want you hardest on r6

1. **Extraction-based naming** — a different mechanism, so old attacks may not transfer.
   Can a reason still name an item it should not, or fail to name one it should?
2. **The claim-release invariant, once more** — is there a THIRD terminal resolution in the
   submit/retry paths that still holds a claim?
3. Anything still stale in the spec.

Product boundary: governance + wire tooling only. No model, artifact, API, or study
execution. The QB-1 study has not run; **H2 QB rushing production remains UNDER TEST**.

**PLEASE REPLY with:** (a) **ENUMERATED CLEAR**, Thread A and TW26O stated separately against
the eight hashes, OR (b) **NOT CLEAR** with reproduced defects and `file:line` locators.
