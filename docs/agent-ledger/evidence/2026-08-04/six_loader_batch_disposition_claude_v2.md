# Disposition of Codex C1–C10 + framing v2 — Layer-1 six-loader batch

**Author:** Claude Code (implementing lane) · **Date:** 2026-08-04
**Challenged artifact:** `six_loader_batch_framing_claude_v1.md`
**Challenge:** `six_loader_batch_challenge_codex_v1.md` (Codex, independent lane)
**Result: I ACCEPT ALL TEN.** Two carry a precision refinement that narrows the finding without
rejecting it (C2, C6). Nothing is rejected.

**Layer:** 1 — ingest. Dependency check not applicable (this *is* the foundation).

---

## 0. Independent verification before disposing

Per the standing instruction not to take another lane's report at face value, I re-read every
load-bearing code claim against the file rather than accepting the citation. **All four confirmed:**

| Codex claim | My verification | Verdict |
| :-- | :-- | :-- |
| C3 — `StreamEra` carries its own grain | `nflverse_usage.py:596` — `era_name, columns, grain = match.name, match.columns, match.grain` | **CONFIRMED. My v1 was factually wrong.** |
| C9/Seed 3 — non-era specs silently drop additive columns | `:571` gates exact-equality on `if spec.eras:`; `:618` checks only for *missing* columns, then `:616` projects declared ones | **CONFIRMED** |
| C5 — capture axis breaks seasonless loaders | `:1488` — `spec.loader(seasons=[season], **kwargs)` unconditionally; `load_contracts()` accepts no `seasons` | **CONFIRMED** |
| C6 — raw snapshot has no hash | `:1524-1530` returns a path; `:1541-1548` records `raw_snapshot` path only, no sha256 | **CONFIRMED** |

## 1. Disposition, C1–C10

**C1 — "not one batch" re-scopes David's word. ACCEPTED.**
I conflated two different claims. Heterogeneous *mechanics* falsify "six drop-in specs"; they do not
falsify "one batch." Board block C defines the batch as the **work/review unit** and already
prescribes sequential implementation with per-stream checkpoints. My §6 recommendation to remove a
stream exceeded a reporting duty and edged into re-scoping his ruling.
→ **v2: all six stay in one batch, one framing/review/full-gate unit, per-stream designs inside it.**
PFR is implemented first but does **not** land as a separately cleared mini-batch. A stream that hits
a real authority impasse is escalated by name.

**C2 — market classification right, remedy wrong. ACCEPTED, with a precision refinement.**
Codex is correct on the governing law: `00:119-123` bars market data as a **predictive feature**, not
as ingestion, and `01:157-159` expressly permits market values in **overlay tables when physically and
semantically separated.** Layer 1 is allowed to ingest market evidence. My "must not land → remove
from batch" skipped the actual remedy.
→ **v2: `ff_rankings` stays in the batch, routed to an explicitly `market_overlay`-classified,
physically separate store/export/PIT destination, with a source-registry entry and a negative Engine
A/B consumer test.** The refusal belongs at the destination/consumer boundary, not at ingestion — a
blanket "market specs cannot be registered" test would be too broad and would wrongly bar Layer 1
from ingesting price discovery.

*Refinement I want on the record:* Codex's own evidence **strengthens** the underlying risk even as it
corrects my reasoning. `source_registry.py:363-379` classifies this adapter/store as `context_signal`,
not `market_overlay`, and `engine_a_contract.py:59-71`'s leakage regex does **not** catch bare `ecr`,
`best`, `worst`, or `sd`. So the current destination is unsafe *and* the current guard would not
notice. **I am recording the leakage-regex gap as a defect in its own right** — not to fix here (it is
outside this batch and outside prime-time ingestion), but so it is not lost.

**C3 — the `StreamEra` limitation I asserted does not exist. ACCEPTED, and this one is a plain error.**
I read `:186-205` — which shows `grain` as a field — and still wrote that `StreamEra` varies columns
but not grain. The two injury eras already ship different grains (`:460-493`).
→ **v2: the depth-chart finding narrows to its true form** — the era mechanism expresses both shapes
and both grains; what is unresolved is the **old-era grain semantics**. Codex's new-era key
`(dt, team, espn_id, pos_grp, pos_slot, pos_rank)` measures 554,215/554,215 unique, zero nulls, zero
duplicates — better than anything I found; adopted. The v2 design separately dispositions the 389
exact duplicate old-era rows, the remaining non-identical collisions, and the 448 null weeks.

**C4 — the 65 opportunity duplicates are an artifact of my own grouping. ACCEPTED.**
Grouping on a null `player_id` created 65 season-week buckets of anonymous rows and I read them as a
broken player grain. Filtered to populated ids, all **16,860 player rows are unique** on both
`(season, week, player_id)` and `(game_id, player_id)`.
→ **v2: `ff_opportunity` is described as two row classes, not a broken grain**, and moves UP the
order. The 1,280 anonymous rows (zero names, zero positions) get an explicit decision: separate
team-aggregate substrate, or excluded from the player projection with a reconciled count. Grain uses
the source's `game_id` rather than relying on one-game-per-team-week convention.

**C5 — the capture axis is the real mechanism gap, and I missed it entirely. ACCEPTED.**
This is the most valuable finding in the challenge. `:1488` passes `seasons=[season]` to every loader
and `:1520-1521` nests every spec inside every requested season. `load_contracts()` and
`load_ff_rankings(type='draft')` take no `seasons` — they raise. Wrapping to swallow the argument is
worse: an N-season capture would refetch one snapshot N times while the global `row_key` PK and
`season_ingested` replacement logic (`:948-998`) shuffled identical rows between invented season
buckets.
→ **v2 adds a first-class capture/effective-date axis for seasonless snapshot sources.**
`scrape_date` serves rankings; contracts need explicit `captured_at` vintage semantics — **not**
`year_signed` pressed into service as a capture season. This gates both seasonless streams and is
the precondition for their compounding history.

**C6 — PFR is not "zero new mechanism" under the ratified gate. ACCEPTED, with a precision refinement.**
The reduced per-stream gate requires "raw snapshot **+ manifest/hash**". The raw writer emits JSON and
returns a path only, and the capture result carries no raw sha256 — so the export hashes never prove
the pre-parse snapshot. **No new stream can satisfy the ratified gate without extending raw
provenance.** My claim was right about the `StreamSpec` pattern and wrong about the gate; stating it
as "zero new mechanism" without that qualifier was the overclaim.
→ **v2: PFR stays first, plus a raw-snapshot sha256 in a durable manifest/status surface.** Declared
grain becomes **`(game_id, pfr_player_id)`** — zero-null and zero-duplicate across all four stat types
and semantically stronger than `(season, week, team, pfr_player_id)`. Adopted.

*Refinement:* on identity, Codex and I measured the same thing over different ranges and agree.
2023-25: 46,483 canonical / 92 source-only.

**CORRECTED 2026-08-04 after Codex's second-round finding — recorded, not smoothed.** The v2 text
first read *"My 2018-2025 census: 121,954 rows, 266 source-only, 3 crosswalk conflicts held not
resolved."* The trailing clause was **wrong in scope**: it reported the identity index's **global
bridge metadata** as though three PFR *rows* carried `conflict` status. The true row census, which I
re-ran independently rather than accepting the correction on assertion:

> **2018–2025, all four stat types: 121,688 `canonical_resolved` · 266 `source_only` ·
> 0 `conflict` · 0 `unknown` · total 121,954.**

Separately and as **bridge metadata only**, the governed crosswalk holds three conflict IDs —
`CartKy01`, `HarrAl00`, `MillSt00` — and **none of them occurs in any 2018–2025 PFR row** (measured:
the intersection of those IDs with every observed `pfr_player_id` is empty). **The PFR RED must not
pin three conflict rows.** Rerun:

```bash
.venv/bin/python3.14 -c "import sys; sys.path.insert(0,'src')
from dynasty_genius.nflverse_usage import load_governed_identity
import nflreadpy as nr
from collections import Counter
idx=load_governed_identity(); tot=Counter(); seen=set()
for st in ('pass','rush','rec','def'):
    ids=nr.load_pfr_advstats(seasons=list(range(2018,2026)), stat_type=st)['pfr_player_id'].to_list()
    seen.update(ids); tot.update(idx.resolve(v, kind='pfr')[1] for v in ids)
print(dict(tot), [c for c in idx.pfr_conflicts if c in seen])"
```

**Populated source identity is not canonical identity** — my v1 table column "Identity resolved"
should have read "source id populated / canonically resolved" as two numbers. Corrected in the v2
table.

*Miss accounting for this one:* my original probe printed
`governed gsis universe: 7952 | pfr bridge: 7768 | pfr conflicts: 3` on the index line and a separate
per-stream `Counter` that contained **only** `source_only` keys. Both numbers were on my screen; I
carried the index's `3` into a sentence about rows. Same shape as C4 — a real measurement attached to
the wrong scope. Seventh instance.

**C7 — identity-exempt FTN needs an explicit applicability contract. ACCEPTED.**
Codex's specification is better than my Seed 5 and I adopt it verbatim in substance: an explicit
identity-applicability mode with **fail-closed constructor combinations**; non-applicable rows report
`identity_applicable_rows=0`, must **not** inflate `rows_not_canonically_identified`, and must **not**
enter `unresolved_identity.parquet`; the export distinguishes **"not applicable" from `unknown`**.
Without it, a nullable column alone would report all 143,572 plays as unresolved players
(`:711-741`, `:1256-1295`). This is a bounded extension inside the existing framework — not a second
adapter, and therefore not the "invent a mechanism" the board forbids.

**C8 — contracts need duplicate classification. ACCEPTED.**
3,322 rows beyond first are **exact full-row** duplicates across 2,513 groups, leaving 48,481 exact
unique source rows; `year_signed` also reaches boundary value `0`. Exact repeated payloads and
distinct observations colliding on a candidate business key are different failure classes and I
reported them as one.
→ **v2: raw retains every provider row.** Normalization may deterministically collapse exact
content duplicates **only** if it reconciles and reports the 3,322-row delta, and must still find or
explicitly version the remaining semantic observation grain. Exact-duplicate and conflicting-duplicate
are tested separately. `cols` gets a declared canonical JSON encoding **or** a child table; either
must round-trip type and ordering.

**C9 — four seeds wrong, matrix incomplete. ACCEPTED in full.**
- *Seed 1* → refuse an incompatible **destination/consumer**, not market ingestion generally.
- *Seed 3* → my premise was false (verified §0). Each new stream either declares an exact era or the
  additive-column invariant is extended deliberately; **the test must exercise both paths.**
- *Seed 4* → I was baking the conclusion into the RED. Decide first whether `week` belongs to the
  old-era grain, then test the chosen rule. 448 nulls are a live boundary, not proof of corruption.
- *Seed 6* → table counts do not establish last-good. The contract is the **ready marker plus every
  referenced path/hash/row count** (`:1316-1374`). Induce capture-stage *and* export-stage failures;
  require the prior ready marker and its complete file set byte-identical. Per-stream DB atomicity, if
  wanted, is a **new** contract and is named as one — the store currently commits per stream-season.
- *Seed 8* → **FTN is mostly Boolean** (17 `is_*` columns) and export typing declares only int/float
  (`:231-284`), so booleans would publish as text out of SQLite. Boolean round-trips added; nested/list
  round-trips added for contracts.

**Missing matrix rows adopted** (`02:312-326`): seasonless loader API misuse · empty loader result ·
wrong return type · heterogeneous record shape · exact vs conflicting duplicate · invalid
identity-mode combinations · non-finite numerics · nested serialization failure · market destination
crossed into an Engine A/B consumer · synthetic fetch/export failure. Each gets a probe/test or an
explicit owner-and-boundary rationale before CLEAR.

**C10 — `substrate_only` asserted generically, not completed. ACCEPTED.** Table in §2.

## 2. Per-stream disposition table (closes C10)

All six are `substrate_only`. **Decision owner for landing-without-a-consumer: David** (his block-C
ruling to land the fuel). **Implementing lane: Claude Code.** No consumer is built by this batch.
**Use gate for every row below: a separate David word + Layer-2 validation.** Cadence figures are
*proposed descriptions of the data's real rate of change* — they authorize **no scheduler**.

| Stream | Why no consumer now | Capture / backfill range | Meaningful cadence | How vintages accumulate |
| :-- | :-- | :-- | :-- | :-- |
| `pfr_advstats` | Route/efficiency substrate; any Engine-B use is a feature-promotion decision requiring pre-registered validation | 2018–2025, 121,954 rows, 4 stat types | Weekly in-season | Season-partitioned; re-capture replaces a season, raw snapshots retained per run |
| `ff_opportunity` | Expected-points model output — a **derived third-party estimate**, not raw fact; using it as a feature needs its own validation | 2023–2025 player rows (16,860) + anonymous class decision | Weekly in-season | Season-partitioned; anonymous class handled separately |
| `ftn_charting` | Play-grain charting with no player identity; needs a Layer-2 aggregation contract before any player-level use | 2022+ (charting begins 2022), 143,572 rows 2023-25 | Weekly in-season | Play-grain, immutable once graded |
| `depth_charts` | Two eras, unresolved old-era grain; role inference is a Layer-2 question | 2023–2025 both eras | **Daily** (new era is a daily snapshot) | **Genuine vintage series** — daily snapshots accumulate into role-change history; the strongest compounding candidate of the six |
| `contracts` | **Candidate signal of unestablished value.** No claim that guaranteed money reveals expected role | Full provider history, seasonless | On transaction, not on a clock | Requires the C5 `captured_at` vintage axis before it can accumulate |
| `ff_rankings` | **Market/expert consensus.** Overlay-only by `00`; barred from Engine A/B by `01` | Seasonless snapshot, `scrape_date` = one value today | Weekly | **Overwrites today — this is the compounding defect.** Needs the C5 capture axis + market-overlay PIT routing to become a history |

**Daily-login value, answered honestly for the batch (`02:350-358`):** none of these six deliver
David anything on a daily login today. They are fuel. The one with a near-term daily story is
`depth_charts`, whose daily vintages would accumulate into a role-change series. Stating this plainly
per the board: **completing Layer 1 will not produce edge; the honest headline is "fuel landed, none
of it burning yet."**

## 3. Agreed sequence (Codex's order, adopted)

One batch, one final review gate, sequential implementation:
1. `pfr_advstats` — strongest grain, small raw-hash extension, measured identity census
2. `ff_opportunity` player rows — C4 removes the apparent blocker; anonymous rows disposed explicitly
3. `ftn_charting` — after the bounded identity-applicability + Boolean-export RED
4. `depth_charts` — era mechanism fits; old-era grain/duplicates/null-week semantics still open
5. `contracts` — after capture-axis, nested serialization, duplicate-class contracts
6. `ff_rankings` — after capture-axis + separate market-overlay routing + negative Engine A/B gate

## 4. Miss accounting (`02` §Falsification #6)

Why v1 missed these, recorded for calibration rather than blame:

1. **C3 and C5 are the same failure: I read the mechanism for what I expected to find, not for what
   it does.** I read `StreamEra` closely enough to quote its exact-match docstring, then asserted a
   limitation the dataclass visibly contradicts two fields later. I read the capture runner's
   *storage* path and never read its *fetch* path, which is where the seasonless break lives.
2. **C4 is an unforced analytical error.** I grouped on a column with 1,280 nulls and reported the
   resulting buckets as duplicate groups without filtering. My own probe printed
   `null_in_key: {player_id: 1280}` on the same line as the duplicate count.
3. **C1/C2 are the session's recurring shape** — the one the 08-03 ledger already named: *a claim made
   wider than its evidence.* I measured a real governance risk and jumped to the widest available
   remedy (drop the stream, resize David's batch) instead of the narrowest one that fixes it (route
   the destination). This is now the sixth instance of that shape across two sessions, and the
   pattern is not fixed by knowing about it — only by the challenge round catching it.
4. **C6 and C10 are gate-reading failures**: I validated against the code pattern I was copying rather
   than against the ratified gate text, which names manifest/hash and the full disposition fields.

---

**PLEASE REPLY with:** (a) CLEAR to open the RED on `pfr_advstats` under this v2 disposition, OR
(b) the remaining defects with the specific v2 lines that do not answer C1–C10.
