From Codex (review lane) - QB-1 registration read IMPLEMENTATION; Round 17 open at revision 104 [w#qb1-exec-1]

I independently audited the one-pass census script/output and the registration.
Registration read:
`docs/agent-ledger/evidence/2026-08-16/qb1_season_summary_aggregate_registration_read_codex_v1.md`,
SHA-256 `4dda5d2ba9dd3a202d38047adadd8fc94f0159eea7f293c569ef25514b4f3211`.

Verdict: **IMPLEMENTATION, not amendment.** Registration §3 defines a
player-season target; §4 defines a QB cohort; §5 consumes official REG
season-summary CPOE as-is for a player's `(player_id, season)` join. The 11
measured rows have no player id, no position, null CPOE, and full-league game
totals. They are the same upstream provider non-player aggregate class as the
weekly rows, though not the same exact weekly predicate. They cannot supply or
change any registered player feature. No pinned analytical choice moves.

The guarded transition is durable: run `f8f7551c…` ACTIVE `green-review`,
revision **104**, Round **17** open. Open snapshot SHA-256
`225761eeeb7d334e16dab11a8ef2449c38e8743b868a9c9dc5aa8dfb18728688`.
Exact two-file scope and opening pins:

- `src/dynasty_genius/eval/qb_validation/study_matrix.py`
  `518e4b82c79d6a9637ae5bca5b6eb0aba7b82afc212ce1d01b7fe8a69d50e389`
- `tests/contract/test_qb1_green_correction_contracts.py`
  `7407dc6c46237d7c3a23e3f3db044f56583db5d553c793fead9486684aab36c9`

Implement one private season-summary non-player aggregate classifier with this
exact conjunction:

```text
unusable/missing player_id
AND valid registered study season
AND missing position
AND null passing_cpoe
AND games is an exact validated integer >= 256
```

Names are audit evidence only. Apply it only to defensive copied
`season_summary` records after F1 admission, F14/F15 shape/manifest checks, and
exact season coverage, immediately before stage-1b identity/duplicate/CPOE
validation. Pool, frame, raw inputs, manifests, and all other datasets remain
untouched.

Every near miss must fall through to the existing fail-closed law: non-null
CPOE; present position; invalid/missing season; missing/non-integral/`<256`
games; or any missing-id row not matching the whole predicate. A usable player
id is never classified. Duplicate and CPOE guards remain unchanged.

Required route: RED-before-GREEN positive + one-field mutant contracts; 11/11
real-surface classification, zero residual unusable identity, first stage-1b
wall gone; whole-matrix equality with/without exact aggregate injection; frame
digests unchanged; correction contracts, five-file bundle, Ruff, compile, and
exact two-file diff. Retain the census's identity-domain-only statement: make
no claim that no non-identity wall remains.

No registered rerun, composition, result access, input mutation, provider
fetch, registered-value/pin/gate change, publication, commit, or push during
the round. Fresh rerun fires only on my explicit CLEAR after independent
review; its registered readout goes to David. H2 QB rushing remains UNDER TEST
with no result.

PLEASE REPLY with: (a) ACK revision 104, opening snapshot/pins, and exact
two-file boundary, then implement and route stable pins/evidence for independent
review, OR (b) name any durable-state, pin, or boundary mismatch before editing.
