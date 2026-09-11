"""Real enrollment/scorer contracts for normalized-capture preparation."""

import hashlib
import json
from datetime import datetime

import pytest

from src.dynasty_genius.capture.track_record_inputs import (
    _momentum,
    _select_history_capture,
)
from tests.contract.test_workspace_track_record import market_enrollment


def instant(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def capture(stamp, values=None, **settings):
    market = {
        "source": "fc_native",
        "settings_hash": "hash",
        "settings": {
            "isDynasty": True,
            "numQbs": 2,
            "numTeams": 12,
            "ppr": 1,
            **settings,
        },
        "retrieved_at": stamp,
        "snapshot_date": stamp[:10],
        "entries": [
            {
                "sleeper_id": sid,
                "position": "UNK" if sid == "unknown" else "QB",
                "value": value,
            }
            for sid, value in (
                values or {"1": 100, "2": 0, "3": None, "unknown": 50}
            ).items()
        ],
    }
    raw = json.dumps(market).encode()
    return {
        "capture_id": hashlib.sha256(raw).hexdigest(),
        "as_of": stamp,
        "known_at": stamp,
        "observed_at": stamp,
        "complete": True,
        "market_bytes": raw,
        "evidence": {"receipt.json": b'{"status":"ok"}'},
    }


def helpers():
    from src.dynasty_genius.capture import forward_market_outcomes

    return forward_market_outcomes


def configuration(cap):
    m = json.loads(cap["market_bytes"])
    return {"source": m["source"], "settings_hash": m["settings_hash"], **m["settings"]}


def enrollment():
    record = market_enrollment()
    from tests.contract.test_grade_workspace_track_record_cli import MARKET_POLICY_SHA

    record["document"]["market"]["plan_sha256"] = MARKET_POLICY_SHA
    record["document"]["market"]["t0"] = "2026-09-10T14:00:00Z"
    record["document"]["market"]["capture_configuration"] = configuration(
        capture("2026-09-10T13:00:00Z")
    )
    return record


def test_history_freezes_exact_sources_and_calculates_real_price_ratio():
    cap = capture("2026-08-11T13:00:00Z")
    history = helpers().build_market_history([cap], now=instant("2026-09-10T14:00:00Z"))
    chosen, why = _select_history_capture(
        history, t0=instant("2026-09-10T14:00:00Z"), configuration=configuration(cap)
    )
    assert not why
    assert _momentum({"1": 120, "2": 20, "3": 30, "unknown": 0}, chosen) == {
        "1": pytest.approx(0.2)
    }
    content = json.loads(chosen["raw_bytes"])
    import base64

    assert (
        base64.b64decode(content["normalized_capture"]["base64"]) == cap["market_bytes"]
    )
    assert content["prices"]["2"] == 0 and content["prices"]["3"] is None
    assert content["prices"]["unknown"] == 50


def test_endpoint_uses_first_compatible_capture_and_actual_selected_bytes(
    tmp_path, capsys
):
    from scripts.grade_workspace_track_record import main
    from tests.contract.test_grade_workspace_track_record_cli import (
        enrolled,
        real_store,
    )

    record = enrollment()
    store = real_store()
    root = tmp_path / "store"
    saved = enrolled(store, root, record)
    early_wrong = capture("2026-12-09T14:00:00Z", numQbs=1)
    first = capture("2026-12-10T13:00:00Z")
    later = capture("2026-12-11T13:00:00Z", {"1": 50000})
    out = helpers().prepare_market_outcome(
        enrollment=saved,
        captures=[later, first, early_wrong],
        now=instant("2026-12-12T00:00:00Z"),
        horizon_days=90,
        output_root=tmp_path / "prepared",
    )
    selected = out["selection"]["chosen"]
    assert selected["sha256"] == hashlib.sha256(first["market_bytes"]).hexdigest()
    manifest = json.loads(out["manifest_path"].read_bytes())
    assert manifest["envelope"]["prices"]["unknown"]["price"] == 50
    assert manifest["envelope"]["prices"]["2"]["price"] == 0
    code = main(
        [
            "--evaluation-root",
            str(root),
            "--enrollment-id",
            saved["record_id"],
            "--claim",
            "market",
            "--outcome-manifest",
            str(out["manifest_path"]),
            "--capture-inventory",
            str(out["inventory_path"]),
            "--horizon-days",
            "90",
            "--evaluated-at",
            "2026-12-12T00:00:00Z",
            "--output-root",
            str(tmp_path / "grade"),
        ],
        store=store,
    )
    assert code == 0, capsys.readouterr().err
    printed = json.loads(capsys.readouterr().out)
    grade = store.read_record(root, printed["record_id"])
    assert grade["document"]["decision_supported"] is False
    assert (
        grade["artifact_hashes"]["source__market.json"]
        == hashlib.sha256(first["market_bytes"]).hexdigest()
    )


def test_no_future_capture_or_invented_observation_time():
    cap = capture("2026-12-10T13:00:00Z")
    assert (
        helpers().select_market_endpoint(
            enrollment=enrollment(),
            captures=[cap],
            now=instant("2026-09-10T14:00:00Z"),
            horizon_days=90,
        )["chosen"]
        is None
    )
    cap["as_of"] = "2026-12-11T13:00:00Z"
    with pytest.raises(ValueError, match="as.of"):
        helpers().build_market_history([cap], now=instant("2026-12-12T00:00:00Z"))


def test_expired_absence_passes_through_real_grader(tmp_path, capsys):
    from scripts.grade_workspace_track_record import main
    from tests.contract.test_grade_workspace_track_record_cli import (
        enrolled,
        real_store,
    )

    store = real_store()
    root = tmp_path / "store"
    saved = enrolled(store, root, enrollment())
    out = helpers().prepare_market_outcome(
        enrollment=saved,
        captures=[],
        now=instant("2026-12-14T00:00:00Z"),
        horizon_days=90,
        output_root=tmp_path / "prepared",
    )
    assert out["selection"]["chosen"] is None
    code = main(
        [
            "--evaluation-root",
            str(root),
            "--enrollment-id",
            saved["record_id"],
            "--claim",
            "market",
            "--outcome-manifest",
            str(out["manifest_path"]),
            "--capture-inventory",
            str(out["inventory_path"]),
            "--horizon-days",
            "90",
            "--evaluated-at",
            "2026-12-14T00:00:00Z",
            "--output-root",
            str(tmp_path / "grade"),
        ],
        store=store,
    )
    assert code == 0, capsys.readouterr().err
    assert json.loads(capsys.readouterr().out)["state"] == "input_unavailable"


def test_receipt_not_yet_preserved_cannot_enter_history_or_grade():
    cap = capture("2026-08-11T13:00:00Z")
    cap["observed_at"] = "2026-09-11T00:00:00Z"
    assert (
        helpers().build_market_history([cap], now=instant("2026-09-10T14:00:00Z"))
        is None
    )
    cap = capture("2026-12-10T13:00:00Z")
    cap["observed_at"] = "2026-12-13T00:00:00Z"
    result = helpers().select_market_endpoint(
        enrollment=enrollment(),
        captures=[cap],
        now=instant("2026-12-12T00:00:00Z"),
        horizon_days=90,
    )
    assert result["chosen"] is None
