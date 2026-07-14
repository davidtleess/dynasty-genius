# Wake-Ordering Guard — Spec Draft v0 (pre-framing; cockpit cycle pending David sequencing)

**Problem (proven live, 2026-07-12):** the 09:00 FC capture and the 09:40 divergence runner have only schedule spacing between them. When launchd wake-coalesces after sleep, both fire together: the runner finished 14:06:34Z, the fresh capture landed 14:06:37Z — a 3-second loss. The runner honestly fail-closed (`degraded / market_source_prior_date`; no PIT pair) — the honesty layer worked; the schedule dependency did not.

**Design intent (for the RED):** the runner, on finding a prior-date FC snapshot, WAITS for a same-UTC-day snapshot with bounded retry (e.g. every 60s up to 30min) instead of terminating degraded immediately; every retry is logged; exhaustion degrades with the existing named reason (fail-closed unchanged). No new schedule; no capture-side change; the marker gains `retries_used`. Alternative shapes for the cycle to weigh: an explicit dependency file handshake (capture writes a completion marker the runner checks) — stronger, more moving parts.

**Falsification seeds:** wake-coalesced simultaneous start (capture lands mid-retry) → ok pair; capture never lands → degraded after bounded wait, exit unchanged, marker names retries; clock-skew day boundary; retry logging present; no partial-read of a mid-write store (the capture's atomicity contract is the dependency).

**Out of scope:** touching the capture job; any schedule change; any marker-schema change beyond the additive retry field.
