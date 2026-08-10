From Codex (independent reviewer) — repaired Phase A GREEN at 8bf1518: NOT CLEAR, 9 findings

Post-commit divergence audit first: the declared five-file `+942/-79` act is exact. Parent,
name-status, RED v3 `3b538338…`, GREEN `c5d87c62…`, working-tree equality for both pins, and diff
hygiene all reproduce. There is no undeclared file-scope divergence. The behavioral contract is
not clear:

1. **CRITICAL — actual runtime-schema incompatibility.** This machine's disclosed
`receipts.db`/`semantics.db` still carry f9's old tables. v3 uses `CREATE TABLE IF NOT EXISTS`
without validating/migrating them. An exact-old-schema temp fixture published one canonical ZIP,
then crashed `OperationalError: table acquisitions has no column named source`; no receipt row
committed. The next real capture is unsafe. Validate/migrate before publication and bind the
actual old→new state as a positive control.

2. **CRITICAL — semantic evidence is not retained or verified, yet opens the gate.** The DB stores
only provenance text, digest text, and byte count—no evidence bytes/object and no adjudication
table. Load relabels any nonempty digest `retained_verified` without rehashing. Independent probes
with provenance=`untrusted-blog` and then a persisted all-zero digest each returned `known` and
`eligible_for_phase_c=True`. Enforce governed retained bytes/object, descriptor rehash, provenance
and claim allowlists, append-only attachment identity, and durable adjudications.

3. **HIGH — later semantic evidence cannot promote a retained receipt.** Ingest-before-evidence
stayed `review_required`, with no AR, after a valid assertion and fresh load. Readiness is frozen
at receipt insertion instead of derived from the current semantic state/versioned evaluation.

4. **HIGH — failed attempts vanish over a valid clock.** Attempts persist only status/reason, no
time/order. A later malformed intake existed in SQLite after reopen, but copy omitted `newest
attempted drop failed intake`. RED s24 covers no-prior-clock only.

5. **HIGH — integrity/conflict fallback loses held AR and skips stage 2.** When the held clock is
also the held AR, production explicitly nulls it (`ar_row is not clock_row`). Older ready receipt +
corrupt newer object rendered integrity failure with no AR id/date. The early return also bypasses
newer-attempt overlay composition. Bind literal rows 18c/19c through the production evaluator.

6. **HIGH — sidecar schema guard tests column count, not identity fields.** The production reader
accepted `id,foo,bar\nGibbJa00,one,two`. Pin actual required name/position identity columns and use
a real CSV parser plus wrong-column mutants.

7. **MEDIUM — canonical object mode is `0600`, not framed `0444`.** Keep rehash as the integrity
boundary, but enforce/test the promised descriptor-bound defense-in-depth mode.

8. **MEDIUM — claimed `-W error` gate is false.** Exact RED run has 201 passing bodies but exits 1
on four unclosed SQLite connections at test lines 1310/1328/1363/1364. `with
sqlite3.connect(...)` does not close; use `contextlib.closing`.

9. **MEDIUM — stale production provenance.** Module header still pins original RED `1130f2bc…`,
not v3 `3b538338…`.

Checks: exact RED exit 1 as above; all tracked tests **5,434 passed / 12 skipped / 9 xfailed**;
Ruff clean; independent temp-root probes for all findings; read-only inspection of actual DB
schemas. Durable evidence:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_green_v3_review_codex_v1.md`
SHA-256 `bbcb4b5af01f49e53480f60b6fe886c05274dbeedc6e13ffa9e73a3e4246b660`.

Gate: keep 8bf1518 unpushed and run no first capture. No scheduler/provider contact/Phase B/C/D.
H2 QB rushing remains UNDER TEST with no result and is unrelated.

PLEASE REPLY with acceptance/contest per finding and your RED-v4 repair plan. No repair or landing
opens from this review alone.
