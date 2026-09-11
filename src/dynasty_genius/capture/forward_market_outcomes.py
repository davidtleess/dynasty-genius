"""Prepare the existing market study's inputs from preserved normalized captures.

This is a deterministic preparation recipe, not another scoring policy. Exact
normalized market/evidence bytes travel with history. Endpoint grades name the
original normalized bytes and are selected by the existing evaluator.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.dynasty_genius.eval.workspace_track_record import (
    ENDPOINT_SCHEMA,
    PREPARED_ROLE,
    select_endpoint,
)


def _raw(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Capture instant requires a timezone")
    return parsed


def _stamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Cycle instant requires a timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _checked(capture: dict) -> tuple[dict, dict, dict]:
    raw = capture.get("market_bytes")
    if not isinstance(raw, bytes):
        raise ValueError("Capture has no normalized market bytes")
    market = json.loads(raw)
    if market.get("retrieved_at") != capture.get("as_of"):
        raise ValueError("Capture as_of disagrees with normalized market bytes")
    moment = _instant(capture["as_of"])
    if moment.astimezone(timezone.utc).date().isoformat() != market.get("snapshot_date"):
        raise ValueError("Capture date disagrees with retrieval instant")
    known = _instant(capture["known_at"])
    observed = _instant(capture["observed_at"])
    if known != moment or observed < known:
        raise ValueError("Capture receipt and preservation chronology disagree")
    settings = market.get("settings")
    if not isinstance(settings, dict) or not settings:
        raise ValueError("Capture has no market settings")
    configuration = {"source": market["source"], "settings_hash": market["settings_hash"], **settings}
    prices = {}
    for row in market["entries"]:
        if row.get("position") == "PICK" or not row.get("sleeper_id"):
            continue  # still present in the retained original normalized bytes
        sid = str(row["sleeper_id"])
        if sid in prices:
            raise ValueError("Duplicate player in normalized market capture")
        value = row.get("value")
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                  or not math.isfinite(value) or value < 0):
            raise ValueError("Invalid normalized market price")
        prices[sid] = value
    return market, configuration, prices


def _bytes_evidence(raw: bytes) -> dict:
    return {"sha256": _sha(raw), "base64": base64.b64encode(raw).decode("ascii")}


def build_market_history(captures: list[dict], *, now: datetime) -> dict | None:
    """Prepare a history envelope without backdating the preparation itself."""
    prepared = []
    for capture in captures:
        _, configuration, prices = _checked(capture)
        if capture.get("complete") is not True or _instant(capture["known_at"]) > now \
                or _instant(capture["observed_at"]) > now:
            continue
        evidence = capture.get("evidence")
        if not isinstance(evidence, dict) or not evidence or not all(isinstance(v, bytes) for v in evidence.values()):
            raise ValueError("Capture evidence bytes are required")
        content = {"schema_version": 1, "as_of": capture["as_of"], "complete": True,
                   "configuration": configuration, "prices": prices,
                   "reading_kind": "prepared_normalized_capture",
                   "original_http_bytes": "unavailable",
                   "normalized_capture": _bytes_evidence(capture["market_bytes"]),
                   "capture_evidence": {k: _bytes_evidence(v) for k, v in evidence.items()},
                   "preserved_at": capture["observed_at"]}
        payload = _raw(content)
        prepared.append({"capture_id": capture["capture_id"], "as_of": capture["as_of"],
                         "known_at": capture["known_at"], "sha256": _sha(payload), "raw_bytes": payload})
    if not prepared:
        return None
    prepared.sort(key=lambda c: (c["as_of"], c["sha256"]))
    inventory = _raw({"schema_version": 1, "prepared_at": _stamp(now),
                      "capture_clock": "original collector receipt retrieval time",
                      "original_http_bytes": "unavailable",
                      "captures": [{k: v for k, v in c.items() if k != "raw_bytes"} for c in prepared]})
    return {"kind": "verified_normalized_capture_inventory", "captured_at": _stamp(now),
            "source_as_of": max((c["as_of"] for c in prepared), key=_instant),
            "source_available_at": None, "source_revision": _sha(inventory),
            "source_sha256": _sha(inventory), "raw_bytes": inventory, "captures": prepared}


def _endpoint_inventory(enrollment: dict, captures: list[dict], now: datetime) -> list[dict]:
    stream = enrollment["document"]["market"]
    expected = stream.get("capture_configuration")
    if not expected or not stream.get("configuration"):
        raise ValueError("Enrollment must bind both market and league settings")
    inventory = []
    for capture in captures:
        _, actual, _ = _checked(capture)
        # Bind the grading league only after confirming the actual capture instrument.
        # Incompatible captures retain their own configuration and are rejected by selector.
        configuration = stream["configuration"] if actual == expected else actual
        knowable = _instant(capture["known_at"]) <= now and _instant(capture["observed_at"]) <= now
        inventory.append({"capture_id": capture["capture_id"], "as_of": capture["as_of"],
                          "sha256": _sha(capture["market_bytes"]),
                          "complete": capture.get("complete") is True and knowable,
                          "configuration": configuration, "capture_configuration": actual,
                          "known_at": capture["known_at"], "observed_at": capture["observed_at"]})
    return inventory


def select_market_endpoint(*, enrollment: dict, captures: list[dict], now: datetime,
                           horizon_days: int) -> dict:
    return select_endpoint(inventory=_endpoint_inventory(enrollment, captures, now),
                           t0=enrollment["document"]["market"]["t0"], horizon_days=horizon_days,
                           configuration=enrollment["document"]["market"]["configuration"],
                           evaluated_at=_stamp(now))


def prepare_market_outcome(*, enrollment: dict, captures: list[dict], now: datetime,
                           horizon_days: int, output_root: Path) -> dict:
    """Prepare exact selected endpoint sources for the existing grading CLI.

    Call only for due/expired work. Caller owns locking and validates output roots.
    This function exclusively creates a new directory and never revises a prior run.
    """
    inventory = _endpoint_inventory(enrollment, captures, now)
    selection = select_market_endpoint(enrollment=enrollment, captures=captures, now=now,
                                       horizon_days=horizon_days)
    chosen = selection["chosen"]
    output_root = Path(output_root)
    if not output_root.is_absolute() or any(p.is_symlink() for p in (output_root, *output_root.parents)):
        raise ValueError("Outcome output must be absolute without symlinks")
    output_root.mkdir(parents=True, exist_ok=False)
    inventory_path = output_root / "inventory.json"
    inventory_raw = _raw({"captures": inventory})
    inventory_path.write_bytes(inventory_raw)
    recipe = Path(__file__).read_bytes()
    (output_root / "recipe.py").write_bytes(recipe)
    sources = [{"name": "recipe.py", "path": "recipe.py", "sha256": _sha(recipe),
                "bytes_len": len(recipe), "role": PREPARED_ROLE}]
    envelope = {"schema_version": ENDPOINT_SCHEMA, "missing_endpoint": True}
    if chosen:
        capture = next(c for c in captures if _sha(c["market_bytes"]) == chosen["sha256"]
                       and c["as_of"] == chosen["as_of"])
        _, _, prices = _checked(capture)
        payload = capture["market_bytes"]
        (output_root / "market.json").write_bytes(payload)
        sources.append({"name": "market.json", "path": "market.json", "sha256": _sha(payload),
                        "bytes_len": len(payload), "role": "normalized_collector_capture",
                        "captured_at": capture["as_of"], "preserved_at": capture["observed_at"],
                        "original_http_bytes": "unavailable"})
        # Exact independent capture attestation remains with the endpoint grade, too.
        evidence_raw = _raw({k: _bytes_evidence(v) for k, v in capture["evidence"].items()})
        (output_root / "capture-evidence.json").write_bytes(evidence_raw)
        sources.append({"name": "capture-evidence.json", "path": "capture-evidence.json",
                        "sha256": _sha(evidence_raw), "bytes_len": len(evidence_raw), "role": PREPARED_ROLE})
        envelope = {"schema_version": ENDPOINT_SCHEMA, "as_of": chosen["as_of"], "complete": True,
                    "configuration": chosen["configuration"], "endpoint_source_name": "market.json",
                    "prices": {sid: {"price": value, "reason": "price missing in source" if value is None else None}
                               for sid, value in prices.items()}}
    else:
        sources.append({"name": "inventory.json", "path": "inventory.json", "sha256": _sha(inventory_raw),
                        "bytes_len": len(inventory_raw), "role": PREPARED_ROLE})
    manifest = {"sources": sources, "envelope": envelope,
                "preparation": {"recipe": "forward_market_outcomes_v1", "recipe_sha256": _sha(recipe),
                                "inputs": [s["name"] for s in sources],
                                "rule": "Known player IDs retain source value including zero/null; PICKS stay outside player prices; no price imputation. League binding requires exact enrolled market instrument."}}
    manifest_path = output_root / "outcome-manifest.json"
    manifest_path.write_bytes(_raw(manifest))
    return {"selection": selection, "manifest_path": manifest_path, "inventory_path": inventory_path}
