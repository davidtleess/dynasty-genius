From Codex (reviewing lane) — GREEN CLEAR: nflverse export repair + last-good freshness

Layer: Layer 1 ingestion.

Final reviewed pins:

- `src/dynasty_genius/nflverse_usage.py`
  `5ee7cbb54c2682ef00e6885df5e4ff41acb8030deddf69a9e2c33748400af6c0`
- `src/dynasty_genius/sources/daily_control.py`
  `7a09c8131434b288916adb1d98e6f41eb33be3c126b72efd167bf36d2c1e6e26`
- export contract `a5c72b1412fcadbfa794ff4dfdf557358762446a9ad789d37e7b1925099bd092`
- last-good contract `77dd25a65f18c0e8d9769fe27c882b4f5f789479dda488762b777f1114a9d05e`
- existing controller contract `4fee6873360460015418509a5bdbe27ddee5aa84367c901b6576b4a87293a53a`
- controller CLI `1abc14da688337e174f4d21ea9aff31a3bd5586b86b93bdd9ff6d6cfde3d4a4a`

## Checks performed

- Reproduced **84 focused passes** across the export, last-good, and controller contracts.
- Ruff is clean on the changed production and contract files; `git diff --check` is clean.
- Accepted the unmasked full gate: pytest itself returned **exit 0**, with **4,773 passed, 12
  skipped, 9 xfailed, zero failures**. The result is corroborated by the terminal completion and
  `/private/tmp/.fs2.txt`; it is not a downstream pipeline exit.
- The exact append-only ten-column all-String unresolved schema is enforced for empty and populated
  runs. The populated path uses real production normalization and includes contracts rows carrying a
  non-null snapshot id after hundreds of seasonal nulls.
- A failed publish leaves the prior ready marker byte-identical. A partial directory created by the
  call is removed; cleanup failure is surfaced as `nflverse_export_cleanup_failed` and retains the
  original export exception as its cause. Pre-existing immutable run directories remain protected.
- Current-attempt outcome and last-good freshness remain separate. Valid primary success wins;
  invalid primary time may fall through to a valid explicit last-good marker; invalid evidence on
  both paths yields `last_success_at=null`, no age, and `freshness=unknown` in the written report.
  An absent primary completion key retains the approved successful-marker mtime fallback.
- The post-CLEAR status-test fixture change from nonexistent macOS `/bin/true` to `/usr/bin/true`
  was reviewed and is included in the final contract pin above.
- Frozen unrelated paths remain byte-identical at `b3247ec8...` / `fd924eb1...`.

GREEN CLEAR. David directly authorized one live controller run after this CLEAR. The corrected
command may execute exactly `nflverse_usage_capture` and `sleeper_transactions`; no paid source,
scheduler installation, provider outreach, subscriber-data access, commit, or push is implied by
this verdict. Report the controller's own exit code and verify the ready marker, manifest, contracts
Parquet, and unresolved schema before landing.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result.
