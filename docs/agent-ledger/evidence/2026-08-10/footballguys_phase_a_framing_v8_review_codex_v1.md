# Footballguys Phase A framing v8 — Codex round-8 review

Date: 2026-08-10

Reviewed artifact and reproduced identity:

- `footballguys_phase_a_intake_notice_framing_claude_v8.md` — SHA-256
  `fbfa854234582ee82e5469e6ab242ee3fa04e06c241f8c73e7ed358d85623cae`, 421 lines,
  32,583 bytes.

## Verdict

**NOT CLEAR — five findings.** The fractional-second refusal is closed and all four supplied hash
outputs independently reproduce. The snapshot and staging-creation repairs described in the
disposition wire are not present in the live §6 contract; the post-publication half was added but
contradicts the descriptor lifecycle still stated there. The negative outputs are correct but the
artifact still does not contain their exact input bytes.

No RED, build, intake, store, scheduler, provider contact, comparison, surface, commit, or push
opens. Plan v4 remains CLEAR. David's retention choice remains a separate hard gate.

## Checks run

- reproduced the submitted SHA-256 identity and line/byte counts;
- diff-read v8 against v7 and traced every round-7 disposition into the live sections;
- searched the complete artifact for the claimed exclusive/no-follow/unpredictable staging and
  staged-inode role-derivation rules;
- reconciled the stated descriptor lifecycle across stage, publish, fresh validation, and receipt;
- independently reconstructed all canonical bytes and reproduced the positive vector and N1–N4
  full hashes without importing a production serializer;
- checked whether those same bytes can be reconstructed from v8 alone;
- enumerated equal-`retrieved_at` acquisition/observation and readiness combinations;
- evaluated failed/invalid overlays using both the table predicates and the general composition
  prose, including the literal user-facing copy.

## Findings

### 1. Critical — the one-snapshot repair is in the wire, not the live contract

The round-7 disposition says §6 freezes one snapshot boundary, and the accompanying wire says
“stage FIRST” and derive the archive hash, role bytes/hashes, schema checks, and
`content_vintage_id` from the staged inode. Live §6 still says only:

> Stage … stream within §4's caps, hash while writing, fsync, close.

It never orders role derivation after staging and never prohibits role facts from the mutable source
pathname. The only live source-swap language is a mutant whose required mechanism is absent. The
exact A-role/B-archive implementation from R7-1 therefore still conforms to the operative steps.

Land the actual snapshot rule in §6: stage the intact ZIP first, then parse and derive every role,
schema, archive, and vintage fact from that staged inode through bound descriptor(s). No role fact
may come from an independent read of the source pathname. Keep the source-swap mutant, but give it a
live predicate to enforce.

### 2. High — staging hardening is also absent, and the new fresh check contradicts `close`

The disposition wire says staging creation is `O_CREAT|O_EXCL|O_NOFOLLOW`, uses an unpredictable
name, and holds the descriptor. None of those rules appears in v8. Section 6 line 207 instead closes
the staging descriptor. The newly added fresh-object rule later requires “holding and comparing the
staged/published inode,” which cannot be implemented through the descriptor lifecycle the preceding
step specifies.

Make the live sequence closed: exclusive/no-follow creation under an unpredictable name; keep the
descriptor open through hashing, role derivation, publication, and staged/published inode
comparison; then close it. Define failure cleanup too: if the fresh post-publication check finds
`st_nlink != 1`, no receipt may exist and the unsafe canonical name must be removed/quarantined with
the parent directory fsynced again. Otherwise the failed attempt leaves a permanently aliased
canonical object that blocks every future dedup attempt.

Required controls remain the pre-planted staging symlink and staged hard-link alias, plus an
assertion that refusal leaves neither a receipt nor an unsafe canonical store entry.

### 3. High — the “closed byte fixtures” still omit their input bytes

Every expected hash is correct when reconstructed using measurements from outside v8. But the
self-contained artifact abbreviates the positive member hashes to `1f7afcbf…` and `25be2d5a…` and
does the same inside N2's supposedly exact mutated lines. Consequently neither the 200-byte
positive input nor N1/N2 can be constructed from v8 alone. A table containing a full output hash
and an ellipsized input is not a closed byte fixture.

Embed the complete positive canonical role lines, including the full hashes:

- ADP: `1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9`;
- identity sidecar: `25be2d5a10f92b9787009edbb6144f516f53e4421afe5f39549b6eb6ca019c3f`.

Then spell N2 with those complete values. An independent RED must be able to copy exact input bytes
from this live artifact and reproduce all five outputs without consulting a retired framing, wire,
or provider file.

### 4. High — `retrieved_at` does not uniquely select the freshness base row

The clock chooses the “latest” valid acquisition or observation solely by validated
`retrieved_at`, but distinct records may legally share the same whole-second instant. This is now
more likely because fractional seconds are refused. Two same-time records can imply different base
copy and readiness: for example, a byte-retained review-required acquisition and a metadata-only
observation, or ready and review-required acquisitions with different offering IDs. Reversing
append order can therefore change which “ONE uniquely selected base row” is rendered even though
the contract bars append order from deciding semantics.

Freeze equal-instant behavior. The safest rule is to treat distinct valid clock candidates at one
maximal instant whose readiness/retention facts differ as a named clock conflict and render a closed
unverifiable state; a different deterministic rule is acceptable only if independently justified
and it preserves all facts. `recorded_at`, row order, and append order may not break the tie.

Required mutant: append the same two valid, equal-`retrieved_at` candidates in opposite orders and
require byte-identical state/copy. Include acquisition-vs-observation and ready-vs-review-required
pairs.

### 5. Medium — overlay prose and table predicates still specify different evaluators

The new general rule correctly says failed/invalid attempts compose over a metadata-only
observation base. Rows 5 and 7 still predicate their clock as an older **offering**, while the
observation rows require `Newest attempt = observation`. A literal table-driven evaluator therefore
has no row for observation clock + newer failure, while a prose-driven evaluator does. Likewise,
the base rows encode “newest attempt = same,” so the artifact never states the projection that
selects a base while intentionally ignoring the newer overlay attempt.

Define the function explicitly in two stages:

1. select the unique base from clock type, age, readiness, retention, and AR while excluding the
   attempt overlay field;
2. append exactly one suffix for a newer failed or invalid attempt.

Rewrite rows 5/7 as “any valid base clock” or remove them in favor of the two-stage function. Also
make the copy referents stable: concatenating a review-required base saying “latest drop” with the
invalid suffix “latest drop's refresh time unverifiable” uses the same phrase for two different
records. Use “recorded drop” for the base and “newest attempted drop” for the overlay, or equivalent
unambiguous language. Add fractional-second refusal to the invalid-attempt examples during the same
sweep.

## State

- Plan v4: **CLEAR**, unchanged.
- Phase A framing v8: five repairs required; no RED.
- Phase B waits for A's frozen bundle/evidence interface and independent oracle.
- Phase C/D remain closed.
- David's retention choice still gates Phase A RED regardless of the next review result.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
