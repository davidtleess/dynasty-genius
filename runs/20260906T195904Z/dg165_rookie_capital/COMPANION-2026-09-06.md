# Companion correction — 2026-09-06 16:20 EDT (Codex's independent review of this run)

Added beside the run. `manifest.json` (sha256 `b863c3cf34d87254ec154a39caeec954e3ae804e88fb7e864f7d43e5e19609e5`) and every other file in this directory are unchanged.

**Captured source population vs modelling cohort.** `manifest.cohort.coverage` describes the CAPTURED source
population: 2,238 skill-position draft picks in classes 1999–2026 (2,130 with a gsis_id; 108 resolved or marked
unresolved). The MODELLING cohort actually used, written to `cohort.csv`, is 2,083 rows in classes 2001–2026: the
runner drops classes 1999 and 2000 (155 picks) because the common outcome artifact does not cover their rookie
seasons (`manifest.outcomes.cohort_restriction` names the dropped classes; labels outside 2001–2025 stay unknown,
never zero). The manifest and REPORT.md did not state both populations side by side; this note does, and the
writer now records `cohort.source_population` and `cohort.modelling_cohort` (with the drop count) for future runs.

**Clocks.** `finished_utc` is 20:00:23Z = 16:00 EDT; a ticket line stamped "~16:45 ET" for this run was wrong
(the clock was not checked); corrected in the ticket.

Nothing in this note changes a forecast, a label or an evaluation number; the fit is the one Codex reviewed.
