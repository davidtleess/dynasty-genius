"""DG-223: preserve a receipted FantasyCalc capture from the normalized store, honestly.

The adapter reads a store it must never write and a receipt it must never synthesize. Every test
here exists because one of those two could be quietly violated and still look like success.

The central fact the whole module is shaped around: **the original HTTP bytes are gone.** What
survives is the collector's success receipt and normalized rows whose per-row content addresses
re-derive from the stored values. Together those attest a complete capture; separately neither does.
A capture that cannot be attested that way is unavailable, never reconstructed into something that
hashes cleanly.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.dynasty_genius.capture.fc_capture_adapter import (
    CaptureAdapterError,
    CorruptCaptureError,
    capture_market_inventory,
)

RETRIEVED = "2026-09-10T13:00:03.986733+00:00"
SNAPSHOT = "2026-09-10"
SOURCE = "fc_native"
SETTINGS_HASH = "e27351d720e9fcf0"
ENDPOINT = (
    "https://api.fantasycalc.com/values/current"
    "?isDynasty=true&numQbs=2&numTeams=12&ppr=1"
)
OBSERVED = datetime(2026, 9, 10, 23, 45, tzinfo=timezone.utc)

HASHED_FIELDS = (
    "sleeper_id", "player_name", "position", "value", "overall_rank",
    "position_rank", "trend_30day", "market_volatility", "market_volatility_status",
)
COLUMNS = (
    "snapshot_date", "source", "settings_hash", "player_key", "sleeper_id", "player_name",
    "position", "value", "overall_rank", "position_rank", "trend_30day", "retrieved_at",
    "payload_hash", "market_volatility", "market_volatility_status",
)


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def make_row(player_key, name, position, value, rank, *, volatility=None, sleeper_id=None,
             snapshot_date=SNAPSHOT, retrieved_at=RETRIEVED):
    """One stored row whose payload_hash re-derives from its own stored values."""
    sleeper_id = player_key.split(":", 1)[1] if sleeper_id is None else sleeper_id
    status = "captured" if volatility is not None else "source_omitted"
    content = {
        "sleeper_id": sleeper_id, "player_name": name, "position": position, "value": value,
        "overall_rank": rank, "position_rank": rank, "trend_30day": None,
        "market_volatility": volatility, "market_volatility_status": status,
    }
    return {
        "snapshot_date": snapshot_date, "source": SOURCE, "settings_hash": SETTINGS_HASH,
        "player_key": player_key, "sleeper_id": sleeper_id, "player_name": name,
        "position": position, "value": value, "overall_rank": rank, "position_rank": rank,
        "trend_30day": None, "retrieved_at": retrieved_at, "payload_hash": digest(content),
        "market_volatility": volatility, "market_volatility_status": status,
    }


def cohort(snapshot_date=SNAPSHOT, retrieved_at=RETRIEVED):
    """A capture that looks like the real one: skill rows, a PICK, an unresolved position,
    a missing volatility and a present one."""
    return [
        make_row("sleeper:4034", "Alvin Kamara", "RB", 2100, 40, volatility=2.0,
                 snapshot_date=snapshot_date, retrieved_at=retrieved_at),
        make_row("sleeper:6794", "Justin Jefferson", "WR", 9100, 3,
                 snapshot_date=snapshot_date, retrieved_at=retrieved_at),
        make_row("sleeper:12530", "Travis Hunter", "UNK", 1601, 120,
                 snapshot_date=snapshot_date, retrieved_at=retrieved_at),
        make_row("sleeper:DP_0_0", "2026 Pick 1.01", "PICK", 7257, 12, sleeper_id="DP_0_0",
                 snapshot_date=snapshot_date, retrieved_at=retrieved_at),
    ]


def store_hash_of(rows) -> str:
    return digest({"sigs": sorted(r["player_key"] + ":" + r["payload_hash"] for r in rows)})


def write_source_db(path: Path, *captures) -> Path:
    conn = sqlite3.connect(path)
    cols = ",\n ".join(f"{c} TEXT" if c not in
                       ("value", "overall_rank", "position_rank", "trend_30day", "market_volatility")
                       else f"{c} {'REAL' if c == 'market_volatility' else 'INTEGER'}"
                       for c in COLUMNS)
    for table in ("fc_forward_capture_raw", "fc_forward_capture_joinable"):
        conn.execute(
            f"CREATE TABLE {table} (\n {cols},\n"
            " PRIMARY KEY (snapshot_date, source, settings_hash, player_key))"
        )
        for rows in captures:
            conn.executemany(
                f"INSERT INTO {table} ({','.join(COLUMNS)}) VALUES ({','.join('?' * len(COLUMNS))})",
                [tuple(r[c] for c in COLUMNS) for r in rows],
            )
    conn.commit()
    conn.close()
    return path


def write_receipt(path: Path, rows, **over) -> Path:
    report = {
        "aborted_reason": None, "decision_supported": False, "duplicate_count": 0,
        "endpoint": ENDPOINT, "joinable_rows_written": len(rows),
        "missing_sleeper_count": 0,
        "payload_hash": "a736ec9ab7d98828d172c100eb420161ed13a5ee6d9424fcd944d9e4979ca161",
        "raw_entries_written": len(rows), "retrieved_at": rows[0]["retrieved_at"],
        "settings_hash": SETTINGS_HASH, "snapshot_date": rows[0]["snapshot_date"],
        "source": SOURCE, "status": "ok", "store_hash": store_hash_of(rows),
    }
    report.update(over)
    path.write_text(json.dumps(report, indent=2, sort_keys=True))
    return path


@pytest.fixture
def world(tmp_path):
    """Two captures in the source store; only the later one carries a receipt — the real shape,
    because the collector keeps only fc_forward_capture_latest_report.json."""
    earlier = cohort("2026-09-09", "2026-09-09T13:00:01.100000+00:00")
    latest = cohort()
    db = write_source_db(tmp_path / "source.db", earlier, latest)
    receipt = write_receipt(tmp_path / "receipt.json", latest)
    return {
        "source_db": db, "latest_receipt": receipt, "store_root": tmp_path / "store",
        "observed_at": OBSERVED, "earlier": earlier, "latest": latest,
    }


def run(world, **over):
    kwargs = {k: world[k] for k in ("source_db", "latest_receipt", "store_root", "observed_at")}
    kwargs.update(over)
    return capture_market_inventory(**kwargs)


# ------------------------------------------------------------------ the happy path
def test_the_receipted_capture_is_preserved_with_the_exact_record_shape(world):
    out = run(world)
    assert out["imported"] == 1
    assert out["source_state"] == "imported"
    assert len(out["captures"]) == 1
    record = out["captures"][0]
    assert set(record) == {
        "capture_id", "as_of", "known_at", "observed_at", "complete", "market_bytes", "evidence",
    }
    assert record["complete"] is True
    assert isinstance(record["capture_id"], str) and record["capture_id"]
    assert isinstance(record["market_bytes"], bytes)
    assert isinstance(record["evidence"], dict)
    assert all(isinstance(v, bytes) for v in record["evidence"].values())


def test_known_at_is_the_original_retrieval_clock_not_the_transfer_time(world):
    """The whole point of the field. `observed_at` is when WE first kept it; `known_at` is when
    the collector actually retrieved it, and they must never be conflated."""
    record = run(world)["captures"][0]
    assert record["as_of"] == RETRIEVED
    assert record["known_at"] == RETRIEVED
    assert record["observed_at"] == OBSERVED.isoformat()
    assert record["observed_at"] != record["known_at"]


def test_the_market_pack_carries_every_row_including_pick_and_unresolved(world):
    pack = json.loads(run(world)["captures"][0]["market_bytes"])
    assert pack["schema_version"] == 1
    assert pack["source"] == SOURCE
    assert pack["settings_hash"] == SETTINGS_HASH
    assert pack["snapshot_date"] == SNAPSHOT
    assert pack["retrieved_at"] == RETRIEVED
    assert pack["settings"] == {"isDynasty": True, "numQbs": 2, "numTeams": 12, "ppr": 1}
    positions = sorted(e["position"] for e in pack["entries"])
    assert positions == ["PICK", "RB", "UNK", "WR"], "no row may be filtered out"
    assert len(pack["entries"]) == 4
    # original per-row content addresses travel unchanged
    assert {e["payload_hash"] for e in pack["entries"]} == {r["payload_hash"] for r in world["latest"]}
    # a missing volatility stays missing and stays labelled
    omitted = next(e for e in pack["entries"] if e["player_name"] == "Justin Jefferson")
    assert omitted["market_volatility"] is None
    assert omitted["market_volatility_status"] == "source_omitted"


def test_the_pack_carries_the_original_capture_report_unaltered(world):
    pack = json.loads(run(world)["captures"][0]["market_bytes"])
    original = json.loads(world["latest_receipt"].read_text())
    for key, value in original.items():
        assert pack["capture_report"][key] == value, f"{key} was altered"


def test_provenance_states_the_original_http_bytes_are_unavailable(world):
    """A reconstruction that hashes cleanly is the most convincing possible packaging for evidence
    that does not exist. The pack must say what it is."""
    record = run(world)["captures"][0]
    pack = json.loads(record["market_bytes"])
    provenance = json.dumps(pack.get("provenance"))
    assert "normalized" in provenance
    assert "unavailable" in provenance
    statement = record["evidence"]["provenance.txt"].decode()
    assert "original HTTP bytes are unavailable" in statement
    assert "not the original HTTP payload" in statement


def test_evidence_holds_the_receipt_bytes_exactly_as_written(world):
    record = run(world)["captures"][0]
    assert record["evidence"]["receipt.json"] == world["latest_receipt"].read_bytes()
    rows = json.loads(record["evidence"]["normalized_rows.json"])
    assert len(rows) == 4
    assert rows == sorted(rows, key=lambda r: r["player_key"]), "canonical order"


# ------------------------------------------------------------------ attestation must hold
def test_a_row_whose_hash_does_not_rederive_refuses_the_whole_capture(world, tmp_path):
    """The DG-050 legacy_content_shape vintage. Re-hashing it would manufacture the very
    attestation that is missing, so the capture is refused instead."""
    broken = cohort()
    broken[1]["payload_hash"] = "0" * 64
    db = write_source_db(tmp_path / "legacy.db", broken)
    receipt = write_receipt(tmp_path / "legacy_receipt.json", broken)
    with pytest.raises(CaptureAdapterError, match="content address"):
        run(world, source_db=db, latest_receipt=receipt)
    assert not (world["store_root"]).exists(), "nothing may be written on refusal"


def test_a_store_hash_that_does_not_match_the_receipt_refuses(world, tmp_path):
    receipt = write_receipt(tmp_path / "bad_store.json", world["latest"], store_hash="f" * 64)
    with pytest.raises(CaptureAdapterError, match="store_hash"):
        run(world, latest_receipt=receipt)
    assert not world["store_root"].exists()


def test_a_row_count_that_disagrees_with_the_receipt_refuses(world, tmp_path):
    receipt = write_receipt(tmp_path / "bad_count.json", world["latest"], raw_entries_written=999)
    with pytest.raises(CaptureAdapterError, match="count"):
        run(world, latest_receipt=receipt)


def test_row_metadata_disagreeing_with_the_receipt_refuses(world, tmp_path):
    rows = cohort()
    rows[0]["retrieved_at"] = "2026-09-10T14:00:00+00:00"       # one row from another moment
    db = write_source_db(tmp_path / "skew.db", rows)
    receipt = write_receipt(tmp_path / "skew_receipt.json", rows)
    receipt.write_text(json.dumps({**json.loads(receipt.read_text()), "retrieved_at": RETRIEVED}))
    with pytest.raises(CaptureAdapterError):
        run(world, source_db=db, latest_receipt=receipt)


def test_a_receipt_that_changes_mid_read_refuses_without_writing(world, monkeypatch):
    """The race the two-read rule exists for: the collector rewriting the receipt while we read
    the rows would pair one capture's receipt with another capture's rows."""
    import src.dynasty_genius.capture.fc_capture_adapter as adapter
    original = adapter._read_bytes
    calls = {"n": 0}

    def shifting(path: Path) -> bytes:
        calls["n"] += 1
        if calls["n"] > 1 and path == world["latest_receipt"]:
            return original(path) + b" "          # same capture, different bytes
        return original(path)

    monkeypatch.setattr(adapter, "_read_bytes", shifting)
    with pytest.raises(CaptureAdapterError, match="changed while"):
        run(world)
    assert not world["store_root"].exists()


# ------------------------------------------------------------------ absence is not corruption
def test_a_receipt_that_is_not_a_success_waits_rather_than_failing(world, tmp_path):
    receipt = write_receipt(tmp_path / "aborted.json", world["latest"],
                            status="aborted", aborted_reason="fatal_http_503")
    out = run(world, latest_receipt=receipt)
    assert out["source_state"] == "waiting"
    assert out["imported"] == 0
    assert out["captures"] == []
    assert any("aborted" in reason for reason in out["history_unavailable"])


def test_a_missing_receipt_waits(world, tmp_path):
    out = run(world, latest_receipt=tmp_path / "not_written_yet.json")
    assert out["source_state"] == "waiting"
    assert out["imported"] == 0


def test_a_receipt_naming_a_date_the_store_does_not_hold_waits(world, tmp_path):
    receipt = write_receipt(tmp_path / "ahead.json", world["latest"], snapshot_date="2026-09-11")
    out = run(world, latest_receipt=receipt)
    assert out["source_state"] == "waiting"
    assert not world["store_root"].exists()


# ------------------------------------------------------------------ append-only and idempotent
def test_an_identical_second_poll_keeps_the_first_observed_at_and_writes_nothing_new(world):
    first = run(world)
    later = OBSERVED + timedelta(hours=6)
    second = run(world, observed_at=later)
    assert second["imported"] == 0
    assert second["source_state"] == "unchanged"
    assert len(second["captures"]) == 1
    assert second["captures"][0]["observed_at"] == OBSERVED.isoformat(), "first preservation wins"
    assert second["captures"][0]["capture_id"] == first["captures"][0]["capture_id"]
    stored = list((world["store_root"]).rglob("market.json"))
    assert len(stored) == 1, "append-only must not duplicate an identical capture"


def test_a_corrected_capture_for_the_same_date_refuses_rather_than_overwriting(world, tmp_path):
    """Same identity key, different content. Silently replacing it would rewrite history."""
    run(world)
    corrected = cohort()
    corrected[0]["value"] = 2222
    corrected[0]["payload_hash"] = digest({
        "sleeper_id": "4034", "player_name": "Alvin Kamara", "position": "RB", "value": 2222,
        "overall_rank": 40, "position_rank": 40, "trend_30day": None,
        "market_volatility": 2.0, "market_volatility_status": "captured",
    })
    db = write_source_db(tmp_path / "corrected.db", corrected)
    receipt = write_receipt(tmp_path / "corrected_receipt.json", corrected)
    with pytest.raises(CaptureAdapterError, match="conflict"):
        run(world, source_db=db, latest_receipt=receipt)
    assert len(list(world["store_root"].rglob("market.json"))) == 1


def test_a_later_date_appends_beside_the_first(world, tmp_path):
    run(world)
    tomorrow = cohort("2026-09-11", "2026-09-11T13:00:02.500000+00:00")
    db = write_source_db(tmp_path / "next.db", world["latest"], tomorrow)
    receipt = write_receipt(tmp_path / "next_receipt.json", tomorrow)
    out = run(world, source_db=db, latest_receipt=receipt,
              observed_at=OBSERVED + timedelta(days=1))
    assert out["imported"] == 1
    assert len(out["captures"]) == 2
    assert sorted(r["as_of"] for r in out["captures"]) == [
        RETRIEVED, "2026-09-11T13:00:02.500000+00:00",
    ]


def test_a_tampered_stored_capture_is_an_error_not_a_silent_reread(world):
    run(world)
    pack = next(world["store_root"].rglob("market.json"))
    pack.write_bytes(pack.read_bytes().replace(b"Kamara", b"Kamera"))
    with pytest.raises(CaptureAdapterError, match="corrupt"):
        run(world)


# ------------------------------------------------------------------ it must not write the source
def test_the_source_store_and_receipt_are_never_written(world):
    before = (world["source_db"].read_bytes(), world["latest_receipt"].read_bytes())
    run(world)
    run(world, observed_at=OBSERVED + timedelta(hours=1))
    assert (world["source_db"].read_bytes(), world["latest_receipt"].read_bytes()) == before
    assert not world["source_db"].with_suffix(".db-wal").exists()
    assert not world["source_db"].with_suffix(".db-journal").exists()


def test_a_store_root_inside_the_shared_data_tree_is_refused(world):
    with pytest.raises(CaptureAdapterError, match="private"):
        run(world, store_root=Path("/Users/davidleess/dynasty-genius-product/app/data/dg223"))


def test_a_symlinked_store_root_is_refused(world, tmp_path):
    real = tmp_path / "real_store"
    real.mkdir()
    link = tmp_path / "linked_store"
    link.symlink_to(real)
    with pytest.raises(CaptureAdapterError, match="symlink"):
        run(world, store_root=link)


# ------------------------------------------------------------------ honest unavailability
def test_history_without_its_own_receipt_is_named_unavailable_never_imported(world):
    out = run(world)
    assert len(out["captures"]) == 1, "only the receipted capture is preserved"
    reasons = " ".join(out["history_unavailable"])
    assert "2026-09-09" in reasons
    assert "receipt" in reasons
    assert "original HTTP" in reasons


def test_history_unavailable_is_a_list_of_readable_reasons(world):
    for reason in run(world)["history_unavailable"]:
        assert isinstance(reason, str) and len(reason) > 20


# ================================================================== historical receipts (DG-223b)
# The collector's stdout log preserved 64 original success receipts, 2026-06-25..2026-08-27. They are
# extracted byte-for-byte by root; this adapter validates them and never composes one.
def legacy_row(player_key, name, position, value, rank, volatility, **over):
    """A row from the pre-DG-050 era: hashed with an INTEGRAL volatility, stored in a REAL column
    that returns it as a float. The named bounded vintage, not an arbitrary reprojection."""
    row = make_row(player_key, name, position, value, rank, volatility=float(volatility), **over)
    content = {
        "sleeper_id": row["sleeper_id"], "player_name": name, "position": position, "value": value,
        "overall_rank": rank, "position_rank": rank, "trend_30day": None,
        "market_volatility": int(volatility), "market_volatility_status": "captured",
    }
    row["payload_hash"] = digest(content)          # the era's address, kept exactly as stored
    return row


def pre_schema_row(player_key, name, position, value, rank, **over):
    """Pre-Phase-0b: no volatility status at all. replay_harness:534-575 states this hash can never
    be rebuilt — it is counted, never compared, and never guessed at."""
    row = make_row(player_key, name, position, value, rank, **over)
    row["market_volatility_status"] = None
    row["payload_hash"] = "9" * 64
    return row


def test_a_historical_receipt_whose_rows_verify_is_imported(world, tmp_path):
    older = cohort("2026-08-11", "2026-08-11T13:00:00.885912+00:00")
    db = write_source_db(tmp_path / "with_history.db", older, world["latest"])
    historical = write_receipt(tmp_path / "aug11.json", older)
    out = run(world, source_db=db, historical_receipts=[historical])
    assert out["imported"] == 2
    by_date = {json.loads(r["market_bytes"])["snapshot_date"]: r for r in out["captures"]}
    assert set(by_date) == {"2026-08-11", SNAPSHOT}
    aug = by_date["2026-08-11"]
    assert aug["as_of"] == aug["known_at"] == "2026-08-11T13:00:00.885912+00:00"
    assert aug["observed_at"] == OBSERVED.isoformat(), "preserved now, retrieved then"
    assert aug["complete"] is True


def test_the_legacy_volatility_vintage_verifies_and_is_disclosed_by_name(world, tmp_path):
    rows = [
        legacy_row("sleeper:4034", "Alvin Kamara", "RB", 2100, 40, 2,
                   snapshot_date="2026-08-11", retrieved_at="2026-08-11T13:00:00.885912+00:00"),
        make_row("sleeper:6794", "Justin Jefferson", "WR", 9100, 3,
                 snapshot_date="2026-08-11", retrieved_at="2026-08-11T13:00:00.885912+00:00"),
    ]
    db = write_source_db(tmp_path / "legacy_hist.db", rows, world["latest"])
    historical = write_receipt(tmp_path / "legacy_hist.json", rows)
    out = run(world, source_db=db, historical_receipts=[historical])
    assert out["imported"] == 2
    aug = next(r for r in out["captures"]
               if json.loads(r["market_bytes"])["snapshot_date"] == "2026-08-11")
    pack = json.loads(aug["market_bytes"])
    assert pack["provenance"]["row_hash_convention"] == "legacy_integral_volatility"
    assert pack["provenance"]["rows_verified_legacy"] == 1
    assert pack["provenance"]["rows_verified_current"] == 1
    # the stored addresses travel unchanged; nothing was rehashed to make it fit
    assert {e["payload_hash"] for e in pack["entries"]} == {r["payload_hash"] for r in rows}


def test_a_pre_schema_capture_is_unavailable_with_its_cause_never_archived(world, tmp_path):
    rows = [pre_schema_row("sleeper:4034", "Alvin Kamara", "RB", 2100, 40,
                           snapshot_date="2026-06-24", retrieved_at="2026-06-24T14:37:40.311722+00:00")]
    db = write_source_db(tmp_path / "preschema.db", rows, world["latest"])
    historical = write_receipt(tmp_path / "june24.json", rows)
    out = run(world, source_db=db, historical_receipts=[historical])
    assert out["imported"] == 1, "only the current capture"
    dates = {json.loads(r["market_bytes"])["snapshot_date"] for r in out["captures"]}
    assert "2026-06-24" not in dates
    reason = next(r for r in out["history_unavailable"] if "2026-06-24" in r)
    assert "market_volatility_status" in reason or "pre-Phase-0b" in reason
    assert "never" in reason or "cannot" in reason


def test_a_row_that_has_an_address_and_does_not_match_it_raises_on_the_historical_path_too(
    world, tmp_path
):
    """The asymmetry this test used to encode: the same tampering raised on the current path and
    became a quiet note on the historical one. A row carrying a content address that will not
    re-derive is a disagreement, not a missing vintage, and it must not sit in the unavailable
    list beside legitimately old captures."""
    rows = cohort("2026-08-11", "2026-08-11T13:00:00.885912+00:00")
    rows[1]["payload_hash"] = "3" * 64
    db = write_source_db(tmp_path / "bad_hist.db", rows, world["latest"])
    historical = write_receipt(tmp_path / "bad_hist.json", rows)
    with pytest.raises(CorruptCaptureError, match="content address"):
        run(world, source_db=db, historical_receipts=[historical])


def test_corruption_and_an_unsupported_vintage_are_different_outcomes(world, tmp_path):
    """Opposite facts: an absent address is an absence; a present one that fails is a fault."""
    pre = [pre_schema_row("sleeper:4034", "Alvin Kamara", "RB", 2100, 40,
                          snapshot_date="2026-06-24",
                          retrieved_at="2026-06-24T14:37:40.311722+00:00")]
    db = write_source_db(tmp_path / "both.db", pre, world["latest"])
    out = run(world, source_db=db,
              historical_receipts=[write_receipt(tmp_path / "pre.json", pre)])
    assert out["imported"] == 1, "the vintage is skipped, the reading continues"
    assert any("2026-06-24" in reason for reason in out["history_unavailable"])


def test_a_historical_store_hash_disagreement_is_an_error_not_a_skip(world, tmp_path):
    """A receipt and a store that disagree about the same batch is an integrity fault, not an
    unsupported vintage. It must not be quietly filed as unavailable."""
    older = cohort("2026-08-11", "2026-08-11T13:00:00.885912+00:00")
    db = write_source_db(tmp_path / "hist.db", older, world["latest"])
    historical = write_receipt(tmp_path / "wrong_store.json", older, store_hash="e" * 64)
    with pytest.raises(CaptureAdapterError, match="store_hash"):
        run(world, source_db=db, historical_receipts=[historical])


def test_the_historical_receipt_bytes_are_preserved_exactly_as_extracted(world, tmp_path):
    older = cohort("2026-08-11", "2026-08-11T13:00:00.885912+00:00")
    db = write_source_db(tmp_path / "hist2.db", older, world["latest"])
    historical = write_receipt(tmp_path / "aug11_exact.json", older)
    out = run(world, source_db=db, historical_receipts=[historical])
    aug = next(r for r in out["captures"]
               if json.loads(r["market_bytes"])["snapshot_date"] == "2026-08-11")
    assert aug["evidence"]["receipt.json"] == historical.read_bytes()
    assert json.loads(aug["market_bytes"])["capture_report"] == json.loads(historical.read_text())


def test_a_historical_receipt_for_a_date_the_store_lacks_is_unavailable_not_an_error(world, tmp_path):
    absent = cohort("2026-07-15", "2026-07-15T13:00:00.000000+00:00")
    historical = write_receipt(tmp_path / "missing_rows.json", absent)
    out = run(world, historical_receipts=[historical])
    assert out["imported"] == 1
    assert any("2026-07-15" in reason for reason in out["history_unavailable"])


def test_historical_imports_are_idempotent_across_polls(world, tmp_path):
    older = cohort("2026-08-11", "2026-08-11T13:00:00.885912+00:00")
    db = write_source_db(tmp_path / "hist3.db", older, world["latest"])
    historical = write_receipt(tmp_path / "aug11_idem.json", older)
    first = run(world, source_db=db, historical_receipts=[historical])
    second = run(world, source_db=db, historical_receipts=[historical],
                 observed_at=OBSERVED + timedelta(days=1))
    assert first["imported"] == 2 and second["imported"] == 0
    assert second["source_state"] == "unchanged"
    assert len(list(world["store_root"].rglob("market.json"))) == 2
    assert {r["observed_at"] for r in second["captures"]} == {OBSERVED.isoformat()}


def test_omitting_historical_receipts_keeps_the_original_behaviour(world):
    """The parameter is additive: a caller that does not pass it sees exactly what it saw before."""
    out = run(world)
    assert out["imported"] == 1 and len(out["captures"]) == 1


# ================================================================== review blockers (DG-225)
def test_the_rows_are_read_once_so_a_capture_in_flight_is_not_an_integrity_fault(world, monkeypatch):
    """BLOCKER 1. The mid-read guard brackets a read whose result must be the one preserved.

    If the rows were read again after the guard, a row appended between the two reads would make
    the receipt's count disagree with the second read — reporting an ordinary capture in flight as
    a receipt/store integrity fault, which is exactly the distinction this module must keep.
    """
    import src.dynasty_genius.capture.fc_capture_adapter as adapter
    original = adapter._rows_for
    calls = {"n": 0}

    def growing(source_db, receipt):
        calls["n"] += 1
        rows = original(source_db, receipt)
        if calls["n"] > 1:                       # a later read sees the collector's next row
            extra = dict(rows[0])
            extra["player_key"] = "sleeper:99999"
            rows = rows + [extra]
        return rows

    monkeypatch.setattr(adapter, "_rows_for", growing)
    out = run(world)
    assert calls["n"] == 1, "the rows must be read exactly once per capture"
    assert out["imported"] == 1
    assert len(json.loads(out["captures"][0]["market_bytes"])["entries"]) == 4


def test_staging_debris_from_an_interrupted_write_does_not_poison_later_calls(world):
    """BLOCKER 2. A crash mid-write left a directory that made every future reading fail — the
    same shape as the DG-215 lock wedge, where abandoned state blocked all later runs."""
    run(world)
    debris = world["store_root"] / "captures" / ".partial-abandoned"
    (debris / "evidence").mkdir(parents=True)
    (debris / "market.json").write_bytes(b"half a capture")
    out = run(world, observed_at=OBSERVED + timedelta(hours=2))
    assert out["source_state"] == "unchanged"
    assert len(out["captures"]) == 1
    assert debris.is_dir(), "debris is ignored, not silently deleted"


def test_two_interrupted_attempts_cannot_mix_their_bytes(world):
    """Each attempt stages in its own directory, so a leftover is never reused."""
    run(world)
    roots = {path.name for path in (world["store_root"] / "captures").iterdir()}
    assert not any(name.startswith(".partial") for name in roots), "no debris on the happy path"


def test_a_capture_holding_a_row_with_no_sleeper_id_is_complete(world, tmp_path):
    """BLOCKER 3. The joinable view holds only rows WITH a Sleeper id, so joinable < raw exactly
    when one is missing. Requiring both counts to equal the raw rows would refuse a complete
    capture the first time an unresolved id appears — and the contract says to retain them."""
    rows = cohort()
    unresolved = make_row("fc:9999", "Unresolved Rookie", "WR", 300, 250)
    unresolved["sleeper_id"] = None
    unresolved["payload_hash"] = digest({
        "sleeper_id": None, "player_name": "Unresolved Rookie", "position": "WR", "value": 300,
        "overall_rank": 250, "position_rank": 250, "trend_30day": None,
        "market_volatility": None, "market_volatility_status": "source_omitted",
    })
    rows = rows + [unresolved]
    db = write_source_db(tmp_path / "unresolved.db", rows)
    receipt = write_receipt(tmp_path / "unresolved_receipt.json", rows,
                            joinable_rows_written=len(rows) - 1, missing_sleeper_count=1)
    out = run(world, source_db=db, latest_receipt=receipt)
    assert out["imported"] == 1
    entries = json.loads(out["captures"][0]["market_bytes"])["entries"]
    assert len(entries) == len(rows), "the unresolved row is retained, not filtered"
    assert any(e["sleeper_id"] is None for e in entries)


def test_a_missing_sleeper_count_that_does_not_match_the_stored_rows_refuses(world, tmp_path):
    rows = cohort()
    receipt = write_receipt(tmp_path / "lying_count.json", rows,
                            joinable_rows_written=len(rows) - 1, missing_sleeper_count=1)
    with pytest.raises(CaptureAdapterError, match="Sleeper id"):
        run(world, latest_receipt=receipt)


def test_a_consistently_edited_capture_json_still_fails(world):
    """MINOR. capture.json is not itself hash-protected, so its claimed identity is bound to the
    bytes it describes: editing the payload AND its recorded digest together still fails."""
    run(world)
    directory = next(world["store_root"].rglob("market.json")).parent
    tampered = (directory / "market.json").read_bytes().replace(b"Kamara", b"Kamera")
    (directory / "market.json").write_bytes(tampered)
    meta = json.loads((directory / "capture.json").read_text())
    meta["market_sha256"] = hashlib.sha256(tampered).hexdigest()      # a consistent edit
    (directory / "capture.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
    with pytest.raises(CaptureAdapterError, match="capture_id"):
        run(world)


def test_every_entry_carries_what_the_real_consumer_cross_checks(world):
    """market_ranks._build (:266-271) requires each entry to repeat snapshot_date, source,
    settings_hash and retrieved_at and to match the pack's top level. A pack that omits them
    reads fine and fails the factory, which is how this was missed the first time."""
    pack = json.loads(run(world)["captures"][0]["market_bytes"])
    expected = {
        "snapshot_date", "source", "settings_hash", "player_key", "sleeper_id", "player_name",
        "position", "value", "overall_rank", "position_rank", "trend_30day", "retrieved_at",
        "payload_hash", "market_volatility", "market_volatility_status",
    }
    for entry in pack["entries"]:
        assert set(entry) == expected, "entry keys must equal the frozen verified pack's"
        for key in ("source", "snapshot_date", "settings_hash", "retrieved_at"):
            assert entry[key] == pack[key], f"{key} must agree with the pack's top level"


def test_the_row_content_hash_the_consumer_recomputes_still_verifies(world):
    """market_ranks recomputes each row's address over its own field set; the entries must carry
    those fields with the values the address was taken over."""
    pack = json.loads(run(world)["captures"][0]["market_bytes"])
    for entry in pack["entries"]:
        content = {field: entry[field] for field in HASHED_FIELDS}
        assert digest(content) == entry["payload_hash"]


def test_a_store_root_under_a_symlinked_parent_is_refused(world, tmp_path):
    """Not only the leaf: a symlinked ancestor redirects the write just as completely."""
    real = tmp_path / "elsewhere"
    real.mkdir()
    link = tmp_path / "linked_parent"
    link.symlink_to(real)
    with pytest.raises(CaptureAdapterError, match="symlink"):
        run(world, store_root=link / "store")


def test_an_evidence_name_that_is_a_path_is_refused_on_read(world):
    """A stored name builds a path on read, so a separator would reach outside the capture."""
    run(world)
    directory = next(world["store_root"].rglob("market.json")).parent
    meta = json.loads((directory / "capture.json").read_text())
    meta["evidence_sha256"] = {"../escape.json": "0" * 64}
    (directory / "capture.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
    with pytest.raises(CaptureAdapterError, match="plain filename"):
        run(world)


def test_a_capture_moved_into_another_identity_slot_is_refused(world):
    run(world)
    directory = next(world["store_root"].rglob("market.json")).parent
    moved = directory.with_name("fc_native__deadbeefdeadbeef__2026-01-01__0000000000000000")
    directory.rename(moved)
    with pytest.raises(CaptureAdapterError, match="directory does not match"):
        run(world)


def test_a_current_convention_pack_passes_the_real_consumers_own_row_checks(world):
    """The consumer's actual constants and hash function, not a copy of them here."""
    from src.dynasty_genius.ranking.market_ranks import ROW_HASH_FIELDS
    from src.dynasty_genius.ranking.market_ranks import digest as consumer_digest

    pack = json.loads(run(world)["captures"][0]["market_bytes"])
    assert pack["provenance"]["row_hash_convention"] == "current"
    for entry in pack["entries"]:
        assert consumer_digest({k: entry[k] for k in ROW_HASH_FIELDS}) == entry["payload_hash"]
        assert all(entry[k] == pack[k]
                   for k in ("source", "snapshot_date", "settings_hash", "retrieved_at"))


def test_a_legacy_vintage_pack_is_labelled_because_the_strict_consumer_will_reject_it(
    world, tmp_path
):
    """Measured on the real store: `market_ranks` recomputes row addresses under the CURRENT
    convention only, so 8,311 of 23,089 entries across the 49 legacy packs fail its check. That is
    correct behaviour on both sides — those packs are the baseline's input, never a fresh market —
    but the pack must say which vintage it is, or the rejection reads as corruption."""
    from src.dynasty_genius.ranking.market_ranks import ROW_HASH_FIELDS
    from src.dynasty_genius.ranking.market_ranks import digest as consumer_digest

    rows = [
        legacy_row("sleeper:4034", "Alvin Kamara", "RB", 2100, 40, 2,
                   snapshot_date="2026-08-11", retrieved_at="2026-08-11T13:00:00.885912+00:00"),
    ]
    db = write_source_db(tmp_path / "vintage.db", rows, world["latest"])
    out = run(world, source_db=db,
              historical_receipts=[write_receipt(tmp_path / "vintage.json", rows)])
    aug = next(r for r in out["captures"]
               if json.loads(r["market_bytes"])["snapshot_date"] == "2026-08-11")
    pack = json.loads(aug["market_bytes"])
    assert pack["provenance"]["row_hash_convention"] == "legacy_integral_volatility"
    entry = pack["entries"][0]
    assert consumer_digest({k: entry[k] for k in ROW_HASH_FIELDS}) != entry["payload_hash"], (
        "if this ever passes, the strict consumer has learned the vintage and this test's "
        "premise needs revisiting"
    )
    assert entry["payload_hash"] == rows[0]["payload_hash"], "the original address is untouched"
