# B21 schedules GREEN v5 — behavioral and post-commit CLEAR

Date: 2026-08-09  
Reviewer: Codex, independent review lane  
Layer: Layer 1 retained source integrity and replay

## Verdict

**CLEAR** on commit `529a3e5e64558b0d3a4f01018022707a853a5c4e`.

The canonical vintage reader now fails closed on missing, substituted, metadata-inconsistent,
unsupported-parser and identity-divergent evidence while continuing to read and project the real
retained schedule vintage. No behavioral or post-commit divergence finding remains.

## Exact pins and divergence audit

- RED: `tests/contract/test_b21_schedules_capture_red.py`
  `d4e5287dbdafc2ef5778a34fd4718329c1a5111c146fb828cb4fdf3ae9042b4e`
- GREEN: `src/dynasty_genius/sources/schedules_capture.py`
  `0c47885efe950b01b810964c7f58a1c0305d006aec3f2e8263398c2f768f3a18`
- Both submitted hashes were recomputed from the working tree and independently from the committed
  blobs. All four measurements agree.
- `HEAD == origin/main == 529a3e5e64558b0d3a4f01018022707a853a5c4e` at review time.
- Commit scope is exactly the RED and GREEN files: 244 insertions, 3 deletions.
- Parked unrelated working-tree paths were preserved; neither cleared file diverges after commit.

## Independent behavioral checks

- Focused contract: **84 passed**, exit 0.
- Four backup suites: **55 passed**, exit 0.
- Ruff on both changed files and on `src app`: clean.
- Commit diff check: clean.
- Exact-SHA GitHub Actions run `31344158000`: terminal **success**.
  - Frontend checks: success.
  - Python checks: success, including Ruff, compile, governance validation, pytest and storage
    policy verification.

## Production-vintage verification

The committed canonical store was read through the new strict path without mutation:

- vintage `v-eeea1f47644cc498`;
- 7,548 rows × 46 columns;
- raw SHA-256 `eeea1f47644cc498676be92b5ac0fb853fd4bce238348f0436aa786c1440d5c1`;
- schema SHA-256 `9bbd6413bc4c498d190db8502a9b6dd7dd326c2feffa6b7208e1ef99d6b4c6a5`;
- 2026 week 1 projection: 16 games.

`replay(check_id)` returned all 7,548 rows with the same raw SHA while vintage count, check count and
the marker bytes remained unchanged. A preliminary probe called `record_offering()` instead of
`replay()` and therefore created the expected accounting event in a temporary copy; that was a
review-harness distinction, not a product defect, and no canonical data was modified.

## Implementation review

The fail-closed order is coherent and matches the cleared contract:

1. requested ID equals stored `vintage_id`, and the ID derives from `raw_sha256`;
2. parser version is supported before interpretation;
3. retained content exists;
4. stored byte count and full SHA independently agree;
5. row count, column count, ordered dtype pairs and schema hash agree with a fresh parse.

Normalizing each stored dtype pair to a list is appropriate: JSON persistence represents pairs as
lists, and tuple/list container spelling carries no source-schema semantic difference. Element
values and ordering remain strictly compared.

No provider call, canonical-data write, config change, additional commit or push was performed by
this review.
