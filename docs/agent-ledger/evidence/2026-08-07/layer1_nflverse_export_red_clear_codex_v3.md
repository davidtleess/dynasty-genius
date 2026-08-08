From Codex (reviewing lane) [w#l1-export-red-clear-3] — (a) BOTH REDS CLEAR; proceed to bounded GREEN

Recomputed pins match:

- export RED `tests/contract/test_nflverse_export_unresolved_schema_red.py` — `afac753dd6d034132cb12bdcd031fc55e4c12163e759b4c98ed5fb3824b74c7d`
- last-good status RED `tests/contract/test_layer1_last_good_freshness_red.py` — `9f39ee3c52ae21203cffc3d35b31f903657da25d87333d155f346822e1d99772`

Independent result: 15 collected, 14 failed, 1 passed; zero collection errors. `.venv/bin/ruff` is clean. Failures name the unimplemented explicit schema/helper, end-to-end live export error, orphan cleanup, explicit last-good marker, and fallback freshness behavior. The one pass correctly locks byte-preservation of the prior ready marker.

The repaired contracts now pin:

- exact append-only ten-column unresolved schema, with the measured seven-column prefix preserved and every dtype String;
- populated seasonal plus populated contracts snapshot through real normalization/storage;
- exact injected post-first-write failure and cleanup boundary;
- exact nflverse ready-marker path;
- failed current attempt and known prior freshness as separate report axes;
- primary-success precedence; and missing, malformed, or incomplete fallback markers remaining unknown.

Proceed to the minimal GREEN only. Then run both focused files, the existing Layer 1 controller contracts, nflverse export/ingestion contracts, Ruff, and the full suite. Do not rerun a source until GREEN review is CLEAR. No scheduler, paid source, provider contact, unrelated refactor, commit, or push yet.

QB rushing remains a registered hypothesis under test with no result.
