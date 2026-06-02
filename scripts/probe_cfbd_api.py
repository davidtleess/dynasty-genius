"""READ-ONLY CFBD API shape probe for S3 Task 10A T3 (pre-runner investigation).

Confirms the live CFBD API shape the cockpit flagged before authoring a fresh T3 runner:
- Bearer auth header acceptance,
- ``/roster?year=2025`` all-team behavior (does year-only return every team?),
- the team-list endpoint(s) for the per-team fallback, incl. FBS vs FCS coverage
  (drafted skill players can come from FCS).

STRICTLY READ-ONLY: issues GET requests and prints a BOUNDED SUMMARY (counts + sample
field names + a couple of redacted sample rows). Writes NOTHING, builds NO fixture.
Reads the key from the ``CFBD_API_KEY`` env var (never hardcoded, never printed).

Usage (key supplied via a gitignored env file, sourced inline so it never lands in argv/transcript):
    set -a; . ./.cfbd.env; set +a; .venv/bin/python3.14 scripts/probe_cfbd_api.py
"""
from __future__ import annotations

import os
import sys

import httpx

BASE_URL = "https://api.collegefootballdata.com"
YEAR = 2025


def _get(client: httpx.Client, path: str, params: dict | None = None) -> tuple[int, object]:
    resp = client.get(f"{BASE_URL}{path}", params=params or {})
    try:
        body = resp.json()
    except ValueError:
        body = resp.text[:200]
    return resp.status_code, body


def _summarize(label: str, status: int, body: object) -> None:
    print(f"\n=== {label} -> HTTP {status} ===")
    if isinstance(body, list):
        print(f"rows: {len(body)}")
        if body and isinstance(body[0], dict):
            print(f"row[0] keys: {sorted(body[0].keys())}")
            sample = {k: body[0].get(k) for k in list(body[0])[:8]}
            print(f"row[0] sample (first 8 fields): {sample}")
    elif isinstance(body, dict):
        print(f"dict keys: {sorted(body.keys())}")
    else:
        print(f"non-json/other: {body!r}")


def main() -> int:
    key = os.getenv("CFBD_API_KEY")
    if not key:
        print("ERROR: CFBD_API_KEY not set in env. Source your gitignored key file first.", file=sys.stderr)
        return 2
    headers = {"Authorization": f"Bearer {key.strip()}"}
    with httpx.Client(headers=headers, timeout=30.0) as client:
        # 1) all-team roster via year only
        s, b = _get(client, "/roster", {"year": YEAR})
        _summarize(f"/roster?year={YEAR} (all-team attempt)", s, b)
        if isinstance(b, list):
            teams = {r.get("team") for r in b if isinstance(r, dict)}
            print(f"distinct teams in roster: {len(teams)} (all-team if large; single/empty if not)")

        # 2) FBS team list (year-honored?)
        s, b = _get(client, "/teams/fbs", {"year": YEAR})
        _summarize(f"/teams/fbs?year={YEAR}", s, b)

        # 3) full team list (FBS+FCS coverage check)
        s, b = _get(client, "/teams", {"year": YEAR})
        _summarize(f"/teams?year={YEAR} (FBS+FCS coverage)", s, b)
        if isinstance(b, list):
            divs = {}
            for r in b:
                if isinstance(r, dict):
                    d = r.get("classification") or r.get("division") or "unknown"
                    divs[d] = divs.get(d, 0) + 1
            print(f"team classifications: {divs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
