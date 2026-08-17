From Claude (write lane) — FBG-CAP-F1 remediation delta: contract-only, 665/665 green; ONE edit beyond your named scope, routed before commit as instructed [w#fbg-cap-1]

Artifact: tests/contract/test_footballguys_phase_a_red.py, worktree SHA-256 36de40c39eaec52a772d975ba98c61f0a4276c851d8c27da486342610a833789, diff 1 file +13/−13. No other file touched; the capture and stores untouched; no re-fire.

Edit 1 (your named remediation): MANIFEST_REQUIREMENTS objects row ("directory", False) → ("directory", True); adjacent comment rewritten to post-capture truth citing receipt 77984aaf… and the landing-order obligation fulfilled.

Edit 2 (DELTA beyond your named scope — the necessary mirror): after Edit 1 alone, the suite failed 664/1 at test_s23_precapture_optional_objects_row_refuses_raw_publication, because _write_manifest treats MANIFEST_REQUIREMENTS as repository truth and force-flipped objects→required only for post_capture_epoch=True fixtures. With repository truth now True, the S23 pre-capture negative got a required row and the refusal never fired. The inversion: the override now forces objects→optional when post_capture_epoch=False (comment updated to match). The S23 scenario semantics are unchanged — an optional objects row must still refuse raw publication.

Proof: exact 665-test set (phase_a_red + backup anti-rot) = 665 passed; Ruff clean on the file.

CI consequence, disclosed: the pushed head d39ff34 carries the manifest flip WITHOUT this test amendment — run 32073785133 will fail at test_p0_option1_manifest_covers_every_durable_store[objects]. My miss: I prepared the flip change set without running the Phase A contract suite against it (the clean-tree-CI lesson, again). The fix is this delta; it awaits your CLEAR then David's commit+push.

PLEASE REPLY with: (a) CLEAR on the two-edit delta (checks enumerated), OR (b) findings. [w#fbg-cap-1]
