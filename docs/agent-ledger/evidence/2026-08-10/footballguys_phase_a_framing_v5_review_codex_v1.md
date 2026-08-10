# Footballguys Phase A framing v5 — Codex round-5 review

Date: 2026-08-10

Reviewed artifact and reproduced identity:

- `footballguys_phase_a_intake_notice_framing_claude_v5.md` — SHA-256
  `a1ec47ec8c40c2ef00152a459a65da5282d1a73a519c9c60ba3f2418af64ca71`, 206 lines,
  14,994 bytes.

## Verdict

**NOT CLEAR — five findings.** All four round-4 dispositions are accepted in direction. The safe
nested-path resolver, acquisition-only receipt identity, descriptor-bound reuse check, downstream
rehash requirement, invalid-attempt precedence, and observation-only copy are substantive repairs.
None of the previous pilot or plan findings is reopened.

No RED, build, intake, store, scheduler, provider contact, comparison, surface, commit, or push
opens. Plan v4 remains CLEAR. David's retention choice remains a separate hard gate.

## Checks run

- reproduced the submitted SHA-256 identity and line/byte counts;
- diff-read v5 against v4 and traced every round-4 disposition to its live replacement contract;
- inspected the real paid ZIP's central-directory metadata without extracting or executing any
  member: 8,540,590 archive bytes, 259 entries / 219 non-directory files, 24,723,646 aggregate
  uncompressed bytes, 12,376,512-byte largest member, maximum measured ratio 11.8766:1;
- classified the real ZIP member types from stored Unix mode bits and found three symlink members,
  all outside the two selected data-role paths;
- checked the fifteen state rows against observation/receipt coexistence and the preserved v2/v3
  timing contract;
- challenged semantic assertion selection with contradictory and late-arriving evidence;
- traced each hash named in §§5–6 to acquisition signature, archive content, and role content.

## Findings

### 1. Critical — v5 still permits a reader that refuses the full real archive

V5's reject list says “symlinks” without limiting that rule to selected role members. The actual
paid ZIP contains three legitimate framework symlink entries:

- `DraftDominator.app/Contents/Frameworks/XojoFramework.framework/XojoFramework`
- `DraftDominator.app/Contents/Frameworks/XojoFramework.framework/Resources`
- `DraftDominator.app/Contents/Frameworks/XojoFramework.framework/Versions/Current`

Neither required role is a symlink, and nothing unselected is extracted or executed. An
archive-wide symlink refusal follows v5 literally and rejects the real input again. The stated
positive control is only the “real two-member nested shape”; it is not the full 259-entry archive,
so it cannot catch this failure.

Scope the type/encryption rule precisely: selected role entries must each be regular,
non-encrypted, non-symlink files; unselected entries are never opened and do not fail intake merely
for being symlinks. Whole-archive central-directory rules should cover only hazards that matter
without extraction: exact-role duplication/ambiguity, structural parsing, and explicit resource
limits.

The limits also need values before RED. “Cap archive bytes/member count/member size/aggregate/ratio”
allows a no-op cap or a cap below the real input. Freeze numeric inclusive boundaries and the
zero-compressed-size rule. Use the complete real ZIP, or a byte-faithful full-structure fixture with
the measured 259-entry/symlink/resource shape, as the acceptance control; retain the small
two-role ZIP only as a unit positive.

Required mutants: reject any unselected symlink; accept a selected-role symlink; cap below the
known-good archive; omit one cap; treat nonempty/zero-compressed-size as a finite ratio; and inspect
or extract an unselected member.

### 2. High — the observation repair still omits the exact older-AR state it claims to adopt

Rows 11 and 12 require `AR = none`. But the round-4 required case was “due observation with
older/no AR,” and v5's own mutant list repeats “older/no AR.” A metadata-only observation can be the
newest valid freshness clock while `latest_analysis_ready` remains an older retained receipt. The
rule that AR never references an observation does not erase that older AR.

Either declare retention modes lifetime-mutually-exclusive and make receipt/observation coexistence
an impossible migration requiring new framing, or add current/due observation rows with an older
AR and exact copy such as the existing “analysis uses the <date> drop” disclosure plus “no data
retained.” The latter matches the accepted design and preserves history.

Add the promised mutants literally: recent observation + older AR and due observation + older AR.
They must advance freshness, leave AR byte-unchanged, disclose both facts, and never make the
observation analysis-ready.

### 3. High — “latest unconflicted assertion” can launder an active semantic conflict

Suppose version 1 says `seasonal_redraft` and version 2 presents retained, hash-valid evidence for
`dynasty_startup`. If v2 is recorded as conflicted, “latest unconflicted assertion” selects v1 and
can open Phase C while the contradiction remains live. That is worse than returning `unknown`: it
makes the first claim win by excluding the evidence that challenged it.

Freeze an effective-state reducer, not a row filter. Any unresolved conflict on the active
content/export/field key must yield `horizon=unknown` and keep Phase C closed. Supersession must be a
separate adjudication record with its own identity, provenance, authority, and explicit parent
versions; append order and evidence retrieval time never resolve a conflict by themselves.

Also define assertion idempotency and ordering. Required mutants: old unconflicted assertion plus
new conflicting assertion still emits the old horizon; a late-arriving older document silently
supersedes; changed claims reuse an assertion id; and an unproven “superseded=true” flag clears a
conflict.

### 4. High — the superseding artifact dropped the closed monthly-clock contract

V3 fixed the due rule as America/New_York **calendar dates**, `due` at `>=30` days, no grace,
season-flat, persistent rather than event-like, with DST/month/year boundaries. V5 has `<30d` and
`>=30d` labels but does not carry the timezone, calendar-date rather than elapsed-hour calculation,
no-grace rule, or persistence contract. It instead says prior dispositions “are carried in v4 and
remain binding.” That is the superseding-artifact dependency class already caught in round 3: an
operational contract cannot require readers to reconstruct live behavior through retired framings.

Restore the complete due rule in v5. Required controls: 29/30 local calendar days; 29 days 23 hours
across a DST change; spring/fall DST boundaries; month/year boundary; same-day timestamps with
different offsets normalized to America/New_York; season-flat behavior; no grace; and repeated
reads remain due until a later valid acquisition/observation advances the clock.

### 5. Medium — v5 conflates the receipt signature hash with the content hash

Section 5 defines `receipt_id` as the offering-signature hash over identity and provenance fields.
Section 6 then says every downstream load reverifies “bytes against the receipt hash.” Raw archive
bytes cannot hash to `receipt_id`; the archive SHA-256 and each role SHA-256 are different values.
An implementation comparing payload bytes to the literal receipt hash will reject every valid
object, while an implementation that guesses another field is no longer following a closed
contract.

Name the exact object model and hash at every edge: whether the immutable ZIP itself is the retained
canonical object, whether decompressed roles are stored objects or regenerable views, which
`object_sha256` each receipt references, and which member hashes establish `content_vintage_id`.
Downstream reads rehash against that object's content SHA-256 stored in the receipt — never against
`receipt_id`.

Because `receipt_id` is durable identity, freeze its canonical serialization and timestamp
normalization with an independent known-answer vector: field order/type, UTF-8 encoding, separators,
integer representation, and canonical UTC representation of equivalent offsets. The oracle must
not call the production serializer.

Required mutants: compare object bytes to `receipt_id`; retain only decompressed roles when the
contract requires the intact archive; swap `adp`/`identity_sidecar` role hashes; and give equivalent
instants in `Z` and `-04:00` forms different receipt identities.

## State

- Plan v4: **CLEAR**, unchanged.
- Phase A framing v5: five repairs required; no RED.
- Phase B waits for A's frozen bundle/evidence interface and independent oracle.
- Phase C/D remain closed.
- David's retention choice still gates Phase A RED regardless of the next review result.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
