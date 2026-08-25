#!/usr/bin/env python3.14
"""Print the QB-1 registered contrasts as a flat table (read-only inspection helper)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "app" / "data" / "backtest" / "qb_validation" / "qb_validation_report.json"


def _num(value: Any, spec: str) -> str:
    return format(value, spec) if isinstance(value, (int, float)) else "-"


def main() -> int:
    payload = json.loads(REPORT.read_text())
    header = (
        f"{'id':<30} {'lane':<8} {'support_status':<24} "
        f"{'delta':>8} {'adj_p':>8} {'folds':>5}  ci95"
    )
    print(header)
    print("-" * len(header))
    for row in payload["comparisons"]:
        ci = row.get("ci95") or []
        if len(ci) == 2 and all(isinstance(v, (int, float)) for v in ci):
            ci_text = f"[{ci[0]:+.3f}, {ci[1]:+.3f}]"
        else:
            ci_text = "-"
        print(
            f"{str(row.get('id'))[:30]:<30} "
            f"{str(row.get('lane'))[:8]:<8} "
            f"{str(row.get('support_status'))[:24]:<24} "
            f"{_num(row.get('pooled_delta'), '+.3f'):>8} "
            f"{_num(row.get('adjusted_p'), '.4f'):>8} "
            f"{str(row.get('evaluable_folds')):>5}  {ci_text}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
