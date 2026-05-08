import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
LATEST_POINTER = BASE_DIR / "app" / "data" / "models" / "latest.json"
EXPECTED_POSITIONS = {"WR", "RB", "TE", "QB"}


def _load_report() -> dict:
    pointer = json.loads(LATEST_POINTER.read_text())
    report_path = BASE_DIR / pointer["validation_report"]
    return json.loads(report_path.read_text())


def test_validation_report_per_position_shape() -> None:
    report = _load_report()
    per_position = report["per_position"]
    assert set(per_position.keys()) == EXPECTED_POSITIONS

    required_fields = {
        "spearman_rank_correlation",
        "top_12_hit_rate",
        "bust_avoidance_rate",
        "position_ceiling",
        "model_grade",
        "caveats",
    }
    for position in EXPECTED_POSITIONS:
        assert required_fields.issubset(per_position[position].keys())


def test_validation_report_position_caveats() -> None:
    report = _load_report()
    per_position = report["per_position"]
    assert "qb_rookie_signal_inherently_low_ceiling" in per_position["QB"]["caveats"]
    assert "te_population_per_class_small" in per_position["TE"]["caveats"]
    assert "rb_career_arc_capped_by_aging_cliff" in per_position["RB"]["caveats"]
