# CFBD DATA Promotion — G14 Contract Ruling

**Date:** 2026-08-03
**Verdict:** **Claude's contract conflict is sustained; fixture amended.**

Claude proved that the original synthetic manifest omitted `raw_file_count`, so the same fixture
was required to be both valid by the base RED and invalid by the G14 amendment after a no-op
`pop`. That is a RED defect, not an implementation choice.

Codex independently verified:

- the fixture writes exactly one raw payload, `qb_raw.json`, excluding `manifest.json` from the
  content/count contract;
- the live `manifest_latest.json` carries `raw_file_count=1202`;
- its immutable run manifest also carries `raw_file_count=1202`; and
- 1,202 raw JSON payload files exist when `manifest.json` is excluded.

As RED author, Codex added `"raw_file_count": 1` to the base fixture manifest. No assertion or
production file was changed.

Original-RED SHA succession:

1. `12ba82d26ffe32d567e88a1be40f936a567704c42a802fbe572f49ec91f9ea27` — initial RED, superseded by
   the safe-default ruling;
2. `69edd460080c7cd8de2539754f14605635a0fc30e50b3dae602f8b7a40625d06` — safe-default RED, superseded
   because its fixture omitted the field G14 requires;
3. `4c6b5f72fd2445ee0934c8f3d751aae0d80e158b3d32b149802d280aab28c4a7` — **current binding original
   RED** with safe defaults and a correct one-file manifest fixture.

Focused result against Claude's current lenient implementation: **100 collected / 99 passed / 1
failed / 0 errors**. The sole failure is now the intended G14 behavior: removing
`raw_file_count` from both manifests must be fatal. Claude may make presence, latest/immutable
equality, and recomputed equality mandatory without collapsing the base fixture.

The first and second review REDs remain unchanged at `06b4c4a1...` and `0be1bbf8...` respectively.

Real active/candidate data remain unchanged and promotion history remains absent. Nothing was
promoted. H2 QB rushing remains **UNDER TEST** with no result.
