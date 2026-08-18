"""Identify WHICH adp.csv column Draft Dominator's Player Pool is currently displaying.

Method: the pool shows ADP as round.pick in a 12-team league; convert to overall pick
and test every ADP column in the bundled adp.csv for an exact match on the observed set.
An exact unique match proves the display reads that named column — the mechanism the
dynamic selector trace needs.

Observed values are transcribed from a screenshot of the running app (state recorded in
OBSERVED_LABEL) and are the only hand-entered input.
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
TEAMS = 12

OBSERVED_LABEL = "default state at first launch, QB-flexed, 2026-08-17 22:1x ET"
# name -> displayed ADP as "round.pick"
OBSERVED = {
    "Jahmyr Gibbs": "01.01",
    "Bijan Robinson": "01.02",
    "Christian McCaffrey": "01.06",
    "Jonathan Taylor": "01.08",
    "Ja'Marr Chase": "01.03",
    "Ashton Jeanty": "01.10",
    "James Cook III": "01.09",
    "Derrick Henry": "02.09",
    "Puka Nacua": "01.04",
    "Josh Allen": "03.03",
    "Saquon Barkley": "02.02",
    "Kenneth Walker": "02.05",
    "De'Von Achane": "02.01",
    "Jaxon Smith-Njigba": "01.05",
    "Amon-Ra St. Brown": "01.07",
    "Kyren Williams": "03.09",
}


def overall(round_pick: str) -> int:
    rnd, pick = round_pick.split(".")
    return (int(rnd) - 1) * TEAMS + int(pick)


def main() -> None:
    import sys

    z = zipfile.ZipFile(ARCHIVE)
    # Optional argv[1]: an alternate adp.csv on disk (e.g. the app's working-directory
    # copy) to test which file the running display actually reads.
    if len(sys.argv) > 1:
        source_label = sys.argv[1]
        adp_text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    else:
        source_label = "bundled (retained capture object)"
        adp_text = z.read("DraftDominator.app/Contents/Resources/adp.csv").decode("utf-8")
    print(f"adp source under test: {source_label}")
    adp_rows = list(csv.DictReader(io.StringIO(adp_text)))
    id_to_name: dict[str, str] = {}
    for row in csv.reader(
        io.StringIO(
            z.read("DraftDominator.app/Contents/Resources/projections.csv").decode(
                "utf-8"
            )
        )
    ):
        if row and row[0] != "id":
            id_to_name[row[0]] = f"{row[2]} {row[1]}"

    name_to_id = {v: k for k, v in id_to_name.items()}
    targets: dict[str, int] = {}
    for name, rp in OBSERVED.items():
        pid = name_to_id.get(name)
        if pid is None:
            # tolerate suffix/pretty-name differences (e.g. "James Cook III")
            for full, pid_candidate in name_to_id.items():
                if full.startswith(name) or name.startswith(full):
                    pid = pid_candidate
                    break
        if pid is None:
            print(f"  [unmatched name] {name}")
            continue
        targets[pid] = overall(rp)

    print(f"observed state: {OBSERVED_LABEL}")
    print(f"resolved {len(targets)}/{len(OBSERVED)} observed players to ids\n")

    columns = [c for c in adp_rows[0] if c.startswith("adp_")]
    by_id = {r["id"]: r for r in adp_rows}
    for col in columns:
        hits = misses = absent = 0
        for pid, want in targets.items():
            row = by_id.get(pid)
            raw = (row or {}).get(col, "").strip()
            if not raw:
                absent += 1
            elif int(float(raw)) == want:
                hits += 1
            else:
                misses += 1
        verdict = "EXACT MATCH" if hits == len(targets) else ""
        print(f"{col:28s} hits {hits:>2}  miss {misses:>2}  blank {absent:>2}  {verdict}")


if __name__ == "__main__":
    main()
