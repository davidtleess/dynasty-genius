"""DG-177 stash-selection evaluation: contract tests on synthetic ids (P1, P2, ...). No names, no real data."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dynasty_genius.eval import stash_selection as ss

DEFS = json.loads(Path("docs/experiments/stash_selection_definitions_v1.json").read_text())


# ── Task 1: frozen definitions ────────────────────────────────────────────────────────────────

def test_definitions_file_is_frozen_complete_and_hashed():
    d = ss.load_definitions(Path("docs/experiments/stash_selection_definitions_v1.json"))
    assert d["version"] == ss.DEFINITIONS_VERSION and d["frozen_before_first_result"] is True
    assert set(ss.REQUIRED_DEFINITION_KEYS) <= set(d)
    assert len(d["_file"]["sha256"]) == 64 and d["_file"]["bytes"] > 0
    assert d["low_production"]["starter_slots"] == {"QB": 24, "RB": 36, "WR": 48, "TE": 18}
    assert d["outcome"]["horizons"] == [1, 2, 3] and d["metrics"]["budgets_per_position_per_origin"] == [2, 4, 8]


def test_definitions_loader_refuses_a_file_missing_a_required_section(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"version": ss.DEFINITIONS_VERSION, "frozen_before_first_result": True}))
    with pytest.raises(ss.StashSelectionError, match="outcome"):
        ss.load_definitions(p)
