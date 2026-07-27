# Codex r5 verdict — Thread A + Thread B + TW26O claim release

**NOT CLEAR.** All eight frozen hashes match the r5 packet exactly. Thread B is clear under
the already accepted bounded-evidence model, but Thread A still over-waives and the broader
TW26O terminal-claim invariant has another live counterexample.

## Thread A — NOT CLEAR

### HIGH: a dot run followed by another legal path separator still over-waives

Locator: `scripts/verify_closeout.py:194`

Exact input:

```text
See docs/a.md
```

`_reason_names("docs/a.md../backup/ is the historical example", "docs/a.md")` returns
`True`. End to end, `check_dangling_citations(...)` returns PASS and reports both nonexistent
paths—`docs/a.md` and `docs/a.md../backup/`—as waived. The gate's own path grammar admits
both dot and slash. `(?!\.+\w)` blocks a dot run only when its next character is a word
character; slash and hyphen are legal path continuations too.

The frozen spec itself correctly says 64 tests and the frozen verifier file independently
collects 64. The r5 packet's checks list still says “spec now 60” at packet line 107, but that
is a stale packet sentence rather than a stale frozen spec.

## Thread B — CLEAR, with the already accepted bounded-evidence residual

The five former prose/glyph inputs now fail, the three evidenced live shapes pass, and the
recognizer is one-line/fullmatch with only optional `›` plus spaces/tabs.

`› [Pasted Content N chars]` remains forgeable as literal composer text because the helper
receives normalized text, not provenance or styling; a concurrent actor could substitute that
exact literal with the intended length. Under the previously accepted owned-buffer,
empty-composer, immediate state-transition threat model, this is a narrow adversarial residual,
not a new ordinary-race blocker. No evidenced live shape failed.

## TW26O claim release — NOT CLEAR

### HIGH: `retry_submit` has another terminal resolution that retains the claim

Locator: `scripts/dg_delivery.py:1660`

Reproduction using the existing real contract helpers:

```text
row: state=submit_attempt(1), attempts=1, wire_digest intact
pane: owner_send_id=<this send>

retry_submit -> submitted / submit_attempt(2), terminal=False
retry_submit -> refused / submit_attempts_exhausted, terminal=True

pane owner after terminal result -> <this send>
row after terminal result -> state=submit_attempt(2), terminal=False
```

The public retry path therefore returns a terminal result while leaving the pane claimed and
the durable row non-terminal. The next sender can again receive `pane_claim_lost`. This is the
same jam class as TW26O, through a different terminal submit resolution.

Manual-clear terminal states are an intentional exception to the packet's broad “a terminal
transaction must not hold a claim” wording: existing ratified tests require
`manual_clear_required` / `orphan_manual_required` to retain their blocking claims until
owner-bound acknowledgment. The safe invariant must distinguish terminal automatic resolution
from terminal manual-clear custody.

### MEDIUM: the new RED can regress into a comment

Locator: `tests/test_dg_delivery_claim_release.py:74`

The test reads source text and asserts only that `_release_pane` and
`expected_owner=send_id` occur between the transition and return. Replacing the executable
line with:

```python
# self._release_pane(pane_id, expected_owner=send_id)
```

leaves both assertions true. A disposable mutation of the source string confirmed this.
The two helper tests prove `_release_pane` works when directly invoked, but no test executes
the terminal `delivery_unconfirmed` branch and checks that its pane owner becomes `None`.

The actual new call at `scripts/dg_delivery.py:1088` does correctly release its own claim and
refuses to clear a foreign owner; the defect is incomplete invariant coverage, not that call.

## Checks actually run

- All eight frozen SHA-256 hashes: exact match.
- Focused frozen suite: **83 passed**.
- Frozen verifier collector: **64 tests**.
- Current enumerated wire/cockpit selection: **208 passed, 1 skipped**.
- Ruff clean on all five r5 Python files.
- Governance validator PASS; `git diff --check` clean.
- `scripts/dg_mail_carrier.py` has no diff against `origin/main`; default-pause guard intact.
- Live closeout gate truthfully refused CLEAN and its two text checks passed, surfacing
  2 locator and 25 citation waivers.
- Disposable real-function probes reproduced the Thread A false PASS, the retry-submit claim
  leak, and the source-test false assurance.

Product boundary: governance + wire tooling only. The QB-1 study has not run; H2 QB rushing
production remains **UNDER TEST**.
