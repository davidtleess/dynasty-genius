"""Phase 21 W3 — Build roster cut report artifacts.

Reads latest Sleeper snapshot + universe PVO, runs RosterCutEngine,
writes JSON and Markdown report cards to app/data/valuation/.

Usage:
    .venv/bin/python3.14 scripts/build_roster_cut_report.py [--roster-id N]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.roster_cut_engine import (  # noqa: E402
    RosterCutCandidate,
    RosterCutResult,
    compute_roster_cut_candidates,
)

SNAPSHOT_PATH = ROOT / "app" / "data" / "league_snapshots" / "sleeper_universe_snapshot_latest.json"
PVO_PATH = ROOT / "app" / "data" / "valuation" / "universe_pvo_latest.json"
OUTPUT_DIR = ROOT / "app" / "data" / "valuation"


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact not found: {path}")
    return json.loads(path.read_text())


def _render_markdown(result: RosterCutResult, run_id: str) -> str:
    lines: list[str] = []
    lines.append(f"# Roster Cut Report — {run_id}")
    lines.append("")
    lines.append(f"- **Roster ID:** {result.roster_id}")
    lines.append(f"- **Total players:** {result.total_players}")
    lines.append(f"- **Active slots:** {result.active_slots}")
    lines.append(f"- **Total capacity:** {result.total_capacity}")
    lines.append(f"- **Cuts required:** {result.cuts_required}")
    lines.append(f"- **Reserve unrestricted:** {result.reserve_unrestricted}")
    lines.append(f"- **Decision supported:** {result.decision_supported}")
    lines.append("")

    if result.cut_candidates:
        lines.append("## Cut Candidates")
        lines.append("")
        lines.append("| Priority | Player | Pos | Age | Tier | xVar% | DVS | IR Status | Cliff | Rationale |")
        lines.append("|----------|--------|-----|-----|------|-------|-----|-----------|-------|-----------|")
        for c in result.cut_candidates:
            xvar_str = f"{c.xvar_pct:.1f}" if c.xvar_pct is not None else "—"
            dvs_str = f"{c.dvs:.1f}" if c.dvs is not None else "—"
            age_str = f"{c.age:.1f}" if c.age is not None else "—"
            cliff_str = "⚠" if c.age_cliff_warning else ""
            rationale = "; ".join(c.cut_rationale) or "—"
            lines.append(
                f"| {c.cut_priority} | {c.full_name} | {c.position} | {age_str} "
                f"| {c.scoring_tier} | {xvar_str} | {dvs_str} "
                f"| {c.ir_compliance_status} | {cliff_str} | {rationale} |"
            )
        lines.append("")
    else:
        lines.append("## Cut Candidates")
        lines.append("")
        lines.append("_No cut candidates — roster is within capacity and IR-compliant._")
        lines.append("")

    if result.exempt_players:
        lines.append("## Exempt Players")
        lines.append("")
        lines.append("| Player | Pos | Exempt Reason | IR Status | Taxi Eligibility |")
        lines.append("|--------|-----|---------------|-----------|-----------------|")
        for e in result.exempt_players:
            lines.append(
                f"| {e.full_name} | {e.position} | {e.exempt_reason or '—'} "
                f"| {e.ir_compliance_status} | {e.taxi_eligibility} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("_decision_supported: False — all outputs are advisory only._")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 21 roster cut report")
    parser.add_argument("--roster-id", type=int, default=1, help="Perspective roster ID (default: 1)")
    args = parser.parse_args()

    snapshot = _load_json(SNAPSHOT_PATH)
    pvo = _load_json(PVO_PATH)

    result = compute_roster_cut_candidates(pvo, snapshot, david_roster_id=args.roster_id)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"phase21-{ts}"

    json_path = OUTPUT_DIR / f"roster_cut_report_{run_id}.json"
    md_path = OUTPUT_DIR / f"roster_cut_report_{run_id}.md"
    latest_json = OUTPUT_DIR / "roster_cut_report_latest.json"
    latest_md = OUTPUT_DIR / "roster_cut_report_latest.md"

    payload = {
        "run_id": run_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "roster_cut_report": json.loads(result.model_dump_json()),
    }

    json_path.write_text(json.dumps(payload, indent=2))
    latest_json.write_text(json.dumps(payload, indent=2))

    md_content = _render_markdown(result, run_id)
    md_path.write_text(md_content)
    latest_md.write_text(md_content)

    print(f"Cuts required: {result.cuts_required}")
    print(f"Cut candidates: {len(result.cut_candidates)}")
    print(f"Exempt players: {len(result.exempt_players)}")
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
