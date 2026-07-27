# Codex r6 verdict — Thread A + TW26O claim release

**NOT CLEAR.** All eight frozen hashes match exactly. Extraction-based naming has two fresh
over-waivers, a third automatic terminal retry route still retains its claim, and the frozen
spec count is stale.

## Thread A — NOT CLEAR

### HIGH: token fallback splits a backticked space-containing path

Locator: `scripts/verify_closeout.py:192`

Exact input:

```text
See docs/a.md
```

The primary extractor correctly yields the full backticked path, but `_named_items` then
splits the reason on whitespace. Its fallback turns the first token into `docs/a.md`, so the
named set becomes:

```text
docs/a.md
docs/a.md backup/file.txt
```

End to end, with both paths nonexistent, dangling-citations returns PASS and waives both.
A reason naming the full space-containing path therefore still names a shorter item it does
not intend to name.

### HIGH: the bare-hex extractor finds a commit inside a larger word

Locators: `scripts/verify_closeout.py:181`, `scripts/verify_closeout.py:196`

Exact input:

```text
See commit deadbee
```

`_named_items("artifact xdeadbee is historical")` yields `deadbee` because `x` is outside
the hexadecimal alphabet even though it is part of the same alphanumeric token.
`_reason_names(..., "deadbee")` returns `True`; the unresolved explicit commit is waived and
the end-to-end check returns PASS.

### LOW: frozen spec count is stale

Locator: `docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md:53`

The frozen spec says 64 verifier tests. The frozen verifier test file independently collects
68. Together with 15 chip and 6 claim-release tests, that is the packet's reported 89.

## TW26O claim release — NOT CLEAR

### HIGH: `retry_submit` has a third automatic terminal route retaining its claim

Locator: `scripts/dg_delivery.py:1673`

Reproduction:

```text
row: state=submit_attempt(1), attempts=1, terminal=False
pane: owner_send_id=<this send>
capture: DIALOG / not READY

retry_submit -> refused / pane_not_ready, terminal=True
pane owner after return -> <this send>
row after return -> submit_attempt(1), terminal=False
```

The `pane_unreadable` and `wire_body_mismatch` sibling returns have the same structure.
These are not transitioned into an intentional `manual_clear_required` custody state; they
return terminal while leaving the durable transaction resumable-looking and the claim held.

The repaired `delivery_unconfirmed` and `submit_attempts_exhausted` paths do release and mark
terminal as required. The behavioural tests for those two paths pass.

## Checks actually run

- All eight frozen SHA-256 hashes: exact match.
- Focused frozen suite: **89 passed**.
- Frozen verifier collector: **68 tests**, versus 64 in the spec.
- Ruff clean on all five r6 Python files.
- Governance validator PASS; `git diff --check` clean.
- `scripts/dg_mail_carrier.py` has no diff against `origin/main`; default-pause guard intact.
- Disposable real-function probes reproduced both extraction false PASSes and the third
  terminal claim retention.

Product boundary: governance + wire tooling only. The QB-1 study has not run; H2 QB rushing
production remains **UNDER TEST**.
