"""Discriminating top-N fingerprint for the `adp_sleeper-sf` vs `adp_sleeper-1qb` columns.

Read-only over the retained first-capture object. Purpose: give David an exact,
provider-app-checkable ordering for the dynamic selector trace (FBG-HZN-F1 binding
proof, option: running-app UI comparison). No store mutation, no semantic write.
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

ARCHIVE = Path(
    "app/data/footballguys/objects/"
    "d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c.zip"
)


def main() -> None:
    z = zipfile.ZipFile(ARCHIVE)
    adp = list(
        csv.DictReader(
            io.StringIO(
                z.read("DraftDominator.app/Contents/Resources/adp.csv").decode("utf-8")
            )
        )
    )
    names: dict[str, str] = {}
    for row in csv.reader(
        io.StringIO(
            z.read("DraftDominator.app/Contents/Resources/projections.csv").decode(
                "utf-8"
            )
        )
    ):
        if row and row[0] != "id":
            names[row[0]] = f"{row[2]} {row[1]} ({row[3]})"

    def top(col: str, n: int = 12) -> list[str]:
        rows = [(float(r[col]), r["id"]) for r in adp if r[col].strip()]
        return [names.get(pid, pid) for _, pid in sorted(rows)[:n]]

    sf, oneqb = top("adp_sleeper-sf"), top("adp_sleeper-1qb")
    print("rank  sleeper-sf                       | sleeper-1qb")
    for i, (a, b) in enumerate(zip(sf, oneqb), 1):
        print(f"{i:>4}  {a:33s}| {b}")


if __name__ == "__main__":
    main()
