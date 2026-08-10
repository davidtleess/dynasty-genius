# Footballguys plan v4 + Phase A framing v4 — Codex round-4 review

Date: 2026-08-10

Reviewed artifacts and reproduced identities:

- `footballguys_horizon_divergence_plan_claude_v4.md` — SHA-256
  `f60c4d22c1b41e7f1981cf9a426dbefc5fcc505f04d545e22e66c42200fe1255`, 139 lines,
  9,924 bytes.
- `footballguys_phase_a_intake_notice_framing_claude_v4.md` — SHA-256
  `e383f605513746b919bcf0a087b5610995d731e5f087704072f55df9dc8d72e2`, 150 lines,
  10,106 bytes.

## Verdict

**Plan v4: CLEAR. Phase A framing v4: NOT CLEAR — four findings.** The eight round-3
dispositions are accepted in substance. Plan v4's live pointers now bind the exact current Phase A
artifact; the phase gates, horizon-unknown vocabulary, prospective identity gates, no-lookahead
pairing, and C/D closures remain intact.

No RED, build, intake, store, scheduler, provider contact, comparison, surface, commit, or push
opens. David's retention choice remains a separate hard gate.

## Checks run

- reproduced both submitted SHA-256 identities and line/byte counts;
- followed every v4 operational pointer and confirmed plan §9 plus the David-word register point to
  Phase A v4 and its exact hash;
- diff-read Phase A v4 against the accepted v2/v3 boundaries and inspected the shipped
  `daily_control`, source-registry, PFF content-store, capture-health, drawer, and backup-manifest
  contracts;
- listed the real paid ZIP's central directory without extracting or executing any member;
- checked the proposed state rows against the preserved v3 acquisition-clock contract and the new
  option-3 observation model;
- challenged the immutable-offering/evidence lifecycle and content-addressed reuse branch with
  late evidence, alias, and post-verification mutation counterexamples.

## Findings

### 1. Phase A / Critical — the archive reader's separator guard refuses the real paid archive

Section 4 rejects “path separators after normalization.” The actual required members are:

- `DraftDominator.app/Contents/Resources/adp.csv`
- `DraftDominator.app/Contents/Resources/projections.csv`

Both contain legitimate separators. Thus the reader described by v4 must reject the exact bundle
this design exists to intake. This is a real-input falsification, not a hypothetical archive edge.

Allow safe relative nested paths. Reject absolute/drive-rooted paths, NULs, empty/dot/traversal
components, separator ambiguity, and duplicate normalized/case-colliding names; do not reject a
separator merely because it exists. Freeze how roles resolve — preferably exact full normalized
member paths for this product/export — so basename search cannot select `__MACOSX/.../._adp.csv`
or a second attacker-controlled `adp.csv`. Add the real two-member path shape as the positive
control and a same-basename/different-directory archive as a refusal mutant.

### 2. Phase A / High — the “reachable-state table” still omits reachable states

The table is materially better, but it is not exhaustive and therefore cannot yet be the RED
oracle:

- option 3 creates a valid `refresh_observation` with `raw_retained=false` and
  `analysis_ready=false`, yet `Newest attempt` has no observation state and no row says whether a
  recent/old observation is `current`/`due`, what AR displays, or what exact copy appears;
- a valid acquisition at least 30 days old whose same offering is `review_required` is reachable
  (for example a late-imported old archive), but `due + review_required` has no row;
- v3's preserved rule says naive/malformed/future `retrieved_at` makes that offering
  freshness-unverifiable and does not advance the clock. V4 has only “ledger unreadable” for
  `unverifiable`; it gives no precedence/copy for an invalid newest attempt with no prior valid
  clock or with an older valid clock.

Enumerate those rows and fix the selection/precedence rule explicitly. Required mutants: recent
observation with no intake receipt; due observation with older/no AR; due+review-required; future
attempt with no prior valid acquisition; and future/malformed attempt after an older current or due
acquisition. A failure-state implementation must not erase a valid prior acquisition, and an
observation must never become analysis-ready.

### 3. Phase A / High — evidence discovered after intake has no honest immutable lifecycle

Section 5 signs semantic-contract fields and evidence-attachment references into the immutable
offering signature. That correctly prevents silent mutation, but the currently decisive semantic
fact is `horizon=unknown`; provider-authentic evidence may be captured after the archive receipt.
Under v4, adding that evidence to the same offering is an identity conflict. Creating a new
`offering_id` instead falsely turns semantic research into a new paid-source acquisition and can
advance/reset the reminder clock.

Separate the immutable acquisition receipt from an append-only, versioned semantic assertion or
evidence-binding record keyed to the relevant content/export/field. A later evidence revision must
leave `receipt_id`, `offering_id`, `retrieved_at`, and freshness byte-unchanged; conflicts and
supersession stay explicit. Define which revision Phase C may use and make evidence retention obey
the manifest/exception law before its first durable write. An unretained or missing attachment
cannot license a non-`unknown` horizon.

Required mutants: adding valid horizon evidence mutates/replaces the receipt; evidence capture
creates a new acquisition; two assertions reuse one evidence identity with conflicting claims; a
missing/unretained attachment opens Phase C.

### 4. Phase A / High — canonical reuse verifies a pathname once, not an immutable object

Section 6's existing-object branch requires only “regular non-symlink file” plus one size/hash
check. This repeats the alias class already found in this pilot: a hard link is regular and
non-symlink. A canonical path hard-linked to another writable name can pass verification and then be
mutated through the alias, leaving the receipt's content address false. There is also an ordinary
path-to-open race if type checks and hashing do not operate on one descriptor. A content-addressed
store that trusts its address after intake is not evidence-preserving.

Freeze the object-integrity boundary before RED. At minimum, perform no-follow open + `fstat` +
size/hash through one descriptor, refuse or explicitly govern multi-link objects, and require every
downstream load to reverify bytes against the receipt hash before using them. Publication must be a
kernel-enforced atomic no-replace operation; never `exists()` followed by an overwriting rename.
State the immutability/permissions rule and what a later hash mismatch does (quarantine/refusal,
never analysis).

Required mutants: pre-existing hard-link alias with matching bytes then alias mutation; pathname
swap between validation and open; post-receipt canonical-byte mutation; and an implementation whose
“no-replace” is an existence check followed by overwrite.

## State

- Plan v4: **CLEAR**.
- Phase A framing v4: four repairs required; no RED.
- Phase B waits for A's frozen bundle/evidence interface and independent oracle.
- Phase C/D remain closed.
- David's retention choice still gates Phase A RED regardless of the next review result.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
