# Retired launchd agents — DO NOT DELETE THIS DIRECTORY UNTIL AFTER THE FREEZE LIFTS

**SR-09 step 7d, verbatim requirement:** do not delete `ops/launchd/retired/` until after the
2026-09-04 freeze lifts (season end is the safe read). These four plists are the ONLY working
copies of the retired schedule definitions — six of the twelve installed agents were copies, not
symlinks, so `~/Library/LaunchAgents` holds no recoverable original either. Deleting this
directory turns a five-minute rollback into git archaeology during a freeze.

**What retired here (2026-08-26, byte-identical):**
`fc-snapshot` (09:00) · `feature-refresh` (09:15) · `league-capture` (09:20) ·
`what-changed-report` (09:45) — their slots now live in
`ops/launchd/com.davidleess.dynasty-daily-chain.plist`, one dependency-ordered fail-soft job.

**What did NOT retire (b-EXCEPTION, David 2026-08-20: "put it back up"):**
`market-divergence-refresh` and `model-pvo-refresh` stay ACTIVE as retry-only jobs — their 09:40
and 09:30 entries were stripped, SR-00's 11:30/14:00 retries kept. SR-09 cannot close until a
live 11:30 retry is observed firing AFTER the chain landed.

**Pre-change evidence:** `PRE-SR09-launchctl.txt` (all 13 agents loaded, exit 0, captured
2026-08-26 ~14:00) and `PRE-SR09-schedules.json` (every plist's label/slots/argv).

**ROLLBACK (minutes, no history spelunking):**
1. `git mv` the four plists back into `ops/launchd/`.
2. Restore the two stripped entries: market 09:40, model-pvo 09:30 (shapes in
   `PRE-SR09-schedules.json`).
3. Re-symlink/re-copy into `~/Library/LaunchAgents` per each plist's original install mode
   (league-capture, model-pvo, market were symlinks; fc-snapshot, feature-refresh, what-changed
   were copies).
4. `launchctl bootstrap` the six; `launchctl bootout` the chain.
