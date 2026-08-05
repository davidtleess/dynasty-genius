# Design note — `load_contracts` (batch stream 5 of 6), routed BEFORE implementation

**Author:** Claude Code · **Date:** 2026-08-05 · **Status:** design, no code written
**Routed before implementing deliberately.** Across three review rounds Codex found nine defects in
work I had already committed, three of them the same shape: a premise asserted inside a safety guard
without measuring it. This note exists so the design is challenged while changing it is still cheap.

**Everything below is measured against the live source today. Nothing is inherited from my earlier
probes** — and that matters, because the earlier probe measured **51,803** rows and today's measures
**51,808**. This source has no season axis and mutates under us. That is itself a finding.

---

## 1. Measured shape

| Property | Value |
| :-- | :-- |
| Rows / columns | **51,808** / 25 |
| Season axis | **NONE** — `load_contracts()` takes no `seasons` argument at all |
| Exact full-row duplicates (incl. the nested column) | **3,316 rows** → 48,492 exact-unique |
| `is_active` | **Boolean** — the FTN lesson applies; must be declared, or it publishes as text |
| `otc_id` | Int32, **zero nulls**, 12,863 distinct |
| `gsis_id` | null on **4,219** rows |
| `cols` | `List(Struct(...))` of 13 year-by-year cap fields; null on **5,933** rows |

**Nulls vs blanks vs whitespace, checked separately on every column** (the `depth_position` lesson):
**zero whitespace-only values anywhere in this stream.** Nulls only, on the columns tabled above.
I am stating this because last round I measured `is_null()` alone and missed 3,964 artifact values.

## 2. The grain — content-based, and I want that called what it is

No natural business key exists. Measured on the exact-unique set:

| Key | Duplicate groups |
| :-- | --: |
| `otc_id + year_signed` | 9,616 |
| `+ team` | 6,668 |
| `+ position` | 6,350 |
| `+ years + value + apy` | 23 |
| **`otc_id + year_signed + team + position + years + value + apy + guaranteed + is_active`** | **0** |

The residual collisions before `position` were the **same contract listed at two positions**
(measured example: one row `RG`, one `LG`, every other field identical) — so `position` is a real
distinguishing coordinate, not padding.

**Honest framing: this is a content-based grain, not a business key.** It is "every column that
distinguishes a row", and it will change meaning if the provider adds a distinguishing field. I am
proposing it because it is measured-unique, not because it is principled. **Codex: this is the
decision I most want challenged.** The alternative is a surrogate key over the content hash, which is
honest in a different way but makes the store's key opaque.

`years` is null on 25 rows and would need declaring nullable in the grain (per-era contract from the
last round).

## 3. The three mechanism gaps

**a) Seasonless capture axis (Codex C5, still unbuilt).** `run_usage_capture` calls
`spec.loader(seasons=[season], **kwargs)` unconditionally, and nests every spec inside every
requested season. `load_contracts()` accepts no `seasons`, so it raises — and wrapping it to swallow
the argument is worse: an N-season run would refetch one snapshot N times while `season_ingested`
shuffled identical rows between invented buckets.

*Proposed:* a declared `seasonless: bool` on `StreamSpec`. When set, the capture calls the loader
**once per run** with no season argument and stamps rows with a **capture vintage** (`captured_at`
from the existing run timestamp) instead of `season_ingested`. **The 5-row drift between two probes
today is the argument for a vintage axis rather than an overwrite** — the compounding lens prefers
capture-and-accumulate, and without a vintage two captures are indistinguishable.

**Open question I cannot answer alone:** does each capture ACCUMULATE as a new vintage (store grows
without bound, real history) or REPLACE the previous one (store stays one snapshot)? Accumulation
serves the compounding lens; replacement matches how every other stream in this batch behaves.
**This is a David-level product decision, not a mechanical one, and I will not decide it silently.**
My proposal for now: **replace**, matching the batch, with the vintage recorded so accumulation can
be turned on later without a migration.

**b) Nested `cols`.** SQLite cannot hold `List(Struct)`. *Proposed:* canonical JSON with sorted keys,
declared explicitly, round-tripping **type and ordering** — with a test that parses the stored string
back and compares against the source structure, not just the string. Null stays null (5,933 rows),
not `"null"`.

**c) Exact duplicates.** 3,316 rows. The `collapse_exact_duplicates` mechanism already built for
depth charts applies verbatim — deterministic, counted, and a row differing in any declared column
still refuses. **The fingerprint must include the serialized `cols`**, or two rows differing only in
cap detail would collapse into one.

## 4. What I will NOT assert

- No claim that contracts data has predictive value. It is a **candidate** signal of **unestablished**
  value; the board's hypothesis boundary applies verbatim, and the earlier "guaranteed money is a
  team's revealed expectation of role" overclaim is exactly the thing not to repeat.
- `substrate_only`, no consumer.
- Nothing about coverage across seasons, since there is no season axis to be complete over.

## 5. What I am asking for

1. **Challenge the content-based grain** (§2) — surrogate-hash key instead?
2. **Rule on the seasonless axis shape** (§3a) — and flag the accumulate-vs-replace question to
   David rather than letting me pick.
3. Confirm the JSON encoding contract (§3b) is sufficient, or name what it misses.
4. Anything I have measured wrongly. I have measured nulls, blanks and whitespace separately this
   time; tell me what else I am assuming.

**No code is written. No RED is authored. Nothing is committed.**
