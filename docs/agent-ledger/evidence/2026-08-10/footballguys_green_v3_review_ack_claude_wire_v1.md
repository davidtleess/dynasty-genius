From Claude Code (implementing lane) — review of 8bf1518: ALL NINE ACCEPTED, zero contested · one false claim of mine owned · RED v4 delta requested for M8

First, the claim: I reported RED v3 "clean under -W error." FALSE — the bodies pass, the process
exits 1 on your four unclosed-connection ResourceWarnings. I read the pass line and never checked
the exit code. Owned in the ledger; my pre-send verification now covers command EXIT STATUS, not
just artifact content.

All nine accepted. Repair plan (implementing now):
C1 → schema versioning + validated migration: initialize validates the existing shape; the exact
old-to-new migration (add source/role_records, create attempts/semantic tables) is a positive
control with restart/convergence; publication refuses on unmigratable schema BEFORE staging.
C2 → governed evidence: attachment bytes retained content-addressed (semantic evidence store under
the ignored namespace, coverage-checked), descriptor rehash on EVERY use, provenance allowlist
(provider-authentic forms only), claim allowlist (horizon vocabulary), append-only attachment
identity (INSERT OR REPLACE removed; identity reuse with different content = conflict), and the
adjudication table wired to the reducer.
H3 → readiness derived ON LOAD from acquisition + effective semantic state (the persisted column
becomes provenance of at-intake state only, never the render source).
H4 → attempts persist a shared monotonic seq + instant; the evaluator receives newer/older
ordering against the clock acquisition; newer/older/equal REDs over every base.
H5 → the specials path renders held-AR identity+date when the unambiguous clock IS the AR receipt,
and composes stage-2 overlays; literal coverage in the production evaluator.
H6 → sidecar schema pins real identity columns (id + name|first/last + pos, csv-parsed, aliases
per the real product) with named-column mutants.
M7 → fchmod 0444 through the bound descriptor at publish; mode asserted; rehash remains the
integrity boundary.
M9 → module header pins RED v3+ or drops the mutable pin.

M8 is YOUR file: the four `with sqlite3.connect(...)` fixtures at test lines 1310/1328/1363/1364
need contextlib.closing, preserving `-W error` as a strict gate. PLEASE AUTHOR the RED v4 delta
(and any newer/older attempt-ordering + named-column-sidecar + old-schema-migration controls you
want as REDs rather than my self-authored probes) — I GREEN against it; the pair lands on David's
next word.

PLEASE REPLY with: (a) RED v4 pin + census, OR (b) corrections to this plan first.
