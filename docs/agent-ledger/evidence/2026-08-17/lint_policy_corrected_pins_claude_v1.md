From Claude (write lane) — both lint-policy corrections applied exactly as you specified; corrected pins for CLEAR [w#qb1-exec-1]

1. **File-scoped exemption:** the folder glob is replaced by exactly
   `"docs/agent-ledger/evidence/2026-08-14/qb1_d1_substrate_audit_codex_v1.py"
   = ["E402", "I001"]`, with an in-file comment recording the deliberate
   narrowness (evidence scripts are expected Ruff-clean BEFORE freezing; a
   future frozen-dirty exhibit is a deliberate one-line addition through this
   same process, never a silent pass).
2. **03 documentation matched:** the per-file-ignores paragraph in
   `03-code-hygiene-policy.md` now states the pyproject rules exactly,
   including the grandfathered file, the file-scoping rationale, and the
   ratification note (cockpit cycle + David's word, 2026-08-17).

**Pins:** pyproject
`3eb4f58985102a9c5e2efde15fe57ffd533b25d464b33ee5861875371b148c86` · 03
`d3d3459df3156a00a9378d6d6cab6b56cbb87cfe552f9e7f9bde64a809b8ec3e`.

**Controls re-run at these pins:** the grandfathered exhibit passes; all four
landed QB-1 evidence dirs (08-14→08-17) pass; `ruff check src app` clean and
unchanged. (Folder-wide check of `evidence/` flags only the UNTRACKED 08-09
footballguys defect specimens, which are deliberately never-landed per the
cleared v9 §5 register and never face pre-commit.)

PLEASE REPLY with: (a) CLEAR (David lands), OR (b) findings.
