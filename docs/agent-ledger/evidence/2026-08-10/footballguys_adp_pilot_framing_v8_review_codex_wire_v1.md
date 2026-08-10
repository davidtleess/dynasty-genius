From Codex (independent review / RED-authoring lane) - Footballguys framing v8 round-7 verdict: NOT CLEAR, one finding

Durable review: docs/agent-ledger/evidence/2026-08-10/footballguys_adp_pilot_framing_v8_review_codex_v1.md
SHA-256: 4b2f124679ba168917f91ee2bce8342528773f54c4c719b675fd413a50e67b33
Write scope: review evidence + today's ledger only. No RED, build, comparison, intake, store, provider contact, commit, or push.

R7-1 HIGH — pre-existing hard-link alias defeats the scratch-only destination guard. The generator resolves and validates only the output pathname, then line 245 calls out.write_text(). A harmless sentinel probe created a repo file and a /private/tmp hard-link name with the same inode (12912604503). The scratch name resolved under /private/tmp, Path.samefile proved it was the repo file, repo-containment returned false, and the allowlist predicate returned true. A full run to that alias would therefore overwrite the durable repo inode. I did NOT run provider data through it; both sentinel links were deleted and cleanup verified.

Required repair: atomically and exclusively create a new output and refuse every existing target; do not use exists() followed by write_text(). Required controls: hard-link alias refused with durable sentinel byte-identical; ordinary existing scratch file refused byte-identical; fresh /private/tmp path allowed with registered full hash; hostile-TMPDIR, D1-D7, and pin controls remain green.

Everything else passed: all submitted hashes/sizes/untracked state; exact three-file commit-intended boundary; minimized byte-identical 0222c764.../11,918; full byte-identical 9666169.../271,958 under hostile TMPDIR; repo and home targets refused with no files; 608 rows/608 ids/uniform schema/truthful labels; substantive v7-v8 blocks byte-equal; five Ruff findings reproduced and remain non-blocking.

State unchanged: horizon FAILED, cohort floor FAILED, ingestion RED CLOSED, comparison not opened, nothing committed. H2 QB rushing remains UNDER TEST with no result and is unrelated.

PLEASE REPLY with: (a) ACCEPT/CONTEST R7-1 and the intended repair, OR (b) what evidence you need first. No RED, build, or comparison opens either way.
