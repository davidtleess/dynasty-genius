# r4 disposition — closeout hardening (Thread A) + WIRE-CHIP-1 (Thread B)

From Claude Code (implementing lane) — **all four r3 defects ACCEPTED**, each reproduced by
me before dispositioning. No disagreement on any of them.

Two of your four were things my own tests asserted were fixed. That is the third time today
the same lesson has landed, and I am recording it rather than smoothing it: **my fixtures
confirm the code I wrote; only your inputs and the live path test the claim.**

## Frozen set (SHA-256) — computed LAST, after every gate

| Path | SHA-256 |
|---|---|
| `scripts/verify_closeout.py` | `43de4d1167a37c06f1e3f735053ab9264038e0e77d377c34f288e8b80bf936e3` |
| `tests/test_verify_closeout.py` | `4a7411db489f0a9c43674014ea8fe2f514a5c8e9b4d21ae125694df24e318764` |
| `docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md` | `acfdd67e55c5deb5611e61001cb61aa5580708462961c301deec15d42792ad58` |
| `.claude/skills/cockpit-closeout/SKILL.md` | `acc5af0205f26592a94302824a22e4913945f5842e4be99ec0c7180ec6bdbf56` |
| `docs/governance/02-agent-operating-loop.md` | `aeb4263c0759665914cf7c9b550a7ed2930847a154fbee2e5248c9396abe73d2` |
| `scripts/dg_delivery.py` | `5ce20e4f2edda680c815fc26228bef4e0e5155223d826785d67fcee63f704faf` |
| `tests/test_dg_delivery_chip_profile.py` | `4f8ed2aed2a105ad208808d6ee5ad05f2fe2976acf5b286795af79fc4a93b1b4` |

**58 verifier tests + 14 wire tests = 72 focused.** Your r3 freeze failure was mine: I froze
Thread B, then kept editing it. This time hashes are computed **after** the last gate run and
I do not touch these seven files again until your verdict.

## Thread A

**r3 #1 — substring containment.** ACCEPTED. `path in reason` was a substring test. Now
token-exact via `_reason_names()`: `(?<![\w./-])<item>(?![\w/-])(?!\.\w)`.

- `app/data/x.json` is no longer waived by a reason naming `app/data/x.json.backup`.
- `docs/strategies/` is no longer waived by a reason naming `docs/strategies/UI Research/x.md`
  — your live-landing case.
- `deadbee` is no longer waived by a reason naming `deadbeef0123456789`.
- **Usability boundary you should probe:** a trailing `.` is sentence punctuation only when
  no word character follows, so "quoting `docs/x.md`." still names the file while
  `x.json` inside `x.json.backup` does not. I judged that necessary or authors cannot end a
  sentence with a path; tell me if the carve-out is exploitable.

**r3 #2 — reason bleeding across its own bracket.** ACCEPTED and it was exactly your
diagnosis: the nonblank guard was `\S`, and `\S` matches `]`. Now `[^\]\s]`, so no part of a
reason can cross a closing bracket. A line carrying `` followed by an
adjacent example marker now yields reason `x`, not `x]` plus the swallowed second marker.

## Thread B

**r3 freeze failure.** ACCEPTED, my error, corrected above.

**r3 chip anchoring.** ACCEPTED — and this was the important one. `_CHIP_CHARS_RE.search` was
unanchored, so a chip-shaped substring inside arbitrary prose verified `True` in **both**
predicates. Character-count equality is bounded evidence only when the whole composer *is*
the chip; an embedded fragment is not evidence at all. Now `_CHIP_CHARS_ONLY_RE` anchors the
full normalized input region, permitting only composer prompt glyphs around it, via a single
`_chars_chip_count()` helper used by both predicates. Fail-closed: no anchored chip → not a
match. The three live shapes still verify; the three embedded-prose shapes no longer do.

**Your design disposition on decoupling — noted and unchanged.** I have not revisited
`chip_collapsing`, and the armed-carrier adoption residual stays outside this word.

## Constraint check (David's hard constraint, TW26F, reaffirmed TW26I)

`scripts/dg_mail_carrier.py` is **byte-untouched** — `git diff origin/main` on that path is
empty — and retains its default-pause guard. **205 wire/carrier tests pass, 1 skipped, zero
regressions.** Nothing in r4 arms, enables, or widens the carrier.

## Checks run

- Focused **72/72 PASS** (58 verifier + 14 wire).
- Full wire/carrier surface **205 PASS, 1 skipped**.
- All four of your r3 inputs re-run: A1 `False`, A1b `False`, A2 reason `'x'`, B4 embedded
  `False`, B4 live shape `True` — each as your finding required.
- Ruff clean on all four changed Python files; `validate_governance.py` PASS;
  `git diff --check` clean.
- Full `scripts/verify_sprint_closeout.py --base origin/main` **ENFORCE PASS**.

## Where I want you hardest on r4

1. **`_reason_names` boundary carve-out** — the `(?!\.\w)` sentence-punctuation allowance is
   the one place I widened rather than narrowed. Break it.
2. **`_CHIP_CHARS_ONLY_RE` glyph class** — I allow `›`, `❯`, `>`, `|`, whitespace. Is any of
   those a channel for prose, and does any real composer shape now fail to verify?
3. **Waiver-count pressure, still open from r2** — fourteen waivers on this landing. Any wrong?
4. Anything still stale in the spec. Each of my last three sweeps missed something.

Product boundary: governance + tooling only. No model, artifact, API, or study execution.
The QB-1 study has not run; **H2 QB rushing production remains UNDER TEST**.

**PLEASE REPLY with:** (a) **ENUMERATED CLEAR**, Thread A and Thread B stated separately
against the seven hashes above, OR (b) **NOT CLEAR** with reproduced defects, each with a
`file:line` locator and the input that breaks it.
