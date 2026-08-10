# Footballguys `adp.csv` pilot framing v9 — Codex round-8 clearance

Date: 2026-08-10  
Layer: Layer 1 ingest framing, with a Layer 2 identity dependency  
Reviewer: Codex, independent review / RED-authoring lane  
Verdict: **CLEAR on framing v9**

This clearance closes R7-1 only. It does not open RED, build, comparison, intake, storage, provider
contact, commit, or push. Horizon and cohort gates remain failed; ingestion RED remains closed.

## Artifact identity

- framing v9: `70eb47738732eb6cb7971ba4e2cadab94e5db56f5eb3f29557f7a814180d8036`
- generator v8: `06b73ffdc2b101e93c5ee260f967958edb6bfabe7d9b6bc1de25de7677d933dc`
- minimized census v9: `1a54fcf44783fdbde907b351f12a4644a1ae2ff09f864c55726d1f4e4f14db77`,
  11,918 bytes
- all three are untracked; the framing names exactly these three as commit-intended and separates
  the full output as scratch-only / never commit-eligible.

## Independent checks

1. **Hard-link refusal:** a repo sentinel and `/private/tmp` alias shared inode `12912604899` and
   hash `baa9878d...`. `--full` to the alias refused at `O_CREAT|O_EXCL`; both names retained the same
   inode and byte-identical hash afterward.
2. **Ordinary-file refusal:** a pre-existing `/private/tmp` file retained hash `221703cf...` after
   the writer refused it.
3. **Fresh minimized output:** regenerated to a new path at exactly `1a54fcf...`, 11,918 bytes, and
   was structurally identical to the submitted minimized census.
4. **Fresh full output:** regenerated to a new path at exactly `35705ae35d0cdcf168a0a011046d5ada510ec873b01ea5e61b7ec586244c6f4e`,
   272,158 bytes. A second run to a different fresh path with hostile `TMPDIR` pointing at the
   repository was byte-identical.
5. **Full shape and labels:** 608 rows, 608 distinct source ids, uniform schema, truthful
   `scratch-only; NOT commit-eligible; NOT committed` status, and the exclusive-create policy in
   metadata.
6. **Provenance:** the minimized census names generator `fbg-identity-census/8` and framing v9 §5;
   the framing register carries the reproduced full hash and fresh-path requirement.
7. **Measurement stability:** both totals, guard evaluation, top-window counts, both ID commitments,
   and all 34 wrong-human mappings are unchanged from v8.
8. **Lint disclosure:** Ruff still reports the same five cosmetic, non-governed-scope findings;
   this remains non-blocking.

The harmless sentinel and hard-link probe files were removed after verification. No provider data
was written through an alias or into a durable location.

## Ruling

**CLEAR on framing v9.** The generator now refuses every pre-existing output name atomically in both
modes and writes a fresh inode through the exclusive descriptor. No round-8 findings.

Standing state remains: **horizon FAILED, cohort floor FAILED, ingestion RED CLOSED, comparison not
opened, nothing committed.** H2 QB rushing remains a registered hypothesis **UNDER TEST** with no
result and is unrelated.
