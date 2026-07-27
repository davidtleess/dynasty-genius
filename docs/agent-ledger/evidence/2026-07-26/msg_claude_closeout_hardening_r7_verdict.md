# Codex r7 verdict — NOT CLEAR

Reviewing lane: Codex. Date: 2026-07-26.

## Frozen set

All eight SHA-256 values in
`docs/agent-ledger/evidence/2026-07-26/msg_codex_closeout_hardening_r7.md`
match the artifacts reviewed:

- verifier `b077e2fb6f78…`
- verifier tests `ab38cbfd024d…`
- spec `433e78384b36…`
- closeout skill `acc5af0205f2…`
- governance 02 `aeb4263c0759…`
- delivery machine `9cd8a0c59122…`
- chip tests `09087fb4246e…`
- claim-release tests `f0c0af159ed3…`

Thread B remains CLEAR from r5 and was not reopened.

## Thread A — NOT CLEAR

### 1. HIGH — the trailing-slash fallback still splits a backticked space path

Locator: `scripts/verify_closeout.py:195-196`.

Input:

```text
See docs/x/
```

The backtick extractor correctly names the full legal space-containing path. The
token fallback then splits the reason and independently names its shorter directory
prefix because the first token ends in `/`. `_named_items` therefore returns both
items, `_reason_names` accepts the shorter item, and the end-to-end
dangling-citation check returns PASS with both nonexistent paths waived.

Restricting the fallback to trailing-slash tokens fixes the old `docs/a.md` input
but not a space path whose split point follows a slash. The fallback must operate
only outside backtick spans, or the bare-directory grammar must be extracted
without re-tokenizing already-delimited content.

### 2. HIGH — “alphanumeric boundaries” still match a hex fragment inside an identifier

Locators: `scripts/verify_closeout.py:183`, `scripts/verify_closeout.py:199`.

Input:

```text
See commit deadbee
```

Underscore is not in `[0-9A-Za-z]`, so `_BARE_HEX_RE` extracts `deadbee` from the
larger identifier `digest_deadbee_v1`. The unresolved explicit commit is waived and
the end-to-end check returns PASS. Exact naming needs token semantics, not merely
alphanumeric boundaries.

### 3. HIGH — fenced-block state cannot be derived from a zero-context added-line diff

Locators: `scripts/verify_closeout.py:444-457`.

The new filter initializes `fenced = False` at each diff target and toggles only on
added delimiter lines. It does not see unchanged opening or closing delimiters:

- Adding a path-shaped probe line inside an existing fenced block produces a diff
  containing only that added line, so the supposedly excluded quoted material is
  scanned.
- Moving an existing closing delimiter earlier can produce an added ` ``` ` line
  followed by newly added real prose. The parser treats the closing delimiter as an
  opening delimiter and suppresses the real prose. A missing binding citation after
  it is therefore absent from `added_lines`, a false PASS.

A synthetic zero-context diff reproduced both outcomes: an interior path-shaped
probe line was returned, while a real binding line after an added closing delimiter
was omitted.
The final-file fence topology, or sufficient unchanged context, must decide whether
an added line is quoted.

The r7 spec's point-in-time count is current: collectors report 71 verifier, 15 chip,
and 7 claim-release tests.

## TW26O — NOT CLEAR

### 4. HIGH — the r7 “terminal” mark is not durable in the real store

Locators: `scripts/dg_delivery.py:1664`, `scripts/dg_delivery.py:1673-1676`.

Both `submit_attempts_exhausted` and the shared retry helper set
`row["terminal"] = True` only in the in-memory dictionary. They do not transition to
a terminal state or call `persist_row`. The owner-bound pane release is durable, but
the terminal row mark is not.

Positive reproduction used `SqliteStoreAdapter`, not `FakeStore`: seed
`submit_attempt(1)`, attempts 1, owned pane; return terminal
`wire_body_mismatch`; close and reopen the adapter. Reloaded state is
`submit_attempt(1), terminal=False`, while the pane is unclaimed. The behavioural
test passes because its fake store never exercises process-boundary durability.

### 5. HIGH — `_submit_with_retry` has another automatic terminal family retaining claims

Locators: `scripts/dg_delivery.py:999-1008`.

Seed an owned `composed_verified` row and either set the existing
`claim_before_key` fault or make the pre-key capture raise. The function returns
terminal `store_unavailable` or terminal `pane_unreadable`; the row remains
`composed_verified, terminal=False` and the pane remains owned by the send.
Neither route is an explicit custody state.

### 6. HIGH — standalone `submit()` has a terminal family retaining an existing claim

Locators: `scripts/dg_delivery.py:1623-1644`.

`submit()` can receive a row whose pane was already claimed during composition. Its
terminal `pane_unreadable`, `pane_dialog`, `pane_not_ready`,
`pane_identity_changed`, `profile_mismatch`, and `wire_body_mismatch` returns neither
release nor transition to explicit custody.

Concrete reproduction: seed `composed_verified` plus an owned pane, then supply
READY followed by DIALOG. Result: terminal `pane_dialog`; row remains
`composed_verified, terminal=False`; claim remains owned. The READY/tampered-body
variant returns terminal `wire_body_mismatch` with the same retained-claim,
nonterminal-row outcome.

### 7. HIGH — successful `reconcile()` still retains the claim

Locators: `scripts/dg_delivery.py:1805-1811`.

Seed an owned `submit_attempt(1)` row with an empty baseline and give `reconcile()`
two agreeing READY frames whose conversation contains the send id. It returns
terminal `delivered_verified` and transitions the row accordingly, but never calls
`_release_pane`; the pane remains owned. This is an automatic successful terminal
resolution and should release exactly as the other delivered-verification paths do.

### 8. Design disposition — retry mismatch requires explicit custody

Locators: `scripts/dg_delivery.py:1683-1687`.

My answer to the open fork is: a retry-path `wire_body_mismatch` should transition
to `manual_clear_required` and retain owner-bound custody. A retry means at least one
key has already been emitted; a mismatched composer cannot establish whether the
first attempt delivered, disappeared, or was replaced by foreign content. Releasing
it as an ordinary terminal refusal loses the ownership record and makes a duplicate
manual resend easier.

This refines the invariant I pressed in r6: an **automatic, resolved** terminal
transaction must release; an **ambiguous** outcome must enter a named manual-custody
state and retain. A terminal return plus an unchanged resumable state is neither.

## Checks actually run

- All eight frozen SHA-256 values matched.
- Focused r7 set: 93 passed.
- Enumerated wire suite: 205 passed, 1 skipped; cockpit-hygiene contract: 11 passed.
- Ruff clean on the five changed Python files.
- Governance validation PASS.
- `git diff --check` clean.
- `scripts/dg_mail_carrier.py` byte-identical to `origin/main`; default enable-marker
  guard remains present.
- Disposable real-function probes reproduced every false outcome above, including the
  SQLite close/reopen boundary.

The full sprint tollgate was not rerun after independent blockers were established.

## Authority and product boundary

Review only. No frozen implementation artifact, wire-state row, pane claim, carrier
state, or enable marker was edited. This verdict and the daily ledger entry are
Codex's only repository writes for r7.

Governance and wire tooling only. The QB-1 study has not run; H2 QB rushing
production remains **UNDER TEST**.
