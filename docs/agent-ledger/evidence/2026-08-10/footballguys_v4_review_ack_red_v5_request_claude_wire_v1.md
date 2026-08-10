From Claude Code (implementing lane) — review of 8a99bd9: ALL SEVEN ACCEPTED, zero contested · PLEASE AUTHOR RED v5

Your probes hold. Accepted repairs, for the RED to bind:
C1 → adjudication writer refuses unless effective_assertion is an active assertion OF THE SAME KEY
and a member of the adjudication's parents; reducer independently validates the same relation and
returns fail-closed unknown (never raises) on any dangling reference.
C2 → load-side revalidation symmetric with the acquisition reducer: attachment provenance,
assertion claims, and adjudication authority/provenance re-checked against the allowlists on
EVERY read; any unsupported persisted value → fail-closed unknown; _horizon_is_effective accepts
only allowlisted claims.
H3 → closed writer schema: canonical validated evidence retrieved_at, integer-typed version,
full attachment equality (incl. bytes identity) BEFORE any noop; reads never TypeError.
H4 → store classification errors enter the reducer as framing row 9
(unverifiable · record unreadable), never an empty collection — while preserving s28's
unmigratable-refusal snapshot contract.
H5 → reducer selects the single newest attempt by order key, projects exactly one suffix.
H6 → globally comparable event order across both stores (single governed event ledger).
H7 → counterpart lookup stays logically read-only: no schema write, no marker, no user_version on
the inactive store; migration only on the ACTIVE write store (or a separately framed transition).

PLEASE AUTHOR RED v5 binding all seven (your fixtures, incl. the cross-key adjudication, restored
corrupt semantic rows, non-SQLite ledger bytes, failed+invalid history, cross-store equal-instant
transition, and inactive-counterpart byte-freeze). I reproduce your census, then GREEN. Pair lands
only on David's word; 8a99bd9 stays unpushed; no first capture/provider/scheduler/Phase B-C-D.
H2 QB rushing remains UNDER TEST with no result.
