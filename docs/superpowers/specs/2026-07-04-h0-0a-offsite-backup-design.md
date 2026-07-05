# H0-0a — Offsite Backup of Irreplaceable Data (Design)

**Date:** 2026-07-04 · **Author:** Claude (implementation lead) · **Status:** v2 — integrates Codex review findings 1–8 (all accepted); cockpit re-review pending. David ratified the destination (Google Cloud Storage) 2026-07-04; gcloud CLI 575.0.0 installed same day (brew cask, David-approved).
**Board item:** Horizon 0, item 0a (`docs/product-assessment-2026-07-04.md`, finding F1).
**Problem:** the PIT capture stores, training data, and model artifacts are gitignored and exist only on this laptop. DEBT-6 detects gaps; nothing prevents loss. A dead disk erases the Dec-2026 edge-evidence base permanently.

## 1. Scope (small slice; protection, not platform)

**In:** a manifest-driven backup script + daily LaunchAgent that snapshots the irreplaceable set into an immutable per-run GCS prefix, verifies the upload against a hash inventory, and writes a local machine-readable last-success marker.
**Out (named follow-ups, David-gated):** surfacing backup health in `GET /api/system/capture-health` (natural Slice 2 — the "what should David SEE" seam); restore-drill automation beyond the first-run proof; off-laptop capture migration (the standing DEBT-6 deferral).

## 2. What is backed up (concrete enumerated manifest — no wildcards) [Codex F2]

The manifest is a committed JSON config listing **concrete repo-relative paths** (files, or explicitly-enumerated directories whose expansion is inventoried per-run):

| Set | Manifest entries | Why irreplaceable |
|---|---|---|
| PIT capture stores | `app/data/fc_forward_capture.db`, `app/data/model_forward_capture.db`, `app/data/fc_snapshots.db` (required) | Point-in-time market/model series — unreconstructable; the Dec-2026 edge test's evidence |
| Model artifacts | The exact artifact + pointer paths already enumerated in `app/config/model_registry.json` (the DEBT-6 provenance registry is the source of truth; the manifest references it by rule, and the run inventory lists every resolved file with its sha256) | Serving truth; hashes are registered but bytes live only here |
| Training data | The concrete training CSV paths enumerated at RED time from the real training roots (e.g. `app/data/training/engine_b_features_v2.csv`; full list fixed in the committed manifest, not globbed) | Reconstruction = weeks of re-scraping; some sources drifted |
| Runtime valuation artifacts | The enumerated `*_latest` runtime JSONs consumed by routes | Cheap; makes a bare-metal restore same-day |

Rules:
- **Path safety [Codex F7]:** every manifest path must be repo-relative, resolve inside the approved roots (`app/data`, `app/config`), contain no `..`/absolute components, and must not traverse a symlink escaping the repo. Violations fail the run before any copy.
- **Required-path absence fails loudly:** marker `status=failed`, non-zero exit — absence is never silently skipped.
- **Unknown-file policy:** directory entries produce a per-run file inventory (path, bytes, sha256) recorded in the run manifest; files appearing/disappearing between runs are visible by inventory diff, never silently absorbed.
- **Marker/staging/log exclusion [Codex F5]:** the status marker, staging dir, and logs live under `app/data/ops/` and are **hard-excluded** — backup status is never part of the protected payload.

## 3. Mechanism

- **SQLite safety:** live DBs are snapshotted via `sqlite3 <db> ".backup <staging>"` (consistent even mid-write), never raw `cp`.
- **Non-DB stability gate [Codex F3]:** each non-DB file's (size, sha256) is sampled twice across a short interval; unstable files trigger bounded retry-with-backoff, then loud failure. No mid-write JSON/CSV/pkl is ever uploaded.
- **Immutable run prefixes — NO deletes [Codex F1]:** each run uploads staging → `gs://<bucket>/dynasty-genius/runs/<started_at_utc>/`. The script issues **no delete or overwrite-mirror operations of any kind** in H0 (`--delete-unmatched-destination-objects` is banned). A small `gs://<bucket>/dynasty-genius/latest.json` pointer object is written **only after** upload verification passes (§5).
- **Retention [Codex F1/F8]:** GCS lifecycle rules (bucket config, not script logic) expire `runs/` prefixes older than 14 days; the first **verified** run of each month is copied by the script to `archive/YYYY-MM/` **from its own immutable run prefix** (never from a mutable mirror) and lifecycle-retained 1 year. ~700MB/run → ≈10GB steady state ≈ $0.20/month.
- **Schedule:** daily LaunchAgent at **10:15** (`RunAtLoad=false`, matching the five existing plists). The stability gate — not the clock — is the correctness mechanism: if the 10:00 weekly outcome-scoring job (Tuesdays in-season) is still writing, the gate defers/retries and, on exhaustion, fails loudly rather than uploading torn files. [Codex F3 / open-question 3]
- **Marker:** on every terminal state the script writes gitignored `app/data/ops/backup_status_latest.json` — `{status, started_at, finished_at, run_prefix, files, bytes, sha256_verified, failures[]}` — the seam a later capture-health slice can surface. Marker-write failure itself exits non-zero.
- **Auth [Codex F4]:** gcloud CLI **user credentials** from David's one-time interactive `gcloud auth login` (no ADC, no service-account key files). The script preflights **non-interactively** (`gcloud auth print-access-token` under `CLOUDSDK_CORE_DISABLE_PROMPTS=1`); a missing/expired credential fails the run loudly with marker `status=failed`, reason `auth_unavailable` — it never hangs a LaunchAgent on an interactive prompt.

## 4. Falsification seeds (for the RED)

1. Required manifest path absent → loud failure, marker `status=failed`, non-zero exit.
2. SQLite mid-write → `.backup` snapshot is consistent; never a torn copy.
3. Non-DB file unstable across the stability-gate samples → bounded retry then loud failure; no torn upload.
4. `gcloud` absent / unauthenticated / bucket unreachable → marker `status=failed` with reason; non-zero exit; `latest.json` pointer NOT updated.
5. Manifest malformed / unknown keys → fail closed before any copy.
6. **Path safety:** absolute path, `..` traversal, or repo-escaping symlink in the manifest → fail closed before any copy. [Codex F7]
7. Upload verification mismatch (count/bytes/sha256 vs staging inventory) → run marked failed; pointer not updated. [Codex F6]
8. Marker write failure → non-zero exit (the health seam must never show a stale success).
9. Staging cleanup on success AND failure (no unbounded local growth).
10. No banned-language tokens in marker/log strings (the marker may later surface in a diagnostic panel — cordon).
11. The script constructs **zero** delete/mirror mutations against the bucket (assert the command surface). [Codex F1]

## 5. Verification [Codex F6]

RED (Codex): unit-level over the script with a fake `gcloud` runner + temp dirs (no network; committed tests depend on no gitignored artifact). GREEN (Claude): implement; then a **David-witnessed live first run**: `gcloud auth login` → bucket create (versioning ON + lifecycle rules) → first backup → evidence bundle shown to David: `gcloud storage ls` of the run prefix, **file count + total bytes + per-file sha256 verification against the staging inventory (all files)**, restore of one DB to a temp path with `PRAGMA integrity_check`, **and restore of one non-DB file with sha256 match**. LaunchAgent load is a separate David-gated step (matching prior plist go-lives).

## 6. Review log

- v1 → v2 (2026-07-04): Codex findings 1–8 all accepted — immutable run prefixes + no-delete contract (F1), wildcard removed / registry-derived enumeration + inventory (F2), non-DB stability gate (F3), user-credential auth + non-interactive preflight (F4), marker under `app/data/ops/` + hard exclusion (F5), full-inventory verification + non-DB restore proof (F6), path-safety seeds (F7), archive sourced from the verified run prefix (F8). Open questions 1–3 resolved in-text (deletes forbidden; ops subdir; 10:15 + stability gate).
