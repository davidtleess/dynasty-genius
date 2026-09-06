# Companion disclosure — 2026-09-06 (Codex's independent audit of this preparation run)

This file is ADDED beside the run. `preparation_manifest.json`, `identified_weekly.parquet`, the quarantine
files and every hash already bound into the common artifact (`DG-179 runs/20260906T194819Z`) are NOT rewritten.

1. **Stale `.gitignore` hash in `outputs_sha256`.** The manifest declares `.gitignore` =
   `e138ca829d938927384c82d7f176eaa6c61a82bd28ba28320ddd736a505c3b4f`; the file's actual bytes hash to
   `1b8b5fc96cc4a8544a55a24e1dc175ccafb7bbeb69008179b17bbff112b21cf0`, because the ignore list was extended (to keep the
   16 MB `identified_weekly.parquet` and `quarantine.parquet` out of git) AFTER the manifest was written. The
   scientific outputs — `identified_weekly.parquet` (`6f7c76cc…`), `quarantine.parquet` (`a0f4d9c6…`),
   `quarantine.csv` — are unchanged and their declared hashes verify. No blanket "all artifact hashes verify"
   claim is made for this run; the data hashes do.
2. **NaN → Arrow null in three non-scoring columns for 2001–2008.** Writing the identified rows to parquet maps
   pandas NaN to Arrow null in `target_share`, `air_yards_share` and `wopr` for seasons 2001–2008 (columns that
   the source itself leaves empty there). Point, identity, game, season and week records are unchanged; no
   outcome point or current basic feature is affected. Raw files are kept for future feature work.

Codex's audit (recorded in the DG-165 ticket): all 27 raw hashes, all 29 preparation input hashes and the exact
442,697 → 442,167 + 530 (524 zero, 6 exact nonzero) partition verified; REG game-id and row season/week parity
2001–2025 pass.
