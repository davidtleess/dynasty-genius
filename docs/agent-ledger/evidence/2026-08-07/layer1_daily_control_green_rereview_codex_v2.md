# Layer 1 daily-control GREEN rereview — Codex v2

Date: 2026-08-07 ET  
Layer: Layer 1  
GREEN reviewed: `src/dynasty_genius/sources/daily_control.py`  
GREEN SHA-256: `e47a34c2aeb7bad69f1b852ff1ae6a8225396bc8773dc9d554e19706a43ea3c7`  
CLI SHA-256: `652673b74d5584045479f6fd91798baa29db3960119cd9eb669b0a09cb1be99e`  
Tests SHA-256: `cdf3bb0921e2d4c4898e3211e6a12fc5265fbf2dab78b2937396bf850299db08`

The 54 focused tests and Ruff pass. G3 and G4 are repaired. G1 and G2 have four exact residuals.

## R1 — freshness still uses marker mtime, not the semantic success time

An `ok` marker whose `finished_at` is `2020-01-01` but whose file was touched now returns
`last_success_at=2020-01-01` and `freshness=current`. Those answers contradict each other. Compute
age/freshness from the parsed semantic completion timestamp when available; use mtime only as an
explicit fallback when no supported semantic timestamp exists. CFBD's real marker uses
`captured_at`, which is missing from `_COMPLETION_KEYS` and currently falls back to mtime despite the
review requirement naming `captured_at` explicitly.

## R2 — manual sources bypass marker-status semantics

A complete manual entry with a freshly written `{"status":"failed"}` marker returns
`state=manual_current`, `freshness=current`, and a non-null last success because `_manual_result`
still calls `_mtime_iso`/`_age_days` directly. Reuse the same parsed marker-success logic for manual
entries; only fall back to destination mtime when the source has no marker at all.

## R3 — scheduler evidence is not verified by preflight

An automatic entry with a real command and `scheduler_evidence=/definitely/missing.plist` returns
`EntryStatus(ok=True)`. G1 required scheduler paths to be verified. Report
`scheduler_evidence_not_found:<path>` without consulting installed host state.

## R4 — CLI preflight returns success for broken automatic routes

`_print_preflight(PreflightReport(entries=(EntryStatus(source="owned", ok=False,
missing=("command_not_found:x",)),)))` prints the defect and returns 0. Expected manual-route gaps
must remain informational, but a broken automatic/controller-owned route must make `--preflight`
nonzero so a scheduler or operator cannot treat a non-runnable controller as ready. Carry mode or a
blocking flag into the preflight status so this distinction is explicit rather than inferred from
source names.

No provider contact, paid call, subscriber-data access, live source execution, scheduler
installation, commit, or push occurred. QB rushing remains a registered hypothesis under test with
no result.
