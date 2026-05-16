from __future__ import annotations

from src.dynasty_genius.audit.te_archetype_taxonomy import (
    classify_alignment_archetype,
    classify_fantasy_role_archetype,
    derive_te_taxonomy_features,
)


def _row(**overrides):
    base = {
        "player_id": "te_test",
        "labeling_status": "labeled",
        "archetype": "ambiguous",
        "coverage_status": "pff_alignment_available",
        "detached_rate_from_snaps": 0.33,
        "inline_rate_from_snaps": 0.67,
        "alignment_snap_total": 240.0,
        "routes": 210.0,
        "yprr_computed": 2.2,
        "tprr_computed": 0.21,
    }
    base.update(overrides)
    return base


def test_alignment_archetype_separates_detached_balanced_inline():
    assert classify_alignment_archetype(_row(detached_rate_from_snaps=0.50, inline_rate_from_snaps=0.50)) == "detached"
    assert classify_alignment_archetype(_row(detached_rate_from_snaps=0.33, inline_rate_from_snaps=0.67)) == "balanced"
    assert classify_alignment_archetype(_row(detached_rate_from_snaps=0.20, inline_rate_from_snaps=0.80)) == "inline"


def test_complete_te_requires_balanced_alignment_and_receiving_utility():
    row = _row(detached_rate_from_snaps=0.33, inline_rate_from_snaps=0.67, yprr_computed=2.2, tprr_computed=0.21)

    assert classify_fantasy_role_archetype(row) == "complete_te"


def test_receiving_specialist_requires_detached_alignment_and_receiving_utility():
    row = _row(detached_rate_from_snaps=0.55, inline_rate_from_snaps=0.45, yprr_computed=2.0, tprr_computed=0.22)

    assert classify_fantasy_role_archetype(row) == "receiving_specialist"


def test_detached_low_efficiency_becomes_role_risk_not_receiving_specialist():
    row = _row(detached_rate_from_snaps=0.54, inline_rate_from_snaps=0.46, yprr_computed=1.16, tprr_computed=0.11)

    assert classify_fantasy_role_archetype(row) == "role_risk"


def test_inline_low_efficiency_becomes_blocking_specialist():
    row = _row(detached_rate_from_snaps=0.33, inline_rate_from_snaps=0.67, yprr_computed=1.2, tprr_computed=0.12)

    assert classify_fantasy_role_archetype(row) == "blocking_specialist"


def test_null_status_rows_remain_unlabeled():
    row = _row(labeling_status="excluded", archetype=None, detached_rate_from_snaps=None, inline_rate_from_snaps=None)

    features = derive_te_taxonomy_features(row)

    assert features["alignment_archetype"] is None
    assert features["fantasy_role_archetype"] is None
    assert features["taxonomy_status"] == "unavailable"
