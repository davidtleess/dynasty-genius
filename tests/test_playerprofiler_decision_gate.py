"""PlayerProfiler Decision Gate.

This test defines the acceptance criterion for promoting PlayerProfiler
from context_signal to model_input in the source registry.

The gate SKIPS until David runs scripts/probe_playerprofiler.py, which writes
app/data/cache/pp_probe_results.json. Once the probe runs, this test evaluates
whether real PP data is available for >=80% of the 2015-2025 draft class.

Path A (PASS): promote PP to model_input, implement the full adapter.
Path B (FAIL): PP stays context_signal; target_share/breakout_age/speed_score
               are deferred — NOT imputed. Remove them from ALLOWED_ENRICHMENT_COLUMNS.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE_RESULTS = ROOT / "app" / "data" / "cache" / "pp_probe_results.json"

COVERAGE_THRESHOLD = 0.80
RECENT_SEASONS = set(range(2015, 2026))


def _load_probe() -> list[dict] | None:
    if not PROBE_RESULTS.exists():
        return None
    try:
        data = json.loads(PROBE_RESULTS.read_text())
        if not data:
            return None
        return data
    except (json.JSONDecodeError, ValueError):
        return None


@pytest.mark.skipif(
    _load_probe() is None,
    reason="PP probe not yet run — execute scripts/probe_playerprofiler.py first",
)
def test_pp_coverage_gate_target_share():
    """target_share must be non-null for >=80% of 2015-2025 draft class rows.

    This is the primary gate. If this fails, PP is not viable as a model_input
    source and must be downgraded to context_signal with no imputation.
    """
    results = _load_probe()
    recent = [r for r in results if r.get("season") in RECENT_SEASONS]
    assert recent, "No rows from 2015-2025 seasons in probe results."

    present = [
        r for r in recent
        if r.get("target_share_raw") not in (None, "", "null", "nan")
    ]
    pct = len(present) / len(recent)
    assert pct >= COVERAGE_THRESHOLD, (
        f"PlayerProfiler target_share coverage {pct:.0%} below {COVERAGE_THRESHOLD:.0%} threshold "
        f"for 2015-2025 draft classes ({len(present)}/{len(recent)} rows). "
        f"Path B applies: PP remains context_signal. "
        f"Remove target_share, breakout_age, speed_score from ALLOWED_ENRICHMENT_COLUMNS. "
        f"Do NOT impute these fields — fabricated values are not model evidence."
    )


@pytest.mark.skipif(
    _load_probe() is None,
    reason="PP probe not yet run — execute scripts/probe_playerprofiler.py first",
)
def test_pp_coverage_gate_breakout_age_wr_te():
    """breakout_age must be non-null for >=80% of WR and TE rows in 2015-2025.

    Checked separately from target_share because breakout_age may have
    different availability patterns.
    """
    results = _load_probe()
    recent_skill = [
        r for r in results
        if r.get("season") in RECENT_SEASONS and r.get("position") in ("WR", "TE")
    ]
    if not recent_skill:
        pytest.skip("No WR/TE rows from 2015-2025 in probe results.")

    present = [
        r for r in recent_skill
        if r.get("breakout_age_raw") not in (None, "", "null", "nan")
    ]
    pct = len(present) / len(recent_skill)
    assert pct >= COVERAGE_THRESHOLD, (
        f"PlayerProfiler breakout_age WR/TE coverage {pct:.0%} below {COVERAGE_THRESHOLD:.0%} "
        f"({len(present)}/{len(recent_skill)} rows). Path B applies."
    )


@pytest.mark.skipif(
    _load_probe() is None,
    reason="PP probe not yet run — execute scripts/probe_playerprofiler.py first",
)
def test_pp_probe_summary():
    """Informational: print the full probe summary for the ledger log."""
    results = _load_probe()
    total = len(results)
    found = sum(1 for r in results if r.get("status") == "found")
    not_found = sum(1 for r in results if r.get("status") == "not_found")
    parse_error = sum(1 for r in results if r.get("status") == "parse_error")
    ts_present = sum(1 for r in results if r.get("target_share_raw") not in (None, "", "null", "nan"))
    ba_present = sum(1 for r in results if r.get("breakout_age_raw") not in (None, "", "null", "nan"))

    print(
        f"\nPP Probe Summary: {total} players probed | "
        f"found={found} not_found={not_found} parse_error={parse_error} | "
        f"target_share={ts_present/total:.0%} breakout_age={ba_present/total:.0%}"
    )
    # This test always passes — it exists to print the summary in pytest -s output.
    assert True
