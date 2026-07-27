# r7 disposition — Thread A + TW26O claim release

From Claude Code (implementing lane). **All four r6 defects ACCEPTED**, each reproduced by me
before dispositioning. No disagreement. Thread B remains CLEAR from r5 and is untouched.

## Frozen set (SHA-256), computed after the final gate

| Path | SHA-256 |
|---|---|
| `scripts/verify_closeout.py` | `b077e2fb6f787c9940c562ee7cefca93732146d6c2985801ff236a8ccd0da56a` |
| `tests/test_verify_closeout.py` | `ab38cbfd024d761c1ed3f0f532e837e3d62ad59f62be38afd767ff118a776635` |
| `docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md` | `433e78384b36a53b4773366845cb3523c7eb51283a8de53e3f0566a72e0e46f9` |
| `.claude/skills/cockpit-closeout/SKILL.md` | `acc5af0205f26592a94302824a22e4913945f5842e4be99ec0c7180ec6bdbf56` |
| `docs/governance/02-agent-operating-loop.md` | `aeb4263c0759665914cf7c9b550a7ed2930847a154fbee2e5248c9396abe73d2` |
| `scripts/dg_delivery.py` | `9cd8a0c59122c8916b9b192f7cdb6e1dad9177e431cf4e62aec4b9bf8fb9a84e` |
| `tests/test_dg_delivery_chip_profile.py` | `09087fb4246eba9dc26ec7cebb4f11e02280a0ebd6cf7c33820752c9a45f334e` |
| `tests/test_dg_delivery_claim_release.py` | `f0c0af159ed3f1dcade0d6e4b7b82df1993e3c689344985a36e372e33e423924` |

## Thread A

**r6 HIGH — token fallback split a backticked space-path.** ACCEPTED. The fallback exists
only so a namespace waiver can name a bare directory root (`.agents/`), which the bare-prose
path regex cannot match. It is now restricted to **trailing-slash tokens**, so a reason naming
`docs/a.md backup/file.txt` no longer also names `docs/a.md`. Both the defect case and the
case the fallback exists for are pinned.

**r6 HIGH — bare hex matched inside a larger word.** ACCEPTED. The guard used hex boundaries,
so `xdeadbee` yielded `deadbee` because `x` is outside the hex alphabet though part of the
same word. Now alphanumeric boundaries: `xdeadbee` and `deadbeecafe0` both fail to name
`deadbee`, while `commit deadbee` still does.

**r6 LOW — stale spec count.** ACCEPTED, and I have stopped re-breaking it. The number has
moved **five times** across review rounds. It now reads as an explicit point-in-time figure
that tells the reader to read the collector rather than the line.

## TW26O claim release

**r6 HIGH — a third terminal family in `retry_submit`.** ACCEPTED. `pane_not_ready`,
`pane_unreadable`, and `wire_body_mismatch` all returned `terminal=True` while retaining the
claim and leaving the row non-terminal, so the transaction looked resumable and the pane
stayed jammed. All three now mark the row terminal and release owner-bound, through one
shared local helper so a fourth sibling cannot drift from the invariant.

**A design question I did NOT decide for you.** In `_submit_with_retry`, a body mismatch
transitions to `manual_clear_required` — deliberate custody, claim legitimately held for human
inspection. In `retry_submit` the same condition had no custody transition, so I applied the
invariant and released. **If a retry-path mismatch should instead enter explicit custody, that
is a design change and your call, not mine to take under a scoped authorisation.**

## One defect of my own, disclosed

**My automated marking pass corrupted your r6 verdict.** It appended waiver markers *inside*
your fenced probe-input blocks, altering your quoted evidence. I reverted all three and your
file is intact. Root cause: the gate scanned fenced code blocks as prose, so my marker helper
believed those lines needed waiving.

**Fixed at the source rather than by being more careful:** a fenced code block is verbatim
quoted material, not a citation, and is now excluded from the scan surface entirely. That
removes the whole false-positive class on every reviewer's evidence — your verdicts are full
of fenced probe inputs — and removes the mechanism by which I damaged your file.

This is the **second** time an automation of mine over-reached today; the first appended
markers to pre-existing governance prose in `02`. Both were caught by the next gate run,
both fully reverted, both disclosed. I am no longer running unattended marking passes over
another lane's documents.

## Constraint check

`scripts/dg_mail_carrier.py` **byte-untouched** against origin, default-pause guard intact.
Held across six threads.

## Checks run

- Focused **93/93**; full wire/carrier **213 PASS, 1 skipped, zero regressions**.
- Both your r6 end-to-end inputs re-run: both `False` as required.
- Ruff clean on five Python files; `validate_governance.py` PASS; `git diff --check` clean.
- Full `scripts/verify_sprint_closeout.py --base origin/main` **ENFORCE PASS**.

## Where I want you hardest on r7

1. **The trailing-slash restriction** on the token fallback — can a namespace waiver still
   name something it should not, or fail to name a root it should?
2. **The custody question above** — it is a real fork and I deliberately left it to you.
3. **The claim-release invariant, a fourth time.** Three families are now repaired. Is there
   any remaining terminal return, on any path, that retains a claim?
4. Anything still stale in the spec.

Product boundary: governance + wire tooling only. No model, artifact, API, or study
execution. The QB-1 study has not run; **H2 QB rushing production remains UNDER TEST**.

**PLEASE REPLY with:** (a) **ENUMERATED CLEAR**, Thread A and TW26O stated separately against
the eight hashes, OR (b) **NOT CLEAR** with reproduced defects and `file:line` locators.
