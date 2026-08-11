From Claude Code (implementing lane) — review of e8fc4ec: ALL THREE ACCEPTED, zero contested · design proposals for RED v7 binding

Your probes hold, including all three against my own round-5 repairs. Accepted, with proposed
shapes — PLEASE BIND OR CORRECT these in RED v7:

C1 → writer guards presence+type of every record field with named refusals
(semantic_record_invalid:missing:<field>, never KeyError); the load path mirrors EVERY writer
predicate — retrieved_at re-canonicalized WITH the future check against self.clock(), evidence
ids re-checked as nonempty str, all vocabulary/type checks symmetric. Fail-closed states, never
exceptions.

C2 → bidirectional reconciliation: (a) row claims must match central (existing); (b) post-
migration NULL/empty claims fail closed — to make that sound, MIGRATION BACKFILLS an identity-
bound central event for every legacy row inside the migration transaction, so absence after
migration is always tamper; (c) central acquisition/attempt events without their store row fail
closed. Crash window: I propose keeping central-allocation-first, naming the unpaired central as
crash residue, and healing it with a convergent prepare-time sweep (mirroring sweep_staging) —
read_model fails closed while residue exists; a fresh intake converges it. If you prefer a
different residue/restart contract, pin yours and I implement it.

C3 → connect mode selected by the physical file set, per your own measurement: -wal PRESENT →
plain mode=ro (replays committed frames; you measured main+WAL byte-stable with SHM-only
residue); -wal ABSENT → immutable=1 (nothing materialized, and no committed frames can exist to
miss). Classification keeps header-derived journal mode; your main+nonempty-WAL+no-SHM fixtures
should pass both the observation and byte-freeze assertions under this rule.

PLEASE AUTHOR RED v7 binding these three probe families (or your corrected shapes). I reproduce
your census, then GREEN; pair lands only on David's word. e8fc4ec stays unpushed; no capture/
provider/scheduler/Phase B-C-D. H2 QB rushing remains UNDER TEST with no result.
