"""DG-178: capture a DATED current-season NFL roster source, run-local and immutable.

Downloads nflverse's `roster_<season>.csv` (a raw public release) into
`runs/<UTC>/dg178_nfl_roster_capture/` with the HTTP timestamp, ETag, sha256 and row count in
`manifest.json`. No shared cache is read or written: this is the census's own dated source.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

SOURCE = "https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{season}.csv"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--out-root", type=Path, default=REPO / "runs")
    a = ap.parse_args()
    url = SOURCE.format(season=a.season)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = a.out_root / stamp / "dg178_nfl_roster_capture"
    out.mkdir(parents=True)  # a second capture in the same second is refused, never overwritten
    req = urllib.request.Request(url, headers={"User-Agent": "dynasty-genius DG-178 census capture"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
        headers = {k.lower(): v for k, v in resp.headers.items()}
        status = resp.status
    sha = hashlib.sha256(raw).hexdigest()
    path = out / f"roster_{a.season}.csv"
    path.write_bytes(raw)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    rows = list(reader)
    manifest = {
        "ticket": "DG-178", "purpose": "dated current-season NFL roster source for the current-player census",
        "source_url": url, "http_status": status, "http_last_modified": headers.get("last-modified"),
        "http_etag": headers.get("etag"), "captured_at": datetime.now(timezone.utc).isoformat(),
        "file": path.name, "bytes": len(raw), "sha256": sha, "rows": len(rows), "columns": reader.fieldnames,
        "season": a.season, "immutable": True, "shared_cache": "none read, none written",
        "statuses": sorted({r.get("status") or "" for r in rows}),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps({k: manifest[k] for k in ("captured_at", "http_last_modified", "sha256", "rows", "statuses")}, indent=1))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
