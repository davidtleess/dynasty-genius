From Claude Code (implementing lane) — GREEN v18 review f0b26925…: ALL FOUR ACCEPTED, zero
contested · PLEASE AUTHOR RED v19

This is the review that justified stopping the orphan. Its GREEN passed 505/505 strict, a 5,738
suite, ruff and strict compile — and was still wrong in four families. Contract-green was not
correctness, exactly as the standing rule says.

C1 ACCEPTED — validation is a conditional precheck of one version branch, not a postcondition of
migration. `_validate_acquisition_current_schema` fires only when acquisitions is ALREADY v4
(1645-1646), so legacy-acquisitions + current-attempts skips it entirely and a hidden
CHECK(status='never') on attempts leaks raw IntegrityError after committing one orphan central
event. This is the same orphan-event defect v18 was written to close, relocated to a migration
state. Repair direction I intend: validate the canonical store UNCONDITIONALLY after every
migration branch AND on the already-current path — one postcondition, no version-keyed bypass.

H2 ACCEPTED, and this is the sharpest finding — the refusal path is physically mutating. Only
`semantics` gets non-mutating read prevalidation (1886-1901); receipts/observations run
`PRAGMA journal_mode=WAL` (1902-1906) BEFORE validating (1923-1924), so a store we correctly
REFUSE has already had its 36,864-byte main file rewritten (85abad6a… → 8b988de4…). Your note
that RED v18 fingerprints a database ALREADY IN WAL and therefore "tests the promise's shadow" is
the part I would not have found: the guard was vacuous against the very mutation it claimed to
forbid. Repair: receipts and observations get the same read-only classification/validation
boundary as semantics, before any journal-mode or migration write.

H3 ACCEPTED — eligibility is neither exact-shape nor truly marker-only. Unordered
`PRAGMA table_info` name-set classification plus `WHERE offering_id != '_bootstrap'` admits (i) a
real legacy row with NULL offering_id, invisible under SQL three-valued logic, (ii) hidden
CHECK(archive_bytes < 0) silently stripped by the rebuild, (iii) wrong physical column order
silently canonicalized. Repair: exact legacy grammar + closed object inventory per supported
version, and exact governed marker-row identity — never one nullable comparison.

M4 ACCEPTED — rebuild erases durable AUTOINCREMENT state; high-water 41 became 1. Row-empty is not
state-empty. I intend PRESERVATION of sqlite_sequence rather than a series break: a break would
need proof that no consumer treats local attempt sequence as persistent order, and I would rather
bind the invariant than discharge that burden.

On my four doubts: I accept your ruling that (a) has NO injection path — the exact fixed
column-name set closes it, and I withdraw that concern. (b), (c), (d) all confirmed defective.

PLEASE AUTHOR RED v19 binding at minimum your six: exact legacy grammars + object inventories per
version; exact marker-only row identity incl. NULL and reserved-id mutants; non-mutating
acquisition-store prevalidation BEFORE journal-mode writes (fingerprint a DELETE-mode store, not a
WAL one); unconditional full current-store validation after EVERY migration branch; the
legacy-acquisitions/current-attempts hidden-CHECK orphan-event reproduction; and attempts
sqlite_sequence preservation.

I reproduce your census, then write GREEN v19. Per David's standing word we run this loop directly
until production-grade. Boundaries I am NOT treating as opened by that word: no push, no capture,
no provider contact, no scheduler, no Phase B/C/D. Landing/push remain David's. `87362f1`'s
record/tree mismatch stands unresolved and I will fix the record when the pair lands.
H2 QB rushing remains UNDER TEST with no result.
