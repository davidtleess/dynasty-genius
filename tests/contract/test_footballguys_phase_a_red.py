"""RED — Footballguys Phase A archive intake and monthly refresh notice.

Authority and scope
-------------------
David selected retention option 1 (full offsite raw backup) on 2026-08-10 after the
Phase A framing v25 review cleared.  This file is the prospective contract for that
choice.  It authorizes no provider contact, GREEN implementation, runtime write,
scheduler, downstream identity promotion, horizon comparison, or UI component.

The production module deliberately does not exist when this RED lands.  Tests which
exercise it fail through ``_mod``; they never skip.  Independent byte vectors and
table fixtures pass now so the future implementation cannot define its own oracle.

One injected seam
-----------------
GREEN exposes ``build_contract_driver(...)`` only as the composition root used by
the real CLI and these contracts.  The driver owns the filesystem/SQLite/process
collaborators and exposes:

* ``intake(archive_bytes=..., offering=..., fault_at=None)``;
* ``write_semantic_assertion(record)``;
* ``read_model(now=..., global_overall_status=...)``;
* ``snapshot()`` (read-only contract evidence, never production truth by itself);
* ``hold_lock()`` and ``spawn(...)`` for the closed concurrency boundary;
* ``sweep_staging()`` for the private staging namespace.

The module also exposes pure ``validate_archive_directory``, ``inspect_archive``,
serialization/hash, time-validation, and state-reducer functions.  The tests derive
expected bytes, hashes, copies, and durable residue independently.

Framing source of record:
``docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v25.md``
SHA-256 ``f44b5ab008c02206cbcba26dacab6efdfd85fcdc279282207c4ae5e99d7301ff``.
"""

from __future__ import annotations

import hashlib
import importlib
import io
import json
import stat
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

MODULE = "src.dynasty_genius.sources.footballguys_intake"
REPO_ROOT = Path(__file__).resolve().parents[2]
FRAMING = (
    REPO_ROOT
    / "docs/agent-ledger/evidence/2026-08-10/"
    "footballguys_phase_a_intake_notice_framing_claude_v25.md"
)
FRAMING_SHA256 = "f44b5ab008c02206cbcba26dacab6efdfd85fcdc279282207c4ae5e99d7301ff"

ADP_PATH = "DraftDominator.app/Contents/Resources/adp.csv"
SIDECAR_PATH = "DraftDominator.app/Contents/Resources/projections.csv"
ROLE_PATHS = {"adp": ADP_PATH, "identity_sidecar": SIDECAR_PATH}
LIMITS = {
    "archive_bytes": 64 * 1024 * 1024,
    "entries": 2048,
    "member_bytes": 64 * 1024 * 1024,
    "aggregate_bytes": 256 * 1024 * 1024,
    "compression_ratio": 100,
}
FULL_PROFILE = {
    "archive_bytes": 8_540_590,
    "entries": 259,
    "symlinks": 3,
    "aggregate_bytes": 24_723_646,
    "largest_member": 12_376_512,
    "max_ratio": 11.8766,
}

RUNTIME_PATHS = {
    "lockfile": "app/data/footballguys/intake/lifecycle.lock",
    "staging": "app/data/footballguys/intake/staging",
    "objects": "app/data/footballguys/objects",
    "receipts": "app/data/footballguys/receipts.db",
    "semantics": "app/data/footballguys/semantics.db",
    "observations": "app/data/footballguys/observations.db",
}

CONTENT_PREIMAGE = (
    "role=adp;"
    "sha256=1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9;"
    "bytes=30388\n"
    "role=identity_sidecar;"
    "sha256=25be2d5a10f92b9787009edbb6144f516f53e4421afe5f39549b6eb6ca019c3f;"
    "bytes=260688\n"
).encode()
CONTENT_ID = "201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab"
SIGNATURE_PREIMAGE = (
    "source=footballguys\n"
    "offering_id=fbg-offering-2026-08-05-a\n"
    f"content_vintage_id={CONTENT_ID}\n"
    "retrieved_at=2026-08-06T00:57:00Z\n"
    "archive_sha256=d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c\n"
    "archive_bytes=8540590\n"
).encode() + CONTENT_PREIMAGE
RECEIPT_ID = "0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e"

NOW = datetime.fromisoformat("2026-08-10T12:00:00-04:00")
RECENT = "2026-08-01T12:00:00-04:00"  # 9 New York calendar dates
DUE = "2026-07-01T12:00:00-04:00"  # 40 New York calendar dates
OLDER = "2026-06-15T12:00:00-04:00"


def _mod():
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:  # pragma: no cover - this is the intended RED
        pytest.fail(f"{MODULE} does not exist yet (RED): {exc}")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _value(result: Any, key: str) -> Any:
    if isinstance(result, dict):
        return result[key]
    return getattr(result, key)


def _error_code(exc: BaseException) -> str:
    return str(getattr(exc, "code", str(exc)))


def _zipinfo(name: str, *, symlink: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name)
    info.create_system = 3
    if symlink:
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
    else:
        info.external_attr = (stat.S_IFREG | 0o600) << 16
    return info


def _unit_zip(
    *,
    omit: str | None = None,
    selected_symlink: str | None = None,
    duplicate_role: str | None = None,
    extra: list[tuple[str, bytes, bool]] | None = None,
) -> bytes:
    """Small integration positive.  The measured 259-entry profile is separate."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for role, name, payload in (
            ("adp", ADP_PATH, b"id,adp_sleeper-sf\nGibbJa00,1\n"),
            ("identity_sidecar", SIDECAR_PATH, b"id,name,pos\nGibbJa00,Jahmyr Gibbs,RB\n"),
        ):
            if omit == role:
                continue
            info = _zipinfo(name, symlink=selected_symlink == role)
            zf.writestr(info, b"target" if selected_symlink == role else payload)
            if duplicate_role == role:
                zf.writestr(info, payload)
        # Real bundle shape includes unselected framework links. They are harmless.
        for idx in range(3):
            zf.writestr(
                _zipinfo(f"DraftDominator.app/Frameworks/link-{idx}", symlink=True),
                b"../Versions/Current",
            )
        for name, payload, symlink in extra or []:
            zf.writestr(_zipinfo(name, symlink=symlink), payload)
    return out.getvalue()


def _entry(
    name: str,
    *,
    size: int = 1,
    compressed: int = 1,
    symlink: bool = False,
    encrypted: bool = False,
    regular: bool = True,
) -> dict[str, Any]:
    return {
        "name": name,
        "file_size": size,
        "compress_size": compressed,
        "crc": 1,
        "is_symlink": symlink,
        "encrypted": encrypted,
        "is_regular": regular,
    }


def _measured_profile_entries() -> list[dict[str, Any]]:
    """259-entry metadata with the measured aggregate/largest/symlink shape."""
    entries = [
        _entry(ADP_PATH, size=30_388, compressed=10_000),
        _entry(SIDECAR_PATH, size=260_688, compressed=50_000),
        _entry("DraftDominator.app/Contents/MacOS/DraftDominator", size=12_376_512, compressed=1_042_111),
    ]
    for idx in range(3):
        entries.append(
            _entry(
                f"DraftDominator.app/Frameworks/link-{idx}",
                size=0,
                compressed=0,
                symlink=True,
                regular=False,
            )
        )
    remaining_count = FULL_PROFILE["entries"] - len(entries)
    remaining_bytes = FULL_PROFILE["aggregate_bytes"] - sum(e["file_size"] for e in entries)
    base, extra = divmod(remaining_bytes, remaining_count)
    for idx in range(remaining_count):
        size = base + (1 if idx < extra else 0)
        entries.append(
            _entry(
                f"DraftDominator.app/Contents/Resources/filler-{idx:03d}.dat",
                size=size,
                compressed=max(1, size // 2),
            )
        )
    assert len(entries) == 259
    assert sum(e["file_size"] for e in entries) == 24_723_646
    return entries


def _offering(
    offering_id: str = "fbg-offering-2026-08-05-a",
    retrieved_at: str = "2026-08-06T00:57:00Z",
    **overrides: Any,
) -> dict[str, Any]:
    value = {
        "source": "footballguys",
        "offering_id": offering_id,
        "retrieved_at": retrieved_at,
        "declared_by": "david",
        "provenance": "manual-paid-drop",
    }
    value.update(overrides)
    return value


def _receipt(
    ident: str,
    retrieved_at: str,
    *,
    readiness: str = "ready",
    content: str | None = None,
    analysis_ready: bool | None = None,
    valid: bool = True,
    offering_id: str | None = None,
    integrity: str = "valid",
) -> dict[str, Any]:
    return {
        "id": ident,
        "kind": "receipt",
        "offering_id": offering_id or ident,
        "retrieved_at": retrieved_at,
        "readiness": readiness,
        "retention": "retained",
        "content_vintage_id": content or f"content-{ident}",
        "analysis_ready": readiness == "ready" if analysis_ready is None else analysis_ready,
        "valid": valid,
        "integrity": integrity,
    }


def _observation(ident: str, retrieved_at: str, *, valid: bool = True) -> dict[str, Any]:
    return {
        "id": ident,
        "kind": "observation",
        "offering_id": ident,
        "retrieved_at": retrieved_at,
        "readiness": "metadata_only",
        "retention": "metadata_only",
        "content_vintage_id": f"content-{ident}",
        "archive_sha256": f"{1:064x}",
        "archive_bytes": 123,
        "provenance": "manual-paid-drop",
        "analysis_ready": False,
        "valid": valid,
    }


def _expected(
    status: str,
    copy: str,
    pill: int,
    *,
    clock: str | None,
    ar: str | None,
    phase_c_open: bool = False,
) -> dict[str, Any]:
    return {
        "status": status,
        "copy": copy,
        "pill_delta": pill,
        "clock_id": clock,
        "latest_analysis_ready_id": ar,
        "phase_c_open": phase_c_open,
    }


# ---------------------------------------------------------------------------
# P0 — immutable external anchors and governance-before-first-write
# ---------------------------------------------------------------------------


def test_p0_framing_pin_is_exact() -> None:
    assert _sha(FRAMING.read_bytes()) == FRAMING_SHA256


def test_p0_source_registry_declares_market_overlay_and_fail_closed() -> None:
    from src.dynasty_genius.sources.source_registry import SOURCE_REGISTRY

    source = SOURCE_REGISTRY["footballguys"]
    assert source.roles == frozenset({"market_overlay"})
    assert source.failure_behavior == "fail_closed"
    assert source.freshness_hours is None
    assert "projection" in " ".join(source.prohibited_fields).lower()


def test_p0_daily_control_uses_one_stable_manual_bundle_id() -> None:
    from src.dynasty_genius.sources.daily_control import build_manifest

    rows = [row for row in build_manifest() if row.source == "footballguys"]
    assert len(rows) == 1
    row = rows[0]
    assert row.mode == "manual_download"
    assert row.registry_sources == ("footballguys",)
    assert row.connection_method == "manual_export_download"
    assert row.drop_location is not None
    assert row.paid_gated is True


IGNORE_CASES = (
    "app/data/footballguys/intake/lifecycle.lock",
    "app/data/footballguys/intake/staging/stage-abc.tmp",
    "app/data/footballguys/objects/" + "a" * 64 + ".zip",
    "app/data/footballguys/receipts.db",
    "app/data/footballguys/receipts.db-wal",
    "app/data/footballguys/receipts.db-shm",
    "app/data/footballguys/receipts.db-journal",
    "app/data/footballguys/semantics.db",
    "app/data/footballguys/semantics.db-wal",
    "app/data/footballguys/semantics.db-shm",
    "app/data/footballguys/observations.db",
    "app/data/footballguys/observations.db-wal",
    "app/data/footballguys/observations.db-shm",
)


@pytest.mark.parametrize("path", IGNORE_CASES, ids=lambda p: p.rsplit("/", 1)[-1])
def test_p0_runtime_paths_are_narrowly_gitignored(path: str) -> None:
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", path],
        cwd=REPO_ROOT,
        check=False,
    )
    assert result.returncode == 0, f"runtime path remains commit-eligible: {path}"


@pytest.mark.parametrize(
    "path",
    (
        "docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_red.md",
        "app/config/backup_manifest.json",
        "tests/contract/test_footballguys_phase_a_red.py",
    ),
)
def test_p0_ignore_rule_does_not_hide_commit_intended_paths(path: str) -> None:
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", path],
        cwd=REPO_ROOT,
        check=False,
    )
    assert result.returncode == 1, f"ignore rule is broader than the runtime namespace: {path}"


MANIFEST_REQUIREMENTS = {
    # PRE-CAPTURE EPOCH ONLY. DGX-02 correctly aborts a required directory that
    # expands to zero files, and objects/ is empty until David authorizes the first
    # real paid drop. Presence as an OPTIONAL directory is coverage before first
    # write without breaking the nightly backup. The first-real-capture change set
    # MUST amend this expectation to True and land the manifest flip in the same
    # reviewed act, before any provider byte is written. This is a landing-order
    # obligation, not permission for a forever-optional irreplaceable store.
    "app/data/footballguys/objects": ("directory", False),
    "app/data/footballguys/receipts.db": ("sqlite", True),
    "app/data/footballguys/semantics.db": ("sqlite", True),
    # Option 3 is not the active write mode. Its transition/counterpart store is
    # declared now so it is backed up if present, without making an absent inactive
    # store fail the option-1 backup run.
    "app/data/footballguys/observations.db": ("sqlite", False),
}


@pytest.mark.parametrize(
    "path_contract",
    tuple(MANIFEST_REQUIREMENTS.items()),
    ids=[path.rsplit("/", 1)[-1] for path in MANIFEST_REQUIREMENTS],
)
def test_p0_option1_manifest_covers_every_durable_store(
    path_contract: tuple[str, tuple[str, bool]],
) -> None:
    path, (kind, required) = path_contract
    payload = json.loads((REPO_ROOT / "app/config/backup_manifest.json").read_text())
    rows = payload["required"] + payload.get("optional", [])
    matches = [row for row in rows if row.get("path") == path]
    assert matches == [{"path": path, "required": required, "kind": kind}]


# ---------------------------------------------------------------------------
# A — archive reader: exact roles, untrusted ZIP, measured caps
# ---------------------------------------------------------------------------


def test_a0_contract_constants_are_independent_and_exact() -> None:
    m = _mod()
    assert m.ROLE_PATHS == ROLE_PATHS
    assert m.ARCHIVE_LIMITS == LIMITS
    assert m.RUNTIME_PATHS == RUNTIME_PATHS
    assert m.ACTIVE_RETENTION_MODE == "full_offsite"


def test_a1_small_unit_positive_selects_only_roles_and_ignores_unselected_symlinks() -> None:
    m = _mod()
    opened: list[str] = []
    result = m.inspect_archive(
        _unit_zip(), role_paths=ROLE_PATHS, limits=LIMITS, member_observer=opened.append
    )
    assert opened == [ADP_PATH, SIDECAR_PATH]
    assert tuple(result["roles"]) == ("adp", "identity_sidecar")
    assert result["role_records"][0]["role"] == "adp"
    assert result["role_records"][1]["role"] == "identity_sidecar"


def test_a2_measured_complete_profile_is_an_acceptance_control_not_a_toy() -> None:
    m = _mod()
    entries = _measured_profile_entries()
    assert len(entries) == FULL_PROFILE["entries"]
    assert sum(row["is_symlink"] for row in entries) == FULL_PROFILE["symlinks"]
    assert sum(row["file_size"] for row in entries) == FULL_PROFILE["aggregate_bytes"]
    result = m.validate_archive_directory(
        entries,
        archive_bytes=FULL_PROFILE["archive_bytes"],
        role_paths=ROLE_PATHS,
        limits=LIMITS,
    )
    assert result["accepted"] is True


DIRECTORY_REFUSALS = (
    ("missing_adp", [_entry(SIDECAR_PATH)], "missing_role:adp"),
    ("missing_sidecar", [_entry(ADP_PATH)], "missing_role:identity_sidecar"),
    ("selected_adp_symlink", [_entry(ADP_PATH, symlink=True), _entry(SIDECAR_PATH)], "selected_not_regular"),
    ("selected_encrypted", [_entry(ADP_PATH, encrypted=True), _entry(SIDECAR_PATH)], "selected_encrypted"),
    ("selected_special", [_entry(ADP_PATH, regular=False), _entry(SIDECAR_PATH)], "selected_not_regular"),
    ("absolute_selected", [_entry("/" + ADP_PATH), _entry(SIDECAR_PATH)], "unsafe_selected_path"),
    ("drive_selected", [_entry("C:/" + ADP_PATH), _entry(SIDECAR_PATH)], "unsafe_selected_path"),
    ("dotdot_selected", [_entry("x/../" + ADP_PATH), _entry(SIDECAR_PATH)], "unsafe_selected_path"),
    ("empty_component", [_entry(ADP_PATH.replace("/Contents", "//Contents")), _entry(SIDECAR_PATH)], "unsafe_selected_path"),
    ("separator_ambiguity", [_entry(ADP_PATH.replace("/", "\\")), _entry(SIDECAR_PATH)], "unsafe_selected_path"),
    ("case_collision", [_entry(ADP_PATH), _entry(ADP_PATH.upper()), _entry(SIDECAR_PATH)], "role_name_collision"),
    ("duplicate_exact", [_entry(ADP_PATH), _entry(ADP_PATH), _entry(SIDECAR_PATH)], "duplicate_role"),
    ("zero_compressed_nonempty", [_entry(ADP_PATH, size=1, compressed=0), _entry(SIDECAR_PATH)], "invalid_compression_ratio"),
)


@pytest.mark.parametrize(
    ("name", "entries", "code"), DIRECTORY_REFUSALS, ids=[row[0] for row in DIRECTORY_REFUSALS]
)
def test_a3_directory_refusals_are_named(name: str, entries: list[dict[str, Any]], code: str) -> None:
    del name
    m = _mod()
    with pytest.raises(m.FootballguysIntakeError) as caught:
        m.validate_archive_directory(
            entries,
            archive_bytes=100,
            role_paths=ROLE_PATHS,
            limits=LIMITS,
        )
    assert _error_code(caught.value).startswith(code)


CAP_CASES = (
    ("archive_bytes", LIMITS["archive_bytes"] + 1, "archive_too_large"),
    ("entries", LIMITS["entries"] + 1, "too_many_entries"),
    ("member_bytes", LIMITS["member_bytes"] + 1, "member_too_large"),
    ("aggregate_bytes", LIMITS["aggregate_bytes"] + 1, "aggregate_too_large"),
    ("compression_ratio", LIMITS["compression_ratio"] + 0.01, "compression_ratio_too_large"),
)


@pytest.mark.parametrize(("dimension", "value", "code"), CAP_CASES, ids=[c[0] for c in CAP_CASES])
def test_a4_every_cap_is_inclusive_and_one_over_refuses(
    dimension: str, value: int | float, code: str
) -> None:
    m = _mod()
    assert m.validate_limit_boundary(dimension, LIMITS[dimension], limits=LIMITS) is True
    with pytest.raises(m.FootballguysIntakeError) as caught:
        m.validate_limit_boundary(dimension, value, limits=LIMITS)
    assert _error_code(caught.value).startswith(code)


def test_a5_decoys_never_change_exact_role_selection() -> None:
    m = _mod()
    decoys = [
        ("elsewhere/adp.csv", b"attacker", False),
        ("__MACOSX/DraftDominator.app/Contents/Resources/._adp.csv", b"fork", False),
        ("other/projections.csv", b"wrong human", False),
    ]
    clean = m.inspect_archive(_unit_zip(), role_paths=ROLE_PATHS, limits=LIMITS)
    attacked = m.inspect_archive(
        _unit_zip(extra=decoys), role_paths=ROLE_PATHS, limits=LIMITS
    )
    assert attacked["role_records"] == clean["role_records"]
    assert attacked["content_vintage_id"] == clean["content_vintage_id"]


# ---------------------------------------------------------------------------
# I — independent identity grammar and known-answer vectors
# ---------------------------------------------------------------------------


def _negative_vectors() -> dict[str, tuple[bytes, str]]:
    adp, sidecar = CONTENT_PREIMAGE.decode().splitlines()
    n1 = (sidecar + "\n" + adp + "\n").encode()
    n2 = (
        "role=adp;"
        "sha256=25be2d5a10f92b9787009edbb6144f516f53e4421afe5f39549b6eb6ca019c3f;"
        "bytes=260688\n"
        "role=identity_sidecar;"
        "sha256=1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9;"
        "bytes=30388\n"
    ).encode()
    n3 = SIGNATURE_PREIMAGE.replace(
        b"retrieved_at=2026-08-06T00:57:00Z",
        b"retrieved_at=2026-08-05T20:57:00-04:00",
    )
    n4 = SIGNATURE_PREIMAGE.replace(b"archive_bytes=8540590", b"archive_bytes=08540590")
    return {
        "N1_line_order": (n1, "86d18b7e0949cbedb64141d8ca3a934f6a2181516c0835019f98ee341c6b8605"),
        "N2_assignment": (n2, "fb6b16f63985abf2efd72b1d311217bcb8cc151c9dc58f57dfb7b8bbc6f1d86f"),
        "N3_offset_literal": (n3, "d5785e03a72b74e968b5afe8d47f06d3e84e4c93c519ab47f7334f9668bac5c8"),
        "N4_zero_padding": (n4, "d87163c387735c4d9a10774d130b0b60d02886d11700f18ccc9637a04a81caf0"),
    }


@pytest.mark.parametrize(
    ("payload", "size", "expected"),
    ((CONTENT_PREIMAGE, 200, CONTENT_ID), (SIGNATURE_PREIMAGE, 478, RECEIPT_ID)),
    ids=("content", "signature"),
)
def test_i0_independent_positive_vectors(payload: bytes, size: int, expected: str) -> None:
    assert len(payload) == size
    assert _sha(payload) == expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    tuple(_negative_vectors().values()),
    ids=tuple(_negative_vectors()),
)
def test_i1_independent_negative_vectors(payload: bytes, expected: str) -> None:
    assert _sha(payload) == expected


def test_i2_production_serializer_reproduces_independent_bytes() -> None:
    m = _mod()
    role_records = [
        {
            "role": "adp",
            "sha256": "1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9",
            "bytes": 30_388,
        },
        {
            "role": "identity_sidecar",
            "sha256": "25be2d5a10f92b9787009edbb6144f516f53e4421afe5f39549b6eb6ca019c3f",
            "bytes": 260_688,
        },
    ]
    assert m.serialize_content_vintage(role_records) == CONTENT_PREIMAGE
    assert m.content_vintage_id(role_records) == CONTENT_ID
    signature = m.serialize_offering_signature(
        source="footballguys",
        offering_id="fbg-offering-2026-08-05-a",
        content_vintage_id=CONTENT_ID,
        retrieved_at="2026-08-05T20:57:00-04:00",
        archive_sha256="d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c",
        archive_bytes=8_540_590,
        role_records=role_records,
    )
    assert signature == SIGNATURE_PREIMAGE
    assert m.receipt_id(signature) == RECEIPT_ID


@pytest.mark.parametrize(
    "invalid_value",
    ("line\nbreak", "space forbidden", "slash/forbidden", "é", "semi;colon"),
)
def test_i3_unrepresentable_values_refuse_never_escape(invalid_value: str) -> None:
    m = _mod()
    with pytest.raises(m.FootballguysIntakeError) as caught:
        m.serialize_field("offering_id", invalid_value)
    assert _error_code(caught.value).startswith("unrepresentable_signature_value")


@pytest.mark.parametrize(
    ("value", "code"),
    (
        ("2026-08-05T20:57:00", "retrieved_at_naive"),
        ("not-a-time", "retrieved_at_malformed"),
        ("2026-08-06T00:57:00.1Z", "retrieved_at_fractional_seconds"),
        ("2026-08-11T00:00:00Z", "retrieved_at_future"),
    ),
)
def test_i4_invalid_retrieval_instants_refuse_before_identity(value: str, code: str) -> None:
    m = _mod()
    with pytest.raises(m.FootballguysIntakeError) as caught:
        m.canonical_retrieved_at(value, now=NOW)
    assert _error_code(caught.value).startswith(code)


def test_i5_equivalent_offsets_make_one_identity() -> None:
    m = _mod()
    assert m.canonical_retrieved_at("2026-08-05T20:57:00-04:00", now=NOW) == "2026-08-06T00:57:00Z"
    assert m.canonical_retrieved_at("2026-08-06T00:57:00Z", now=NOW) == "2026-08-06T00:57:00Z"


def test_i6_identity_sidecar_values_are_never_model_or_market_signal() -> None:
    m = _mod()
    assert m.IDENTITY_SIDECAR_ROLE == "identity_evidence_only"
    assert m.IDENTITY_SIDECAR_SIGNAL_FIELDS == frozenset()
    assert m.MODEL_INPUT_FIELDS == frozenset()


def _assertion(
    ident: str,
    claim: str,
    *,
    version: int,
    evidence: str,
) -> dict[str, Any]:
    return {
        "key": "classic.adp_sleeper-sf.horizon",
        "assertion_id": ident,
        "version": version,
        "claim": claim,
        "evidence_id": evidence,
        "active": True,
    }


@pytest.mark.parametrize("evidence_state", ("missing", "unretained", "hash_failed"))
def test_i7_semantic_reducer_never_filters_an_unusable_challenger(
    evidence_state: str,
) -> None:
    m = _mod()
    assertions = [
        _assertion("old", "redraft", version=1, evidence="e-old"),
        _assertion("new", "dynasty_startup", version=2, evidence="e-new"),
    ]
    attachments = {
        "e-old": {"state": "retained_verified"},
        "e-new": {"state": evidence_state},
    }
    result = m.reduce_semantic_assertions(
        assertions=assertions, attachments=attachments, adjudications=[]
    )
    assert result == {
        "state": "unknown",
        "reason": "active_evidence_unverifiable",
        "eligible_for_phase_c": False,
    }


@pytest.mark.parametrize("order", (("old", "new"), ("new", "old")))
def test_i8_semantic_conflict_is_order_invariant_and_old_claim_never_wins(
    order: tuple[str, str],
) -> None:
    m = _mod()
    rows = {
        "old": _assertion("old", "redraft", version=1, evidence="e-old"),
        "new": _assertion("new", "dynasty_startup", version=2, evidence="e-new"),
    }
    result = m.reduce_semantic_assertions(
        assertions=[rows[key] for key in order],
        attachments={
            "e-old": {"state": "retained_verified"},
            "e-new": {"state": "retained_verified"},
        },
        adjudications=[],
    )
    assert result["state"] == "unknown"
    assert result["reason"] == "unresolved_assertion_conflict"
    assert result["eligible_for_phase_c"] is False


def test_i9_only_provenance_bound_parent_adjudication_resolves_semantic_conflict() -> None:
    m = _mod()
    assertions = [
        _assertion("old", "redraft", version=1, evidence="e-old"),
        _assertion("new", "dynasty_startup", version=2, evidence="e-new"),
    ]
    attachments = {
        "e-old": {"state": "retained_verified"},
        "e-new": {"state": "retained_verified"},
    }
    weak = m.reduce_semantic_assertions(
        assertions=assertions,
        attachments=attachments,
        adjudications=[{"superseded": True}],
    )
    assert weak["state"] == "unknown"
    governed = m.reduce_semantic_assertions(
        assertions=assertions,
        attachments=attachments,
        adjudications=[
            {
                "adjudication_id": "adj-1",
                "authority": "david",
                "provenance": "explicit-ruling",
                "parents": ["old", "new"],
                "effective_assertion_id": "new",
            }
        ],
    )
    assert governed == {
        "state": "known",
        "value": "dynasty_startup",
        "assertion_id": "new",
        "eligible_for_phase_c": True,
    }


# ---------------------------------------------------------------------------
# S — option-1 driver, filesystem/SQLite ordering, crash residue
# ---------------------------------------------------------------------------


def _write_manifest(root: Path, *, omit: str | None = None) -> Path:
    required_rows = []
    optional_rows = []
    for store_path, (kind, required) in MANIFEST_REQUIREMENTS.items():
        if store_path == omit:
            continue
        row = {"path": store_path, "required": required, "kind": kind}
        (required_rows if required else optional_rows).append(row)
    path = root / "app/config/backup_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "backup_manifest.v2",
                "required": required_rows,
                "optional": optional_rows,
                "exclude_paths": [],
                "exclusions": [],
            }
        )
    )
    return path


def _driver(tmp_path: Path, *, mode: str = "full_offsite", omit_coverage: str | None = None):
    m = _mod()
    return m.build_contract_driver(
        repo_root=tmp_path,
        manifest_path=_write_manifest(tmp_path, omit=omit_coverage),
        retention_mode=mode,
        clock=lambda: NOW,
    )


@pytest.mark.parametrize(
    ("fault", "code"),
    (
        ("symlinked_ancestor", "namespace_symlink"),
        ("symlinked_leaf", "namespace_symlink"),
        ("private_group_writable", "namespace_mode"),
        ("private_world_writable", "namespace_mode"),
        ("private_wrong_owner", "namespace_owner"),
    ),
)
def test_s_namespace_refuses_before_lock_stage_or_sweep(
    tmp_path: Path, fault: str, code: str
) -> None:
    driver = _driver(tmp_path)
    driver.seed_namespace_fault(fault)
    with pytest.raises(driver.error_type) as caught:
        driver.bootstrap_namespace()
    assert _error_code(caught.value).startswith(code)
    assert driver.snapshot()["trace"] == []


def test_s_namespace_missing_root_creation_converges_without_chmodding_trusted_parents(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.bootstrap_namespace(concurrent_creators=2)
    snap = driver.snapshot()
    assert snap["trusted_parent_modes"] == {
        ".": 0o755,
        "app": 0o755,
        "app/data": 0o755,
    }
    assert snap["private_node_modes"] == {
        "app/data/footballguys": 0o700,
        "app/data/footballguys/intake": 0o700,
        "app/data/footballguys/intake/staging": 0o700,
        "app/data/footballguys/objects": 0o700,
    }
    assert snap["lock_identity_count"] == 1


def test_s0_option1_success_trace_is_prepare_publish_verify_receipt_last(tmp_path: Path) -> None:
    driver = _driver(tmp_path)
    result = driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    assert result.status == "ready"
    assert result.raw_retained is True
    assert result.receipt_id is not None
    trace = driver.snapshot()["trace"]
    assert trace.count("staging_create") == 1
    assert trace.count("source_stream") == 1
    assert trace.count("receipt_transaction") == 1
    assert trace.index("staging_create") < trace.index("source_stream")
    assert trace.index("source_stream") < trace.index("archive_validate")
    assert trace.index("archive_validate") < trace.index("publish_no_replace")
    assert trace.index("publish_no_replace") < trace.index("published_inode_verify")
    assert trace.index("published_inode_verify") < trace.index("receipt_transaction")


@pytest.mark.parametrize("store", tuple(MANIFEST_REQUIREMENTS), ids=lambda p: p.rsplit("/", 1)[-1])
def test_s1_coverage_is_verified_before_each_store_first_write(tmp_path: Path, store: str) -> None:
    driver = _driver(tmp_path, omit_coverage=store)
    before = driver.snapshot()
    with pytest.raises(driver.error_type) as caught:
        driver.attempt_first_write(store)
    assert _error_code(caught.value).startswith("backup_coverage_missing")
    assert driver.snapshot() == before


def test_s2_same_content_new_offering_reuses_one_object_and_adds_one_receipt(tmp_path: Path) -> None:
    driver = _driver(tmp_path)
    payload = _unit_zip()
    first = driver.intake(archive_bytes=payload, offering=_offering("offering-a"))
    second = driver.intake(archive_bytes=payload, offering=_offering("offering-b"))
    snap = driver.snapshot()
    assert first.receipt_id != second.receipt_id
    assert len(snap["objects"]) == 1
    assert len(snap["receipts"]) == 2
    assert snap["staging_entries"] == []
    assert snap["trace"].count("receipt_transaction") == 2


def test_s3_same_offering_same_signature_is_a_true_noop(tmp_path: Path) -> None:
    driver = _driver(tmp_path)
    payload = _unit_zip()
    first = driver.intake(archive_bytes=payload, offering=_offering("offering-a"))
    before = driver.snapshot()
    second = driver.intake(archive_bytes=payload, offering=_offering("offering-a"))
    after = driver.snapshot()
    assert second.status == "noop"
    assert second.receipt_id == first.receipt_id
    assert after["objects"] == before["objects"]
    assert after["receipts"] == before["receipts"]
    assert after["staging_entries"] == []


def test_s4_same_offering_changed_signed_field_conflicts_globally(tmp_path: Path) -> None:
    driver = _driver(tmp_path)
    driver.intake(archive_bytes=_unit_zip(), offering=_offering("offering-a"))
    before = driver.snapshot()
    with pytest.raises(driver.error_type) as caught:
        driver.intake(
            archive_bytes=_unit_zip(extra=[("wrapper-only", b"different", False)]),
            offering=_offering("offering-a"),
        )
    assert _error_code(caught.value).startswith("offering_identity_conflict")
    assert driver.snapshot()["receipts"] == before["receipts"]


CRASH_CASES = (
    ("during_staged_write", "partial_staging", "sweep_remove"),
    ("after_staging_fsync", "complete_staging", "sweep_remove"),
    ("after_publish_before_dir_fsync", "canonical_optional", "reuse_or_republish"),
    ("receipt_commit_fresh", "canonical_orphan", "adopt_on_reuse"),
    ("receipt_commit_reuse", "no_new_residue", "keep_reference_set"),
)


@pytest.mark.parametrize(
    ("fault_at", "residue", "restart"), CRASH_CASES, ids=[row[0] for row in CRASH_CASES]
)
def test_s5_branch_a_crash_matrix_names_residue_and_restart(
    tmp_path: Path, fault_at: str, residue: str, restart: str
) -> None:
    driver = _driver(tmp_path)
    if fault_at == "receipt_commit_reuse":
        driver.intake(archive_bytes=_unit_zip(), offering=_offering("prior"))
    result = driver.intake(
        archive_bytes=_unit_zip(),
        offering=_offering("attempt"),
        fault_at=fault_at,
    )
    assert result.status == "failed"
    snap = driver.snapshot()
    assert snap["last_crash_residue"] == residue
    assert snap["restart_contract"] == restart
    assert all(row["offering_id"] != "attempt" for row in snap["receipts"])
    converged = driver.intake(archive_bytes=_unit_zip(), offering=_offering("attempt"))
    assert converged.status == "ready"
    assert driver.snapshot()["staging_entries"] == []


@pytest.mark.parametrize(
    "fault_at",
    ("archive_malformed", "cap_refusal", "missing_role", "crc_failure", "schema_failure", "source_read_error"),
)
def test_s6_every_failure_family_closes_the_owned_descriptor_in_a_live_process(
    tmp_path: Path, fault_at: str
) -> None:
    driver = _driver(tmp_path, mode="metadata_only")
    before = driver.snapshot()
    result = driver.intake(
        archive_bytes=_unit_zip(), offering=_offering(), fault_at=fault_at
    )
    assert result.status == "failed"
    after = driver.snapshot()
    assert after["open_raw_descriptors"] == 0
    assert after["raw_provider_entries"] == []
    assert after["observations"] == before["observations"]
    assert after["clock_id"] == before["clock_id"]
    assert after["latest_analysis_ready_id"] == before["latest_analysis_ready_id"]


def test_s7_intake_busy_is_a_control_result_with_complete_unchanged_state(tmp_path: Path) -> None:
    driver = _driver(tmp_path)
    before = driver.snapshot()
    with driver.hold_lock():
        result = driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    assert result.status == "intake_busy"
    assert result.attempt_recorded is False
    assert driver.snapshot() == before


def test_s8_process_spawn_abstraction_refuses_while_lock_is_held(tmp_path: Path) -> None:
    driver = _driver(tmp_path)
    with driver.hold_lock():
        with pytest.raises(driver.error_type) as caught:
            driver.spawn(["true"])
    assert _error_code(caught.value).startswith("spawn_while_intake_locked")


def test_s9_intake_module_has_no_direct_process_spawn_surface() -> None:
    m = _mod()
    source_path = Path(m.__file__)
    source = source_path.read_text()
    forbidden = ("os.fork", "os.posix_spawn", "subprocess.", "multiprocessing.")
    assert not [token for token in forbidden if token in source]


SWEEP_CASES = (
    ("stage-good.tmp", "regular", "remove"),
    ("stage-link.tmp", "symlink", "remove_link_only"),
    ("stage-multi.tmp", "multilink", "remove_name_only"),
    ("stage-dir.tmp", "directory", "refuse"),
    ("stage-special.tmp", "special", "refuse"),
    ("other.tmp", "regular", "untouched"),
    ("other-link.tmp", "symlink", "untouched"),
    ("other-multi.tmp", "multilink", "untouched"),
    ("other-dir.tmp", "directory", "untouched"),
    ("other-special.tmp", "special", "untouched"),
)


@pytest.mark.parametrize(
    ("name", "kind", "expected"), SWEEP_CASES, ids=[f"{r[0]}-{r[1]}" for r in SWEEP_CASES]
)
def test_s10_staging_sweep_is_grammar_first_nonrecursive_and_nofollow(
    tmp_path: Path, name: str, kind: str, expected: str
) -> None:
    driver = _driver(tmp_path)
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"untouched")
    driver.seed_staging_entry(name=name, kind=kind, symlink_target=sentinel)
    result = driver.sweep_staging()
    assert result[name] == expected
    assert sentinel.read_bytes() == b"untouched"


def test_s11_cross_device_publish_refuses_before_no_replace(tmp_path: Path) -> None:
    driver = _driver(tmp_path)
    before = driver.snapshot()
    result = driver.intake(
        archive_bytes=_unit_zip(), offering=_offering(), fault_at="cross_device"
    )
    assert result.status == "failed"
    assert result.reason == "staging_objects_cross_device"
    assert driver.snapshot()["receipts"] == before["receipts"]


def test_s12_live_wal_counterpart_read_preserves_main_and_wal_bytes(tmp_path: Path) -> None:
    driver = _driver(tmp_path)
    fixture = driver.seed_live_wal_counterpart(main=True, wal=True, shm=False, committed_row=True)
    before = driver.file_fingerprints((fixture.main, fixture.wal))
    row = driver.read_counterpart_readonly(fixture.main)
    during = driver.file_fingerprints((fixture.main, fixture.wal))
    driver.close_counterpart()
    after = driver.file_fingerprints((fixture.main, fixture.wal))
    assert row["committed"] is True
    assert before == during == after
    assert fixture.shm.exists()
    assert not fixture.wal_growth


COUNTERPART_CASES = (
    ("all_absent", "empty"),
    ("main_only_valid", "existing"),
    ("main_absent_wal", "malformed"),
    ("main_absent_shm", "malformed"),
    ("wrong_schema", "unverifiable"),
    ("wrong_journal", "unverifiable"),
    ("unreadable", "unverifiable"),
)


@pytest.mark.parametrize(
    ("shape", "expected"), COUNTERPART_CASES, ids=[row[0] for row in COUNTERPART_CASES]
)
def test_s13_counterpart_lookup_is_noncreating_tri_state(
    tmp_path: Path, shape: str, expected: str
) -> None:
    driver = _driver(tmp_path)
    before = driver.snapshot_files()
    result = driver.classify_counterpart(shape)
    assert result.state == expected
    if shape == "all_absent":
        assert driver.snapshot_files() == before


def test_s14_sqlite_wal_is_verified_before_schema_or_application_write(tmp_path: Path) -> None:
    driver = _driver(tmp_path)
    result = driver.initialize_database("receipts")
    trace = result.trace
    assert result.effective_journal_mode == "wal"
    assert trace.index("pragma_journal_mode_wal") < trace.index("schema_write")
    assert trace.index("schema_write") < trace.index("application_write")


def test_s15_online_backup_restores_uncheckpointed_committed_wal_row(tmp_path: Path) -> None:
    driver = _driver(tmp_path)
    live = driver.seed_live_wal_counterpart(main=True, wal=True, shm=True, committed_row=True)
    staged = driver.online_backup(live.main)
    restored = driver.restore_staged_backup(staged)
    assert restored.query_one("select committed from fixture") == (1,)
    assert staged.name.endswith(".db")
    assert not driver.backup_payloads_include_sidecars()


def test_s16_option1_to_option3_transition_preserves_older_raw_and_ar(tmp_path: Path) -> None:
    driver = _driver(tmp_path)
    old = driver.intake(archive_bytes=_unit_zip(), offering=_offering("old", DUE))
    before_objects = driver.snapshot()["objects"]
    driver.set_retention_mode("metadata_only")
    obs = driver.intake(archive_bytes=_unit_zip(), offering=_offering("new", RECENT))
    snap = driver.snapshot()
    assert obs.raw_retained is False
    assert snap["objects"] == before_objects
    assert snap["latest_analysis_ready_id"] == old.receipt_id
    assert snap["receipts"][-1]["receipt_id"] == old.receipt_id
    assert "archive was not retained" in driver.read_model(now=NOW)["copy"]
    assert "analysis uses the 2026-07-01 drop" in driver.read_model(now=NOW)["copy"]


def test_s17_option3_to_option1_upgrade_coalesces_one_acquisition(tmp_path: Path) -> None:
    driver = _driver(tmp_path, mode="metadata_only")
    obs = driver.intake(archive_bytes=_unit_zip(), offering=_offering("same", RECENT))
    driver.set_retention_mode("full_offsite")
    receipt = driver.intake(archive_bytes=_unit_zip(), offering=_offering("same", RECENT))
    snap = driver.snapshot()
    assert obs.observation_id == receipt.receipt_id
    assert len(snap["effective_acquisitions"]) == 1
    assert snap["effective_acquisitions"][0]["retention"] == "retained"
    assert "archive was not retained" not in driver.read_model(now=NOW)["copy"]


# ---------------------------------------------------------------------------
# C — clock arithmetic and complete literal state function
# ---------------------------------------------------------------------------


DUE_CASES = (
    ("29_days", "2026-07-12T12:00:00-04:00", "2026-08-10T12:00:00-04:00", False),
    ("30_days", "2026-07-11T12:00:00-04:00", "2026-08-10T12:00:00-04:00", True),
    ("spring_719_hours", "2026-02-07T12:00:00-05:00", "2026-03-09T12:00:00-04:00", True),
    ("spring_under_30_dates", "2026-02-08T11:00:00-05:00", "2026-03-09T12:00:00-04:00", False),
    ("fall_over_720_hours", "2026-10-05T12:00:00-04:00", "2026-11-04T12:00:00-05:00", True),
    ("month_boundary", "2026-06-30T23:59:00-04:00", "2026-07-30T00:01:00-04:00", True),
    ("year_boundary", "2025-12-31T23:59:00-05:00", "2026-01-30T00:01:00-05:00", True),
)


@pytest.mark.parametrize(
    ("name", "retrieved", "now", "expected"), DUE_CASES, ids=[row[0] for row in DUE_CASES]
)
def test_c0_due_uses_new_york_calendar_dates_not_elapsed_hours(
    name: str, retrieved: str, now: str, expected: bool
) -> None:
    del name
    m = _mod()
    assert m.is_refresh_due(retrieved_at=retrieved, now=datetime.fromisoformat(now)) is expected


def _state_cases() -> list[Any]:
    older = _receipt("older", OLDER)
    current = _receipt("current", RECENT)
    current_no_ar = _receipt(
        "current-no-ar", RECENT, readiness="review_required", analysis_ready=False
    )
    due = _receipt("due", DUE)
    review = _receipt("review", RECENT, readiness="review_required", analysis_ready=False)
    due_review = _receipt("due-review", DUE, readiness="review_required", analysis_ready=False)
    obs = _observation("obs", RECENT)
    due_obs = _observation("due-obs", DUE)
    cases: list[Any] = [
        pytest.param([], [], _expected("no_record", "No Footballguys refresh recorded", 1, clock=None, ar=None), id="row01"),
        pytest.param([], [{"status": "failed"}], _expected("no_record", "No Footballguys refresh recorded · last intake attempt failed", 1, clock=None, ar=None), id="row02"),
        pytest.param([current], [], _expected("current", "Last Footballguys refresh recorded 9 days ago", 0, clock="current", ar="current"), id="row03"),
        pytest.param([review], [], _expected("current", "Last Footballguys refresh recorded 9 days ago · latest recorded drop awaiting data review", 0, clock="review", ar=None), id="row04"),
        pytest.param([current], [{"status": "failed", "newer": True}], _expected("current", "Last Footballguys refresh recorded 9 days ago · newest attempted drop failed intake", 0, clock="current", ar="current"), id="row05"),
        pytest.param([due], [], _expected("due", "Last Footballguys refresh recorded 40 days ago — monthly refresh due", 1, clock="due", ar="due"), id="row06"),
        pytest.param([due], [{"status": "failed", "newer": True}], _expected("due", "Last Footballguys refresh recorded 40 days ago — monthly refresh due · newest attempted drop failed intake", 1, clock="due", ar="due"), id="row07"),
        pytest.param([older, review], [], _expected("current", "Last Footballguys refresh recorded 9 days ago · latest recorded drop awaiting data review · analysis uses the 2026-06-15 drop", 0, clock="review", ar="older"), id="row08"),
        pytest.param([], [{"status": "ledger_unreadable"}], _expected("unverifiable", "Footballguys refresh record unreadable", 1, clock=None, ar=None), id="row09"),
        pytest.param([obs], [], _expected("current", "Last Footballguys refresh recorded 9 days ago · latest drop metadata only — its archive was not retained", 0, clock="obs", ar=None), id="row11"),
        pytest.param([older, obs], [], _expected("current", "Last Footballguys refresh recorded 9 days ago · latest drop metadata only — its archive was not retained · analysis uses the 2026-06-15 drop", 0, clock="obs", ar="older"), id="row11b"),
        pytest.param([due_obs], [], _expected("due", "Last Footballguys refresh recorded 40 days ago — monthly refresh due · latest drop metadata only — its archive was not retained", 1, clock="due-obs", ar=None), id="row12"),
        pytest.param([older, due_obs], [], _expected("due", "Last Footballguys refresh recorded 40 days ago — monthly refresh due · latest drop metadata only — its archive was not retained · analysis uses the 2026-06-15 drop", 1, clock="due-obs", ar="older"), id="row12b"),
        pytest.param([due_review], [], _expected("due", "Last Footballguys refresh recorded 40 days ago — monthly refresh due · latest recorded drop awaiting data review", 1, clock="due-review", ar=None), id="row13a"),
        pytest.param([older, due_review], [], _expected("due", "Last Footballguys refresh recorded 40 days ago — monthly refresh due · latest recorded drop awaiting data review · analysis uses the 2026-06-15 drop", 1, clock="due-review", ar="older"), id="row13b"),
        pytest.param([], [{"status": "invalid", "reason": "future"}], _expected("unverifiable", "Footballguys refresh time unverifiable · no valid refresh recorded", 1, clock=None, ar=None), id="row14"),
        pytest.param([current], [{"status": "invalid", "newer": True}], _expected("current", "Last Footballguys refresh recorded 9 days ago · newest attempted drop's refresh time unverifiable", 0, clock="current", ar="current"), id="row15"),
        pytest.param([{"special": "same_instant_conflict", "retrieved_at": RECENT, "members": ["a", "b"]}], [], _expected("current", "Last Footballguys refresh recorded 9 days ago · multiple drops at that time disagree — data review required", 0, clock="same-instant:2026-08-01", ar=None), id="row16a"),
        pytest.param([older, {"special": "same_instant_conflict", "retrieved_at": RECENT, "members": ["a", "b"]}], [], _expected("current", "Last Footballguys refresh recorded 9 days ago · multiple drops at that time disagree — data review required · analysis uses the 2026-06-15 drop", 0, clock="same-instant:2026-08-01", ar="older"), id="row16b"),
        pytest.param([{"special": "same_instant_conflict", "retrieved_at": DUE, "members": ["a", "b"]}], [], _expected("due", "Last Footballguys refresh recorded 40 days ago — monthly refresh due · multiple drops at that time disagree — data review required", 1, clock="same-instant:2026-07-01", ar=None), id="row17a"),
        pytest.param([older, {"special": "same_instant_conflict", "retrieved_at": DUE, "members": ["a", "b"]}], [], _expected("due", "Last Footballguys refresh recorded 40 days ago — monthly refresh due · multiple drops at that time disagree — data review required · analysis uses the 2026-06-15 drop", 1, clock="same-instant:2026-07-01", ar="older"), id="row17b"),
        pytest.param([{"special": "offering_identity_conflict", "members": ["x", "y"]}], [], _expected("unverifiable", "Footballguys drop records conflict — one drop declared with differing identities · no unambiguous refresh recorded", 1, clock=None, ar=None), id="row18a"),
        pytest.param([current_no_ar, {"special": "offering_identity_conflict", "members": ["x", "y"]}], [], _expected("unverifiable", "Footballguys drop records conflict — one drop declared with differing identities · last unambiguous refresh recorded 9 days ago", 1, clock="current-no-ar", ar=None), id="row18b"),
        pytest.param([older, current_no_ar, {"special": "offering_identity_conflict", "members": ["x", "y"]}], [], _expected("unverifiable", "Footballguys drop records conflict — one drop declared with differing identities · last unambiguous refresh recorded 9 days ago · analysis uses the 2026-06-15 drop", 1, clock="current-no-ar", ar="older"), id="row18c"),
        pytest.param([{"special": "integrity_failure", "id": "bad"}], [], _expected("unverifiable", "Footballguys drop record failed integrity check · no unambiguous refresh recorded", 1, clock=None, ar=None), id="row19a"),
        pytest.param([current_no_ar, {"special": "integrity_failure", "id": "bad"}], [], _expected("unverifiable", "Footballguys drop record failed integrity check · last unambiguous refresh recorded 9 days ago", 1, clock="current-no-ar", ar=None), id="row19b"),
        pytest.param([older, current_no_ar, {"special": "integrity_failure", "id": "bad"}], [], _expected("unverifiable", "Footballguys drop record failed integrity check · last unambiguous refresh recorded 9 days ago · analysis uses the 2026-06-15 drop", 1, clock="current-no-ar", ar="older"), id="row19c"),
    ]
    return cases


@pytest.mark.parametrize(("acquisitions", "attempts", "expected"), _state_cases())
def test_c1_every_reachable_state_is_literal_and_total(
    acquisitions: list[dict[str, Any]], attempts: list[dict[str, Any]], expected: dict[str, Any]
) -> None:
    m = _mod()
    actual = m.evaluate_refresh_state(acquisitions=acquisitions, attempts=attempts, now=NOW)
    assert actual == expected


def test_c1b_global_health_does_not_change_the_footballguys_row10_state() -> None:
    m = _mod()
    acquisitions = [_receipt("current", RECENT)]
    healthy = m.evaluate_refresh_state(
        acquisitions=acquisitions,
        attempts=[],
        now=NOW,
        global_overall_status="ok",
    )
    degraded = m.evaluate_refresh_state(
        acquisitions=acquisitions,
        attempts=[],
        now=NOW,
        global_overall_status="degraded",
    )
    assert degraded == healthy == _expected(
        "current",
        "Last Footballguys refresh recorded 9 days ago",
        0,
        clock="current",
        ar="current",
    )


@pytest.mark.parametrize("order", (("a", "b"), ("b", "a")))
@pytest.mark.parametrize("age", (RECENT, DUE))
def test_c2_same_instant_non_equivalent_candidates_are_order_invariant(
    order: tuple[str, str], age: str
) -> None:
    m = _mod()
    rows = {
        "a": _receipt("a", age, content="content-a"),
        "b": _receipt("b", age, content="content-b"),
    }
    actual = m.evaluate_refresh_state(
        acquisitions=[rows[key] for key in order], attempts=[], now=NOW
    )
    assert actual["readiness"] == "same_instant_conflict"
    assert actual["clock_id"].startswith("same-instant:")
    assert actual["latest_analysis_ready_id"] is None
    assert actual["status"] == ("current" if age == RECENT else "due")
    assert actual["pill_delta"] == (0 if age == RECENT else 1)
    assert actual["phase_c_open"] is False


@pytest.mark.parametrize("overlay", ("failed", "invalid"))
@pytest.mark.parametrize("base", ("review_with_ar", "observation_with_ar", "conflict", "integrity"))
def test_c3_newer_attempt_overlay_preserves_every_base_fact_once(
    overlay: str, base: str
) -> None:
    m = _mod()
    actual = m.render_overlay_fixture(base=base, overlay=overlay, now=NOW)
    assert actual["base_copy"] in actual["copy"]
    assert actual["overlay_suffix"] in actual["copy"]
    assert actual["copy"].count(actual["overlay_suffix"]) == 1
    assert actual["clock_id"] == actual["base_clock_id"]
    assert actual["latest_analysis_ready_id"] == actual["base_ar_id"]


@pytest.mark.parametrize(
    "impossible",
    (
        "ar_newer_than_clock",
        "ready_with_failed_freshness",
        "due_and_no_record",
        "pill_from_readiness",
        "observation_analysis_ready",
        "observation_selected_as_ar",
        "invalid_attempt_advances_clock",
    ),
)
def test_c4_impossible_states_are_refused_not_normalized(impossible: str) -> None:
    m = _mod()
    with pytest.raises(m.FootballguysStateError) as caught:
        m.evaluate_impossible_fixture(impossible, now=NOW)
    assert _error_code(caught.value).startswith("impossible_state")


def test_c5_due_is_persistent_season_flat_and_has_no_grace_or_dismissal() -> None:
    m = _mod()
    first = m.evaluate_refresh_state(acquisitions=[_receipt("due", DUE)], attempts=[], now=NOW)
    second = m.evaluate_refresh_state(acquisitions=[_receipt("due", DUE)], attempts=[], now=NOW)
    in_season = m.evaluate_refresh_state(
        acquisitions=[_receipt("due", DUE)],
        attempts=[],
        now=NOW,
        season_phase="regular_season",
    )
    assert first == second == in_season
    assert first["status"] == "due"
    assert first["pill_delta"] == 1
    assert set(first).isdisjoint({"dismissed", "snoozed", "toast", "notification"})


# ---------------------------------------------------------------------------
# R — read-model isolation and option-1 composition
# ---------------------------------------------------------------------------


def test_r0_stream_read_model_is_id_addressed_and_does_not_mutate_stores_zero() -> None:
    m = _mod()
    existing = {
        "overall_status": "degraded",
        "stores": [{"id": "fc", "status": "ok", "bytes": 123}],
    }
    before = json.loads(json.dumps(existing))
    composed = m.compose_capture_health(
        existing,
        stream_id="footballguys.bundle",
        stream_state=_expected(
            "due",
            "Last Footballguys refresh recorded 40 days ago — monthly refresh due",
            1,
            clock="due",
            ar="due",
        ),
    )
    assert existing == before
    assert composed["overall_status"] == "degraded"
    assert composed["stores"] == before["stores"]
    assert composed["manual_feeds_by_id"]["footballguys.bundle"]["status"] == "due"
    assert composed["status_pill_delta"] == 1


def test_r1_unreadable_footballguys_state_degrades_only_that_stream() -> None:
    m = _mod()
    existing = {"overall_status": "ok", "stores": [{"id": "fc", "status": "ok"}]}
    composed = m.compose_capture_health(
        existing,
        stream_id="footballguys.bundle",
        stream_state=_expected(
            "unverifiable",
            "Footballguys refresh record unreadable",
            1,
            clock=None,
            ar=None,
        ),
    )
    assert composed["overall_status"] == "ok"
    assert composed["stores"] == existing["stores"]
    assert composed["manual_feeds_by_id"]["footballguys.bundle"]["status"] == "unverifiable"


@pytest.mark.parametrize(
    "banned",
    ("downloaded", "buy", "sell", "hold", "recommended", "verdict", "must act"),
)
def test_r2_public_copy_uses_refresh_recorded_and_no_banned_decision_language(banned: str) -> None:
    m = _mod()
    copies = m.all_public_copy_rows()
    lowered = "\n".join(copies).lower()
    assert "refresh recorded" in lowered
    assert banned not in lowered


def test_r3_option1_is_the_only_active_write_mode_but_transition_controls_remain() -> None:
    m = _mod()
    assert m.ACTIVE_RETENTION_MODE == "full_offsite"
    assert m.active_intake_branch() == "A"
    assert m.transition_read_modes() == frozenset({"retained", "metadata_only"})
