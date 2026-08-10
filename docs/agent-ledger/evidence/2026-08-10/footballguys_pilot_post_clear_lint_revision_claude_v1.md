# Footballguys pilot — post-CLEAR lint revision (disclosed, mechanical)

Date: 2026-08-10 · Lane: Claude Code (implementing) · Layer 1 (ingest), Layer-2 identity dependency

## Why this document exists

Codex's round-8 CLEAR (`6d8bd2b3…`) pinned the cleared artifact set. When David's commit word was
executed, **the repository's own pre-commit gate (`ruff-check`) refused the landing** on the five
cosmetic findings both lanes had disclosed in every round since v5 and Codex had ruled non-blocking
*for clearance* ("No Ruff cleanup required for clearance"; framing v9: "say the word and they go in
the same edit"). **The pre-commit gate is that word.** Bypassing the gate is prohibited without
David's explicit approval, so the findings were fixed instead — a mechanical formatting change with
no semantic content, the class `02` §When-the-cockpit-applies exempts from a review cycle.

Because the generator hashes itself into its census, the fix cascades hashes. **This document
discloses the exact delta rather than landing silently changed bytes over a CLEAR.**

## The change (lint only)

- `E401`/`I001`: the one-line `import csv, hashlib, json, os, re, sys` split and sorted (ruff --fix).
- `E702` ×2: `pid = …; dg, status = …; p = …` split onto three lines.
- `GENERATOR_VERSION` bumped `fbg-identity-census/8` → **`fbg-identity-census/8.1`** so the version
  string still uniquely identifies bytes.
- `CURRENT_FRAMING` now names framing v9 §5 **as amended by this document**.

No predicate, pin, guard, label, or output logic was touched.

## Hash delta — cleared → landed

| Artifact | Cleared (round-8) | Landed (this commit) |
| :-- | :-- | :-- |
| generator (`…_generator_v8.py`) | `06b73ffd…` | `8cbe9618cb72c0b23510806cd930aab52175fcd7c9732f0852680c0c819ec6e6` |
| minimized census (`…_census_claude_v9_minimized.json`) | `1a54fcf4…` / 11,918 B | `778623e04a5ea556a55d233a31305e510bf49417d1ff38ba64982bf2be6bc8dc` / 11,993 B |
| full census (scratch-only expected target) | `35705ae3…` / 272,158 B | `f2e6b0045d60aa38159517744a705e8a011bb88ea1b679c76c65cf5ac9b61117` / 272,160 B |
| framing v9 | `70eb4773…` | **unchanged** — its §5 hash rows for the two artifacts above are superseded by this table |

## Equivalence evidence (measured, not asserted)

- **All seven substantive blocks byte-equal** between the cleared census and the landed census:
  `totals_all_608`, `totals_sf_populated`, `position_guard_evaluation`,
  `wrong_human_top_window_counts`, both ID commitments, all 34 `wrong_human_mappings`.
- Changed keys are exactly: `inputs.generator_sha256`, `inputs.generator_version`, and the
  `expected_full_census_sha256_note` text (which now names this amendment).
- Guard spot-checks re-run on the lint-fixed generator: mutated input REFUSED · `--full`→repo
  REFUSED, no file · pre-existing scratch path REFUSED with contents intact (exclusive create).
- `ruff check` on the generator: **clean**; the pre-commit gate passes.

## Standing

This revision changes no decision state: **horizon FAILED, cohort floor FAILED, ingestion RED
CLOSED, comparison not opened.** The round-8 CLEAR's substantive verdicts stand; Codex is asked to
confirm zero *semantic* divergence in the post-commit audit of this commit.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
