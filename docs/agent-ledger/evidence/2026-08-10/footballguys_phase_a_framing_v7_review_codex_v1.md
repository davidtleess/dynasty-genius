# Footballguys Phase A framing v7 — Codex round-7 review

Date: 2026-08-10

Reviewed artifact and reproduced identity:

- `footballguys_phase_a_intake_notice_framing_claude_v7.md` — SHA-256
  `5e883be15677f565669fc31b7f8a815eb02be70d4b8465a2ee4d5d3ac12fe9ac`, 376 lines,
  28,597 bytes.

## Verdict

**NOT CLEAR — five findings.** All six round-6 dispositions are accepted in direction. The live
receipt/object hash instruction is repaired, archive-object/vintage cardinality is separated, the
same-attempt readiness rows are disjoint, the DST oracle is correct, the positive durable-ID vectors
reproduce, and unavailable evidence remains inside the semantic reducer. No previous plan or pilot
finding is reopened.

No RED, build, intake, store, scheduler, provider contact, comparison, surface, commit, or push
opens. Plan v4 remains CLEAR. David's retention choice remains a separate hard gate.

## Checks run

- reproduced the submitted SHA-256 identity and line/byte counts;
- diff-read every round-6 disposition against the live self-contained contract;
- independently hand-concatenated the canonical content-vintage and offering-signature bytes,
  importing no production serializer;
- reproduced the positive vector exactly: 200 bytes / `201d2484…` and 478 bytes / `0d6bf306…`;
- reproduced the offset-form and zero-padded-archive-byte negative prefixes;
- tested both plausible meanings of “role swap” and found different hashes;
- traced the selected-role hashes and intact-archive hash through stage, publish, receipt commit,
  and downstream reload;
- challenged both the source-path-to-stage edge and the fresh-publication inode edge with mutation
  between validation steps;
- enumerated failed-attempt overlays over ready, review-required, and metadata-only clock states;
- challenged seconds-only timestamp serialization with two distinct subsecond instants.

## Findings

### 1. High — role records are not bound to the exact archive snapshot that is retained

Section 4 requires selected-member bytes to be verified before publication, while section 6 stages
and hashes the intact ZIP. It never says the role hashes and sizes must be derived from the staged
ZIP bytes that produce `archive_object_sha256`. A conforming-looking implementation can therefore:

1. read and hash the two selected roles from source ZIP A;
2. have the mutable source path replaced with valid ZIP B;
3. stage and hash B as the retained archive object; and
4. commit a receipt containing A's role records and B's archive hash.

Every individual hash was honestly computed, but the signed bundle is incoherent. A later role load
will quarantine it, but the invalid receipt has already been committed and may already have advanced
freshness.

Freeze one snapshot boundary: stage the intact archive first, then derive the archive hash, selected
role bytes/hashes, schema checks, and `content_vintage_id` from that staged inode through bound
descriptor(s); only then publish and commit. Equivalently strong mechanics are acceptable, but no
role fact may be computed from a mutable source pathname independently of the retained bytes.

Required mutant: replace the source ZIP after role profiling but before the archive copy. Intake
must emit one coherent A snapshot, one coherent B snapshot, or fail; it must never sign A's roles to
B's archive.

### 2. High — the fresh-publication branch does not establish the hard-link invariant

The `st_nlink == 1`, no-follow, descriptor-bound integrity check applies only when the canonical
object **already exists**. A new object is staged, closed, and renamed into place without a stated
exclusive/no-follow staging creation rule or a post-publication inode check. A hard link created to
the staged inode before rename survives publication, so the new canonical object can enter the
store with `st_nlink == 2`; the alias can mutate it after receipt commit. A pre-planted staging
symlink is the analogous creation-time hazard if the implementation chooses a predictable temporary
name and ordinary overwrite-open.

Require exclusive, no-follow creation of the staging file and apply the same descriptor-bound
regular-file, link-count, size, and full-hash invariant to a newly published object before the
receipt transaction. Holding and comparing the staged/published inode is preferable to revalidating
an unrelated pathname.

Required mutants: pre-plant the proposed staging name as a symlink to a sentinel; and hard-link the
fresh staged inode before publication, then mutate through the alias. Neither may alter the sentinel
or produce a receipt.

### 3. High — failed-attempt rows flatten or omit the clock's readiness/retention state

Rows 5 and 7 collapse every AR state into `<= clock` and report only the newer failure. This hides
reachable facts. For example, acquisition A advances the clock as `review_required` while analysis
still uses older receipt R; a newer attempt B fails. Row 5 or 7 matches but omits both “latest drop
awaiting data review” and “analysis uses the <date> drop.” A metadata-only observation clock followed
by a failed intake is not represented by rows 5/7 at all, because observations are separately typed
in rows 11/12.

The invalid-attempt repair already has the right structural idea: select one unique base row from
the clock plus readiness/retention state, then compose the attempt overlay. Apply that rule to newer
failed attempts as well (or enumerate disjoint equivalents). A transport failure must not erase the
truth that the clock is metadata-only, review-required, or backed by an older analysis-ready drop.

Required mutants: current review-required clock + older AR + newer failed attempt; and current
metadata-only observation + older AR + newer failed attempt. Both must retain every base fact and
append the failure fact exactly once.

### 4. High — “seconds precision” leaves a durable-identity collision policy undefined

The signature signs validated `retrieved_at`, but its canonical form is declared only at seconds
precision. The contract does not say whether a valid input with fractional seconds is rejected,
truncated, or rounded. If `00:57:00.100Z` and `00:57:00.900Z` are both truncated to
`00:57:00Z`, two different signed instants become the same `receipt_id`; with the same
`offering_id`, the second can be misclassified as an idempotent no-op instead of an identity
conflict. Rounding also creates date-boundary ambiguity.

Choose one closed rule before RED: either `retrieved_at` must be an exact whole-second instant and
fractional inputs fail validation without advancing freshness, or the canonical serialization must
preserve a fixed fractional precision without loss. Do not silently quantize a signed field.

Required mutant: submit the same offering identity at two distinct subsecond instants within one
second. They must not collapse to an idempotent receipt; under the simpler whole-second contract,
both nonconforming values are refused.

### 5. Medium — the negative vectors still require reverse-engineering

The positive vectors are complete and reproduce exactly. The negative vectors are not closed byte
fixtures: hashes are abbreviated, and two mutation descriptions are ambiguous. Independently:

- swapping the **order of the two complete role-record lines** hashes to `86d18b7e…`;
- swapping the **member assignments under the fixed role names** hashes to the documented
  `fb6b16f6…`;
- zero-padding `archive_bytes` hashes to the documented `d87163c3…`, while padding the ADP or
  sidecar byte count produces different hashes.

A RED author should not infer the intended mutation by trying candidates until a prefix matches.
Embed the exact mutated canonical bytes (or fully specify the changed field and before/after value)
and full expected SHA-256 for each negative. State that “role swap” means assignment swap under the
fixed role order, and that the padded integer is `archive_bytes=08540590` if those are the intended
vectors.

## State

- Plan v4: **CLEAR**, unchanged.
- Phase A framing v7: five repairs required; no RED.
- Phase B waits for A's frozen bundle/evidence interface and independent oracle.
- Phase C/D remain closed.
- David's retention choice still gates Phase A RED regardless of the next review result.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
