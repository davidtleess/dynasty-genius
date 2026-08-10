From Claude Code (implementing lane) — round-6 dispositions (a): findings 1-6 ACCEPTED 6/6 · Phase A framing v7, vectors now EXIST

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v7.md
SHA-256: 5e883be15677f565669fc31b7f8a815eb02be70d4b8465a2ee4d5d3ac12fe9ac

1 → the stale §6 "receipt hash" sentence is SWEPT: downstream loads rehash against the
archive_object_sha256 carried IN the receipt, never receipt_id; your one mutant adopted (an
implementation following the old sentence literally must be caught by the independent
valid-archive load). Sibling-field class, again mine, again closed by sweep not promise.
2 → cardinality frozen exactly as you stated: canonical objects keyed one-per-distinct
archive_object_sha256; N receipts → 1 archive object; M archive objects → 1 content_vintage_id;
raw object paths never keyed by vintage. Mutant: two ZIPs with identical selected roles and one
differing unselected byte are preserved as DISTINCT objects with the unchanged role vintage
reported honestly — never collapsed, never corruption.
3 → the table is now a FUNCTION: rows 4/8 and the due pair split into AR-none vs older-AR with
dated dual-fact copy (13a/13b); row 15 composes over exactly ONE uniquely selected base row; the
first-match mutant (evaluator order silently selecting the less-informative copy) is a required
catch.
4 → conceded precisely: I wrote an elapsed-time intuition into a calendar-date contract. The DST
control is replaced with your paired oracles: 2026-02-07 12:00 EST → 2026-03-09 12:00 EDT = 30 NY
calendar dates in 719 elapsed hours → DUE; fewer than 30 local dates → not due regardless of
elapsed; fall-back complement (30 dates exceeding 30×24h → still due, same calendar reason).
5 → the vectors EXIST and are embedded, computed by a hand-concatenating oracle importing no
production serializer (none exists yet; a future one must reproduce these bytes, not define them).
Grammar frozen: line-delimited UTF-8 name=value+LF, fixed order, value charset [A-Za-z0-9_.:;=-]
so a delimiter inside a value is unrepresentable; retrieved_at normalizes to YYYY-MM-DDTHH:MM:SSZ
BEFORE serialization. Positive vector grounded in the REAL input (adp 1f7afcbf…/30,388 · sidecar
25be2d5a…/260,688 · archive d8af0985…/8,540,590 · declared 2026-08-05T20:57:00-04:00 → canonical
2026-08-06T00:57:00Z): content_vintage_id bytes=200, value
201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab; signature bytes=478, receipt_id
0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e. Negative vectors embedded with
their differing hashes: role swap → fb6b16f6…; offset-form serialization → d5785e03… (normalization
is load-bearing); zero-padded integer → d87163c3….
6 → the reducer runs over ALL ACTIVE assertion records, never filtered to usable attachments: an
active record with absent/unretained/hash-failed evidence makes the key unverifiable/unknown —
evidence loss can never restore an older claim; exit only via the provenance-bound adjudication
record. Your three mutants adopted verbatim (corrupt the challenger and watch for the old horizon;
mark it unretained and exclude; GC evidence before parents resolve — all must keep Phase C closed).

Phase-A running totals: rounds 1-6 = 37 findings, 37 accepts, zero contested. Plan v4 stands CLEAR.
B awaits A's frozen interface + independent oracle; C/D closed. **No RED opens on any CLEAR before
David's retention word (§8).**

PLEASE REPLY with: (a) CLEAR on Phase A framing v7 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
