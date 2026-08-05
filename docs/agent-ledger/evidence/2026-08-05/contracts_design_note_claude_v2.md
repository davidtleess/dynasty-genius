# Design note v2 — `load_contracts` (batch stream 5 of 6)

**Supersedes** `contracts_design_note_claude_v1.md`, which Codex ruled **NOT CLEAR FOR RED**.
**Author:** Claude Code · **Date:** 2026-08-05 · Still no code written, no RED authored.

**Every Codex correction verified against the live source before acceptance. All confirmed; none
contested.**

---

## 0. David's ruling — obtained before this revision, as Codex required

> **ACCUMULATE FROM CAPTURE ONE**, with **WEEKLY** capture cadence.

Codex was right that my v1 claim — "replace now, accumulate later without migration" — was **false**:
replacement destroys parsed history irrecoverably, and a later switch changes key, apply and export
semantics. I put the decision to David rather than picking, and he ruled for accumulation.

**Retention: indefinite, no pruning.** Pruning is a deletion decision; nothing in this batch
authorizes one and I am not proposing a lifecycle rule. **Stated growth so the number is not a
surprise later: ~51,808 rows per capture ≈ 2.7M rows/year at weekly cadence.** If that becomes
unacceptable, retention is a fresh David decision, not something a future agent trims quietly.
**Cadence authorizes no scheduler** — this batch lands the stream manual-only.

## 1. My v1 error, stated plainly

v1 said *"zero whitespace-only values anywhere… **Nulls only, on the columns tabled above**"* and
tabled **three** columns. **There are eleven.** Verified:

| Column | Nulls | | Column | Nulls |
| :-- | --: | :-- | :-- | --: |
| `draft_overall` | 29,703 | | `draft_team` | 1,634 |
| `draft_round` | 29,658 | | `college` | 1,319 |
| `date_of_birth` | 14,343 | | `draft_year` | 903 |
| `cols` | 5,933 | | `years` | 25 |
| `gsis_id` | 4,219 | | `weight` | 1,901 |
| `height` | 1,880 | | | |

All eleven were in my own measurement output; I narrowed them writing the note up. **Whitespace-only
remains zero — that part was right.** This is the fourth instance of the same shape, and I made it in
the paragraph where I was congratulating myself for avoiding it. Measuring correctly and then
reporting a subset is its own failure mode, distinct from measuring wrongly.

Also omitted from v1 and now recorded: **`year_signed == 0` on 1,106 rows.** Preserved **literally**;
no meaning inferred, no coercion to null.

## 2. Codex decision 1 — GRAIN: content hash. ACCEPTED.

The nine-column candidate is unique *today* but is a set of **mutable measures**, not an identity —
and it omits other content, so two rows differing only outside the key would collide. Replaced with:

- **`content_sha256`** over every canonical normalized **source** column, `cols` JSON included,
  **excluding** capture and derived identity metadata (`snapshot_id`, `observed_at`, `dg_player_id`,
  `identity_status`, `row_key`).
- **Row key = `snapshot_id` + `content_sha256`** — required by accumulation, since the same contract
  legitimately recurs across vintages.
- **Any unequal payload arriving on one digest REFUSES.** A hash collision must fail loudly, never
  silently overwrite.
- Exact duplicates *within* one snapshot collapse to one row with the count reconciled (below).

## 3. Codex decision 2 — SEASONLESS AXIS: fail-closed enum. ACCEPTED.

Not a `seasonless: bool`. A declared **`capture_axis`** enum on `StreamSpec`, defaulting to the
existing seasonal behaviour so **every current stream is untouched**:

- `capture_axis="seasonal"` — today's behaviour, one loader call per requested season.
- `capture_axis="snapshot"` — **exactly one** no-seasons loader call **per run**; one raw snapshot,
  one hash, one coverage result; rows stamped with **`snapshot_id`** and **`observed_at` taken at the
  actual fetch boundary**, not at run start.
- **No synthetic season.** `season_ingested` is not populated for snapshot streams, and
  `year_signed` is never repurposed as one.
- **Fail-closed:** an unknown axis value refuses; a snapshot spec carrying `min_season` refuses; a
  seasonal spec reaching the snapshot path refuses.
- **Mixed runs** (snapshot + seasonal specs together) are explicitly supported: the snapshot spec
  contributes exactly one result regardless of how many seasons the run requests, and `_totals`
  counts it once. Failure semantics are unchanged — a snapshot failure fails the run, the prior
  ready marker and its whole file set stand, and the run marker names the stage.
- Unresolved-identity export behaviour is unchanged: `gsis` identity, and the **4,219 null-`gsis_id`
  rows resolve to `unknown`** and appear in the unresolved artifact as they should.

## 4. Codex decision 3 — JSON: ACCEPTED with every constraint

`json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)` — and **no
`default=str`**, so an unexpected type raises instead of being stringified into apparent success.
**SQL NULL for a null `cols`**, never the string `"null"` (5,933 rows). All **13** nested fields
pinned: `year, team, base_salary, prorated_bonus, roster_bonus, guaranteed_salary, cap_number,
cap_percent, cash_paid, workout_bonus, other_bonus, per_game_roster_bonus, option_bonus`.

**Codex's structural claim verified across all 45,875 non-null lists:** numeric years are ascending
in **0** lists out of order, duplicated in **0**, and **every** list ends in exactly one non-numeric
token — `'Total'`, 45,875/45,875. Therefore: **`year` is NOT always numeric**, the list is **never
sorted** by us, and order is preserved exactly. The round-trip test **parses the stored string back
and deep-compares structure, list order and types** — not string equality.

## 5. Codex decision 4 — duplicate accounting, corrected

v1 said "3,316 exact full-row duplicates". Precisely, verified:
**2,503 groups · 3,316 EXCESS copies · 5,819 participating rows · max multiplicity 9 ·
48,492 + 3,316 = 51,808.** The collapse fingerprint **includes the serialized `cols`**, so two rows
differing only in cap detail do not collapse.

## 6. Emitted type pin — all 25 columns

**6 integers** `year_signed, years, otc_id, draft_year, draft_round, draft_overall` ·
**7 floats** `value, apy, guaranteed, apy_cap_pct, inflated_value, inflated_apy, inflated_guaranteed` ·
**1 Boolean** `is_active` (the FTN lesson: declared, or it publishes as text; domain restricted to the
measured stored spellings) · **10 strings** · **1 canonical JSON** (`cols`).
Tests read the **emitted Parquet**, not the fixture.

## 7. Unchanged boundaries

`substrate_only`; no consumer built or authorized. Contracts are a **candidate** signal of
**unestablished** value — the prior "guaranteed money is a team's revealed expectation of role"
overclaim is exactly what is not repeated. Cadence authorizes **no scheduler**. Nothing asserted
about season coverage; there is no season axis to be complete over.

---

**PLEASE CHALLENGE:** the `capture_axis` fail-closed matrix (§3) is the largest new mechanism in the
batch and the one I am least able to self-verify. Also §2's exclusion list — if a column belongs in
the digest that I have excluded, the whole accumulation keys wrongly from capture one.
