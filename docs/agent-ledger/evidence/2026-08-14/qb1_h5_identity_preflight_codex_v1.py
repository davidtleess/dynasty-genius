"""Read-only QB-1 H5 fp_id bridge and F32 preflight measurement."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CROSSWALK = ROOT / "app/data/identity/_runs/ff_playerids_20260516.json"
DP_ROOT = Path("/var/tmp/dp-values")
EXPECTED_CROSSWALK_SHA = (
    "8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593"
)
EXPECTED_DP = {
    2021: "589d16422e46018a8c3d80a7008fd038403d75383e4a873f249417fa9d2e4c36",
    2022: "7027e46234165ef8c8a6e3bc28a1ab244007d0010353bd288ac32e7433a54bc3",
    2023: "bb753e7753bc729235bab8426c674753ac0db68c3d96fe3db1e5b73cfb837174",
    2024: "9f38f637131d66425a215a2aacd3a1e973644143da8e693275c7c46f9ae50997",
}
_SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv)\b\.?", re.IGNORECASE)
_PUNCT = re.compile(r"[^\w\s]")
_SPACE = re.compile(r"\s+")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize(value: object) -> str:
    if value is None:
        return ""
    folded = unicodedata.normalize("NFKD", str(value))
    folded = folded.encode("ascii", "ignore").decode("ascii").lower()
    folded = _SUFFIX.sub(" ", folded)
    folded = _PUNCT.sub(" ", folded)
    return _SPACE.sub(" ", folded).strip()


def main() -> int:
    failures: list[str] = []
    crosswalk_sha = _sha256(CROSSWALK)
    if crosswalk_sha != EXPECTED_CROSSWALK_SHA:
        failures.append(f"crosswalk sha drift: {crosswalk_sha}")
    payload = json.loads(CROSSWALK.read_text())

    claims: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in payload["entries"]:
        fp_id = row.get("fantasypros_id")
        gsis_id = row.get("gsis_id")
        if fp_id not in (None, "") and gsis_id not in (None, ""):
            claims[str(fp_id)].append(row)

    mapping: dict[str, dict[str, object]] = {}
    identical_duplicates = 0
    conflicts: dict[str, list[str]] = {}
    for fp_id, rows in claims.items():
        gsis_ids = sorted({str(row["gsis_id"]) for row in rows})
        if len(gsis_ids) == 1:
            mapping[fp_id] = rows[0]
            identical_duplicates += len(rows) - 1
        else:
            conflicts[fp_id] = gsis_ids

    folds: list[dict[str, object]] = []
    for season, expected_sha in EXPECTED_DP.items():
        path = DP_ROOT / f"values_{season}-09-08.csv"
        actual_sha = _sha256(path)
        if actual_sha != expected_sha:
            failures.append(f"{season} sha drift: {actual_sha}")
        with path.open(newline="", encoding="utf-8") as handle:
            qb_rows = [row for row in csv.DictReader(handle) if row.get("pos") == "QB"]

        joined = 0
        mismatches = 0
        missing_fp_id = 0
        unresolved_fp_id = 0
        conflict_fp_id = 0
        for row in qb_rows:
            fp_id = str(row.get("fp_id") or "").strip()
            if not fp_id:
                missing_fp_id += 1
                continue
            if fp_id in conflicts:
                conflict_fp_id += 1
                continue
            crosswalk_row = mapping.get(fp_id)
            if crosswalk_row is None:
                unresolved_fp_id += 1
                continue
            joined += 1
            if not _normalize(row.get("player")) or _normalize(
                row.get("player")
            ) != _normalize(crosswalk_row.get("name")):
                mismatches += 1

        folds.append(
            {
                "season": season,
                "qb_rows": len(qb_rows),
                "joined": joined,
                "coverage": joined / len(qb_rows),
                "mismatches": mismatches,
                "mismatch_rate_joined_denominator": mismatches / joined if joined else None,
                "missing_fp_id": missing_fp_id,
                "unresolved_fp_id": unresolved_fp_id,
                "conflict_fp_id": conflict_fp_id,
                "coverage_gate_pass": joined / len(qb_rows) >= 0.70,
                "reconciliation_gate_pass": joined > 0 and mismatches / joined <= 0.02,
            }
        )

    result = {
        "status": "passed" if not failures else "failed",
        "crosswalk_sha256": crosswalk_sha,
        "crosswalk_entries": len(payload["entries"]),
        "fantasypros_claims": len(claims),
        "unambiguous_fantasypros_ids": len(mapping),
        "identical_duplicate_rows": identical_duplicates,
        "conflicting_fantasypros_ids": conflicts,
        "folds": folds,
        "failures": failures,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
