"""DG-207 — the grading runner, proved against the REAL DG206 store.

The runner's job is to be unable to fool itself. It hashes the real bytes rather than trusting
the manifest, it stores those bytes inside the immutable record so a later replay does not depend
on a mutable external path, it requires a disclosed preparation recipe binding the scored numbers
to the capture, it selects the market endpoint deterministically from a complete inventory before
seeing any result, and it refuses to overwrite a previous run's evidence.

The real immutable store is loaded from this checkout, so these checks also run in a clean clone.
"""

import copy
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from scripts.grade_workspace_track_record import main  # noqa: E402
from tests.contract.test_workspace_track_record import (  # noqa: E402
    endpoint_source,
    market_enrollment,
    outcome_source,
    production_enrollment,
)

DG206_STORE = REPO / "src/dynasty_genius/capture/track_record_store.py"
MARKET_POLICY_SHA = hashlib.sha256(
    json.dumps(json.loads((REPO / "app/config/workspace_market_movement_90d_v1.json").read_bytes()),
               sort_keys=True, separators=(",", ":"), ensure_ascii=True,
               allow_nan=False).encode("utf-8")
).hexdigest()

def real_store():
    spec = importlib.util.spec_from_file_location("dg206_track_record_store", DG206_STORE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PLAN_BYTES = json.dumps({"plan_id": "workspace-production-2026-v1"},
                        sort_keys=True).encode("utf-8")


def enrolled(store, root, record):
    """Save a real enrollment carrying the archived evaluation-plan.json artifact."""
    document = copy.deepcopy(record["document"])
    # the enrolled hash must be the artifact's own, or the runner refuses — as it should
    if document.get("production", {}).get("plan_sha256"):
        document["production"]["plan_sha256"] = hashlib.sha256(PLAN_BYTES).hexdigest()
    saved = store.save_record(root, kind="enrollment", document=document,
                              artifacts={"evaluation-plan.json": PLAN_BYTES},
                              recorded_at=datetime(2026, 9, 9, tzinfo=timezone.utc))
    return saved["record"]


def write_manifest(tmp_path, envelope, *, name="weekly.json", payload=b'{"weekly": "rows"}',
                   preparation=True, duplicate=False, bad_len=False,
                   endpoint_source_name=None, captured_at="2027-01-06T00:00:00Z"):
    (tmp_path / name).write_bytes(payload)
    source = {"name": name, "path": name, "sha256": hashlib.sha256(payload).hexdigest(),
              "url": "https://example.invalid/w", "captured_at": captured_at,
              "bytes_len": (len(payload) + 1) if bad_len else len(payload)}
    sources = [source, dict(source)] if duplicate else [source]
    if envelope.get("schema_version") == "track_record.endpoint_source.v1":
        envelope = {**envelope, "endpoint_source_name": endpoint_source_name or name}
    manifest = {"sources": sources, "envelope": envelope}
    if preparation:
        manifest["preparation"] = {
            "recipe": "research_ppr_weekly_sum_v1",
            "recipe_sha256": "f" * 64,
            "inputs": [name],
        }
    path = tmp_path / "manifest.json"
    path.write_bytes(json.dumps(manifest).encode())
    return path


CONFIGURATION = {"isDynasty": True, "numQbs": 2, "numTeams": 12, "ppr": 1}


def inventory_file(tmp_path, captures):
    """Every capture carries the settings it was taken under; compatibility is filtered, not assumed."""
    path = tmp_path / "inventory.json"
    filled = [{"configuration": CONFIGURATION, **capture} for capture in captures]
    path.write_bytes(json.dumps({"captures": filled}).encode())
    return path


# --------------------------------------------------------------------------- end to end
def test_end_to_end_production_through_the_real_store(tmp_path, capsys):
    store = real_store()
    root = tmp_path / "store"
    record = enrolled(store, root, production_enrollment())
    envelope = outcome_source(production_enrollment())
    manifest = write_manifest(tmp_path, envelope)
    out = tmp_path / "run1"

    code = main([
        "--evaluation-root", str(root), "--enrollment-id", record["record_id"],
        "--claim", "production", "--outcome-manifest", str(manifest),
        "--output-root", str(out), "--evaluated-at", "2027-01-10T00:00:00Z",
    ], store=store)
    assert code == 0, capsys.readouterr().err

    printed = json.loads(capsys.readouterr().out)
    assert printed["state"] == "graded"

    # read the grade back out of the REAL store and validate it end to end
    grade_record = store.read_record(root, printed["record_id"])
    assert grade_record["kind"] == "grade"
    assert grade_record["document"]["enrollment_id"] == record["record_id"]
    assert grade_record["document"]["claim"] == "football_production"
    assert grade_record["document"]["decision_supported"] is False

    # the raw capture bytes and the prepared table both live INSIDE the immutable record
    hashes = grade_record["artifact_hashes"]
    assert "source__weekly.json" in hashes
    assert "prepared_outcome.json" in hashes
    assert "code_identity.json" in hashes
    assert hashes["policy.json"] == hashlib.sha256(PLAN_BYTES).hexdigest()
    # and the prepared table's hash is the one the grade names
    assert grade_record["document"]["outcome_source_hashes"]["prepared_outcome.json"] == \
        hashes["prepared_outcome.json"]


def test_production_policy_bytes_come_from_the_enrollment_artifact_not_a_declared_hash(tmp_path, capsys):
    store = real_store()
    root = tmp_path / "store"
    record = production_enrollment()
    record["document"]["production"]["plan_sha256"] = hashlib.sha256(PLAN_BYTES).hexdigest()
    saved = enrolled(store, root, record)
    manifest = write_manifest(tmp_path, outcome_source(record))
    code = main([
        "--evaluation-root", str(root), "--enrollment-id", saved["record_id"],
        "--claim", "production", "--outcome-manifest", str(manifest),
        "--output-root", str(tmp_path / "run"), "--evaluated-at", "2027-01-10T00:00:00Z",
    ], store=store)
    assert code == 0, capsys.readouterr().err
    diagnostics = json.loads((tmp_path / "run" / "grade-diagnostics.json").read_bytes())
    assert diagnostics["policy_source"] == "enrollment artifact evaluation-plan.json"
    assert diagnostics["policy_sha256"] == hashlib.sha256(PLAN_BYTES).hexdigest()


def test_refuses_when_the_enrollment_holds_no_plan_artifact(tmp_path, capsys):
    store = real_store()
    root = tmp_path / "store"
    document = copy.deepcopy(production_enrollment()["document"])
    saved = store.save_record(root, kind="enrollment", document=document, artifacts={},
                              recorded_at=datetime(2026, 9, 9, tzinfo=timezone.utc))["record"]
    manifest = write_manifest(tmp_path, outcome_source(production_enrollment()))
    code = main([
        "--evaluation-root", str(root), "--enrollment-id", saved["record_id"],
        "--claim", "production", "--outcome-manifest", str(manifest),
        "--output-root", str(tmp_path / "run"), "--evaluated-at", "2027-01-10T00:00:00Z",
    ], store=store)
    assert code == 2
    assert "cannot stand on a declared hash alone" in capsys.readouterr().err


# --------------------------------------------------------------------------- source binding
def test_refuses_a_manifest_with_no_preparation_recipe(tmp_path, capsys):
    store = real_store()
    root = tmp_path / "store"
    record = enrolled(store, root, production_enrollment())
    manifest = write_manifest(tmp_path, outcome_source(production_enrollment()), preparation=False)
    code = main([
        "--evaluation-root", str(root), "--enrollment-id", record["record_id"],
        "--claim", "production", "--outcome-manifest", str(manifest),
        "--output-root", str(tmp_path / "run"), "--evaluated-at", "2027-01-10T00:00:00Z",
    ], store=store)
    assert code == 2
    assert "no preparation recipe" in capsys.readouterr().err


def test_refuses_duplicate_source_names(tmp_path, capsys):
    store = real_store()
    root = tmp_path / "store"
    record = enrolled(store, root, production_enrollment())
    manifest = write_manifest(tmp_path, outcome_source(production_enrollment()), duplicate=True)
    code = main([
        "--evaluation-root", str(root), "--enrollment-id", record["record_id"],
        "--claim", "production", "--outcome-manifest", str(manifest),
        "--output-root", str(tmp_path / "run"), "--evaluated-at", "2027-01-10T00:00:00Z",
    ], store=store)
    assert code == 2
    assert "duplicate source name" in capsys.readouterr().err


def test_refuses_a_truncated_capture(tmp_path, capsys):
    store = real_store()
    root = tmp_path / "store"
    record = enrolled(store, root, production_enrollment())
    manifest = write_manifest(tmp_path, outcome_source(production_enrollment()), bad_len=True)
    code = main([
        "--evaluation-root", str(root), "--enrollment-id", record["record_id"],
        "--claim", "production", "--outcome-manifest", str(manifest),
        "--output-root", str(tmp_path / "run"), "--evaluated-at", "2027-01-10T00:00:00Z",
    ], store=store)
    assert code == 2
    assert "not the declared" in capsys.readouterr().err


def test_refuses_to_overwrite_a_previous_runs_evidence(tmp_path, capsys):
    store = real_store()
    root = tmp_path / "store"
    record = enrolled(store, root, production_enrollment())
    manifest = write_manifest(tmp_path, outcome_source(production_enrollment()))
    out = tmp_path / "run"
    args = ["--evaluation-root", str(root), "--enrollment-id", record["record_id"],
            "--claim", "production", "--outcome-manifest", str(manifest),
            "--output-root", str(out), "--evaluated-at", "2027-01-10T00:00:00Z"]
    assert main(args, store=store) == 0, capsys.readouterr().err
    capsys.readouterr()
    assert main(args, store=store) == 2
    assert "run evidence is immutable" in capsys.readouterr().err


# --------------------------------------------------------------------------- endpoint selection
def test_market_requires_a_capture_inventory(tmp_path, capsys):
    store = real_store()
    root = tmp_path / "store"
    record = enrolled(store, root, market_enrollment())
    manifest = write_manifest(tmp_path, endpoint_source(market_enrollment()))
    code = main([
        "--evaluation-root", str(root), "--enrollment-id", record["record_id"],
        "--claim", "market", "--outcome-manifest", str(manifest),
        "--output-root", str(tmp_path / "run"), "--horizon-days", "90",
        "--evaluated-at", "2026-12-09T00:00:00Z",
    ], store=store)
    assert code == 2
    assert "--capture-inventory is required" in capsys.readouterr().err


def test_market_selects_the_first_in_window_capture_regardless_of_inventory_order(tmp_path, capsys):
    """A later, more flattering capture cannot displace the first compatible one."""
    store = real_store()
    root = tmp_path / "store"
    enrollment = market_enrollment()
    enrollment["document"]["market"]["plan_sha256"] = MARKET_POLICY_SHA
    record = enrolled(store, root, enrollment)
    envelope = endpoint_source(enrollment, as_of="2026-12-08T00:00:00Z")
    payload = b'{"capture": "day90"}'
    manifest = write_manifest(tmp_path, envelope, name="capture.json", payload=payload)
    day90 = hashlib.sha256(payload).hexdigest()
    captures = [
        {"as_of": "2026-12-10T00:00:00Z", "sha256": "b" * 64, "complete": True},   # flattering, later
        {"as_of": "2026-12-08T00:00:00Z", "sha256": day90, "complete": True},      # first compatible
    ]
    for ordering in (captures, list(reversed(captures))):
        out = tmp_path / f"run{len(ordering)}{captures.index(ordering[0])}"
        code = main([
            "--evaluation-root", str(root), "--enrollment-id", record["record_id"],
            "--claim", "market", "--outcome-manifest", str(manifest),
            "--capture-inventory", str(inventory_file(tmp_path, ordering)),
            "--output-root", str(out), "--horizon-days", "90",
            "--evaluated-at", "2026-12-11T00:00:00Z",
        ], store=store)
        assert code == 0, capsys.readouterr().err
        capsys.readouterr()
        diagnostics = json.loads((out / "grade-diagnostics.json").read_bytes())
        assert diagnostics["endpoint_selection"]["chosen"]["as_of"] == "2026-12-08T00:00:00Z"


def test_market_refuses_an_endpoint_the_inventory_did_not_select(tmp_path, capsys):
    store = real_store()
    root = tmp_path / "store"
    enrollment = market_enrollment()
    enrollment["document"]["market"]["plan_sha256"] = MARKET_POLICY_SHA
    record = enrolled(store, root, enrollment)
    manifest = write_manifest(tmp_path, endpoint_source(enrollment, as_of="2026-12-10T00:00:00Z"),
                              name="capture.json", payload=b'{"capture": "day92"}')
    captures = [{"as_of": "2026-12-08T00:00:00Z", "sha256": "a" * 64, "complete": True}]
    code = main([
        "--evaluation-root", str(root), "--enrollment-id", record["record_id"],
        "--claim", "market", "--outcome-manifest", str(manifest),
        "--capture-inventory", str(inventory_file(tmp_path, captures)),
        "--output-root", str(tmp_path / "run"), "--horizon-days", "90",
        "--evaluated-at", "2026-12-11T00:00:00Z",
    ], store=store)
    assert code == 2
    assert "is not the capture the inventory selects" in capsys.readouterr().err


def test_market_refuses_a_day92_envelope_when_the_inventory_selected_day90(tmp_path, capsys):
    """The re-review's exact case, with BOTH raw captures present and verified.

    Previously the selected digest could be witnessed by ANY verified source, so a manifest
    carrying both day-90 and day-92 bytes let a day-90 selection grade a day-92 envelope and
    exit 0. The endpoint that is graded must be the capture that was chosen.
    """
    store = real_store()
    root = tmp_path / "store"
    enrollment = market_enrollment()
    enrollment["document"]["market"]["plan_sha256"] = MARKET_POLICY_SHA
    record = enrolled(store, root, enrollment)

    day90_bytes, day92_bytes = b'{"capture": "day90"}', b'{"capture": "day92"}'
    (tmp_path / "day90.json").write_bytes(day90_bytes)
    (tmp_path / "day92.json").write_bytes(day92_bytes)
    def source(name, payload):
        return {"name": name, "path": name, "sha256": hashlib.sha256(payload).hexdigest(),
                "url": "https://example.invalid/v", "captured_at": "2026-12-10T00:00:00Z",
                "bytes_len": len(payload)}
    envelope = dict(endpoint_source(enrollment, as_of="2026-12-10T00:00:00Z"))
    envelope["endpoint_source_name"] = "day92.json"          # the flattering one
    manifest_path = tmp_path / "both.json"
    manifest_path.write_bytes(json.dumps({
        "sources": [source("day90.json", day90_bytes), source("day92.json", day92_bytes)],
        "envelope": envelope,
        "preparation": {"recipe": "fantasycalc_endpoint_v1", "recipe_sha256": "f" * 64,
                        "inputs": ["day90.json", "day92.json"]},
    }).encode())

    # the inventory selects the EARLIER compatible capture, whose bytes are also present
    captures = [
        {"as_of": "2026-12-08T00:00:00Z", "sha256": hashlib.sha256(day90_bytes).hexdigest(),
         "complete": True},
        {"as_of": "2026-12-10T00:00:00Z", "sha256": hashlib.sha256(day92_bytes).hexdigest(),
         "complete": True},
    ]
    code = main([
        "--evaluation-root", str(root), "--enrollment-id", record["record_id"],
        "--claim", "market", "--outcome-manifest", str(manifest_path),
        "--capture-inventory", str(inventory_file(tmp_path, captures)),
        "--output-root", str(tmp_path / "run"), "--horizon-days", "90",
        "--evaluated-at", "2026-12-11T00:00:00Z",
    ], store=store)
    assert code == 2, "a day-92 envelope must not be graded against a day-90 selection"
    error = capsys.readouterr().err
    assert "is not the capture the inventory selects" in error
    assert "2026-12-08" in error


def test_market_with_no_capture_in_window_is_a_declared_state_not_a_refusal(tmp_path, capsys):
    store = real_store()
    root = tmp_path / "store"
    enrollment = market_enrollment()
    enrollment["document"]["market"]["plan_sha256"] = MARKET_POLICY_SHA
    record = enrolled(store, root, enrollment)
    manifest = write_manifest(tmp_path, endpoint_source(enrollment), name="capture.json",
                              payload=b'{"capture": "none"}')
    empty = inventory_file(tmp_path, [])
    out = tmp_path / "run"
    code = main([
        "--evaluation-root", str(root), "--enrollment-id", record["record_id"],
        "--claim", "market", "--outcome-manifest", str(manifest),
        "--capture-inventory", str(empty), "--output-root", str(out),
        "--horizon-days", "90", "--evaluated-at", "2027-06-01T00:00:00Z",
    ], store=store)
    assert code == 0, capsys.readouterr().err
    printed = json.loads(capsys.readouterr().out)
    assert printed["state"] == "input_unavailable"
    grade = store.read_record(root, printed["record_id"])["document"]
    assert grade["result"] is None and grade["counts"]["scored"] == 0


def test_market_before_the_window_opens_is_awaiting_capture(tmp_path, capsys):
    store = real_store()
    root = tmp_path / "store"
    enrollment = market_enrollment()
    enrollment["document"]["market"]["plan_sha256"] = MARKET_POLICY_SHA
    record = enrolled(store, root, enrollment)
    manifest = write_manifest(tmp_path, endpoint_source(enrollment), name="capture.json",
                              payload=b'{"capture": "none yet"}')
    code = main([
        "--evaluation-root", str(root), "--enrollment-id", record["record_id"],
        "--claim", "market", "--outcome-manifest", str(manifest),
        "--capture-inventory", str(inventory_file(tmp_path, [])),
        "--output-root", str(tmp_path / "run"), "--horizon-days", "90",
        "--evaluated-at", "2026-10-01T00:00:00Z",
    ], store=store)
    assert code == 0, capsys.readouterr().err
    assert json.loads(capsys.readouterr().out)["state"] == "awaiting_capture"


# --------------------------------------------------------------------------- argument guards
def test_market_claim_requires_an_allowed_horizon(tmp_path, capsys):
    store = real_store()
    record = market_enrollment()
    code = main([
        "--evaluation-root", str(tmp_path), "--enrollment-id", record["record_id"],
        "--claim", "market", "--outcome-manifest", str(tmp_path / "x.json"),
        "--output-root", str(tmp_path), "--horizon-days", "45",
        "--evaluated-at", "2026-12-09T00:00:00Z",
    ], store=store)
    assert code == 2
    assert "--horizon-days must be one of" in capsys.readouterr().err


def test_production_claim_rejects_a_horizon(tmp_path, capsys):
    store = real_store()
    record = production_enrollment()
    code = main([
        "--evaluation-root", str(tmp_path), "--enrollment-id", record["record_id"],
        "--claim", "production", "--outcome-manifest", str(tmp_path / "x.json"),
        "--output-root", str(tmp_path), "--horizon-days", "90",
        "--evaluated-at", "2027-01-10T00:00:00Z",
    ], store=store)
    assert code == 2
    assert "does not apply" in capsys.readouterr().err


def test_runner_requires_an_explicit_evaluation_instant(tmp_path):
    with pytest.raises(SystemExit):
        main(["--evaluation-root", str(tmp_path), "--enrollment-id", "a" * 64,
              "--claim", "production", "--outcome-manifest", str(tmp_path / "m.json"),
              "--output-root", str(tmp_path)], store=real_store())


# ------------------------------------------------- re-review round 3: chronology holes
def test_production_cli_refuses_when_the_only_raw_capture_is_midseason(tmp_path, capsys):
    """The runner's own prepared entry must not witness for the raw bytes.

    It used to be stamped at the target end, which satisfied the chronology check that the only
    actual capture -- taken on November 1, mid-season -- failed. Exit was 0 and the state graded.
    """
    store = real_store()
    root = tmp_path / "store"
    record = enrolled(store, root, production_enrollment())
    manifest = write_manifest(tmp_path, outcome_source(production_enrollment()),
                              captured_at="2026-11-01T00:00:00Z")
    code = main([
        "--evaluation-root", str(root), "--enrollment-id", record["record_id"],
        "--claim", "production", "--outcome-manifest", str(manifest),
        "--output-root", str(tmp_path / "run"), "--evaluated-at", "2027-01-10T00:00:00Z",
    ], store=store)
    assert code == 0, capsys.readouterr().err
    printed = json.loads(capsys.readouterr().out)
    assert printed["state"] == "input_unavailable", printed
    saved = store.read_record(root, printed["record_id"])["document"]
    assert saved["result"] is None
    assert "predates the close" in saved["reason"]


def test_market_cli_refuses_a_raw_capture_stamped_in_the_future(tmp_path, capsys):
    """endpoint.as_of said 2026; the raw bytes behind it declared 2099."""
    store = real_store()
    root = tmp_path / "store"
    enrollment = market_enrollment()
    enrollment["document"]["market"]["plan_sha256"] = MARKET_POLICY_SHA
    record = enrolled(store, root, enrollment)
    payload = b'{"capture": "day90"}'
    manifest = write_manifest(tmp_path, endpoint_source(enrollment, as_of="2026-12-08T00:00:00Z"),
                              name="capture.json", payload=payload,
                              captured_at="2099-12-08T00:00:00Z")
    captures = [{"as_of": "2026-12-08T00:00:00Z",
                 "sha256": hashlib.sha256(payload).hexdigest(), "complete": True}]
    code = main([
        "--evaluation-root", str(root), "--enrollment-id", record["record_id"],
        "--claim", "market", "--outcome-manifest", str(manifest),
        "--capture-inventory", str(inventory_file(tmp_path, captures)),
        "--output-root", str(tmp_path / "run"), "--horizon-days", "90",
        "--evaluated-at", "2026-12-11T00:00:00Z",
    ], store=store)
    assert code == 0, capsys.readouterr().err
    printed = json.loads(capsys.readouterr().out)
    assert printed["state"] == "input_unavailable", printed
    saved = store.read_record(root, printed["record_id"])["document"]
    assert saved["result"] is None
    assert "after the evaluation instant" in saved["reason"]
