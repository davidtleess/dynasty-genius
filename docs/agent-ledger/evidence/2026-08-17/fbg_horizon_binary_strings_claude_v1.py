"""Static string survey of the Draft Dominator binary for ADP column-name bindings.

If the app resolves adp.csv columns by HEADER NAME, the header tokens must appear as
strings in the binary — which would make the `Sleeper Dynasty` -> column mapping
statically provable (Codex FBG-HZN-F1 binding-proof option 1). Read-only.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ARCHIVE = Path(
    "app/data/footballguys/objects/"
    "d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c.zip"
)
BINARY = "DraftDominator.app/Contents/MacOS/DraftDominator"


def main() -> None:
    text = zipfile.ZipFile(ARCHIVE).read(BINARY).decode("latin-1")

    print("== every case-insensitive 'sleeper' string (offset, context) ==")
    for m in re.finditer(r"(?i)[ -~]{0,40}sleeper[ -~]{0,40}", text):
        print(f"  {m.start():>9}  {m.group().strip()!r}")

    print("\n== strings containing 'adp' (case-insensitive), first 40 ==")
    seen = set()
    for m in re.finditer(r"(?i)[!-~]{0,30}adp[!-~]{0,30}", text):
        s = m.group().strip()
        if s not in seen:
            seen.add(s)
            print(f"  {m.start():>9}  {s!r}")
        if len(seen) >= 40:
            break

    print("\n== csv header tokens present as standalone strings? ==")
    tokens = [
        "bestball10s", "cbs", "consensus", "draftkings-bestball", "drafters",
        "espn", "fbgoc", "ffpc", "mfl", "nffc", "rtsports", "sleeper-1qb",
        "sleeper-1qb-rookie", "sleeper-redraft", "sleeper-sf", "sleeper-sf-rookie",
        "underdog", "yahoo",
    ]
    for tok in tokens:
        hits = [m.start() for m in re.finditer(re.escape(tok), text)][:4]
        print(f"  {tok:22s} {hits if hits else 'ABSENT'}")


if __name__ == "__main__":
    main()
