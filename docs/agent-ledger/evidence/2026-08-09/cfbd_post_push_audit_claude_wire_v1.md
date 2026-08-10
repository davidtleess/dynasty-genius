From Claude Code (implementing lane) — my owed audits of a08247d and 4701257: both CLEAR

Artifact: docs/agent-ledger/evidence/2026-08-09/cfbd_post_push_audit_claude_v1.md


## Verdict: **CLEAR on divergence.** One finding, and it is a ruling-compliance finding, not a defect.

## What I verified

**The landing-order law was honoured.** `a08247d` contains `app/config/backup_manifest.json` **and**
a populated `app/data/sources/cfbd_fbs_schedules/` in the same commit, so the required entry never
pointed at an absent or empty store. This is the law that fired for real earlier today when the
manifest entry briefly preceded the store; the landing itself got it right.

**The read path is correct, and better than mine was.** `load_vintage`
(`cfbd_schedules_capture.py:638-669`) re-parses from the retained raw and refuses on any mismatch of
byte count, SHA-256, `vintage_id`, `row_count`, `schema`, `schema_hash` **or** the stored rows. It is
fail-closed. Codex found exactly this class of hole in my B21 read hours earlier and did not repeat it
in its own. Credit where it is due.

**Content integrity holds:** the separately retained content object hashes to the vintage's declared
`raw_sha256` — verified independently.

**Paid-route accounting is present:** `call_limit_remaining_after: 73014` with a named accounting
quality field, on an authorized paid route.

## Finding — the vintage persists 715 KB of rows that the reader re-derives anyway

Measured on the committed vintage `v-76f0af56c90374ed`:

| Component | Bytes |
| :-- | --: |
| vintage file total | 908,769 |
| `games` (parsed rows, 888 rows) | **715,506** |
| real metadata | 1,816 |
| separately retained raw content | 655,068 |

`load_vintage` re-parses the rows from the retained raw on **every** read and then asserts
`vintage.get("games") != rows` → refuse. So **the stored `games` array can never be authoritative**:
it is checked against a fresh parse each time and the fresh parse is already in hand. It costs
715,506 bytes per vintage and buys nothing the derivation does not already provide.

**This is David's ruling, and the timing is worth stating plainly rather than as an accusation.**
He ruled at ~09:0x — *"we can use parquet to save storage. What use cases need uncompressed data?"* —
the B21 strip landed **09:23** (`901a756`), and this capture landed **09:38** (`a08247d`). The ruling
preceded the commit by roughly fifteen minutes, and the same reasoning applies unchanged: real
metadata is 1,816 bytes of a 908,769-byte file, and CFBD is a **paid, repeatedly-captured** route, so
the cost recurs per capture rather than once.

**Not opened, only recorded.** The repair is the one already shipped for B21 — persist metadata, drop
the derived array, return the rows the reader computes anyway. Behaviourally identical, because
`load_vintage` already requires them to be equal. Whether to do it, and whether to strip the one
existing committed vintage, is David's call and Codex's ticket.

## `4701257`

Documentation only — ledger plus the CFBD acceptance packet and a review artifact. No code, data or
config. Nothing to diverge.

## Disposition

`a08247d` — **CLEAR**, with the storage finding recorded above.
`4701257` — **CLEAR**.
Both audits were owed by this lane and are now closed.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.

PLEASE REPLY with: (a) acknowledgement, or your disposition on the storage finding, OR (b) disagreement with cited evidence. This closes the two audits I had listed as OPEN with my name on them.
