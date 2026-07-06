# 02 Amendment Proposal — Offsite Backup as Standing Workflow Law

**Status:** DRAFT v1 — awaiting cockpit adversarial review (Codex technical + Gemini advisory), then David ratification. No edit to `02-agent-operating-loop.md` until David's word.
**Authorization basis:** David, 2026-07-06 (session-close addendum, ledger + AGENT_SYNC ★★ block): "the storage in gcp must become part of our standard workflow" — the queued David-gated 02 standing-infra amendment ticket is GO for drafting.
**Author:** Claude (implementation lead).

## 1. What changes

`docs/governance/02-agent-operating-loop.md` gains a new section, **"Standing Infrastructure: Offsite Backup Workflow"**, placed after "Sprint-closeout tollgate" and before "Postflight: Session End". The backup is elevated from a scheduled job (H0-0a, PR #122) to binding workflow law that every agent must honor.

## 2. Proposed section text (the amendment payload)

> ## Standing Infrastructure: Offsite Backup Workflow
>
> The offsite backup of irreplaceable data is standing workflow law, not an optional job. The single-laptop copy of the PIT capture stores, model artifacts, and operational SQLite databases is a known single point of failure; the daily GCS backup is the product's disaster floor.
>
> **The mechanism (facts, not aspiration).** `scripts/backup_irreplaceable_data.py` runs daily via LaunchAgent `com.davidleess.dynasty-backup-irreplaceable` (10:15 local). Each run uploads one immutable prefix under `gs://dynasty-genius-backup-dtl/dynasty-genius/runs/<run_id>/` and constructs NO delete or mirror mutations. The `latest.json` pointer advances only after the daily restore drill passes: list parity, then download of every object with sha256 comparison against the staging inventory. `sha256_verified` is earned, never implied. Every terminal state writes `app/data/ops/backup_status_latest.json`.
>
> **Rulings:**
>
> 1. **No-delete clause.** No agent may construct, propose-and-run, or schedule any delete, overwrite, rotation, or lifecycle mutation against protected payload objects or any run/archive prefix in the backup bucket. **Explicit carve-out:** the verified `dynasty-genius/latest.json` pointer update — which the shipped mechanism performs only AFTER the restore drill passes — is the one sanctioned overwrite. Retention and pruning are David-gated per action, with an exact-prefix manifest presented before any approval. Bucket-level changes (lifecycle rules, IAM, location, naming) are David-only decisions.
> 2. **Manifest coverage law.** Any change that introduces a new irreplaceable store — a gitignored database, CSV, pickle, or capture artifact under `app/data/` or `app/config/` that cannot be regenerated from the repo plus public sources — MUST add the store to `app/config/backup_manifest.json` in the same change set. Enforcement is layered honestly: the anti-rot contract test (`tests/contract/test_backup_manifest_anti_rot_red.py`) mechanically enforces only its current scope (present `app/data/*.db` files plus registry-referenced paths); the BROADER law — arbitrary new CSV/pickle/capture artifacts — is enforced by reviewers at review time until a future RED extends the scan to the governed gitignored artifact classes (named follow-up). Reviewers treat an uncovered new irreplaceable store as a defect, not a follow-up.
> 3. **Silence is not success.** A missed or failed run must surface, never pass silently: the status marker (with a named fail-closed reason) is the truth surface. **By law, effective immediately:** marker absence, or a marker older than **26 hours past the last scheduled 10:15 local run (one interval plus a sleep/timezone grace)**, is a degraded state. Automated surfacing of that state is PENDING the named follow-up (backup health wired into `GET /api/system/capture-health`) — the law binds now; the automation lands with the ticket.
> 4. **Backups are not bootstrap pre-work.** Agents do not run manual backups, restore drills, or bucket inspections as session pre-work. Manual runs are David-gated. Reading the local status marker is always allowed.
> 5. **Restore-drill integrity.** The restore drill is part of the backup's definition. Any change that weakens verification (sampling instead of full download+hash, pointer advance before verification) is a contract change requiring the full cockpit cycle plus David's ratification.

## 3. Why (rationale for reviewers)

- **Compounding-product lens:** the PIT capture stores are the compounding asset; losing them resets the Gate-4 clock permanently (~Dec 2026 accrual). The backup is what makes "capture-and-accumulate" durable.
- **Fail-closed symmetry:** the repo's discipline (fail-closed loaders, honest degradation) currently stops at the laptop's edge. This amendment extends it to the disaster boundary.
- **Anti-rot:** H0 shipped a 32-entry manifest; without coverage law, every new store added after H0 silently erodes backup completeness. The anti-rot test already exists — this makes honoring it workflow law rather than test trivia.

## 4. Falsification seeds for the cockpit round

1. New capture store added under `app/data/` without a manifest entry — layered check: a new `.db` file must fail the anti-rot test mechanically (in-scope); a new CSV/pickle must be caught by reviewer law (out of mechanical scope until the follow-up RED) — the seed verifies BOTH layers behave as rule 2 states.
2. LaunchAgent silently unloaded (laptop migration, OS update) — which rule surfaces the miss, and how fast? (Rule 3: marker staleness; verify the capture-health ticket covers marker age.)
3. An agent asked to "clean up old backups to save cost" — does rule 1 unambiguously block unilateral action and force the David-gated exact-prefix path?
4. Restore drill weakened to sampling for speed — does rule 5 force a cockpit cycle?
5. Marker path itself accidentally added to the protected payload (recursion) — script already hard-excludes it; does the amendment text stay consistent with that?
6. Bucket renamed/migrated — is it unambiguous that this is David-only (rule 1 last sentence)?

## 5. Out of scope

- No change to the backup script, manifest, or LaunchAgent (all shipped and live).
- No new enforcement surface in this amendment (the capture-health wiring is its own named ticket).
- No change to 00/01/03/04.
