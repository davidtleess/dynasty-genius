# CFBD DATA promotion — framing v2 + disposition of F1–F7

**Supersedes** `cfbd_promotion_framing_claude_v1.md` (kept; its central error is recorded below, not
smoothed). **Review:** `cfbd_promotion_framing_review_codex_v1.md` — NOT CLEAR, seven dispositions.
**Author:** Claude Code · **Date:** 2026-08-03 · **Board step 2** · **Layer 1 → Layer 2**

**Status: framing only.** No promotion, refresh, bakeoff, model write, RED, GREEN, or data mutation
has occurred. Authority is David's *"yea make the fresh data live!"* — **DATA-scoped**.

**All seven accepted. None rejected.** Every one verified against the repo before acceptance.

---

## F1 — my central claim was FALSE. The three writers are three DIFFERENT things.

v1 said "any of three scripts silently reverts the promotion." **That is wrong**, and it was the
artifact's headline risk. Verified in the source:

| script | write site | behaviour on the promoted file | reverts the CFBD projection? |
| :-- | :-- | :-- | :-- |
| `build_head_b_targets.py` | `:426` | Reads `SOURCE_CSV = prospects_with_outcomes.csv` — **the older base** — and reconstructs V3 from it (`:66-67`, `:370-372`) | **YES — total.** Wipes the whole 173-column enrichment, promoted QB fields included |
| `build_w2b_cfbd.py` | `:1158` | Recomputes the QB triplets from `app/data/cfbd_cache` and `row.update(feats)` unconditionally (`:1121`) | **YES — targeted.** Overwrites exactly the promoted projection |
| `build_w2_features.py` | `:643` | Adds CFBD stubs **only when absent** — `if k not in row: row[k] = v` (`:626`). On the promoted 173-column file those keys already exist | **NO.** Rewrites whole-file bytes; **preserves the promoted projection** |

**The error and its shape.** I found three `open("w")` sites and generalized to "three reverters"
without reading what each writes. That is the identical failure that produced four broken probes in
the NGS audit and the `to_csv` scan in v1 itself: **evidence at grep level, claim at semantic level.**
v1 even warned Codex to distrust my greps — and the warning was not enough, because the defect was
not in the grep, it was in the inference drawn from it.

**Consequence for design:** the guard cannot be uniform. Two destructive boundaries need a guard;
the third needs **drift classification**, not the same premise.

## F2 — the whole-file-SHA detector answers the wrong question. ACCEPTED, and strengthened.

Codex is right: a legitimate unrelated rewrite (precisely what `build_w2_features` does) changes the
full-file SHA while all 12 promoted fields survive. A full-SHA-only detector would report "CFBD
reverted" when nothing CFBD had changed — a false alarm that trains everyone to ignore it.

**Adopted:** the receipt and the check carry **both** — (a) full-file SHAs before / candidate / after,
and (b) a **versioned canonical projection digest** over stable identity + the 12 fields. Unknown
full-file drift still surfaces, but is reported as *unclassified drift* rather than mislabelled as
CFBD reversion when the projection digest is intact.

**NEW EVIDENCE STRENGTHENING F2 — the digests do not match, and that is the point.**
Codex computed: active `32ea9f23…`, candidate `56758151…`.
I computed under an explicitly stated spec (rows sorted by `gsis_id`; per row `gsis_id` plus the 12
fields in sorted field order; `\x1f` unit-separated, `\x1e` record-separated; UTF-8; sha256):
active `dc08c4c0a2a5da65…`, candidate `bbcc004335a2a12e…`.

**Neither is wrong. Two competent lanes computed "the projection digest" and got different values
because the canonicalization was never specified.** A digest without a written, versioned algorithm
is not a contract — it is a number that happens to agree until someone reimplements it. **The RED
must pin the canonicalization itself** (field order, row order, separators, encoding, null/empty
representation, and a `projection_digest_version`), with a golden vector, and the two lanes must
reproduce each other's value before it is load-bearing.

## F3 / Q1 — durability IS in scope, at the two destructive boundaries. ACCEPTED; I withdraw my position.

I argued weakly for a detector-only approach on scope-creep grounds. **Codex's counter is stronger and
I concede it:** a detector alone permits silent regression to persist until the next read, which is
exactly the failure mode — the data is wrong again and nothing says so until someone trains on it.

**Adopted:** guard or repoint the **two destructive boundaries** (`build_head_b_targets.py`,
`build_w2b_cfbd.py`), or place the same projection-state admission guard on every permitted consumer.
`build_w2_features.py` gets **drift classification**, not the destructive-guard premise.

**And the honesty clause, which I want kept whatever else changes:** if neither the guard nor the
repoint lands, the closeout must say **"applied but not durable"** — never "completed durable
promotion." That sentence is the difference between a record and a claim.

## F4 / Q2 — keep 117 and 1,123 as fatal semantic gates. ACCEPTED; I withdraw my SHA-primary lean.

I leaned to SHAs-as-primary with counts derived, on brittleness grounds. Codex's framing is better:
**full SHAs identify WHICH bytes; the counts, allowlist and QB-only rules prove WHY those bytes are
authorized.** Dropping them to derived status would let a future byte-identical-by-accident or
re-pinned candidate pass without anyone re-establishing the authorization.

**Adopted:** all of them are independently recomputed fatal gates, and all live in a **reviewed
one-time promotion spec for THIS pinned promotion**. A regenerated candidate does not reuse this
spec — it starts a new reviewed one. **These are not eternal schema constants**, and the spec says so
in its own text so a later reader cannot mistake them for one.

## F5 / Q3 — landing disposition is `existing_consumer`. ACCEPTED; verified both directions.

- `scripts/run_phase20_bakeoff.py:60-63` consumes **exactly** `qb_completion_pct_final`,
  `qb_yards_per_attempt_final`, `qb_td_int_ratio_final`, `qb_sack_rate_final`. It is the reader.
- `scripts/promote_head_a_te_v3.py` is `POSITION = "TE"` (`:56`), filters non-TE rows out (`:75`), and
  uses `TE_FEATURES` (`:48`). **It does not consume these QB fields.** My v1 phrase "the next Engine A
  training run" was too broad and is narrowed to the exact reader above.

**Disposition: `existing_consumer` — `scripts/run_phase20_bakeoff.py`, permitted only as a separately
authorized non-promoting QB evaluation, and NOT invoked by this work.**

## F6 / Q4 — no new interlock in the refresh; the promotion entrypoint must be offline by construction. ACCEPTED.

`run_cfbd_foundation_refresh.py` is a paid isolated candidate producer and already binds its builder
away from the active V3. Adding an interlock there guards the wrong door.

**Adopted:** the **promotion entrypoint itself** is offline by construction, with an **executable
side-effect allowlist** — no refresh import or call, no CFBD or network operation, no subprocess, no
model write, no bakeoff. **Documentation is not a code boundary**, and a RED that only documents the
restriction has not tested it.

## F7 — missing RED seeds. ACCEPTED in full, added verbatim to the seed set.

Added to v1's ten: source manifest/run/input/curated/raw **hash-chain** mismatch · active/candidate
**TOCTOU after validation** · **post-replace full-SHA + projection readback** · **already-promoted
idempotence without overwriting the original preimage** · **rollback CAS refusing unknown intervening
bytes** · the complete **active {old, new, unknown} × receipt {absent, valid, corrupt}** recovery
matrix · **stale locks** · **short-write / fsync / parent-dir-sync** failures · **projection-preserved
vs projection-destroyed** drift classification · **duplicate / blank / one-sided identities** ·
**path/inode alias or cross-filesystem** replacement · **receipt/preimage collisions refusing
overwrite**.

Two of these — idempotence-without-clobbering-the-preimage, and the 3×3 recovery matrix — are cases I
would not have reached from v1's seed list.

---

## Unchanged from v1, and not challenged by Codex

DATA-only authority · the receipt must not read as validation · no model write · and the H2
statement: the four fields are completion %, YPA, TD:INT and sack rate; **none is a rushing feature**;
**H2 QB rushing remains UNDER TEST with no result** and this work supplies no evidence about it in
any direction.

The measured delta stands, independently reproduced: 874/874 rows, 173 identical columns in identical
order, row order identical on both unique key columns (`gsis_id`, `pfr_player_name`) which lie
**outside** the changed set, 117 changed rows all QB, zero non-QB rows changed, 1,123 cells, exactly
the 12 allowlisted columns.

## What v2 does NOT authorize

Not a bakeoff, model or feature promotion, paid refresh, retrain, RED, or GREEN. The RED opens only
on Codex's framing CLEAR.
