"""File DG-033 and DG-034 — the two BLOCKER findings this lane re-derived at source."""

from __future__ import annotations

import sys
from pathlib import Path

TICKETS = Path("/Users/davidleess/dg-build/tickets")
BOARD = Path("/Users/davidleess/dg-build/BOARD.md")

DG033 = """# DG-033 — A producer can abort and still be graded fresh

**Layer:** 1  ·  **State:** todo  ·  **Lane:** —  ·  **DG 3.0**
**Source:** Codex Consultant read-only sweep, 2026-08-19; independently re-derived at source by the
crew Claude lane the same afternoon

**Problem:** `pvo_refresh` and `feature_refresh` both write a terminal `status` into their reports,
and neither declares `status_field` in `app/config/report_freshness.json`. That field is **opt-in**
by design (`app/api/routes/system_health_models.py:78-97`), so with it absent the health gate grades
on **mtime alone** and never reads the status the producer already wrote. A wholly aborted run
reports `fresh`. `pvo_refresh` is `tier: core_substrate` — the artifact the entire valuation runtime
is built from.

**How we know:**
```
$ grep -n '"status": "aborted"' scripts/run_pvo_refresh.py
345, 388, 429, 492, 558        # five distinct abort sites, each writing a terminal status

$ grep -n status_field app/config/report_freshness.json
131, 148, 172                  # three artifacts declare it; pvo_refresh and feature_refresh do not
```
Both live reports currently read `status: ok`, so the gate is not lying today — it is structurally
unable to notice when it should.

**Done looks like:** an aborted `run_pvo_refresh.py` makes `/api/health` say so. The two entries
declare `status_field` and the `success_status` its validator requires, and a test writes a report
with `status: aborted` and asserts the gate degrades.

**Depends on:** nothing.

---

**Notes**
Same class as DG-021 and DG-023: a status computed from a proxy rather than from evidence the
producer already emits. The evidence field exists in every case; it just is not read.
"""

DG034 = """# DG-034 — Backup health reports `ok` while the backup is failing

**Layer:** 1  ·  **State:** todo  ·  **Lane:** —  ·  **DG 3.0**
**Source:** Codex Consultant read-only sweep, 2026-08-19; independently re-derived at source by the
crew Claude lane the same afternoon

**Problem:** two independent faults in the same function, either of which alone hides a failed
backup. In `app/api/routes/system_capture_health_models.py:735-776`:

1. Staleness is `now - finished_at > threshold`. A **future-dated** marker yields a negative delta,
   so it is never stale.
2. `failures` is read out of the marker and echoed to the caller, but **is never appended to
   `reasons`** — while the returned status is literally `"degraded" if reasons else "ok"`.

So a marker with `status="completed"`, `sha256_verified=true`, a future `finished_at` and a
non-empty `failures` list returns **`status="ok"`, `reasons=[]`**.

**How we know:** read `system_capture_health_models.py:748-776`. `reasons` is appended to for
staleness, non-`completed` status and unverified sha256 — and never for `failures`, which is
collected at :756-761 and passed only into the echo at :774.

**Done looks like:** a marker carrying failures cannot read `ok`, and a `finished_at` in the future
is itself a degraded state rather than a free pass. A test asserts both.

**Depends on:** nothing.

---

**Notes**
`02` §Standing Infrastructure ruling 3 is explicit: *"Silence is not success. A missed or failed run
must surface, never pass silently."* The backup is the product's disaster floor — the single copy of
the PIT capture stores, model artifacts and operational databases.

A third finding from the same sweep — backup failure disappearing from two aggregate health surfaces
(`system_tier_readiness.py:75-101`, `system_health.py:110-141`) — is **not yet independently
reproduced** and is deliberately not filed until someone measures it.
"""

ROWS = (
    "| DG-033 | A producer can abort and still be graded fresh | **1** | todo | — |\n"
    "| DG-034 | Backup health reports `ok` while the backup is failing | **1** | todo | — |\n"
)

ANCHOR = "| DG-032 | Six ledger trees, three versions of the same day; reconcile the channel | process | todo | — |\n"


def main() -> int:
    (TICKETS / "DG-033-aborted-producers-grade-fresh.md").write_text(DG033)
    (TICKETS / "DG-034-backup-reports-ok-while-failing.md").write_text(DG034)

    board = BOARD.read_text()
    if ANCHOR not in board:
        print("REFUSED: DG-032 board row not found; board rows not added")
        return 1
    if "DG-033" in board:
        print("board already carries DG-033; rows not re-added")
        return 0
    BOARD.write_text(board.replace(ANCHOR, ANCHOR + ROWS))
    print("filed DG-033, DG-034; board rows added after DG-032")
    return 0


if __name__ == "__main__":
    sys.exit(main())
