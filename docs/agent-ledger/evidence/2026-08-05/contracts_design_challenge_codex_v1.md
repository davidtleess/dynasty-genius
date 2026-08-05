# Contracts stream design challenge — Codex v1

Date: 2026-08-05

Reviewed artifact: `contracts_design_note_claude_v1.md`

Disposition: **DESIGN NOT CLEAR FOR RED**. The measurement-first/routing approach is accepted, but
the design needs one product ruling and several contract corrections before a RED can pin the right
mechanism.

## Independent data-quality profile

Codex independently reloaded the live source and reproduced **51,808 rows / 25 columns**.

| Check | Independent result |
| :-- | :-- |
| Exact duplicate accounting | 48,492 unique rows; **3,316 excess copies** across 2,503 groups; 5,819 rows participate; max multiplicity 9 |
| Proposed nine-column key | 48,492 / 48,492 unique after exact collapse; 25 rows have null `years` |
| `year_signed=0` | **1,106 rows** |
| `is_active` | 48,860 false / 2,948 true / 0 null |
| Scalar and nested non-finite values | zero |
| `cols` | 45,875 non-null lists; every list has ascending unique numeric years followed by exactly one final `Total` row |
| Canonical JSON positive control | strict JSON round-trips the full row and preserves list order |

The note's statement at lines 26-27 that nulls occur only on tabled columns is false. The complete
null census is: `years=25`, `gsis_id=4,219`, `date_of_birth=14,343`, `height=1,880`,
`weight=1,901`, `college=1,319`, `draft_year=903`, `draft_round=29,658`,
`draft_overall=29,703`, `draft_team=1,634`, and `cols=5,933`. There are still zero
whitespace-only strings; the whitespace measurement itself is accepted.

## Required design decisions

### 1. Grain: use an explicit full-content SHA-256, not the nine-column quasi-key

The nine-column key is measured-unique today, but it includes mutable measures (`value`, `apy`,
`guaranteed`, `is_active`) and omits other content. It is neither a stable business identity nor
actually “every column that distinguishes a row.” Adding fields until a key happens to become
unique disguises a content identity as a domain key.

Use `content_sha256` over the canonical normalized values of **every declared source column**,
including canonical `cols` JSON and excluding derived identity/capture metadata. Preserve all
business columns visibly; the digest is opaque only as a key, not as evidence. Exact duplicate
collapse occurs on the same canonical source content. Detect the theoretical hash-collision case
by refusing if one digest maps to unequal canonical payloads.

If snapshots accumulate, the observation row key is `(snapshot_id, content_sha256)`. Identical
content in two snapshots is two observations and must survive twice.

### 2. Seasonless mechanism: declare an axis, not a Boolean exception

Prefer a fail-closed `capture_axis`/partition enum such as `season` versus `snapshot`, rather than
`seasonless: bool`. Snapshot semantics are not merely “do not pass a parameter”; they change fetch
cardinality, partition identity, store application, result/status vocabulary, raw naming,
unresolved-identity context, and export grain.

For `snapshot`:

- fetch the loader exactly once per run with no `seasons` argument, regardless of the seasonal
  list used for other specs;
- write exactly one raw snapshot/hash and one coverage result;
- use a `snapshot_id` plus `observed_at`, never a synthetic season or `year_signed`;
- record observation time at the actual fetch boundary, not the overall run start; it is our
  retrieval time and **not** a provider effective date;
- make mixed seasonal+snapshot runs, snapshot-only runs, failure markers, totals, and
  unresolved-identity export fail-closed and explicitly tested;
- keep existing seasonal streams byte/behavior compatible.

### 3. Accumulate versus replace requires David's ruling before RED

The proposal at lines 73-74 to replace now and enable accumulation later “without a migration” is
not correct. Replacement loses the historical parsed rows immediately; recording only the latest
vintage does not recover them. Switching later changes the table key, apply/delete behavior,
capture history, and export grain—a migration—and cannot restore snapshots already discarded.

Codex recommendation: **accumulate from the first capture**, keyed by
`(snapshot_id, content_sha256)`, because the source changed by five rows during this session and
the batch is building a compounding Layer-1 substrate. David must rule before the RED. The revised
design must also state capture cadence and retention so the storage cost is explicit.

### 4. Canonical JSON is acceptable only as a strict, measured contract

Use JSON, not a child table, for this substrate-only landing. The contract must specify:

- sorted object keys, stable compact separators, UTF-8, and `allow_nan=False`;
- **no** `default=str` or other fallback coercion;
- preserve list order exactly—do not sort the list;
- null `cols` stays SQL null, not JSON `null` text;
- pin the 13 nested field names/types;
- parse back and deep-compare values, numeric/null types, and order;
- test the measured list invariant: ascending unique year entries followed by exactly one `Total`.

The final invariant matters: all 45,875 non-null lists contain `Total`, so treating every nested
`year` as numeric or sorting the list by an assumed numeric key would fail or corrupt every record.

## Other required contract corrections

- Pin the full 25-column schema and emitted types. At minimum: six scalar integers
  (`year_signed`, `years`, `otc_id`, `draft_year`, `draft_round`, `draft_overall`), seven floats,
  one Boolean, and one canonical-JSON column. Otherwise SQLite will publish usable numeric contract
  values as strings.
- Preserve `year_signed=0` on all 1,106 rows as the observed source value. Do not silently null,
  reject, or reinterpret it as a capture/contract year without source evidence explaining its
  meaning.
- Identity is applicable via `gsis_id`; its 4,219 null rows must remain and reconcile as `unknown`,
  never be excluded. `otc_id` is source attribution, not a governed player-identity kind.
- Name duplicate accounting precisely: 3,316 is the number of **excess copies collapsed**, not the
  number of all rows participating in duplicate groups.

## Minimum RED before GREEN

The revised design should seed falsifiers for one loader call in a mixed multi-season run; no
season argument; actual fetch-time observation labeling; snapshot accumulation or replacement per
David's ruling; unchanged-snapshot behavior; changed-snapshot behavior; failed snapshot with
last-good preservation; content-hash sensitivity to `cols` only; strict JSON refusal/no fallback;
all nested order/type round-trips; exact duplicate reconciliation; `year_signed=0`; every emitted
dtype; nullable identity accounting; and non-regression of all existing seasonal streams.
