# Codex r4 verdict — closeout hardening Thread A + WIRE-CHIP-1 Thread B

**NOT CLEAR.** Three reproduced defects remain.

## Review basis

Six current artifacts match the r4 packet hashes exactly. `scripts/dg_delivery.py` now also
contains the later, separately authorised TW26O claim-release hunk. Removing only that
seven-line hunk produces the r4 frozen hash
`5ce20e4f2edda680c815fc26228bef4e0e5155223d826785d67fcee63f704faf`;
the chip code under review is unchanged by TW26O.

## Thread A

1. **HIGH — double-dot suffix still over-waives a shorter path.**
   `scripts/verify_closeout.py:192`

   Exact predicate probe:

   ```text
   _reason_names("docs/a.md..backup is the historical example", "docs/a.md")
   -> True
   ```

   End-to-end input:

   ```text
   See docs/a.md
   ```

   With both paths non-existent, `check_dangling_citations(...)` returns PASS and reports
   both `docs/a.md` and `docs/a.md..backup` as waived. The `(?!\.\w)` carve-out treats the
   first dot of the valid double-dot suffix as sentence punctuation. The reason therefore
   still waives an item it does not name.

2. **LOW — the frozen spec's test count is stale.**
   `docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md:53`

   It says 53 contract tests. The frozen test file independently collects 58, matching the
   r4 packet's own 58-test claim.

## Thread B

3. **HIGH — the anchored chip recognizer still accepts non-live prose shapes.**
   `scripts/dg_delivery.py:76`

   Using the stamped 28-character wire body
   `subject\nbody\n [w#7bt0fwg2-1]`:

   ```text
   _observed_matches_body("> |\n[Pasted Content 28 chars]", wire_body)
   -> True
   ```

   The prefix class permits arbitrary repetitions of ASCII `>`, `|`, and `\s`, including
   newline. ASCII `>` is explicitly rejected as a selection glyph elsewhere in the same
   profile registry because it collides with Markdown, and `|` is not a registered Codex
   prompt glyph. A wrong composer can therefore satisfy the pre-key/retry body check with
   chip-shaped Markdown/table prose. The evidence-backed live shapes in the r4 tests are
   empty prefix and `›`; the recognizer should not admit unobserved glyph grammar.

   The earlier design disposition stands: an authentic whole-composer character-count chip
   is acceptable bounded evidence within the owned-buffer, empty-composer, state-transition
   protocol. Decoupling this from `chip_collapsing` was correct. The defect is the recognizer
   accepting shapes not evidenced as authentic chrome.

## Checks actually run

- All seven packet hashes checked; the r4 delivery hash was reconstructed exactly after
  excluding only TW26O's later seven-line hunk.
- Focused r4 suite: **72 passed**.
- Frozen verifier file: **58 tests collected**.
- Current full wire/cockpit selection, including later TW26O tests: **207 passed, 1 skipped**.
- Ruff clean on all four r4 Python files.
- Governance validator PASS; `git diff --check` clean.
- `scripts/dg_mail_carrier.py` has no diff against `origin/main`; its default-pause guard is
  present.
- Live closeout gate truthfully refused CLEAN and surfaced 2 locator plus 18 citation waivers.
- Disposable probes exercised the real functions and reproduced both false positives above.

TW26O claim release is a separate review surface and is not dispositioned by this r4 verdict.

Product boundary: governance + tooling only. The QB-1 study has not run; H2 QB rushing
production remains **UNDER TEST**.
