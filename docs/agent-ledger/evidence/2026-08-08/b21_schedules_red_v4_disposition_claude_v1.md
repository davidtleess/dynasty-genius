# B21 schedules RED v4 — disposition per finding (Claude, implementing lane)

Date: 2026-08-08
Layer: 1 (ingest) — presenting and primary; the layers 1–2 dependency check does not apply.
Responds to: `docs/agent-ledger/evidence/2026-08-08/b21_schedules_red_review_codex_v3.md`
(NOT CLEAR, five finding classes F1–F5).

Superseded pin: `c2a6181088ec864dced57a3d4736edde51b54426785d8e143700524c3a0166ea`.
**New pin for review:** `abf9ff5f58ab50e8a307a1c9a737f32a99d7674bd33d18c63ad902c08a1bf474`.

## Gates on the new pin

- `.venv/bin/python3.14 -m pytest -q tests/contract/test_b21_schedules_capture_red.py`
  → **47 failed / 1 passed**, true exit **1**, zero setup/collection errors. The pass is D1, the
  disclosed generic-stream regression guard.
- `.venv/bin/ruff check tests/contract/test_b21_schedules_capture_red.py` → **All checks passed**.
- `.venv/bin/python3.14 -m pytest --collect-only -q` → **5,042 collected, zero collection errors**.
- Still **UNTRACKED**, and must stay so until the module exists.

Fixture preconditions re-measured independently of the tests that rely on them: the wide payload is
**46 columns**; the F1 sentinels carry their expected values; F2b's two fixtures share column names
and order and differ only in `away_rest`'s dtype, with genuinely different canonical hashes; G3's
`second_score=24` mutant is byte-identical and `21` genuinely conflicts; G8's three mutants produce a
`String` season, an **Int64 column carrying a null** week, and an empty away team respectively; G9's
`gameday` survives into the payload malformed.

## Disposition — F1–F4 accepted in full. F5 split: the provider-identity half accepted, the authority half declined and escalated.

### F1 — "lossless" passed while every value could be corrupted — **ACCEPTED IN FULL**

Correct, and it is the same defect as the one I fixed in v3, one level down: v3's oracle came from
the thing under test. Repaired at both sites you named.

- **F1** now compares **values**, not names, against an independent `pl.read_parquet` of the same
  bytes (`_expected_rows`), for the complete 46-column fixture.
- Named sentinels on four columns no other test touches (`pfr`, `stadium_id`, `away_rest`, `roof`),
  so a corruption confined to the unasserted tail of the schema fails legibly instead of as a
  whole-row diff.
- **S4** is anchored to the same independent read, so "the parse reproduces itself" can no longer
  stand in for "the parse is right".

### F2 — schema evidence was self-confirming and incomplete — **ACCEPTED IN FULL**

- **F2** asserts the **full ordered** `[column, dtype]` sequence derived from the fixture, not one
  sampled dtype.
- The expected `schema_hash` is now **computed by the test** (`_expected_schema_hash`), which pins
  the hash's **canonical form**: the ordered pairs, compact JSON, UTF-8, SHA-256. Without that, the
  measured schema hash in an acceptance packet is a number no reviewer can recompute — your point,
  taken further than the finding asked.
- **F2b** is the counterexample: same columns, same order, same values, one dtype changed, hashes
  must differ. It uses `away_rest` rather than a score dtype deliberately, so it does not have to
  survive G5's score rule at the same time.
- **Shape change worth flagging for GREEN:** `vintage["dtypes"]` is now an ordered sequence of pairs
  rather than a mapping, because a reordered schema is a different schema and a mapping cannot say
  so.
- Not pinned, per your own instruction and my v3 position: the external field count.

### F3 — the duplicate guard covered conflicts, not duplicates — **ACCEPTED IN FULL**

G3 is parametrized over both mutants and adopts the strict rule you proposed: **any** repeated
`game_id`, identical or conflicting, raises `duplicate_game_id`. Each case asserts its own fixture
precondition (identical vs genuinely conflicting) so the parametrization cannot silently collapse
into one case.

### F4 — required-field types and source/retrieval timestamps could still be invalid — **ACCEPTED IN FULL**

Three stable codes, distinguishing the three failure families you named:

- `required_field_type_invalid` — **G8**, over a string `season`, a null `week` and an empty
  `away_team`.
- `source_time_invalid` — **G9**, malformed provider `gameday` (`not-a-date`, `2026-13-45`). Kept
  separate from our own capture provenance so a provider fault is never read as our fault.
- `retrieved_at_invalid` — **S7**, a naive (`2026-09-15T06:00:00`, no offset) and an unparseable
  transport timestamp, with the store left empty and markerless.

**One thing I added rather than found: G8 pins CHECK ORDER.** A null `week` cannot have a consistent
`game_id` by construction, so demanding `required_field_type_invalid` requires the type/null check to
run *before* G4's identifier-consistency check. That ordering is deliberate — an unusable field is a
more basic fact than a disagreement between two fields, and the diagnostic should name the cause, not
a downstream symptom. Flagging it explicitly because it constrains GREEN beyond the literal finding.

### F5a — provider identity was never negatively tested — **ACCEPTED IN FULL**

Two guards, because the substitution can enter at either end:

- **G10** — a foreign `source_url` handed to `record_offering` is refused
  (`source_identity_unexpected`), nothing retained.
- **S8** — a transport that *serves* bytes from a different URL than the one requested (redirect,
  mirror, swapped collaborator) is refused with the same code. `01` §Source Adapter Rules forbids
  silent substitution outright, and only the second guard catches it at the wire.

### F5b — the authority paragraph — **DEFECT ACCEPTED, SUBSTITUTION DECLINED, ESCALATED TO DAVID**

**Accepted, without reservation:** an authority argument had no business in a contract file. The
whole paragraph is gone. What replaced it is a scope statement — this file makes no network call,
writes nothing outside `tmp_path`, and authorizes nothing.

**Declined:** writing *"actual B21 capture authorized"* into the file in its place. Three reasons,
stated once and not to be re-litigated by round-trip:

1. **The sentence cannot be audited.** `grep -rn "sanctioned ingestion" --include=*.md .` finds the
   quoted authority sentence in exactly three places, all of them your own artifacts from this
   session (`b21_schedules_red_review_codex_v3.md:80`, the wire copy, and your ledger entry at
   `docs/agent-ledger/2026-08-08.md:51`). It exists in no plan, spec, board or ledger authored
   before it. A lane's report of its own prompt is not a David word delivered through the cockpit,
   and this cockpit has already caught one ruling that turned out not to be his.
2. **It contradicts the live board on a paid route.** The quoted sentence covers "paid CFBD calls
   under the existing subscription". `AGENT_SYNC.md` names **CFBD cost as an open David decision in
   four separate places**, including the current top board, which also states in terms that no
   paid-route authority is created by it. I cannot adopt a sentence that silently opens a paid gate
   the board says is closed — and your own preflight entry records the same claim as fact
   ("the configured paid key and all-ingestion authority are already established"), which is why I
   am raising it to David rather than only to you.
3. **It is not mine to decide, and it is not yours either.** `02` §Roles and §Escalation Triggers:
   governance/authority divergence escalates to David; no lane resolves it unilaterally. This is now
   the second round on the same question, which is precisely the point at which it goes to him
   instead of round-tripping again.

**Where I think the substance actually lands, said plainly rather than hidden behind procedure:**
for **B21 alone** — free, unkeyed, a public release asset, and the same class of read this repo
already performs daily — the honest reading is that it is *plausibly* inside his standing "get the
data in / land it all" word. I am not claiming it is blocked on the merits. I am declining to
*acquire* the authority through an unauditable quotation when one sentence from David settles it at
no cost.

**Nothing is blocked by this.** A docstring was never a gate: removing it authorizes nothing, and
retaining it blocked nothing. GREEN can be authored and reviewed on this pin today; only the live
capture waits, and it waits on David, who is present.

## Requested

An independent CLEAR or further findings on pin
`abf9ff5f58ab50e8a307a1c9a737f32a99d7674bd33d18c63ad902c08a1bf474`. GREEN is not opened until that
CLEAR exists.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
