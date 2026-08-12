"""RED v17 — Footballguys Phase A archive intake and monthly refresh notice.

Authority and scope
-------------------
David selected retention option 1 (full offsite raw backup) on 2026-08-10 after the
Phase A framing v25 review cleared.  This file is the prospective contract for that
choice.  It authorizes no provider contact, GREEN implementation, runtime write,
scheduler, downstream identity promotion, horizon comparison, or UI component.

The original RED landed with GREEN at ``f9b57d3``.  RED v3 then hardened seven
production boundaries and landed with its repair at ``8bf1518``.  Adversarial review
found nine remaining divergences: legacy-schema incompatibility, ungoverned semantic
evidence, sticky readiness, unordered attempt overlays, lost held-AR state, a shadow
sidecar schema, wrong object mode, leaking test connections, and stale provenance.
RED v4 preserves all earlier controls and makes those boundaries executable.  It never
skips; the reviewed 8bf1518 GREEN must fail the new controls before repair.

Adversarial review of RED v4's GREEN found seven further real-boundary defects:
cross-key semantic adjudication, writer-only semantic governance, an open semantic
writer schema, unreadable ledgers erased as empty, multiple simultaneous "newest"
attempts, per-store rather than global event order, and write-capable inactive-store
lookup.  RED v5 binds those accepted findings without changing the GREEN.

Adversarial review of RED v5's GREEN found five final sibling boundaries: the common
semantic/event store was validated after raw publication; semantic writer/load schemas
were still non-total; attempts-relation errors were erased; the alleged global event
ledger was only an unbound integer allocator; and the inactive-store freeze control
never reached lookup. RED v6 binds all five accepted findings against the committed
21cd11d GREEN while preserving every inherited contract.

Adversarial review of RED v6's GREEN found three fail-open persistence edges:
restored semantic fields could still bypass the writer and open eligibility; event
reconciliation skipped absent claims and ignored orphan central events; and immutable
SQLite reads preserved WAL bytes by ignoring their committed contents. RED v7 binds
all three against the committed e8fc4ec GREEN. It deliberately does not authorize an
orphan-deleting sweep or fabricate event identity for populated legacy rows whose
historical order cannot be reconstructed.

Adversarial review of RED v7's GREEN found four remaining real-boundary defects: a
populated or structurally non-unique central event ledger could migrate and reconcile
as healthy; unreadable inactive acquisition relations were noticed but did not block
raw publication; unhashable semantic vocabulary values leaked ``TypeError``; and the
WAL-aware URI choice raced the later SQLite open. RED v8 binds all four against the
committed c183c11 GREEN. Reader races use a bounded observe-open-reobserve contract;
they do not broaden the lifecycle lock or authorize any new work.

Adversarial review of RED v8's GREEN found five surviving persistence boundaries:
semantic identity constraints were inferred from column names and duplicate rows could
collapse into Phase-C eligibility; event uniqueness accepted an index on the wrong
column; persisted event order accepted incomparable or otherwise invalid instants and
non-integer sequences; refusal-class validation changed a rejected DELETE-mode store
before refusing; and adjudication identity fields still leaked bare exceptions. RED v9
binds all five against the committed 7e39763 GREEN while retaining the byte-freeze
promise through pre-write validation.

Adversarial review of RED v9's GREEN found five sibling boundaries: restored semantic
scalar types still crossed the reducer; central sequence identity was not the whole
ordering structure; the exact-integer claim guard covered acquisitions but not attempts;
an invalid read clock still leaked a bare aware/naive comparison; and the semantic
writers initialized durable state before validating a malformed record. RED v10 binds
all five against the committed b582b1d GREEN and includes the reviewing lane's own
fresh-root unchanged-state oracle repair.

Adversarial review of RED v10's GREEN found three remaining validation shadows: assertion
rows were key-filtered before scalar validation, allowing a corrupt conflicting row to
vanish and open Phase-C eligibility; the AUTOINCREMENT guard accepted the word anywhere
in the table DDL rather than binding it to ``seq``; and non-datetime clock dependencies
raised before the row-9 fallback. RED v11 binds all three against the committed 297c52f
GREEN without opening any downstream phase.

Adversarial review of RED v11's GREEN found two surviving boundary shadows: the alleged
seq binding was still a whole-DDL substring search spoofable through quoted literals and
comments, and a type-correct Python integer outside SQLite's signed-64 storage domain
raised after creating the governed store. RED v12 binds parser-level token ownership and
the complete storable version domain against the committed c32884a GREEN.

Adversarial review of RED v12's GREEN found one final parser-prefix defect: the seq
column's first four tokens were governed, but arbitrary suffix constraints were accepted.
RED v13 binds the complete exact token grammar against the committed 62278ab GREEN,
including one suffix whose first automatic value makes the operational consequence live.

Adversarial review of RED v13's GREEN found the same failure mechanism one syntactic
level higher: a canonical seq column plus a separate table-level constraint passed
schema validation, then broke the first governed event allocation. RED v14 binds the
complete six-segment event-table grammar against the committed e19d056 GREEN.

Adversarial review of RED v14's GREEN found that byte-canonical table DDL could
coexist with unvalidated triggers, views, tables, and surplus indexes stored as
separate sqlite_master objects. RED v15 binds the complete semantics-store object
inventory against the committed f971244 GREEN.

Adversarial review of RED v15's GREEN found two signature shadows inside the
new inventory allowlist: any SQLite-generated autoindex name passed regardless of
its indexed columns, and the marker acquisitions table passed by name without a
schema contract. RED v16 binds both exact signatures against committed ba890ec.

Adversarial review of RED v16's GREEN found three remaining schema shadows:
the four non-event semantic tables still had no closed DDL grammar; index
validation discarded origin, collation, direction, and key metadata; and marker
grammar accepted trailing table options after the matched close parenthesis.
RED v17 binds all three against committed 1e5492b. Its constraint mutants are
operational on every semantic writer branch, including the evidence-object path
whose ``INSERT OR IGNORE`` falsely reported ``written`` after storing no bytes.

One injected seam
-----------------
GREEN exposes ``build_contract_driver(...)`` only as the composition root used by
the real CLI and these contracts.  The driver owns the filesystem/SQLite/process
collaborators and exposes:

* ``intake(archive_bytes=..., offering=..., fault_at=None)``;
* ``write_semantic_assertion(record)``;
* ``write_semantic_adjudication(record)``;
* ``semantic_state(key=...)`` for durable effective-state read-back;
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

import contextlib
import hashlib
import importlib
import io
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import zipfile
from datetime import datetime, timedelta
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
    adp_payload: bytes | None = None,
    sidecar_payload: bytes | None = None,
) -> bytes:
    """Small integration positive.  The measured 259-entry profile is separate."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for role, name, payload in (
            (
                "adp",
                ADP_PATH,
                adp_payload
                if adp_payload is not None
                else b"id,adp_sleeper-sf\nGibbJa00,1\n",
            ),
            (
                "identity_sidecar",
                SIDECAR_PATH,
                sidecar_payload
                if sidecar_payload is not None
                else b"id,name,pos\nGibbJa00,Jahmyr Gibbs,RB\n",
            ),
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


def test_a0b_production_header_does_not_claim_the_superseded_original_red() -> None:
    m = _mod()
    assert "1130f2bc" not in (m.__doc__ or "")


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


@pytest.mark.parametrize(
    ("adp_payload", "sidecar_payload", "role"),
    (
        (b"not-the-adp-schema", b"id,name,pos\nGibbJa00,Jahmyr Gibbs,RB\n", "adp"),
        (b"id,adp_sleeper-sf\nGibbJa00,1\n", b"not-the-sidecar-schema", "identity_sidecar"),
        (b"id,value\nGibbJa00,1\n", b"id,name,pos\nGibbJa00,Jahmyr Gibbs,RB\n", "adp"),
        (
            b"id,adp_sleeper-sf\nGibbJa00,1\n",
            b"id,foo,bar\nGibbJa00,one,two\n",
            "identity_sidecar",
        ),
        (
            b"id,adp_sleeper-sf\nGibbJa00,1\n",
            b"id,name,team\nGibbJa00,Jahmyr Gibbs,DET\n",
            "identity_sidecar",
        ),
    ),
    ids=(
        "malformed-adp",
        "malformed-sidecar",
        "adp-without-adp-column",
        "sidecar-without-name-or-position",
        "sidecar-without-position",
    ),
)
def test_a6_real_role_member_schema_refuses_before_publish(
    tmp_path: Path, adp_payload: bytes, sidecar_payload: bytes, role: str
) -> None:
    driver = _driver(tmp_path)
    result = driver.intake(
        archive_bytes=_unit_zip(
            adp_payload=adp_payload,
            sidecar_payload=sidecar_payload,
        ),
        offering=_offering(),
    )
    assert result.status == "failed"
    assert result.reason is not None
    assert result.reason.startswith(f"role_schema_invalid:{role}")
    snap = driver.snapshot()
    assert snap["objects"] == []
    assert snap["receipts"] == []


@pytest.mark.parametrize(
    "sidecar_payload",
    (
        b"id,name,pos\nGibbJa00,Jahmyr Gibbs,RB\n",
        b"id,first,last,pos\nGibbJa00,Jahmyr,Gibbs,RB\n",
    ),
    ids=("combined-name", "real-first-last"),
)
def test_a6b_pinned_identity_column_aliases_are_accepted(
    sidecar_payload: bytes,
) -> None:
    result = _mod().inspect_archive(
        _unit_zip(sidecar_payload=sidecar_payload),
        role_paths=ROLE_PATHS,
        limits=LIMITS,
    )
    assert tuple(result["roles"]) == ("adp", "identity_sidecar")


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


SEMANTIC_KEY = "classic.adp_sleeper-sf.horizon"
SEMANTIC_EVIDENCE = b"provider-authentic field contract: redraft"


def _semantic_record(
    *, assertion_id: str = "horizon-v1", claim: str = "redraft", version: int = 1
) -> dict[str, Any]:
    """Closed durable writer shape; GREEN computes the attachment hash/size."""
    return {
        "assertion": {
            "key": SEMANTIC_KEY,
            "assertion_id": assertion_id,
            "version": version,
            "claim": claim,
            "active": True,
        },
        "attachment": {
            "evidence_id": f"evidence-{assertion_id}",
            "retrieved_at": "2026-08-09T12:00:00-04:00",
            "provenance": "provider-authentic-exact-field-contract",
            "retention": "retained",
            "evidence_bytes": SEMANTIC_EVIDENCE,
        },
    }


def _seed_effective_horizon(driver: Any) -> None:
    result = driver.write_semantic_assertion(_semantic_record())
    assert _value(result, "status") in {"written", "noop"}


def test_i10_semantic_assertion_writer_is_durable_hashed_and_idempotent(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    record = _semantic_record()
    first = driver.write_semantic_assertion(record)
    second = driver.write_semantic_assertion(record)
    assert _value(first, "status") == "written"
    assert _value(second, "status") == "noop"

    state = driver.semantic_state(key=SEMANTIC_KEY)
    assert state == {
        "state": "known",
        "value": "redraft",
        "assertion_id": "horizon-v1",
        "evidence_id": "evidence-horizon-v1",
        "evidence_sha256": _sha(SEMANTIC_EVIDENCE),
        "evidence_bytes": len(SEMANTIC_EVIDENCE),
        "eligible_for_phase_c": True,
    }

    # Durable read-back: a fresh composition root must reproduce the same state.
    reopened = _driver(tmp_path)
    assert reopened.semantic_state(key=SEMANTIC_KEY) == state


def test_i11_changed_semantic_assertion_reusing_an_id_refuses_without_mutation(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record())
    before = driver.semantic_state(key=SEMANTIC_KEY)
    with pytest.raises(driver.error_type) as caught:
        driver.write_semantic_assertion(
            _semantic_record(assertion_id="horizon-v1", claim="dynasty_startup")
        )
    assert "assertion_identity_conflict" in _error_code(caught.value)
    assert driver.semantic_state(key=SEMANTIC_KEY) == before


def test_i12_semantic_evidence_bytes_and_adjudications_are_durable_governed_state(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    db = tmp_path / RUNTIME_PATHS["semantics"]
    _create_legacy_acquisition_db(db)
    driver.write_semantic_assertion(_semantic_record())
    with contextlib.closing(sqlite3.connect(db)) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"semantic_evidence_objects", "semantic_adjudications"} <= tables
        evidence = conn.execute(
            "SELECT evidence_sha256, evidence_blob FROM semantic_evidence_objects"
        ).fetchone()
    assert evidence == (_sha(SEMANTIC_EVIDENCE), SEMANTIC_EVIDENCE)


def test_i13_untrusted_semantic_provenance_refuses_without_opening_horizon(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    record = _semantic_record()
    record["attachment"]["provenance"] = "untrusted-blog"
    with pytest.raises(driver.error_type) as caught:
        driver.write_semantic_assertion(record)
    assert "semantic_provenance_invalid" in _error_code(caught.value)
    assert driver.semantic_state(key=SEMANTIC_KEY)["state"] == "unknown"


def test_i14_non_horizon_claim_refuses_without_opening_horizon(tmp_path: Path) -> None:
    driver = _driver(tmp_path)
    with pytest.raises(driver.error_type) as caught:
        driver.write_semantic_assertion(
            _semantic_record(claim="weekly_projection")
        )
    assert "semantic_claim_invalid" in _error_code(caught.value)
    assert driver.semantic_state(key=SEMANTIC_KEY)["state"] == "unknown"


def test_i15_reused_evidence_identity_with_different_bytes_is_a_conflict(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record(assertion_id="horizon-v1"))
    changed = _semantic_record(assertion_id="horizon-v2", version=2)
    changed["attachment"]["evidence_id"] = "evidence-horizon-v1"
    changed["attachment"]["evidence_bytes"] = b"different evidence"
    before = driver.semantic_state(key=SEMANTIC_KEY)
    with pytest.raises(driver.error_type) as caught:
        driver.write_semantic_assertion(changed)
    assert "evidence_identity_conflict" in _error_code(caught.value)
    assert driver.semantic_state(key=SEMANTIC_KEY) == before


def test_i16_tampered_retained_evidence_bytes_close_the_semantic_gate(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record())
    db = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(db)) as conn:
        conn.execute(
            "UPDATE semantic_evidence_objects SET evidence_blob=?",
            (b"corrupt",),
        )
        conn.commit()
    state = _driver(tmp_path).semantic_state(key=SEMANTIC_KEY)
    assert state == {
        "state": "unknown",
        "reason": "active_evidence_unverifiable",
        "eligible_for_phase_c": False,
    }


def test_i17_durable_governed_adjudication_resolves_a_persisted_conflict(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record(assertion_id="old", version=1))
    driver.write_semantic_assertion(
        _semantic_record(assertion_id="new", claim="dynasty_startup", version=2)
    )
    assert driver.semantic_state(key=SEMANTIC_KEY)["state"] == "unknown"
    result = driver.write_semantic_adjudication(
        {
            "adjudication_id": "adj-1",
            "key": SEMANTIC_KEY,
            "authority": "david",
            "provenance": "explicit-ruling",
            "parents": ["old", "new"],
            "effective_assertion_id": "new",
        }
    )
    assert _value(result, "status") == "written"
    assert _driver(tmp_path).semantic_state(key=SEMANTIC_KEY)["value"] == "dynasty_startup"


# ---------------------------------------------------------------------------
# S — option-1 driver, filesystem/SQLite ordering, crash residue
# ---------------------------------------------------------------------------


def _write_manifest(
    root: Path, *, omit: str | None = None, post_capture_epoch: bool = True
) -> Path:
    required_rows = []
    optional_rows = []
    for store_path, (kind, required) in MANIFEST_REQUIREMENTS.items():
        if store_path == omit:
            continue
        # Repository truth is pre-capture and therefore optional. Driver positives
        # model the first-capture/post-capture epoch: raw publication is legal only
        # after the objects row flips to required in that same reviewed act.
        if store_path == RUNTIME_PATHS["objects"] and post_capture_epoch:
            required = True
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


def _driver(
    tmp_path: Path,
    *,
    mode: str = "full_offsite",
    omit_coverage: str | None = None,
    post_capture_epoch: bool = True,
):
    m = _mod()
    return m.build_contract_driver(
        repo_root=tmp_path,
        manifest_path=_write_manifest(
            tmp_path,
            omit=omit_coverage,
            post_capture_epoch=post_capture_epoch,
        ),
        retention_mode=mode,
        clock=lambda: NOW,
    )


def _clocked_driver(tmp_path: Path, clock: list[datetime]):
    m = _mod()
    return m.build_contract_driver(
        repo_root=tmp_path,
        manifest_path=_write_manifest(tmp_path),
        retention_mode="full_offsite",
        clock=lambda: clock[0],
    )


def _create_legacy_acquisition_db(path: Path) -> None:
    """Exact schema created by the first landed GREEN before RED v3."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.closing(sqlite3.connect(path)) as conn:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        conn.execute(
            "CREATE TABLE acquisitions ("
            " row_id TEXT PRIMARY KEY, offering_id TEXT UNIQUE, kind TEXT,"
            " retrieved_at TEXT, readiness TEXT, retention TEXT,"
            " content_vintage_id TEXT, archive_sha256 TEXT, archive_bytes INTEGER,"
            " analysis_ready INTEGER, signature BLOB)"
        )
        conn.execute(
            "INSERT INTO acquisitions(row_id, offering_id, kind)"
            " VALUES ('bootstrap-marker', '_bootstrap', 'marker')"
        )
        conn.commit()


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
    assert result.status == "review_required"
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
    assert converged.status == "review_required"
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
    _seed_effective_horizon(driver)
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
    _seed_effective_horizon(driver)
    obs = driver.intake(archive_bytes=_unit_zip(), offering=_offering("same", RECENT))
    driver.set_retention_mode("full_offsite")
    receipt = driver.intake(archive_bytes=_unit_zip(), offering=_offering("same", RECENT))
    snap = driver.snapshot()
    assert obs.observation_id == receipt.receipt_id
    assert len(snap["effective_acquisitions"]) == 1
    assert snap["effective_acquisitions"][0]["retention"] == "retained"
    assert "archive was not retained" not in driver.read_model(now=NOW)["copy"]


def test_s18_short_writes_are_completed_and_every_signed_fact_matches_staged_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    m = _mod()
    driver = _driver(tmp_path)
    payload = _unit_zip()
    real_write = m.os.write

    def short_write(fd: int, data: bytes) -> int:
        return real_write(fd, data[: max(1, len(data) // 2)])

    monkeypatch.setattr(m.os, "write", short_write)
    result = driver.intake(archive_bytes=payload, offering=_offering())
    assert result.status in {"ready", "review_required"}
    objects = list((tmp_path / RUNTIME_PATHS["objects"]).iterdir())
    assert len(objects) == 1
    retained = objects[0].read_bytes()
    assert retained == payload
    assert objects[0].name == f"{_sha(retained)}.zip"
    assert len(driver.snapshot()["receipts"]) == 1


def test_s19_publish_fsync_targets_objects_parent_not_only_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    m = _mod()
    driver = _driver(tmp_path)
    real_fsync = m.os.fsync
    fsynced: list[tuple[int, int]] = []

    def traced_fsync(fd: int) -> None:
        info = os.fstat(fd)
        fsynced.append((info.st_dev, info.st_ino))
        real_fsync(fd)

    monkeypatch.setattr(m.os, "fsync", traced_fsync)
    result = driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    assert result.status in {"ready", "review_required"}
    staging = os.stat(tmp_path / RUNTIME_PATHS["staging"])
    objects = os.stat(tmp_path / RUNTIME_PATHS["objects"])
    assert staging.st_dev == objects.st_dev
    assert (objects.st_dev, objects.st_ino) in fsynced


def test_s20_post_receipt_object_corruption_becomes_integrity_state_on_fresh_load(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    object_path = next((tmp_path / RUNTIME_PATHS["objects"]).iterdir())
    object_path.chmod(0o600)
    object_path.write_bytes(b"corrupt")

    reopened = _driver(tmp_path)
    state = reopened.read_model(now=NOW)
    assert state["status"] == "unverifiable"
    assert "integrity check" in state["copy"]
    assert state["clock_id"] is None
    assert state["latest_analysis_ready_id"] is None


def test_s20b_post_receipt_hardlink_alias_becomes_integrity_state(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    object_path = next((tmp_path / RUNTIME_PATHS["objects"]).iterdir())
    os.link(object_path, tmp_path / "durable-alias.zip")

    reopened = _driver(tmp_path)
    state = reopened.read_model(now=NOW)
    assert state["status"] == "unverifiable"
    assert "integrity check" in state["copy"]
    assert state["clock_id"] is None
    assert state["latest_analysis_ready_id"] is None


def test_s21_receipt_schema_persists_every_signed_field_for_reconstruction(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    with contextlib.closing(
        sqlite3.connect(tmp_path / RUNTIME_PATHS["receipts"])
    ) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(acquisitions)")}
    assert {
        "source",
        "offering_id",
        "content_vintage_id",
        "retrieved_at",
        "archive_sha256",
        "archive_bytes",
        "role_records",
    } <= columns


def test_s21_persisted_signed_field_tamper_is_not_laundered_into_a_clock(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    with contextlib.closing(
        sqlite3.connect(tmp_path / RUNTIME_PATHS["receipts"])
    ) as conn:
        conn.execute(
            "UPDATE acquisitions SET content_vintage_id=?, retrieved_at=? "
            "WHERE offering_id=?",
            ("forged-vintage", RECENT, _offering()["offering_id"]),
        )
        conn.commit()

    reopened = _driver(tmp_path)
    state = reopened.read_model(now=NOW)
    assert state["status"] == "unverifiable"
    assert "integrity check" in state["copy"]
    assert state["clock_id"] is None
    assert state["latest_analysis_ready_id"] is None


def test_s22_skewed_cross_store_restore_yields_global_offering_conflict(
    tmp_path: Path,
) -> None:
    retained_root = tmp_path / "retained"
    observation_root = tmp_path / "observation"
    retained = _driver(retained_root)
    observed = _driver(observation_root, mode="metadata_only")
    shared_offering = "same-offering"
    retained.intake(
        archive_bytes=_unit_zip(extra=[("wrapper-a", b"a", False)]),
        offering=_offering(shared_offering, DUE),
    )
    observed.intake(
        archive_bytes=_unit_zip(extra=[("wrapper-b", b"b", False)]),
        offering=_offering(shared_offering, RECENT),
    )

    source = observation_root / RUNTIME_PATHS["observations"]
    target = retained_root / RUNTIME_PATHS["observations"]
    with contextlib.closing(
        sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    ) as source_conn:
        with contextlib.closing(sqlite3.connect(target)) as target_conn:
            source_conn.backup(target_conn)

    reopened = _driver(retained_root)
    state = reopened.read_model(now=NOW)
    assert state["status"] == "unverifiable"
    assert "records conflict" in state["copy"]
    assert state["clock_id"] is None
    assert state["latest_analysis_ready_id"] is None


def test_s23_precapture_optional_objects_row_refuses_raw_publication(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path, post_capture_epoch=False)
    before = driver.snapshot()
    with pytest.raises(driver.error_type) as caught:
        driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    code = _error_code(caught.value)
    assert "required" in code and "objects" in code
    after = driver.snapshot()
    assert after["objects"] == before["objects"] == []
    assert after["receipts"] == before["receipts"] == []


def test_s24_failed_intake_is_durable_and_visible_after_fresh_load(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    result = driver.intake(archive_bytes=b"not-a-zip", offering=_offering())
    assert result.status == "failed"
    assert result.attempt_recorded is True

    reopened = _driver(tmp_path)
    state = reopened.read_model(now=NOW)
    assert state == _expected(
        "no_record",
        "No Footballguys refresh recorded · last intake attempt failed",
        1,
        clock=None,
        ar=None,
    )


def test_s25_unknown_horizon_advances_freshness_but_not_analysis_ready(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    result = driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    assert result.status == "review_required"
    effective = driver.snapshot()["effective_acquisitions"]
    assert len(effective) == 1
    assert effective[0]["readiness"] == "review_required"
    assert effective[0]["analysis_ready"] is False
    state = driver.read_model(now=NOW)
    assert state["status"] == "current"
    assert "awaiting data review" in state["copy"]
    assert state["latest_analysis_ready_id"] is None


def test_s26_effective_provider_horizon_allows_retained_receipt_to_become_ar(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    _seed_effective_horizon(driver)
    result = driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    assert result.status == "ready"
    state = driver.read_model(now=NOW)
    assert state["latest_analysis_ready_id"] == result.receipt_id
    assert "awaiting data review" not in state["copy"]


def test_s27_exact_pre_v3_schema_migrates_before_first_publication(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    receipts = tmp_path / RUNTIME_PATHS["receipts"]
    _create_legacy_acquisition_db(receipts)

    result = driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    assert result.status in {"ready", "review_required"}
    assert len(driver.snapshot()["objects"]) == 1
    assert len(driver.snapshot()["receipts"]) == 1
    with contextlib.closing(sqlite3.connect(receipts)) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(acquisitions)")}
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        schema_version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert {"source", "role_records"} <= columns
    assert "attempts" in tables
    assert schema_version >= 1

    reopened = _driver(tmp_path)
    assert len(reopened.snapshot()["objects"]) == 1
    assert len(reopened.snapshot()["receipts"]) == 1


def test_s28_unmigratable_schema_refuses_before_staging_or_publication(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    receipts = tmp_path / RUNTIME_PATHS["receipts"]
    with contextlib.closing(sqlite3.connect(receipts)) as conn:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        conn.execute("CREATE TABLE acquisitions(row_id TEXT PRIMARY KEY)")
        conn.commit()

    with pytest.raises(driver.error_type) as caught:
        driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    assert "store_schema_unmigratable" in _error_code(caught.value)
    snap = driver.snapshot()
    assert "staging_create" not in snap["trace"]
    assert snap["staging_entries"] == []
    assert snap["objects"] == []
    assert snap["receipts"] == []


def test_s29_later_effective_horizon_promotes_retained_receipt_on_load(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    result = driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    assert result.status == "review_required"
    assert driver.read_model(now=NOW)["latest_analysis_ready_id"] is None

    driver.write_semantic_assertion(_semantic_record())
    reopened = _driver(tmp_path)
    state = reopened.read_model(now=NOW)
    assert state["clock_id"] == result.receipt_id
    assert state["latest_analysis_ready_id"] == result.receipt_id
    assert "awaiting data review" not in state["copy"]
    assert reopened.snapshot()["receipts"] == [
        {
            "offering_id": _offering()["offering_id"],
            "receipt_id": result.receipt_id,
        }
    ]


def test_s29b_evidence_hash_failure_demotes_ar_without_changing_acquisition_identity(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    _seed_effective_horizon(driver)
    result = driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    assert driver.read_model(now=NOW)["latest_analysis_ready_id"] == result.receipt_id

    with contextlib.closing(
        sqlite3.connect(tmp_path / RUNTIME_PATHS["semantics"])
    ) as conn:
        conn.execute(
            "UPDATE semantic_evidence_objects SET evidence_blob=?",
            (b"corrupt",),
        )
        conn.commit()

    reopened = _driver(tmp_path)
    state = reopened.read_model(now=NOW)
    assert state["clock_id"] == result.receipt_id
    assert state["latest_analysis_ready_id"] is None
    assert "awaiting data review" in state["copy"]
    assert reopened.snapshot()["receipts"] == [
        {
            "offering_id": _offering()["offering_id"],
            "receipt_id": result.receipt_id,
        }
    ]


@pytest.mark.parametrize(
    ("order", "same_instant", "expects_suffix"),
    (
        ("failure_then_success", False, False),
        ("success_then_failure", False, True),
        ("failure_then_success", True, False),
        ("success_then_failure", True, True),
    ),
)
def test_s30_attempt_order_is_durable_relative_to_the_successful_acquisition(
    tmp_path: Path, order: str, same_instant: bool, expects_suffix: bool
) -> None:
    clock = [NOW - timedelta(hours=1)]
    driver = _clocked_driver(tmp_path, clock)

    def fail() -> None:
        result = driver.intake(
            archive_bytes=b"not-a-zip",
            offering=_offering("failed-offering"),
        )
        assert result.status == "failed"

    def succeed() -> None:
        result = driver.intake(
            archive_bytes=_unit_zip(),
            offering=_offering("successful-offering"),
        )
        assert result.status in {"ready", "review_required"}

    first, second = (fail, succeed) if order == "failure_then_success" else (succeed, fail)
    first()
    if not same_instant:
        clock[0] = clock[0] + timedelta(minutes=30)
    second()

    copy = _clocked_driver(tmp_path, clock).read_model(now=NOW)["copy"]
    suffix = "newest attempted drop failed intake"
    assert (suffix in copy) is expects_suffix


def test_s31_integrity_state_holds_ar_and_composes_newer_failed_overlay(
    tmp_path: Path,
) -> None:
    clock = [NOW]
    driver = _clocked_driver(tmp_path, clock)
    _seed_effective_horizon(driver)
    old = driver.intake(
        archive_bytes=_unit_zip(extra=[("wrapper-old", b"old", False)]),
        offering=_offering("old-ready", DUE),
    )
    before = set((tmp_path / RUNTIME_PATHS["objects"]).iterdir())
    driver.intake(
        archive_bytes=_unit_zip(extra=[("wrapper-new", b"new", False)]),
        offering=_offering("new-ready", RECENT),
    )
    new_object = next(iter(set((tmp_path / RUNTIME_PATHS["objects"]).iterdir()) - before))
    new_object.chmod(0o600)
    new_object.write_bytes(b"corrupt")
    clock[0] = NOW + timedelta(minutes=1)
    failed = driver.intake(
        archive_bytes=b"not-a-zip",
        offering=_offering("newest-failed"),
    )
    assert failed.status == "failed"

    state = _clocked_driver(tmp_path, clock).read_model(now=clock[0])
    assert state["status"] == "unverifiable"
    assert state["clock_id"] == old.receipt_id
    assert state["latest_analysis_ready_id"] == old.receipt_id
    assert "analysis uses the 2026-07-01 drop" in state["copy"]
    assert "newest attempted drop failed intake" in state["copy"]


def test_s32_published_object_is_0444_but_rehash_remains_authoritative(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    object_path = next((tmp_path / RUNTIME_PATHS["objects"]).iterdir())
    assert stat.S_IMODE(object_path.stat().st_mode) == 0o444
    assert _driver(tmp_path).read_model(now=NOW)["status"] == "current"


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


# ---------------------------------------------------------------------------
# V5 — accepted adversarial findings at the real persistence/read boundaries
# ---------------------------------------------------------------------------


def _v5_semantic_record(
    *,
    key: str = SEMANTIC_KEY,
    assertion_id: str,
    claim: str = "redraft",
    version: Any = 1,
    evidence_id: str | None = None,
    retrieved_at: str = "2026-08-09T12:00:00-04:00",
    evidence_bytes: bytes = SEMANTIC_EVIDENCE,
) -> dict[str, Any]:
    record = _semantic_record(
        assertion_id=assertion_id,
        claim=claim,
        version=version,
    )
    record["assertion"]["key"] = key
    record["attachment"]["evidence_id"] = evidence_id or f"evidence-{assertion_id}"
    record["attachment"]["retrieved_at"] = retrieved_at
    record["attachment"]["evidence_bytes"] = evidence_bytes
    return record


def _v5_seed_target_conflict(driver: Any) -> None:
    driver.write_semantic_assertion(
        _v5_semantic_record(assertion_id="target-old", version=1)
    )
    driver.write_semantic_assertion(
        _v5_semantic_record(
            assertion_id="target-new",
            claim="dynasty_startup",
            version=2,
        )
    )
    assert driver.semantic_state(key=SEMANTIC_KEY)["state"] == "unknown"


def _v5_insert_cross_key_adjudication(driver: Any, tmp_path: Path) -> None:
    other_key = "classic.adp_sleeper-sf.scoring"
    driver.write_semantic_assertion(
        _v5_semantic_record(key=other_key, assertion_id="other-key")
    )
    db = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(db)) as conn:
        conn.execute(
            "INSERT INTO semantic_adjudications"
            " (adjudication_id, key, authority, provenance, parents,"
            "  effective_assertion_id) VALUES (?,?,?,?,?,?)",
            (
                "cross-key-adjudication",
                SEMANTIC_KEY,
                "david",
                "explicit-ruling",
                json.dumps(["target-old", "target-new"]),
                "other-key",
            ),
        )
        conn.commit()


def _v5_assert_fail_closed_semantic_state(driver: Any) -> None:
    try:
        state = driver.semantic_state(key=SEMANTIC_KEY)
    except Exception as exc:  # pragma: no cover - reviewed GREEN raises here
        pytest.fail(f"semantic reducer raised instead of failing closed: {exc!r}")
    assert state["state"] == "unknown"
    assert state["eligible_for_phase_c"] is False


def test_v5_c1_writer_refuses_cross_key_effective_assertion_before_mutation(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    _v5_seed_target_conflict(driver)
    driver.write_semantic_assertion(
        _v5_semantic_record(
            key="classic.adp_sleeper-sf.scoring",
            assertion_id="other-key",
        )
    )
    before = driver.semantic_state(key=SEMANTIC_KEY)
    with pytest.raises(driver.error_type) as caught:
        driver.write_semantic_adjudication(
            {
                "adjudication_id": "cross-key-adjudication",
                "key": SEMANTIC_KEY,
                "authority": "david",
                "provenance": "explicit-ruling",
                "parents": ["target-old", "target-new"],
                "effective_assertion_id": "other-key",
            }
        )
    assert "adjudication" in _error_code(caught.value)
    assert driver.semantic_state(key=SEMANTIC_KEY) == before


def test_v5_c1_reducer_rejects_restored_cross_key_adjudication_without_raising(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    _v5_seed_target_conflict(driver)
    _v5_insert_cross_key_adjudication(driver, tmp_path)
    _v5_assert_fail_closed_semantic_state(_driver(tmp_path))


def test_v5_c1_invalid_adjudication_cannot_orphan_a_published_archive(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    _v5_seed_target_conflict(driver)
    _v5_insert_cross_key_adjudication(driver, tmp_path)

    result = driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    assert result.status == "review_required"
    snapshot = driver.snapshot()
    assert len(snapshot["objects"]) == 1
    assert len(snapshot["receipts"]) == 1


@pytest.mark.parametrize(
    ("table", "column", "value"),
    (
        ("semantic_attachments", "provenance", "untrusted-blog"),
        ("semantic_assertions", "claim", "weekly_projection"),
    ),
)
def test_v5_c2_persisted_unsupported_semantic_values_fail_closed_on_read(
    tmp_path: Path, table: str, column: str, value: str
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record())
    db = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(db)) as conn:
        conn.execute(f"UPDATE {table} SET {column}=?", (value,))
        conn.commit()
    _v5_assert_fail_closed_semantic_state(_driver(tmp_path))


@pytest.mark.parametrize(
    ("column", "value"),
    (("authority", "attacker"), ("provenance", "untrusted-blog")),
)
def test_v5_c2_persisted_unsupported_adjudication_fails_closed_on_read(
    tmp_path: Path, column: str, value: str
) -> None:
    driver = _driver(tmp_path)
    _v5_seed_target_conflict(driver)
    driver.write_semantic_adjudication(
        {
            "adjudication_id": "governed-adjudication",
            "key": SEMANTIC_KEY,
            "authority": "david",
            "provenance": "explicit-ruling",
            "parents": ["target-old", "target-new"],
            "effective_assertion_id": "target-new",
        }
    )
    db = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(db)) as conn:
        conn.execute(
            f"UPDATE semantic_adjudications SET {column}=?",
            (value,),
        )
        conn.commit()
    _v5_assert_fail_closed_semantic_state(_driver(tmp_path))


def test_v5_c2_unsupported_restored_claim_cannot_promote_analysis_readiness(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record())
    db = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(db)) as conn:
        conn.execute(
            "UPDATE semantic_assertions SET claim='weekly_projection'"
        )
        conn.commit()

    result = _driver(tmp_path).intake(
        archive_bytes=_unit_zip(),
        offering=_offering(),
    )
    assert result.status == "review_required"
    state = _driver(tmp_path).read_model(now=NOW)
    assert state["latest_analysis_ready_id"] is None
    assert "awaiting data review" in state["copy"]


@pytest.mark.parametrize("changed_field", ("bytes", "retrieved_at"))
def test_v5_h3_assertion_noop_requires_full_attachment_equality(
    tmp_path: Path, changed_field: str
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record())
    changed = _semantic_record()
    if changed_field == "bytes":
        changed["attachment"]["evidence_bytes"] = b"different retained bytes"
    else:
        changed["attachment"]["retrieved_at"] = "2026-08-08T12:00:00-04:00"
    with pytest.raises(driver.error_type) as caught:
        driver.write_semantic_assertion(changed)
    assert "identity_conflict" in _error_code(caught.value)


def test_v5_h3_reused_evidence_id_requires_full_attachment_equality(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record())
    changed = _v5_semantic_record(
        assertion_id="horizon-v2",
        version=2,
        evidence_id="evidence-horizon-v1",
        retrieved_at="2026-08-08T12:00:00-04:00",
    )
    with pytest.raises(driver.error_type) as caught:
        driver.write_semantic_assertion(changed)
    assert "evidence_identity_conflict" in _error_code(caught.value)


@pytest.mark.parametrize(
    "retrieved_at",
    ("not-a-date", "2026-08-09T12:00:00", "2026-08-09T12:00:00.5-04:00"),
)
def test_v5_h3_semantic_evidence_retrieved_at_has_a_closed_schema(
    tmp_path: Path, retrieved_at: str
) -> None:
    driver = _driver(tmp_path)
    record = _v5_semantic_record(
        assertion_id="invalid-time",
        retrieved_at=retrieved_at,
    )
    with pytest.raises(driver.error_type) as caught:
        driver.write_semantic_assertion(record)
    assert "retrieved_at" in _error_code(caught.value)
    assert driver.semantic_state(key=SEMANTIC_KEY)["state"] == "unknown"


@pytest.mark.parametrize("version", ("two", 2.5, True))
def test_v5_h3_semantic_version_is_an_integer_not_a_coercible_value(
    tmp_path: Path, version: Any
) -> None:
    driver = _driver(tmp_path)
    with pytest.raises(driver.error_type) as caught:
        driver.write_semantic_assertion(
            _v5_semantic_record(assertion_id="wrong-version", version=version)
        )
    assert "version" in _error_code(caught.value)
    assert driver.semantic_state(key=SEMANTIC_KEY)["state"] == "unknown"


def test_v5_h3_restored_wrong_type_version_returns_unknown_never_typeerror(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(
        _v5_semantic_record(assertion_id="version-one", version=1)
    )
    driver.write_semantic_assertion(
        _v5_semantic_record(assertion_id="version-two", version=2)
    )
    db = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(db)) as conn:
        conn.execute(
            "UPDATE semantic_assertions SET version='two'"
            " WHERE assertion_id='version-two'"
        )
        conn.commit()
    _v5_assert_fail_closed_semantic_state(_driver(tmp_path))


def test_v5_h3_equivalent_instant_spellings_share_canonical_evidence_identity(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record())
    equivalent = _v5_semantic_record(
        assertion_id="horizon-v2",
        version=2,
        evidence_id="evidence-horizon-v1",
        retrieved_at="2026-08-09T16:00:00Z",
    )
    result = driver.write_semantic_assertion(equivalent)
    assert _value(result, "status") == "written"


def _v5_write_non_sqlite_store(tmp_path: Path, store: str) -> Path:
    path = tmp_path / RUNTIME_PATHS[store]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not a sqlite database")
    return path


def _v5_assert_row9(state: dict[str, Any]) -> None:
    assert state == _expected(
        "unverifiable",
        "Footballguys refresh record unreadable",
        1,
        clock=None,
        ar=None,
    )


def test_v5_h4_non_sqlite_receipt_ledger_renders_literal_row9(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    _v5_write_non_sqlite_store(tmp_path, "receipts")
    _v5_assert_row9(driver.read_model(now=NOW))


def test_v5_h4_unreadable_counterpart_cannot_fall_back_to_a_healthy_clock(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    result = driver.intake(archive_bytes=_unit_zip(), offering=_offering())
    assert result.status == "review_required"
    _v5_write_non_sqlite_store(tmp_path, "observations")
    state = _driver(tmp_path).read_model(now=NOW)
    _v5_assert_row9(state)


@pytest.mark.parametrize(
    ("order", "expected_suffix", "forbidden_suffix"),
    (
        (
            "failed_then_invalid",
            "newest attempted drop's refresh time unverifiable",
            "newest attempted drop failed intake",
        ),
        (
            "invalid_then_failed",
            "newest attempted drop failed intake",
            "newest attempted drop's refresh time unverifiable",
        ),
    ),
)
def test_v5_h5_only_the_single_newest_attempt_supplies_an_overlay(
    tmp_path: Path, order: str, expected_suffix: str, forbidden_suffix: str
) -> None:
    clock = [NOW]
    driver = _clocked_driver(tmp_path, clock)
    driver.intake(archive_bytes=_unit_zip(), offering=_offering("base"))

    def failed() -> None:
        assert driver.intake(
            archive_bytes=b"not-a-zip",
            offering=_offering("failed"),
        ).status == "failed"

    def invalid() -> None:
        assert driver.intake(
            archive_bytes=_unit_zip(),
            offering=_offering("invalid", "2027-01-01T00:00:00Z"),
        ).status == "failed"

    first, second = (
        (failed, invalid) if order == "failed_then_invalid" else (invalid, failed)
    )
    clock[0] = NOW + timedelta(minutes=1)
    first()
    clock[0] = NOW + timedelta(minutes=2)
    second()

    copy = _clocked_driver(tmp_path, clock).read_model(now=clock[0])["copy"]
    assert expected_suffix in copy
    assert forbidden_suffix not in copy


@pytest.mark.parametrize(
    ("order", "expects_failed_overlay"),
    (("receipt_then_observation_failure", True), ("observation_failure_then_receipt", False)),
)
def test_v5_h6_equal_instant_cross_store_events_have_one_global_order(
    tmp_path: Path, order: str, expects_failed_overlay: bool
) -> None:
    def receipt() -> None:
        result = _driver(tmp_path).intake(
            archive_bytes=_unit_zip(),
            offering=_offering("retained"),
        )
        assert result.status == "review_required"

    def observation_failure() -> None:
        result = _driver(tmp_path, mode="metadata_only").intake(
            archive_bytes=b"not-a-zip",
            offering=_offering("metadata-failure"),
        )
        assert result.status == "failed"

    first, second = (
        (receipt, observation_failure)
        if order == "receipt_then_observation_failure"
        else (observation_failure, receipt)
    )
    first()
    second()
    copy = _driver(tmp_path).read_model(now=NOW)["copy"]
    assert ("newest attempted drop failed intake" in copy) is expects_failed_overlay


def _v5_main_wal_fingerprint(path: Path) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for candidate in (path, Path(f"{path}-wal")):
        if candidate.exists():
            payload = candidate.read_bytes()
            result[candidate.name] = (len(payload), _sha(payload))
    return result


@pytest.mark.parametrize(
    ("active_mode", "inactive_store"),
    (("metadata_only", "receipts"), ("full_offsite", "observations")),
)
def test_v5_h7_inactive_legacy_counterpart_is_byte_frozen_during_lookup(
    tmp_path: Path, active_mode: str, inactive_store: str
) -> None:
    driver = _driver(tmp_path, mode=active_mode)
    inactive = tmp_path / RUNTIME_PATHS[inactive_store]
    _create_legacy_acquisition_db(inactive)
    before = _v5_main_wal_fingerprint(inactive)

    result = driver.intake(
        archive_bytes=b"not-a-zip",
        offering=_offering(f"{active_mode}-failure"),
    )
    assert result.status == "failed"
    assert _v5_main_wal_fingerprint(inactive) == before


# ---------------------------------------------------------------------------
# V6 — accepted committed-GREEN findings at the remaining persistence edges
# ---------------------------------------------------------------------------


def _v6_real_acquisition_count(path: Path) -> int:
    if not path.exists():
        return 0
    with contextlib.closing(sqlite3.connect(path)) as conn:
        return int(
            conn.execute(
                "SELECT count(*) FROM acquisitions WHERE offering_id != '_bootstrap'"
            ).fetchone()[0]
        )


def _v6_attempt_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with contextlib.closing(sqlite3.connect(path)) as conn:
            return int(conn.execute("SELECT count(*) FROM attempts").fetchone()[0])
    except sqlite3.Error:
        return 0


def _v6_staging_entries(root: Path) -> list[str]:
    staging = root / RUNTIME_PATHS["staging"]
    return sorted(path.name for path in staging.iterdir()) if staging.exists() else []


def _v6_assert_no_raw_or_event_residue(root: Path) -> None:
    objects = root / RUNTIME_PATHS["objects"]
    assert list(objects.glob("*.zip")) == []
    assert _v6_staging_entries(root) == []
    assert _v6_real_acquisition_count(root / RUNTIME_PATHS["receipts"]) == 0
    assert _v6_real_acquisition_count(root / RUNTIME_PATHS["observations"]) == 0
    assert _v6_attempt_count(root / RUNTIME_PATHS["receipts"]) == 0
    assert _v6_attempt_count(root / RUNTIME_PATHS["observations"]) == 0


def test_v6_c1_corrupt_common_semantics_store_refuses_before_staging(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    semantics.write_bytes(b"not a sqlite database")

    caught: BaseException | None = None
    try:
        driver.intake(archive_bytes=_unit_zip(), offering=_offering("corrupt-semantics"))
    except BaseException as exc:  # assertion below checks the stable domain error
        caught = exc

    _v6_assert_no_raw_or_event_residue(tmp_path)
    assert isinstance(caught, driver.error_type)
    assert "semantic" in _error_code(caught) or "store_schema" in _error_code(caught)


def test_v6_c1_unmigratable_common_event_schema_refuses_before_staging(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        conn.execute("CREATE TABLE semantic_assertions(wrong_column TEXT)")
        conn.commit()

    caught: BaseException | None = None
    try:
        driver.intake(
            archive_bytes=_unit_zip(), offering=_offering("wrong-semantics-schema")
        )
    except BaseException as exc:  # assertion below checks the stable domain error
        caught = exc

    _v6_assert_no_raw_or_event_residue(tmp_path)
    assert isinstance(caught, driver.error_type)
    assert "store_schema_unmigratable:semantics" in _error_code(caught)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    (
        ("assertion", "active", "false"),
        ("assertion", "active", 1),
        ("assertion", "active", None),
        ("assertion", "assertion_id", ""),
        ("assertion", "key", ""),
        ("attachment", "evidence_id", ""),
        ("attachment", "retention", "not-a-retention-state"),
        ("attachment", "evidence_bytes", "not-bytes"),
    ),
)
def test_v6_c2_semantic_writer_rejects_every_open_schema_value_before_mutation(
    tmp_path: Path, section: str, field: str, value: Any
) -> None:
    driver = _driver(tmp_path)
    record = _semantic_record()
    record[section][field] = value
    with pytest.raises(driver.error_type):
        driver.write_semantic_assertion(record)
    assert driver.semantic_state(key=SEMANTIC_KEY)["state"] == "unknown"


def test_v6_c2_explicit_false_is_valid_but_never_active(tmp_path: Path) -> None:
    driver = _driver(tmp_path)
    record = _semantic_record()
    record["assertion"]["active"] = False
    assert _value(driver.write_semantic_assertion(record), "status") == "written"
    assert driver.semantic_state(key=SEMANTIC_KEY) == {
        "state": "unknown",
        "reason": "no_active_assertion",
        "eligible_for_phase_c": False,
    }


@pytest.mark.parametrize(
    ("sql", "params"),
    (
        (
            "UPDATE semantic_attachments SET retrieved_at=?",
            ("not-a-date",),
        ),
        (
            "UPDATE semantic_assertions SET active=?",
            ("false",),
        ),
        (
            "UPDATE semantic_assertions SET assertion_id=?",
            ("",),
        ),
    ),
)
def test_v6_c2_restored_malformed_semantic_scalar_fails_closed(
    tmp_path: Path, sql: str, params: tuple[Any, ...]
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record())
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute(sql, params)
        conn.commit()

    try:
        state = _driver(tmp_path).semantic_state(key=SEMANTIC_KEY)
    except Exception as exc:  # pragma: no cover - reviewed GREEN must not raise
        pytest.fail(f"malformed semantic scalar raised instead of failing closed: {exc!r}")
    assert state["state"] == "unknown"
    assert state["eligible_for_phase_c"] is False


def test_v6_c2_restored_non_blob_evidence_fails_closed_without_typeerror(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record())
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute("UPDATE semantic_evidence_objects SET evidence_blob=7")
        conn.commit()
    try:
        state = _driver(tmp_path).semantic_state(key=SEMANTIC_KEY)
    except Exception as exc:  # pragma: no cover - reviewed GREEN raises TypeError
        pytest.fail(f"non-BLOB semantic evidence raised instead of failing closed: {exc!r}")
    assert state["state"] == "unknown"
    assert state["eligible_for_phase_c"] is False


@pytest.mark.parametrize(
    "parents_payload",
    (
        "{bad-json",
        json.dumps({"target-old": True, "target-new": True}),
        json.dumps(["target-old", 7, "target-new"]),
    ),
)
def test_v6_c2_restored_adjudication_parents_require_a_json_string_list(
    tmp_path: Path, parents_payload: str
) -> None:
    driver = _driver(tmp_path)
    _v5_seed_target_conflict(driver)
    driver.write_semantic_adjudication(
        {
            "adjudication_id": "governed-adjudication",
            "key": SEMANTIC_KEY,
            "authority": "david",
            "provenance": "explicit-ruling",
            "parents": ["target-old", "target-new"],
            "effective_assertion_id": "target-new",
        }
    )
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute(
            "UPDATE semantic_adjudications SET parents=?",
            (parents_payload,),
        )
        conn.commit()
    try:
        state = _driver(tmp_path).semantic_state(key=SEMANTIC_KEY)
    except Exception as exc:  # pragma: no cover - reviewed GREEN raises on bad JSON
        pytest.fail(f"malformed adjudication parents raised: {exc!r}")
    assert state["state"] == "unknown"
    assert state["eligible_for_phase_c"] is False


@pytest.mark.parametrize("shape", ("missing", "wrong_columns"))
def test_v6_h3_attempt_relation_failure_renders_literal_row9(
    tmp_path: Path, shape: str
) -> None:
    driver = _driver(tmp_path)
    assert driver.intake(
        archive_bytes=_unit_zip(), offering=_offering("attempt-ledger-base")
    ).status == "review_required"
    receipts = tmp_path / RUNTIME_PATHS["receipts"]
    with contextlib.closing(sqlite3.connect(receipts)) as conn:
        conn.execute("DROP TABLE attempts")
        if shape == "wrong_columns":
            conn.execute(
                "CREATE TABLE attempts(seq INTEGER PRIMARY KEY, status TEXT)"
            )
        conn.commit()
    _v5_assert_row9(_driver(tmp_path).read_model(now=NOW))


def test_v6_h3_inactive_legacy_store_without_attempts_cannot_be_masked(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    inactive = tmp_path / RUNTIME_PATHS["observations"]
    _create_legacy_acquisition_db(inactive)
    assert driver.intake(
        archive_bytes=_unit_zip(), offering=_offering("healthy-sibling")
    ).status == "review_required"
    _v5_assert_row9(_driver(tmp_path).read_model(now=NOW))


_V6_EVENT_LEDGER_COLUMNS = {
    "seq",
    "event_id",
    "event_type",
    "store_name",
    "subject_id",
    "event_at",
}


def _v6_clocked_mode_driver(
    root: Path, *, mode: str, clock: list[datetime]
) -> Any:
    m = _mod()
    return m.build_contract_driver(
        repo_root=root,
        manifest_path=_write_manifest(root),
        retention_mode=mode,
        clock=lambda: clock[0],
    )


def _v6_seed_cross_store_event_pair(tmp_path: Path) -> tuple[Path, Path, Path]:
    clock = [NOW]
    retained = _v6_clocked_mode_driver(tmp_path, mode="full_offsite", clock=clock)
    assert retained.intake(
        archive_bytes=_unit_zip(), offering=_offering("event-retained")
    ).status == "review_required"
    metadata = _v6_clocked_mode_driver(tmp_path, mode="metadata_only", clock=clock)
    assert metadata.intake(
        archive_bytes=b"not-a-zip", offering=_offering("event-failure")
    ).status == "failed"
    return (
        tmp_path / RUNTIME_PATHS["semantics"],
        tmp_path / RUNTIME_PATHS["receipts"],
        tmp_path / RUNTIME_PATHS["observations"],
    )


def _v6_assert_event_schema(
    semantics: Path, receipts: Path, observations: Path
) -> None:
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        central = {row[1] for row in conn.execute("PRAGMA table_info(event_sequence)")}
    with contextlib.closing(sqlite3.connect(receipts)) as conn:
        acquisition = {row[1] for row in conn.execute("PRAGMA table_info(acquisitions)")}
    with contextlib.closing(sqlite3.connect(observations)) as conn:
        attempts = {row[1] for row in conn.execute("PRAGMA table_info(attempts)")}
    assert central >= _V6_EVENT_LEDGER_COLUMNS
    assert "event_id" in acquisition
    assert {"attempt_id", "event_id"} <= attempts


def _v6_assert_event_integrity_fail_closed(tmp_path: Path) -> None:
    state = _driver(tmp_path).read_model(now=NOW)
    assert state["status"] == "unverifiable"
    assert state["phase_c_open"] is False
    assert state["pill_delta"] == 1


def test_v6_h4_central_event_records_bind_type_store_subject_and_claim(
    tmp_path: Path,
) -> None:
    semantics, receipts, observations = _v6_seed_cross_store_event_pair(tmp_path)
    _v6_assert_event_schema(semantics, receipts, observations)
    with contextlib.closing(sqlite3.connect(receipts)) as conn:
        acquisition = conn.execute(
            "SELECT row_id, event_id, event_at, event_seq FROM acquisitions"
            " WHERE offering_id='event-retained'"
        ).fetchone()
    with contextlib.closing(sqlite3.connect(observations)) as conn:
        attempt = conn.execute(
            "SELECT attempt_id, event_id, at, event_seq FROM attempts"
        ).fetchone()
    assert acquisition is not None and attempt is not None
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        rows = {
            row[0]: row[1:]
            for row in conn.execute(
                "SELECT event_id, event_type, store_name, subject_id, event_at, seq"
                " FROM event_sequence"
            )
        }
    assert rows[acquisition[1]] == (
        "acquisition",
        "receipts",
        acquisition[0],
        acquisition[2],
        acquisition[3],
    )
    assert rows[attempt[1]] == (
        "attempt",
        "observations",
        attempt[0],
        attempt[2],
        attempt[3],
    )


def test_v6_h4_missing_central_event_mapping_fails_closed(tmp_path: Path) -> None:
    semantics, receipts, observations = _v6_seed_cross_store_event_pair(tmp_path)
    _v6_assert_event_schema(semantics, receipts, observations)
    with contextlib.closing(sqlite3.connect(observations)) as conn:
        event_id = conn.execute("SELECT event_id FROM attempts").fetchone()[0]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute("DELETE FROM event_sequence WHERE event_id=?", (event_id,))
        conn.commit()
    _v6_assert_event_integrity_fail_closed(tmp_path)


def test_v6_h4_wrong_store_binding_fails_closed(tmp_path: Path) -> None:
    semantics, receipts, observations = _v6_seed_cross_store_event_pair(tmp_path)
    _v6_assert_event_schema(semantics, receipts, observations)
    with contextlib.closing(sqlite3.connect(observations)) as conn:
        event_id = conn.execute("SELECT event_id FROM attempts").fetchone()[0]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute(
            "UPDATE event_sequence SET store_name='receipts' WHERE event_id=?",
            (event_id,),
        )
        conn.commit()
    _v6_assert_event_integrity_fail_closed(tmp_path)


def test_v6_h4_skewed_per_store_sequence_claim_fails_closed(tmp_path: Path) -> None:
    semantics, receipts, observations = _v6_seed_cross_store_event_pair(tmp_path)
    _v6_assert_event_schema(semantics, receipts, observations)
    with contextlib.closing(sqlite3.connect(receipts)) as conn:
        receipt_seq = conn.execute(
            "SELECT event_seq FROM acquisitions WHERE offering_id='event-retained'"
        ).fetchone()[0]
    with contextlib.closing(sqlite3.connect(observations)) as conn:
        conn.execute("UPDATE attempts SET event_seq=?", (receipt_seq,))
        conn.commit()
    _v6_assert_event_integrity_fail_closed(tmp_path)


@pytest.mark.parametrize(
    ("active_mode", "inactive_store", "inactive_shape"),
    (
        ("full_offsite", "observations", "legacy"),
        ("metadata_only", "receipts", "legacy"),
        ("full_offsite", "observations", "current"),
        ("metadata_only", "receipts", "current"),
    ),
)
def test_v6_h5_valid_archive_reaches_lookup_and_freezes_inactive_main_wal(
    tmp_path: Path, active_mode: str, inactive_store: str, inactive_shape: str
) -> None:
    # Bootstrap the verified private namespace before creating the inactive DB.
    setup = _driver(tmp_path, mode=active_mode)
    inactive = tmp_path / RUNTIME_PATHS[inactive_store]
    if inactive_shape == "legacy":
        _create_legacy_acquisition_db(inactive)
    else:
        setup.initialize_database(inactive_store)
    before = _v5_main_wal_fingerprint(inactive)

    driver = _driver(tmp_path, mode=active_mode)
    result = driver.intake(
        archive_bytes=_unit_zip(),
        offering=_offering(f"lookup-{active_mode}-{inactive_shape}"),
    )
    assert result.status in {"ready", "review_required"}
    assert _v5_main_wal_fingerprint(inactive) == before


# ---------------------------------------------------------------------------
# V7 — accepted e8fc4ec findings: semantic symmetry, event bijection, WAL truth
# ---------------------------------------------------------------------------


_V7_SEMANTIC_FIELDS = (
    ("assertion", "assertion_id"),
    ("assertion", "key"),
    ("assertion", "version"),
    ("assertion", "claim"),
    ("assertion", "active"),
    ("attachment", "evidence_id"),
    ("attachment", "retrieved_at"),
    ("attachment", "provenance"),
    ("attachment", "retention"),
    ("attachment", "evidence_bytes"),
)


@pytest.mark.parametrize("section", ("assertion", "attachment"))
def test_v7_c1_semantic_writer_missing_section_is_named_refusal(
    tmp_path: Path, section: str
) -> None:
    driver = _driver(tmp_path)
    record = _semantic_record()
    del record[section]
    with pytest.raises(driver.error_type) as caught:
        driver.write_semantic_assertion(record)
    assert _error_code(caught.value) == f"semantic_record_invalid:missing:{section}"
    assert driver.semantic_state(key=SEMANTIC_KEY)["state"] == "unknown"


@pytest.mark.parametrize(("section", "field"), _V7_SEMANTIC_FIELDS)
def test_v7_c1_semantic_writer_missing_field_is_named_refusal(
    tmp_path: Path, section: str, field: str
) -> None:
    driver = _driver(tmp_path)
    record = _semantic_record()
    del record[section][field]
    with pytest.raises(driver.error_type) as caught:
        driver.write_semantic_assertion(record)
    assert _error_code(caught.value) == (
        f"semantic_record_invalid:missing:{section}.{field}"
    )
    assert driver.semantic_state(key=SEMANTIC_KEY)["state"] == "unknown"


@pytest.mark.parametrize("section", ("assertion", "attachment"))
def test_v7_c1_semantic_writer_section_type_is_named_refusal(
    tmp_path: Path, section: str
) -> None:
    driver = _driver(tmp_path)
    record = _semantic_record()
    record[section] = []
    with pytest.raises(driver.error_type) as caught:
        driver.write_semantic_assertion(record)
    assert _error_code(caught.value) == f"semantic_record_invalid:type:{section}"


@pytest.mark.parametrize(
    ("section", "field", "bad_value"),
    (
        ("assertion", "assertion_id", b"blob-id"),
        ("assertion", "key", b"blob-key"),
        ("assertion", "version", "1"),
        ("assertion", "claim", b"redraft"),
        ("assertion", "active", 1),
        ("attachment", "evidence_id", b"blob-id"),
        ("attachment", "retrieved_at", 7),
        ("attachment", "provenance", b"provider-authentic-exact-field-contract"),
        ("attachment", "retention", b"retained"),
        ("attachment", "evidence_bytes", "not-bytes"),
    ),
)
def test_v7_c1_semantic_writer_wrong_types_are_domain_refusals(
    tmp_path: Path, section: str, field: str, bad_value: Any
) -> None:
    driver = _driver(tmp_path)
    record = _semantic_record()
    record[section][field] = bad_value
    try:
        driver.write_semantic_assertion(record)
    except driver.error_type:
        pass
    except Exception as exc:  # pragma: no cover - reviewed GREEN leaks bare errors
        pytest.fail(f"semantic writer leaked {type(exc).__name__}: {exc}")
    else:  # pragma: no cover - reviewed GREEN accepts some malformed values
        pytest.fail(f"semantic writer accepted malformed {section}.{field}")


def test_v7_c1_restored_future_evidence_time_cannot_open_eligibility(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record())
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute(
            "UPDATE semantic_attachments SET retrieved_at='2099-01-01T00:00:00Z'"
        )
        conn.commit()
    state = _driver(tmp_path).semantic_state(key=SEMANTIC_KEY)
    assert state["state"] == "unknown"
    assert state["eligible_for_phase_c"] is False


@pytest.mark.parametrize("bad_id", ("", sqlite3.Binary(b"blob-id")))
def test_v7_c1_restored_evidence_identity_must_be_nonempty_text(
    tmp_path: Path, bad_id: Any
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record())
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute("UPDATE semantic_attachments SET evidence_id=?", (bad_id,))
        conn.execute("UPDATE semantic_assertions SET evidence_id=?", (bad_id,))
        conn.commit()
    state = _driver(tmp_path).semantic_state(key=SEMANTIC_KEY)
    assert state["state"] == "unknown"
    assert state["eligible_for_phase_c"] is False


@pytest.mark.parametrize("bad_id", (None, ""))
def test_v7_c2_missing_acquisition_event_claim_fails_closed(
    tmp_path: Path, bad_id: str | None
) -> None:
    driver = _driver(tmp_path)
    assert driver.intake(
        archive_bytes=_unit_zip(), offering=_offering("missing-acquisition-event")
    ).status == "review_required"
    receipts = tmp_path / RUNTIME_PATHS["receipts"]
    with contextlib.closing(sqlite3.connect(receipts)) as conn:
        conn.execute(
            "UPDATE acquisitions SET event_id=? WHERE offering_id=?",
            (bad_id, "missing-acquisition-event"),
        )
        conn.commit()
    _v6_assert_event_integrity_fail_closed(tmp_path)


@pytest.mark.parametrize("bad_id", (None, ""))
def test_v7_c2_missing_attempt_event_claim_fails_closed(
    tmp_path: Path, bad_id: str | None
) -> None:
    _, _, observations = _v6_seed_cross_store_event_pair(tmp_path)
    with contextlib.closing(sqlite3.connect(observations)) as conn:
        conn.execute("UPDATE attempts SET event_id=?", (bad_id,))
        conn.commit()
    _v6_assert_event_integrity_fail_closed(tmp_path)


@pytest.mark.parametrize("event_type", ("acquisition", "attempt"))
def test_v7_c2_unpaired_central_event_fails_closed(
    tmp_path: Path, event_type: str
) -> None:
    semantics, receipts, observations = _v6_seed_cross_store_event_pair(tmp_path)
    if event_type == "acquisition":
        with contextlib.closing(sqlite3.connect(receipts)) as conn:
            conn.execute(
                "DELETE FROM acquisitions WHERE offering_id='event-retained'"
            )
            conn.commit()
    else:
        with contextlib.closing(sqlite3.connect(observations)) as conn:
            conn.execute("DELETE FROM attempts")
            conn.commit()
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM event_sequence WHERE event_type=?", (event_type,)
        ).fetchone()[0] == 1
    _v6_assert_event_integrity_fail_closed(tmp_path)


@pytest.mark.parametrize(
    ("mode", "store"),
    (("full_offsite", "receipts"), ("metadata_only", "observations")),
)
def test_v7_c2_populated_unbound_legacy_store_refuses_before_staging(
    tmp_path: Path, mode: str, store: str
) -> None:
    # Bootstrap the governed 0700 namespace first; then install the exact
    # historical database shape inside it.  The refusal under test is schema
    # provenance, never an accidental parent-mode failure.
    driver = _driver(tmp_path, mode=mode)
    legacy = tmp_path / RUNTIME_PATHS[store]
    _create_legacy_acquisition_db(legacy)
    with contextlib.closing(sqlite3.connect(legacy)) as conn:
        conn.execute(
            "INSERT INTO acquisitions"
            " (row_id, offering_id, kind, retrieved_at, readiness, retention,"
            "  content_vintage_id, archive_sha256, archive_bytes, analysis_ready,"
            "  signature) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                "legacy-row", "legacy-offering", "receipt", RECENT,
                "review_required", "retained", "legacy-vintage", "0" * 64,
                1, 0, b"legacy-signature",
            ),
        )
        conn.commit()
    with pytest.raises(driver.error_type) as caught:
        driver.intake(
            archive_bytes=_unit_zip(), offering=_offering(f"legacy-{store}")
        )
    assert _error_code(caught.value) == f"store_migration_unreconcilable:{store}"
    assert driver.snapshot()["objects"] == []
    assert "staging_create" not in driver.snapshot()["trace"]


def test_v7_c2_orphan_event_is_not_deleted_as_generic_crash_residue(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    offering = _offering("orphan-must-remain-visible")
    assert driver.intake(archive_bytes=_unit_zip(), offering=offering).status == (
        "review_required"
    )
    receipts = tmp_path / RUNTIME_PATHS["receipts"]
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(receipts)) as conn:
        conn.execute(
            "DELETE FROM acquisitions WHERE offering_id='orphan-must-remain-visible'"
        )
        conn.commit()
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        before = conn.execute(
            "SELECT event_id, event_type, store_name, subject_id, event_at, seq"
            " FROM event_sequence ORDER BY seq"
        ).fetchall()
    retry = _driver(tmp_path)
    with pytest.raises(retry.error_type) as caught:
        retry.intake(archive_bytes=_unit_zip(), offering=offering)
    assert _error_code(caught.value) == "event_ledger_unreconciled"
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        after = conn.execute(
            "SELECT event_id, event_type, store_name, subject_id, event_at, seq"
            " FROM event_sequence ORDER BY seq"
        ).fetchall()
    assert after == before
    _v6_assert_event_integrity_fail_closed(tmp_path)


def _v7_install_committed_wal_attempts_drop(path: Path) -> None:
    """Install a closed main+WAL/no-SHM snapshot whose WAL drops attempts."""
    source = path.with_name(path.name + ".wal-source")
    shutil.copy2(path, source)
    writer = sqlite3.connect(source)
    try:
        assert writer.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("DROP TABLE attempts")
        writer.commit()
        source_wal = Path(f"{source}-wal")
        assert source_wal.exists() and source_wal.stat().st_size > 0
        shutil.copy2(source, path)
        shutil.copy2(source_wal, Path(f"{path}-wal"))
        Path(f"{path}-shm").unlink(missing_ok=True)
    finally:
        writer.close()
        source.unlink(missing_ok=True)
        Path(f"{source}-wal").unlink(missing_ok=True)
        Path(f"{source}-shm").unlink(missing_ok=True)


@pytest.mark.parametrize(
    ("active_mode", "inactive_store"),
    (("full_offsite", "observations"), ("metadata_only", "receipts")),
)
def test_v7_c3_wal_aware_lookup_observes_committed_state_and_freezes_main_wal(
    tmp_path: Path, active_mode: str, inactive_store: str
) -> None:
    setup = _driver(tmp_path, mode=active_mode)
    setup.initialize_database(inactive_store)
    inactive = tmp_path / RUNTIME_PATHS[inactive_store]
    _v7_install_committed_wal_attempts_drop(inactive)
    before = _v5_main_wal_fingerprint(inactive)
    assert Path(f"{inactive}-wal").stat().st_size > 0
    assert not Path(f"{inactive}-shm").exists()

    result = _driver(tmp_path, mode=active_mode).intake(
        archive_bytes=_unit_zip(),
        offering=_offering(f"wal-aware-{active_mode}"),
    )
    assert result.status in {"ready", "review_required"}
    _v5_assert_row9(_driver(tmp_path).read_model(now=NOW))
    assert _v5_main_wal_fingerprint(inactive) == before
    assert Path(f"{inactive}-shm").exists()  # the only permitted new residue


@pytest.mark.parametrize(
    ("active_mode", "inactive_store"),
    (("full_offsite", "observations"), ("metadata_only", "receipts")),
)
def test_v7_c3_wal_absent_lookup_materializes_no_sidecar(
    tmp_path: Path, active_mode: str, inactive_store: str
) -> None:
    setup = _driver(tmp_path, mode=active_mode)
    setup.initialize_database(inactive_store)
    inactive = tmp_path / RUNTIME_PATHS[inactive_store]
    assert not Path(f"{inactive}-wal").exists()
    assert not Path(f"{inactive}-shm").exists()
    before = _v5_main_wal_fingerprint(inactive)
    result = _driver(tmp_path, mode=active_mode).intake(
        archive_bytes=_unit_zip(),
        offering=_offering(f"wal-absent-{active_mode}"),
    )
    assert result.status in {"ready", "review_required"}
    assert _v5_main_wal_fingerprint(inactive) == before
    assert not Path(f"{inactive}-wal").exists()
    assert not Path(f"{inactive}-shm").exists()


# ---------------------------------------------------------------------------
# V8 — accepted c183c11 findings: central truth, prewrite refusal, read races
# ---------------------------------------------------------------------------


def _v8_create_bare_event_allocator(path: Path, *, populated: bool) -> None:
    with contextlib.closing(sqlite3.connect(path)) as conn:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        conn.execute(
            "CREATE TABLE event_sequence"
            " (seq INTEGER PRIMARY KEY AUTOINCREMENT)"
        )
        if populated:
            conn.execute("INSERT INTO event_sequence DEFAULT VALUES")
        conn.commit()


def test_v8_c1_populated_bare_central_ledger_refuses_before_mutation(
    tmp_path: Path,
) -> None:
    setup = _driver(tmp_path)
    setup.initialize_database("receipts")
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    _v8_create_bare_event_allocator(semantics, populated=True)
    before = _v5_main_wal_fingerprint(semantics)

    driver = _driver(tmp_path)
    with pytest.raises(driver.error_type) as caught:
        driver.intake(
            archive_bytes=_unit_zip(),
            offering=_offering("populated-bare-central"),
        )
    assert _error_code(caught.value) == (
        "store_migration_unreconcilable:semantics"
    )
    assert _v5_main_wal_fingerprint(semantics) == before
    assert driver.snapshot()["objects"] == []
    assert "staging_create" not in driver.snapshot()["trace"]


def test_v8_c1_empty_bare_central_rebuilds_with_real_event_id_uniqueness(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.initialize_database("receipts")
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    _v8_create_bare_event_allocator(semantics, populated=False)
    driver.initialize_database("semantics")

    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        unique_indexes = [
            row[1]
            for row in conn.execute("PRAGMA index_list(event_sequence)")
            if row[2] == 1
        ]
        assert unique_indexes, "event_id uniqueness must exist in SQLite, not prose"
        conn.execute(
            "INSERT INTO event_sequence"
            " (event_id,event_type,store_name,subject_id,event_at)"
            " VALUES ('duplicate','attempt','receipts','a','2026-08-10T00:00:00Z')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO event_sequence"
                " (event_id,event_type,store_name,subject_id,event_at)"
                " VALUES ('duplicate','attempt','receipts','a','2026-08-10T00:00:00Z')"
            )


def _v8_remove_event_uniqueness_and_duplicate(semantics: Path) -> None:
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        rows = conn.execute(
            "SELECT seq,event_id,event_type,store_name,subject_id,event_at"
            " FROM event_sequence ORDER BY seq"
        ).fetchall()
        assert rows
        conn.execute("ALTER TABLE event_sequence RENAME TO event_sequence_governed")
        conn.execute(
            "CREATE TABLE event_sequence"
            " (seq INTEGER, event_id TEXT, event_type TEXT, store_name TEXT,"
            "  subject_id TEXT, event_at TEXT)"
        )
        conn.executemany(
            "INSERT INTO event_sequence"
            " (seq,event_id,event_type,store_name,subject_id,event_at)"
            " VALUES (?,?,?,?,?,?)",
            rows + [rows[0]],
        )
        conn.execute("DROP TABLE event_sequence_governed")
        conn.commit()


def test_v8_c1_duplicate_central_ids_cannot_hide_behind_dict_collapse(
    tmp_path: Path,
) -> None:
    first = _driver(tmp_path)
    assert first.intake(
        archive_bytes=_unit_zip(), offering=_offering("central-duplicate-base")
    ).status == "review_required"
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    _v8_remove_event_uniqueness_and_duplicate(semantics)

    retry = _driver(tmp_path)
    with pytest.raises(retry.error_type) as caught:
        retry.intake(
            archive_bytes=_unit_zip(),
            offering=_offering("central-duplicate-next"),
        )
    assert _error_code(caught.value) == "store_schema_unmigratable:semantics"
    assert "staging_create" not in retry.snapshot()["trace"]


def test_v8_c1_restored_duplicate_central_ids_fail_closed_on_read(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    assert driver.intake(
        archive_bytes=_unit_zip(), offering=_offering("central-duplicate-read")
    ).status == "review_required"
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    _v8_remove_event_uniqueness_and_duplicate(semantics)
    _v6_assert_event_integrity_fail_closed(tmp_path)


@pytest.mark.parametrize(
    ("event_id", "event_type", "store_name", "subject_id", "event_at"),
    (
        (None, "attempt", "receipts", "subject", "2026-08-10T00:00:00Z"),
        ("event", None, "receipts", "subject", "2026-08-10T00:00:00Z"),
        ("event", "foreign", "receipts", "subject", "2026-08-10T00:00:00Z"),
        ("event", "attempt", None, "subject", "2026-08-10T00:00:00Z"),
        ("event", "attempt", "receipts", None, "2026-08-10T00:00:00Z"),
        ("event", "attempt", "receipts", "subject", None),
    ),
)
def test_v8_c1_every_central_row_has_closed_identity_and_type(
    tmp_path: Path,
    event_id: Any,
    event_type: Any,
    store_name: Any,
    subject_id: Any,
    event_at: Any,
) -> None:
    driver = _driver(tmp_path)
    driver.initialize_database("semantics")
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute(
            "INSERT INTO event_sequence"
            " (event_id,event_type,store_name,subject_id,event_at)"
            " VALUES (?,?,?,?,?)",
            (event_id, event_type, store_name, subject_id, event_at),
        )
        conn.commit()
    _v6_assert_event_integrity_fail_closed(tmp_path)


def test_v8_c1_unreadable_central_ledger_fails_closed_without_store_claims(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.initialize_database("receipts")
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    semantics.write_bytes(b"not-a-sqlite-database")
    _v5_assert_row9(_driver(tmp_path).read_model(now=NOW))


def _v8_create_unreadable_counterpart_relation(
    path: Path, *, relation: str
) -> None:
    with contextlib.closing(sqlite3.connect(path)) as conn:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        if relation == "acquisitions":
            conn.execute("CREATE TABLE acquisitions(row_id TEXT)")
            conn.execute(
                "CREATE TABLE attempts"
                " (seq INTEGER PRIMARY KEY, status TEXT, reason TEXT, at TEXT,"
                "  event_seq INTEGER, attempt_id TEXT, event_id TEXT)"
            )
        else:
            conn.execute(
                "CREATE TABLE acquisitions(row_id TEXT, offering_id TEXT)"
            )
            conn.execute("CREATE TABLE attempts(seq INTEGER PRIMARY KEY)")
        conn.commit()


@pytest.mark.parametrize(
    ("active_mode", "inactive_store", "relation"),
    (
        ("full_offsite", "observations", "acquisitions"),
        ("full_offsite", "observations", "attempts"),
        ("metadata_only", "receipts", "acquisitions"),
        ("metadata_only", "receipts", "attempts"),
    ),
)
def test_v8_c2_any_unreadable_counterpart_relation_refuses_before_staging(
    tmp_path: Path, active_mode: str, inactive_store: str, relation: str
) -> None:
    setup = _driver(tmp_path, mode=active_mode)
    setup.initialize_database("semantics")
    inactive = tmp_path / RUNTIME_PATHS[inactive_store]
    _v8_create_unreadable_counterpart_relation(inactive, relation=relation)

    driver = _driver(tmp_path, mode=active_mode)
    with pytest.raises(driver.error_type) as caught:
        driver.intake(
            archive_bytes=_unit_zip(),
            offering=_offering(f"unreadable-{inactive_store}-{relation}"),
        )
    assert _error_code(caught.value) == (
        f"store_unreadable:{inactive_store}.{relation}"
    )
    assert driver.snapshot()["objects"] == []
    assert driver.snapshot()["raw_provider_entries"] == []
    assert "staging_create" not in driver.snapshot()["trace"]


@pytest.mark.parametrize(
    ("section", "field", "expected_prefix"),
    (
        ("assertion", "claim", "semantic_claim_invalid:"),
        ("attachment", "provenance", "semantic_provenance_invalid:"),
        ("attachment", "retention", "semantic_retention_invalid:"),
    ),
)
def test_v8_h3_unhashable_semantic_vocabulary_is_a_domain_refusal(
    tmp_path: Path, section: str, field: str, expected_prefix: str
) -> None:
    driver = _driver(tmp_path)
    before = driver.semantic_state(key=SEMANTIC_KEY)
    record = _semantic_record()
    record[section][field] = []
    try:
        driver.write_semantic_assertion(record)
    except driver.error_type as exc:
        assert _error_code(exc).startswith(expected_prefix)
    except Exception as exc:  # pragma: no cover - c183c11 leaks TypeError
        pytest.fail(f"semantic writer leaked {type(exc).__name__}: {exc}")
    else:  # pragma: no cover - malformed vocabulary must never be accepted
        pytest.fail(f"semantic writer accepted unhashable {section}.{field}")
    assert driver.semantic_state(key=SEMANTIC_KEY) == before


@pytest.mark.parametrize(
    ("field", "expected_prefix"),
    (
        ("authority", "adjudication_authority_invalid:"),
        ("provenance", "adjudication_provenance_invalid:"),
    ),
)
def test_v8_h3_unhashable_adjudication_vocabulary_is_a_domain_refusal(
    tmp_path: Path, field: str, expected_prefix: str
) -> None:
    driver = _driver(tmp_path)
    driver.initialize_database("semantics")
    record = {
        "adjudication_id": "unhashable-adjudication",
        "key": SEMANTIC_KEY,
        "authority": "david",
        "provenance": "explicit-ruling",
        "parents": ["parent"],
        "effective_assertion_id": "parent",
    }
    record[field] = []
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        before = conn.execute(
            "SELECT count(*) FROM semantic_adjudications"
        ).fetchone()[0]
    try:
        driver.write_semantic_adjudication(record)
    except driver.error_type as exc:
        assert _error_code(exc).startswith(expected_prefix)
    except Exception as exc:  # pragma: no cover - c183c11 leaks TypeError
        pytest.fail(f"adjudication writer leaked {type(exc).__name__}: {exc}")
    else:  # pragma: no cover - malformed vocabulary must never be accepted
        pytest.fail(f"adjudication writer accepted unhashable {field}")
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        after = conn.execute(
            "SELECT count(*) FROM semantic_adjudications"
        ).fetchone()[0]
    assert after == before


def _v8_committed_attempts_drop_wal(path: Path) -> bytes:
    source = path.with_name(f"{path.name}.race-source")
    shutil.copy2(path, source)
    writer = sqlite3.connect(source)
    try:
        assert writer.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("DROP TABLE attempts")
        writer.commit()
        wal = Path(f"{source}-wal")
        assert wal.exists() and wal.stat().st_size > 0
        assert source.read_bytes() == path.read_bytes()
        return wal.read_bytes()
    finally:
        writer.close()
        source.unlink(missing_ok=True)
        Path(f"{source}-wal").unlink(missing_ok=True)
        Path(f"{source}-shm").unlink(missing_ok=True)


def test_v8_h4_wal_appearance_between_observe_and_open_retries_truthfully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = _driver(tmp_path)
    setup.initialize_database("observations")
    target = tmp_path / RUNTIME_PATHS["observations"]
    wal_bytes = _v8_committed_attempts_drop_wal(target)
    mod = _mod()
    observer = getattr(mod, "_observe_sqlite_file_set", None)
    assert callable(observer), "reader needs one observable file-set boundary"
    injected = False

    def appear_after_observation(path: Path):
        nonlocal injected
        observed = observer(path)
        if Path(path) == target and not injected:
            assert not Path(f"{target}-wal").exists()
            Path(f"{target}-wal").write_bytes(wal_bytes)
            injected = True
        return observed

    monkeypatch.setattr(mod, "_observe_sqlite_file_set", appear_after_observation)
    _v5_assert_row9(_driver(tmp_path).read_model(now=NOW))
    assert injected


def test_v8_h4_persistently_unstable_file_set_fails_closed_with_a_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = _driver(tmp_path)
    setup.initialize_database("observations")
    target = tmp_path / RUNTIME_PATHS["observations"]
    mod = _mod()
    observer = getattr(mod, "_observe_sqlite_file_set", None)
    assert callable(observer), "reader needs one observable file-set boundary"
    stable = observer(target)
    wal_path = Path(f"{target}-wal")
    wal_path.write_bytes(b"unstable-sentinel")
    changed = observer(target)
    wal_path.unlink()
    assert changed != stable
    calls = 0

    def never_stable(path: Path):
        nonlocal calls
        if Path(path) != target:
            return observer(path)
        calls += 1
        return stable if calls % 2 else changed

    monkeypatch.setattr(mod, "_observe_sqlite_file_set", never_stable)
    _v5_assert_row9(_driver(tmp_path).read_model(now=NOW))
    assert 2 <= calls <= 64, "observe-open-reobserve retries must be bounded"


# ---------------------------------------------------------------------------
# V9 — accepted 7e39763 findings: constraint identity, event closure, freeze
# ---------------------------------------------------------------------------


_V9_SEMANTIC_LAYOUTS = {
    "semantic_assertions": (
        "assertion_id",
        "key",
        "CREATE TABLE semantic_assertions (assertion_id TEXT, key TEXT,"
        " version INTEGER, claim TEXT, active INTEGER, evidence_id TEXT)",
    ),
    "semantic_attachments": (
        "evidence_id",
        "provenance",
        "CREATE TABLE semantic_attachments (evidence_id TEXT, retrieved_at TEXT,"
        " provenance TEXT, retention TEXT, evidence_sha256 TEXT,"
        " evidence_bytes INTEGER)",
    ),
    "semantic_evidence_objects": (
        "evidence_sha256",
        "evidence_blob",
        "CREATE TABLE semantic_evidence_objects (evidence_sha256 TEXT,"
        " evidence_blob BLOB)",
    ),
    "semantic_adjudications": (
        "adjudication_id",
        "key",
        "CREATE TABLE semantic_adjudications (adjudication_id TEXT, key TEXT,"
        " authority TEXT, provenance TEXT, parents TEXT,"
        " effective_assertion_id TEXT)",
    ),
}


def _v9_rebuild_semantic_table_without_identity_constraint(
    path: Path, table: str, *, substitute: str | None = None
) -> None:
    identity, wrong_column, ddl = _V9_SEMANTIC_LAYOUTS[table]
    with contextlib.closing(sqlite3.connect(path)) as conn:
        conn.execute(f"ALTER TABLE {table} RENAME TO {table}_governed")
        conn.execute(ddl)
        columns = [
            row[1] for row in conn.execute(f"PRAGMA table_info({table})")
        ]
        joined = ",".join(columns)
        conn.execute(
            f"INSERT INTO {table} ({joined})"
            f" SELECT {joined} FROM {table}_governed"
        )
        conn.execute(f"DROP TABLE {table}_governed")
        if substitute == "wrong_column":
            conn.execute(
                f"CREATE UNIQUE INDEX v9_wrong_{table}"
                f" ON {table}({wrong_column})"
            )
        elif substitute == "partial_identity":
            conn.execute(
                f"CREATE UNIQUE INDEX v9_partial_{table}"
                f" ON {table}({identity}) WHERE {identity} IS NOT NULL"
            )
        conn.commit()


@pytest.mark.parametrize("table", tuple(_V9_SEMANTIC_LAYOUTS))
@pytest.mark.parametrize(
    "substitute", (None, "wrong_column", "partial_identity")
)
def test_v9_c1_every_semantic_identity_requires_exact_nonpartial_constraint(
    tmp_path: Path, table: str, substitute: str | None
) -> None:
    driver = _driver(tmp_path)
    driver.initialize_database("semantics")
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    _v9_rebuild_semantic_table_without_identity_constraint(
        semantics, table, substitute=substitute
    )

    with pytest.raises(driver.error_type) as caught:
        _driver(tmp_path).initialize_database("semantics")
    assert _error_code(caught.value) == "store_schema_unmigratable:semantics"


def _v9_seed_conflicted_semantics(driver: Any) -> None:
    driver.write_semantic_assertion(
        _semantic_record(assertion_id="v9-redraft", claim="redraft", version=1)
    )
    driver.write_semantic_assertion(
        _semantic_record(
            assertion_id="v9-dynasty", claim="dynasty_startup", version=2
        )
    )
    result = driver.write_semantic_adjudication(
        {
            "adjudication_id": "v9-adjudication",
            "key": SEMANTIC_KEY,
            "authority": "david",
            "provenance": "explicit-ruling",
            "parents": ["v9-redraft", "v9-dynasty"],
            "effective_assertion_id": "v9-dynasty",
        }
    )
    assert _value(result, "status") == "written"


@pytest.mark.parametrize("table", tuple(_V9_SEMANTIC_LAYOUTS))
def test_v9_c1_duplicate_semantic_identity_fails_before_projection(
    tmp_path: Path, table: str
) -> None:
    driver = _driver(tmp_path)
    _v9_seed_conflicted_semantics(driver)
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    _v9_rebuild_semantic_table_without_identity_constraint(semantics, table)
    identity = _V9_SEMANTIC_LAYOUTS[table][0]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        joined = ",".join(columns)
        conn.execute(
            f"INSERT INTO {table} ({joined})"
            f" SELECT {joined} FROM {table} WHERE {identity}=("
            f" SELECT {identity} FROM {table} LIMIT 1) LIMIT 1"
        )
        duplicate_count = conn.execute(
            f"SELECT count(*) FROM {table} GROUP BY {identity}"
            " HAVING count(*) > 1"
        ).fetchone()[0]
        conn.commit()
    assert duplicate_count == 2

    state = _driver(tmp_path).semantic_state(key=SEMANTIC_KEY)
    assert state == {
        "state": "unknown",
        "reason": f"semantic_identity_duplicate:{table}",
        "eligible_for_phase_c": False,
    }


def _v9_rebuild_event_ledger_with_substitute_index(
    path: Path, *, substitute: str
) -> None:
    with contextlib.closing(sqlite3.connect(path)) as conn:
        conn.execute("ALTER TABLE event_sequence RENAME TO event_sequence_governed")
        conn.execute(
            "CREATE TABLE event_sequence (seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " event_id TEXT, event_type TEXT, store_name TEXT, subject_id TEXT,"
            " event_at TEXT)"
        )
        conn.execute(
            "INSERT INTO event_sequence"
            " (seq,event_id,event_type,store_name,subject_id,event_at)"
            " SELECT seq,event_id,event_type,store_name,subject_id,event_at"
            " FROM event_sequence_governed"
        )
        conn.execute("DROP TABLE event_sequence_governed")
        if substitute == "wrong_column":
            conn.execute(
                "CREATE UNIQUE INDEX v9_wrong_event_unique"
                " ON event_sequence(subject_id)"
            )
        else:
            conn.execute(
                "CREATE UNIQUE INDEX v9_partial_event_unique"
                " ON event_sequence(event_id) WHERE event_type='attempt'"
            )
        conn.commit()


@pytest.mark.parametrize("substitute", ("wrong_column", "partial_event_id"))
def test_v9_h2_event_id_requires_exact_full_nonpartial_unique_index(
    tmp_path: Path, substitute: str
) -> None:
    driver = _driver(tmp_path)
    driver.initialize_database("semantics")
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    _v9_rebuild_event_ledger_with_substitute_index(
        semantics, substitute=substitute
    )

    with pytest.raises(driver.error_type) as caught:
        _driver(tmp_path).initialize_database("semantics")
    assert _error_code(caught.value) == "store_schema_unmigratable:semantics"


def _v9_seed_acquisition_and_attempt(tmp_path: Path) -> tuple[Path, Path, str]:
    driver = _driver(tmp_path)
    assert driver.intake(
        archive_bytes=_unit_zip(), offering=_offering("v9-event-acquisition")
    ).status == "review_required"
    assert driver.intake(
        archive_bytes=b"not-a-zip", offering=_offering("v9-event-attempt")
    ).status == "failed"
    receipts = tmp_path / RUNTIME_PATHS["receipts"]
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(receipts)) as conn:
        event_id = conn.execute(
            "SELECT event_id FROM acquisitions"
            " WHERE offering_id='v9-event-acquisition'"
        ).fetchone()[0]
    return receipts, semantics, event_id


@pytest.mark.parametrize(
    "bad_event_at",
    (
        "2026-08-10T12:00:00",
        "2026-08-10T12:00:00.123456-04:00",
        "2099-01-01T00:00:00Z",
        "not-an-instant",
    ),
    ids=("naive", "fractional", "future", "malformed"),
)
def test_v9_h3_persisted_event_instant_is_canonical_or_fail_closed(
    tmp_path: Path, bad_event_at: str
) -> None:
    receipts, semantics, event_id = _v9_seed_acquisition_and_attempt(tmp_path)
    with contextlib.closing(sqlite3.connect(receipts)) as conn:
        conn.execute(
            "UPDATE acquisitions SET event_at=? WHERE event_id=?",
            (bad_event_at, event_id),
        )
        conn.commit()
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute(
            "UPDATE event_sequence SET event_at=? WHERE event_id=?",
            (bad_event_at, event_id),
        )
        conn.commit()

    try:
        state = _driver(tmp_path).read_model(now=NOW)
    except Exception as exc:  # pragma: no cover - 7e39763 raises on mixed tz
        pytest.fail(f"malformed persisted event instant raised: {exc!r}")
    assert state["status"] == "unverifiable"
    assert state["phase_c_open"] is False
    assert state["pill_delta"] == 1


def _v9_retype_event_sequence_as_text(path: Path) -> None:
    with contextlib.closing(sqlite3.connect(path)) as conn:
        conn.execute("ALTER TABLE event_sequence RENAME TO event_sequence_governed")
        conn.execute(
            "CREATE TABLE event_sequence (seq TEXT, event_id TEXT UNIQUE,"
            " event_type TEXT, store_name TEXT, subject_id TEXT, event_at TEXT)"
        )
        conn.execute(
            "INSERT INTO event_sequence"
            " (seq,event_id,event_type,store_name,subject_id,event_at)"
            " SELECT CAST(seq AS TEXT),event_id,event_type,store_name,subject_id,"
            " event_at FROM event_sequence_governed"
        )
        conn.execute("DROP TABLE event_sequence_governed")
        conn.commit()


def _v9_retype_acquisition_event_sequence_as_text(path: Path) -> None:
    with contextlib.closing(sqlite3.connect(path)) as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(acquisitions)")]
        conn.execute("ALTER TABLE acquisitions RENAME TO acquisitions_governed")
        select = ",".join(
            "CAST(event_seq AS TEXT) AS event_seq" if name == "event_seq" else name
            for name in columns
        )
        conn.execute(f"CREATE TABLE acquisitions AS SELECT {select} FROM acquisitions_governed")
        conn.execute("DROP TABLE acquisitions_governed")
        conn.commit()


def test_v9_h3_persisted_event_sequence_must_be_exact_integer(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    assert driver.intake(
        archive_bytes=_unit_zip(), offering=_offering("v9-string-event-seq")
    ).status == "review_required"
    receipts = tmp_path / RUNTIME_PATHS["receipts"]
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    _v9_retype_acquisition_event_sequence_as_text(receipts)
    _v9_retype_event_sequence_as_text(semantics)

    _v6_assert_event_integrity_fail_closed(tmp_path)


def test_v9_h3_writer_refuses_fractional_event_clock_before_commit(
    tmp_path: Path,
) -> None:
    clock = [datetime.fromisoformat("2026-08-10T12:00:00.123456-04:00")]
    driver = _clocked_driver(tmp_path, clock)
    try:
        result = driver.intake(
            archive_bytes=_unit_zip(),
            offering=_offering("v9-fractional-event-writer"),
        )
    except driver.error_type as exc:
        assert _error_code(exc).startswith("event_at_invalid:")
    except Exception as exc:  # pragma: no cover - domain errors only
        pytest.fail(f"fractional event clock leaked {type(exc).__name__}: {exc}")
    else:
        pytest.fail(f"fractional event clock was accepted: {result.status}")


def test_v9_h4_delete_mode_unreconcilable_store_refuses_byte_frozen(
    tmp_path: Path,
) -> None:
    setup = _driver(tmp_path)
    setup.initialize_database("receipts")
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        assert conn.execute("PRAGMA journal_mode=DELETE").fetchone()[0] == "delete"
        conn.execute("CREATE TABLE event_sequence(seq INTEGER)")
        conn.execute("INSERT INTO event_sequence VALUES (1)")
        conn.commit()
    before = _v5_main_wal_fingerprint(semantics)

    driver = _driver(tmp_path)
    with pytest.raises(driver.error_type) as caught:
        driver.intake(
            archive_bytes=_unit_zip(),
            offering=_offering("v9-delete-mode-unreconcilable"),
        )
    assert _error_code(caught.value) == "store_migration_unreconcilable:semantics"
    assert _v5_main_wal_fingerprint(semantics) == before
    assert driver.snapshot()["objects"] == []
    assert "staging_create" not in driver.snapshot()["trace"]


@pytest.mark.parametrize(
    ("field", "bad_value", "expected_prefix"),
    (
        ("adjudication_id", [], "adjudication_id_invalid:"),
        ("adjudication_id", 7, "adjudication_id_invalid:"),
        ("key", [], "adjudication_key_invalid:"),
        ("key", b"blob-key", "adjudication_key_invalid:"),
        (
            "effective_assertion_id",
            [],
            "adjudication_effective_assertion_id_invalid:",
        ),
        (
            "effective_assertion_id",
            7,
            "adjudication_effective_assertion_id_invalid:",
        ),
    ),
)
def test_v9_h5_adjudication_identity_fields_are_total_named_refusals(
    tmp_path: Path, field: str, bad_value: Any, expected_prefix: str
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(
        _semantic_record(assertion_id="v9-parent", version=1)
    )
    record: dict[str, Any] = {
        "adjudication_id": "v9-total-adjudication",
        "key": SEMANTIC_KEY,
        "authority": "david",
        "provenance": "explicit-ruling",
        "parents": ["v9-parent"],
        "effective_assertion_id": "v9-parent",
    }
    record[field] = bad_value
    before_state = driver.semantic_state(key=SEMANTIC_KEY)
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        before_rows = conn.execute(
            "SELECT count(*) FROM semantic_adjudications"
        ).fetchone()[0]

    try:
        driver.write_semantic_adjudication(record)
    except driver.error_type as exc:
        assert _error_code(exc).startswith(expected_prefix)
    except Exception as exc:  # pragma: no cover - 7e39763 leaks bare errors
        pytest.fail(f"adjudication writer leaked {type(exc).__name__}: {exc}")
    else:  # pragma: no cover - malformed identity is never accepted
        pytest.fail(f"adjudication writer accepted malformed {field}")

    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        after_rows = conn.execute(
            "SELECT count(*) FROM semantic_adjudications"
        ).fetchone()[0]
    assert after_rows == before_rows
    assert driver.semantic_state(key=SEMANTIC_KEY) == before_state


# ---------------------------------------------------------------------------
# V10 — accepted b582b1d findings: load types, whole order, clock, pure refusal
# ---------------------------------------------------------------------------


def _v10_seed_semantic_conflict(driver: Any) -> None:
    driver.write_semantic_assertion(
        _semantic_record(assertion_id="v10-redraft", claim="redraft", version=1)
    )
    driver.write_semantic_assertion(
        _semantic_record(
            assertion_id="v10-dynasty", claim="dynasty_startup", version=2
        )
    )
    result = driver.write_semantic_adjudication(
        {
            "adjudication_id": "v10-adjudication",
            "key": SEMANTIC_KEY,
            "authority": "david",
            "provenance": "explicit-ruling",
            "parents": ["v10-redraft", "v10-dynasty"],
            "effective_assertion_id": "v10-dynasty",
        }
    )
    assert _value(result, "status") == "written"


@pytest.mark.parametrize(
    ("field", "bad_value"),
    (
        ("adjudication_id", ""),
        ("adjudication_id", sqlite3.Binary(b"blob-adjudication")),
        ("key", ""),
        ("key", sqlite3.Binary(b"blob-key")),
        ("effective_assertion_id", ""),
        ("effective_assertion_id", sqlite3.Binary(b"blob-effective")),
    ),
)
def test_v10_c1_restored_adjudication_scalars_fail_before_projection(
    tmp_path: Path, field: str, bad_value: Any
) -> None:
    driver = _driver(tmp_path)
    _v10_seed_semantic_conflict(driver)
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute(
            f"UPDATE semantic_adjudications SET {field}=?",
            (bad_value,),
        )
        conn.commit()

    state = _driver(tmp_path).semantic_state(key=SEMANTIC_KEY)
    assert state == {
        "state": "unknown",
        "reason": "adjudication_row_invalid",
        "eligible_for_phase_c": False,
    }


def test_v10_c1_restored_assertion_active_requires_exact_sqlite_integer(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(_semantic_record())
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        columns = [
            row[1] for row in conn.execute("PRAGMA table_info(semantic_assertions)")
        ]
        conn.execute(
            "ALTER TABLE semantic_assertions RENAME TO semantic_assertions_governed"
        )
        conn.execute(
            "CREATE TABLE semantic_assertions (assertion_id TEXT PRIMARY KEY,"
            " key TEXT, version INTEGER, claim TEXT, active REAL, evidence_id TEXT)"
        )
        select = ",".join(
            "CAST(active AS REAL) AS active" if column == "active" else column
            for column in columns
        )
        conn.execute(
            f"INSERT INTO semantic_assertions SELECT {select}"
            " FROM semantic_assertions_governed"
        )
        conn.execute("DROP TABLE semantic_assertions_governed")
        conn.commit()
        stored = conn.execute(
            "SELECT active, typeof(active) FROM semantic_assertions"
        ).fetchone()
    assert stored == (1.0, "real")

    state = _driver(tmp_path).semantic_state(key=SEMANTIC_KEY)
    assert state == {
        "state": "unknown",
        "reason": "assertion_row_invalid",
        "eligible_for_phase_c": False,
    }


def _v10_replace_event_sequence_schema(path: Path, variant: str) -> None:
    if variant == "no_primary_key":
        seq_ddl = "seq INTEGER"
    elif variant == "wrong_type":
        seq_ddl = "seq TEXT PRIMARY KEY"
    else:
        seq_ddl = "seq INTEGER PRIMARY KEY"
    with contextlib.closing(sqlite3.connect(path)) as conn:
        conn.execute("ALTER TABLE event_sequence RENAME TO event_sequence_governed")
        conn.execute(
            f"CREATE TABLE event_sequence ({seq_ddl}, event_id TEXT UNIQUE,"
            " event_type TEXT, store_name TEXT, subject_id TEXT, event_at TEXT)"
        )
        conn.execute(
            "INSERT INTO event_sequence"
            " (seq,event_id,event_type,store_name,subject_id,event_at)"
            " SELECT seq,event_id,event_type,store_name,subject_id,event_at"
            " FROM event_sequence_governed"
        )
        conn.execute("DROP TABLE event_sequence_governed")
        conn.commit()


@pytest.mark.parametrize(
    "variant", ("no_primary_key", "wrong_type", "no_autoincrement")
)
def test_v10_h2_event_sequence_requires_whole_pk_autoincrement_structure(
    tmp_path: Path, variant: str
) -> None:
    driver = _driver(tmp_path)
    driver.initialize_database("semantics")
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    _v10_replace_event_sequence_schema(semantics, variant)

    with pytest.raises(driver.error_type) as caught:
        _driver(tmp_path).initialize_database("semantics")
    assert _error_code(caught.value) == "store_schema_unmigratable:semantics"


def _v10_seed_event_pair(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    driver = _driver(tmp_path)
    assert driver.intake(
        archive_bytes=_unit_zip(), offering=_offering("v10-acquisition")
    ).status == "review_required"
    assert driver.intake(
        archive_bytes=b"not-a-zip", offering=_offering("v10-attempt")
    ).status == "failed"
    receipts = tmp_path / RUNTIME_PATHS["receipts"]
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        event_ids = {
            event_type: event_id
            for event_id, event_type in conn.execute(
                "SELECT event_id,event_type FROM event_sequence"
            )
        }
    return receipts, semantics, event_ids


@pytest.mark.parametrize(
    ("shape", "acquisition_seq", "attempt_seq"),
    (
        ("duplicate", 1, 1),
        ("nonpositive", 0, 2),
        ("nonmonotonic", 2, 1),
    ),
)
def test_v10_h2_invalid_central_sequence_fails_before_order_projection(
    tmp_path: Path, shape: str, acquisition_seq: int, attempt_seq: int
) -> None:
    del shape
    receipts, semantics, event_ids = _v10_seed_event_pair(tmp_path)
    assigned = {
        event_ids["acquisition"]: acquisition_seq,
        event_ids["attempt"]: attempt_seq,
    }
    with contextlib.closing(sqlite3.connect(receipts)) as conn:
        conn.execute(
            "UPDATE acquisitions SET event_seq=? WHERE event_id=?",
            (acquisition_seq, event_ids["acquisition"]),
        )
        conn.execute(
            "UPDATE attempts SET event_seq=? WHERE event_id=?",
            (attempt_seq, event_ids["attempt"]),
        )
        conn.commit()
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        rows = conn.execute(
            "SELECT seq,event_id,event_type,store_name,subject_id,event_at"
            " FROM event_sequence ORDER BY seq"
        ).fetchall()
        conn.execute("ALTER TABLE event_sequence RENAME TO event_sequence_governed")
        conn.execute(
            "CREATE TABLE event_sequence (seq INTEGER, event_id TEXT UNIQUE,"
            " event_type TEXT, store_name TEXT, subject_id TEXT, event_at TEXT)"
        )
        conn.executemany(
            "INSERT INTO event_sequence VALUES (?,?,?,?,?,?)",
            [(assigned[row[1]], *row[1:]) for row in rows],
        )
        conn.execute("DROP TABLE event_sequence_governed")
        conn.commit()

    _v6_assert_event_integrity_fail_closed(tmp_path)


def test_v10_h3_attempt_sequence_uses_acquisition_exact_int_predicate(
    tmp_path: Path,
) -> None:
    receipts, _, _ = _v10_seed_event_pair(tmp_path)
    with contextlib.closing(sqlite3.connect(receipts)) as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(attempts)")]
        conn.execute("ALTER TABLE attempts RENAME TO attempts_governed")
        select = ",".join(
            "CAST(event_seq AS REAL) AS event_seq" if column == "event_seq" else column
            for column in columns
        )
        conn.execute(f"CREATE TABLE attempts AS SELECT {select} FROM attempts_governed")
        conn.execute("DROP TABLE attempts_governed")
        conn.commit()
        stored = conn.execute("SELECT event_seq, typeof(event_seq) FROM attempts").fetchone()
    assert stored[1] == "real" and isinstance(stored[0], float)

    _v6_assert_event_integrity_fail_closed(tmp_path)


def test_v10_h4_invalid_naive_read_clock_is_named_fail_closed(
    tmp_path: Path,
) -> None:
    assert _driver(tmp_path).intake(
        archive_bytes=_unit_zip(), offering=_offering("v10-aware-event")
    ).status == "review_required"
    driver = _clocked_driver(tmp_path, [datetime(2026, 8, 10, 12, 0, 0)])
    try:
        state = driver.read_model(now=NOW)
    except Exception as exc:  # pragma: no cover - b582b1d leaks TypeError
        pytest.fail(f"invalid read clock raised {type(exc).__name__}: {exc}")
    _v5_assert_row9(state)


def test_v10_h4_read_clock_is_validated_once_and_reused(
    tmp_path: Path,
) -> None:
    seeded = _driver(tmp_path)
    assert seeded.intake(
        archive_bytes=_unit_zip(), offering=_offering("v10-clock-once")
    ).status == "review_required"
    assert seeded.intake(
        archive_bytes=b"not-a-zip", offering=_offering("v10-clock-once-failure")
    ).status == "failed"
    calls = 0

    def counted_clock() -> datetime:
        nonlocal calls
        calls += 1
        return NOW

    driver = _mod().build_contract_driver(
        repo_root=tmp_path,
        manifest_path=_write_manifest(tmp_path),
        retention_mode="full_offsite",
        clock=counted_clock,
    )
    driver.read_model(now=NOW)
    assert calls == 1


@pytest.mark.parametrize("writer", ("assertion", "adjudication"))
def test_v10_h5_invalid_semantic_record_is_pure_before_store_initialization(
    tmp_path: Path, writer: str
) -> None:
    driver = _driver(tmp_path)
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    sidecars = (semantics, Path(f"{semantics}-wal"), Path(f"{semantics}-shm"))
    assert not any(path.exists() for path in sidecars)

    if writer == "assertion":
        record = _semantic_record()
        record["assertion"]["key"] = []
        expected_prefix = "semantic_id_invalid:key"
        call = driver.write_semantic_assertion
    else:
        record = {
            "adjudication_id": "v10-fresh-invalid",
            "key": [],
            "authority": "david",
            "provenance": "explicit-ruling",
            "parents": ["parent"],
            "effective_assertion_id": "parent",
        }
        expected_prefix = "adjudication_key_invalid:"
        call = driver.write_semantic_adjudication

    try:
        call(record)
    except driver.error_type as exc:
        assert _error_code(exc).startswith(expected_prefix)
    except Exception as exc:  # pragma: no cover - named domain refusal only
        pytest.fail(f"invalid fresh {writer} raised {type(exc).__name__}: {exc}")
    else:  # pragma: no cover - invalid records are never accepted
        pytest.fail(f"invalid fresh {writer} record was accepted")

    assert not any(path.exists() for path in sidecars)


# ---------------------------------------------------------------------------
# V11 — accepted 297c52f findings: pre-filter assertions, bound DDL, total clock
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_key",
    (pytest.param("", id="empty"), pytest.param(sqlite3.Binary(b"bad-key"), id="blob")),
)
def test_v11_c1_corrupt_conflicting_assertion_key_cannot_open_eligibility(
    tmp_path: Path, bad_key: Any
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(
        _semantic_record(assertion_id="v11-redraft", claim="redraft", version=1)
    )
    driver.write_semantic_assertion(
        _semantic_record(
            assertion_id="v11-dynasty", claim="dynasty_startup", version=2
        )
    )
    before = driver.semantic_state(key=SEMANTIC_KEY)
    assert before == {
        "state": "unknown",
        "reason": "unresolved_assertion_conflict",
        "eligible_for_phase_c": False,
    }

    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute(
            "UPDATE semantic_assertions SET key=? WHERE assertion_id='v11-dynasty'",
            (bad_key,),
        )
        conn.commit()

    # The corrupt conflicting row must be validated before any key filter can
    # make it disappear and promote the healthy sibling into eligibility.
    assert _driver(tmp_path).semantic_state(key=SEMANTIC_KEY) == {
        "state": "unknown",
        "reason": "assertion_row_invalid",
        "eligible_for_phase_c": False,
    }


@pytest.mark.parametrize(
    ("field", "bad_value"),
    (
        pytest.param("assertion_id", "", id="assertion-id-empty"),
        pytest.param(
            "assertion_id", sqlite3.Binary(b"bad-id"), id="assertion-id-blob"
        ),
        pytest.param("key", "", id="key-empty"),
        pytest.param("key", sqlite3.Binary(b"bad-key"), id="key-blob"),
        pytest.param("version", "version-one", id="version-text"),
        pytest.param("version", 1.5, id="version-real"),
        pytest.param("claim", "seasonal-ish", id="claim-off-vocabulary"),
        pytest.param("claim", sqlite3.Binary(b"redraft"), id="claim-blob"),
        pytest.param("evidence_id", "", id="evidence-id-empty"),
        pytest.param(
            "evidence_id", sqlite3.Binary(b"bad-evidence"), id="evidence-id-blob"
        ),
    ),
)
def test_v11_c1_inactive_assertion_still_validates_every_writer_scalar(
    tmp_path: Path, field: str, bad_value: Any
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(
        _semantic_record(assertion_id="v11-healthy", claim="redraft", version=1)
    )
    driver.write_semantic_assertion(
        _semantic_record(
            assertion_id="v11-inactive", claim="dynasty_startup", version=2
        )
    )
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute(
            "UPDATE semantic_assertions SET active=0 WHERE assertion_id='v11-inactive'"
        )
        conn.execute(
            f"UPDATE semantic_assertions SET {field}=?"
            " WHERE assertion_id='v11-inactive'",
            (bad_value,),
        )
        conn.commit()

    # Validation is table-wide and precedes active/key projection. An inactive
    # corrupt row cannot be ignored merely because a healthy active sibling exists.
    assert _driver(tmp_path).semantic_state(key=SEMANTIC_KEY) == {
        "state": "unknown",
        "reason": "assertion_row_invalid",
        "eligible_for_phase_c": False,
    }


def test_v11_h2_autoincrement_token_in_unrelated_default_does_not_prove_seq(
    tmp_path: Path,
) -> None:
    driver = _driver(tmp_path)
    driver.initialize_database("semantics")
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute("ALTER TABLE event_sequence RENAME TO event_sequence_governed")
        conn.execute(
            "CREATE TABLE event_sequence ("
            "seq INTEGER PRIMARY KEY, event_id TEXT UNIQUE, event_type TEXT,"
            "store_name TEXT, subject_id TEXT,"
            "event_at TEXT DEFAULT 'AUTOINCREMENT')"
        )
        conn.execute("DROP TABLE event_sequence_governed")
        conn.commit()
        ddl = conn.execute(
            "SELECT sql FROM sqlite_master"
            " WHERE type='table' AND name='event_sequence'"
        ).fetchone()[0]
        seq_info = next(
            row for row in conn.execute("PRAGMA table_info(event_sequence)")
            if row[1] == "seq"
        )
    assert "AUTOINCREMENT" in ddl
    assert "seq INTEGER PRIMARY KEY AUTOINCREMENT" not in ddl
    assert seq_info[2].upper() == "INTEGER" and seq_info[5] == 1

    with pytest.raises(driver.error_type) as caught:
        _driver(tmp_path).initialize_database("semantics")
    assert _error_code(caught.value) == "store_schema_unmigratable:semantics"


@pytest.mark.parametrize(
    "bad_clock",
    (
        pytest.param("2026-08-10T12:00:00-04:00", id="string"),
        pytest.param(None, id="none"),
        pytest.param(7, id="integer"),
    ),
)
def test_v11_m3_every_non_datetime_read_clock_is_named_fail_closed(
    tmp_path: Path, bad_clock: Any
) -> None:
    driver = _mod().build_contract_driver(
        repo_root=tmp_path,
        manifest_path=_write_manifest(tmp_path),
        retention_mode="full_offsite",
        clock=lambda: bad_clock,
    )
    try:
        state = driver.read_model(now=NOW)
    except Exception as exc:  # pragma: no cover - 297c52f leaks AttributeError
        pytest.fail(f"non-datetime read clock raised {type(exc).__name__}: {exc}")
    _v5_assert_row9(state)


# ---------------------------------------------------------------------------
# V12 — accepted c32884a findings: parsed seq ownership, SQLite int domain
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "event_at_suffix",
    (
        pytest.param(
            "DEFAULT 'SEQ INTEGER PRIMARY KEY AUTOINCREMENT'",
            id="quoted-literal",
        ),
        pytest.param(
            "/* SEQ INTEGER PRIMARY KEY AUTOINCREMENT */",
            id="block-comment",
        ),
        pytest.param(
            "-- SEQ INTEGER PRIMARY KEY AUTOINCREMENT\n",
            id="line-comment",
        ),
    ),
)
def test_v12_h1_seq_autoincrement_proof_ignores_literals_and_comments(
    tmp_path: Path, event_at_suffix: str
) -> None:
    driver = _driver(tmp_path)
    driver.initialize_database("semantics")
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute("ALTER TABLE event_sequence RENAME TO event_sequence_governed")
        conn.execute(
            "CREATE TABLE event_sequence ("
            "seq INTEGER PRIMARY KEY, event_id TEXT UNIQUE, event_type TEXT,"
            "store_name TEXT, subject_id TEXT, event_at TEXT "
            + event_at_suffix
            + ")"
        )
        conn.execute("DROP TABLE event_sequence_governed")
        conn.commit()
        ddl = conn.execute(
            "SELECT sql FROM sqlite_master"
            " WHERE type='table' AND name='event_sequence'"
        ).fetchone()[0]
        seq_info = next(
            row for row in conn.execute("PRAGMA table_info(event_sequence)")
            if row[1] == "seq"
        )
    assert "SEQ INTEGER PRIMARY KEY AUTOINCREMENT" in ddl.upper()
    assert seq_info[2].upper() == "INTEGER" and seq_info[5] == 1

    with pytest.raises(driver.error_type) as caught:
        _driver(tmp_path).initialize_database("semantics")
    assert _error_code(caught.value) == "store_schema_unmigratable:semantics"


@pytest.mark.parametrize(
    "version",
    (
        pytest.param(2**63, id="positive-overflow"),
        pytest.param(-(2**63) - 1, id="negative-overflow"),
    ),
)
def test_v12_m2_unstorable_version_refuses_before_store_initialization(
    tmp_path: Path, version: int
) -> None:
    driver = _driver(tmp_path)
    record = _semantic_record(assertion_id=f"v12-overflow-{version}")
    record["assertion"]["version"] = version
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    sidecars = (semantics, Path(f"{semantics}-wal"), Path(f"{semantics}-shm"))
    assert not any(path.exists() for path in sidecars)

    try:
        driver.write_semantic_assertion(record)
    except driver.error_type as exc:
        assert _error_code(exc).startswith("semantic_version_invalid")
    except Exception as exc:  # pragma: no cover - c32884a leaks OverflowError
        pytest.fail(f"unstorable semantic version raised {type(exc).__name__}: {exc}")
    else:  # pragma: no cover - values outside signed 64-bit are never accepted
        pytest.fail("unstorable semantic version was accepted")

    assert not any(path.exists() for path in sidecars)


@pytest.mark.parametrize(
    "version",
    (
        pytest.param(-(2**63), id="minimum"),
        pytest.param(2**63 - 1, id="maximum"),
    ),
)
def test_v12_m2_signed_64_boundary_versions_remain_storable(
    tmp_path: Path, version: int
) -> None:
    driver = _driver(tmp_path)
    assertion_id = f"v12-boundary-{version}"
    record = _semantic_record(assertion_id=assertion_id)
    record["assertion"]["version"] = version
    assert _value(driver.write_semantic_assertion(record), "status") == "written"
    state = driver.semantic_state(key=SEMANTIC_KEY)
    assert state["state"] == "known"
    assert state["assertion_id"] == assertion_id


# ---------------------------------------------------------------------------
# V13 — accepted 62278ab finding: seq tokens are complete, not a prefix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("suffix", "governed"),
    (
        pytest.param("", True, id="canonical"),
        pytest.param(" CHECK(seq > 100)", False, id="load-bearing-check"),
        pytest.param(" UNIQUE", False, id="redundant-unique"),
    ),
)
def test_v13_h1_seq_declaration_requires_complete_exact_token_list(
    tmp_path: Path, suffix: str, governed: bool
) -> None:
    driver = _driver(tmp_path)
    driver.initialize_database("semantics")
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute("ALTER TABLE event_sequence RENAME TO event_sequence_governed")
        conn.execute(
            "CREATE TABLE event_sequence ("
            "seq INTEGER PRIMARY KEY AUTOINCREMENT"
            + suffix
            + ", event_id TEXT UNIQUE, event_type TEXT, store_name TEXT,"
            " subject_id TEXT, event_at TEXT)"
        )
        conn.execute("DROP TABLE event_sequence_governed")
        conn.commit()
        ddl = conn.execute(
            "SELECT sql FROM sqlite_master"
            " WHERE type='table' AND name='event_sequence'"
        ).fetchone()[0]
    assert "SEQ INTEGER PRIMARY KEY AUTOINCREMENT" in ddl.upper()

    reopened = _driver(tmp_path)
    if governed:
        reopened.initialize_database("semantics")
    else:
        with pytest.raises(driver.error_type) as caught:
            reopened.initialize_database("semantics")
        assert _error_code(caught.value) == "store_schema_unmigratable:semantics"


# ---------------------------------------------------------------------------
# V14 — accepted e19d056 finding: the whole event-table grammar is closed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("event_table_body", "governed"),
    (
        pytest.param(
            "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " event_id TEXT UNIQUE, event_type TEXT, store_name TEXT,"
            " subject_id TEXT, event_at TEXT",
            True,
            id="canonical-six-segment-table",
        ),
        pytest.param(
            "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " event_id TEXT UNIQUE, event_type TEXT, store_name TEXT,"
            " subject_id TEXT, event_at TEXT, CHECK(seq > 100)",
            False,
            id="load-bearing-table-check",
        ),
        pytest.param(
            "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " event_id TEXT UNIQUE, event_type TEXT, store_name TEXT,"
            " subject_id TEXT, event_at TEXT,"
            " CONSTRAINT seq_floor CHECK(seq > 100)",
            False,
            id="named-table-constraint",
        ),
        pytest.param(
            "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " event_id TEXT UNIQUE, event_type TEXT, store_name TEXT,"
            " subject_id TEXT, event_at TEXT, UNIQUE(seq)",
            False,
            id="redundant-table-unique",
        ),
        pytest.param(
            "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " event_id TEXT UNIQUE NOT NULL, event_type TEXT, store_name TEXT,"
            " subject_id TEXT, event_at TEXT",
            False,
            id="event-id-definition-suffix",
        ),
        pytest.param(
            "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " event_id TEXT UNIQUE, event_type TEXT NOT NULL, store_name TEXT,"
            " subject_id TEXT, event_at TEXT",
            False,
            id="event-type-definition-suffix",
        ),
        pytest.param(
            "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " event_id TEXT UNIQUE, event_type TEXT,"
            " store_name TEXT COLLATE BINARY, subject_id TEXT, event_at TEXT",
            False,
            id="store-name-definition-suffix",
        ),
        pytest.param(
            "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " event_id TEXT UNIQUE, event_type TEXT, store_name TEXT,"
            " subject_id TEXT DEFAULT '', event_at TEXT",
            False,
            id="subject-id-definition-suffix",
        ),
        pytest.param(
            "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " event_id TEXT UNIQUE, event_type TEXT, store_name TEXT,"
            " subject_id TEXT, event_at TEXT NOT NULL",
            False,
            id="event-at-definition-suffix",
        ),
        pytest.param(
            "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " event_id TEXT UNIQUE, store_name TEXT, event_type TEXT,"
            " subject_id TEXT, event_at TEXT",
            False,
            id="canonical-definitions-wrong-order",
        ),
    ),
)
def test_v14_h1_event_sequence_requires_complete_six_segment_grammar(
    tmp_path: Path, event_table_body: str, governed: bool
) -> None:
    driver = _driver(tmp_path)
    driver.initialize_database("semantics")
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute("ALTER TABLE event_sequence RENAME TO event_sequence_governed")
        conn.execute(
            "CREATE TABLE event_sequence (" + event_table_body + ")"
        )
        conn.execute("DROP TABLE event_sequence_governed")
        conn.commit()
        assert conn.execute("SELECT count(*) FROM event_sequence").fetchone()[0] == 0

    reopened = _driver(tmp_path)
    if governed:
        reopened.initialize_database("semantics")
        with contextlib.closing(sqlite3.connect(semantics)) as conn:
            assert conn.execute(
                "SELECT count(*) FROM event_sequence"
            ).fetchone()[0] == 0
    else:
        with pytest.raises(driver.error_type) as caught:
            reopened.initialize_database("semantics")
        assert _error_code(caught.value) == "store_schema_unmigratable:semantics"
        with contextlib.closing(sqlite3.connect(semantics)) as conn:
            assert conn.execute(
                "SELECT count(*) FROM event_sequence"
            ).fetchone()[0] == 0


# ---------------------------------------------------------------------------
# V15 — accepted f971244 finding: semantics-store object inventory is closed
# ---------------------------------------------------------------------------


_V15_APPLICATION_TABLES = (
    "acquisitions",
    "semantic_assertions",
    "semantic_attachments",
    "semantic_evidence_objects",
    "semantic_adjudications",
    "event_sequence",
)


def _v15_application_rows(conn: sqlite3.Connection) -> dict[str, list[tuple[Any, ...]]]:
    return {
        table: [tuple(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY rowid")]
        for table in _V15_APPLICATION_TABLES
    }


@pytest.mark.parametrize(
    ("schema_object_sql", "governed"),
    (
        pytest.param(None, True, id="canonical-object-inventory"),
        pytest.param(
            "CREATE TRIGGER reject_event BEFORE INSERT ON event_sequence "
            "BEGIN SELECT RAISE(ABORT, 'event blocked'); END",
            False,
            id="event-abort-trigger",
        ),
        pytest.param(
            "CREATE TRIGGER ignore_event BEFORE INSERT ON event_sequence "
            "BEGIN SELECT RAISE(IGNORE); END",
            False,
            id="event-ignore-trigger",
        ),
        pytest.param(
            "CREATE TRIGGER reject_assertion BEFORE INSERT ON semantic_assertions "
            "BEGIN SELECT RAISE(ABORT, 'assertion blocked'); END",
            False,
            id="second-governed-table-trigger",
        ),
        pytest.param(
            "CREATE VIEW semantic_shadow AS SELECT * FROM semantic_assertions",
            False,
            id="surplus-view",
        ),
        pytest.param(
            "CREATE TABLE semantic_shadow (payload TEXT)",
            False,
            id="surplus-table",
        ),
        pytest.param(
            "CREATE UNIQUE INDEX one_event_type ON event_sequence(event_type)",
            False,
            id="surplus-unique-index",
        ),
        pytest.param(
            "CREATE INDEX event_at_lookup ON event_sequence(event_at)",
            False,
            id="surplus-nonunique-index",
        ),
    ),
)
def test_v15_h1_semantics_store_requires_exact_schema_object_inventory(
    tmp_path: Path, schema_object_sql: str | None, governed: bool
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(
        _semantic_record(assertion_id="v15-application-marker")
    )
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute(
            "INSERT INTO event_sequence"
            " (event_id, event_type, store_name, subject_id, event_at)"
            " VALUES ('v15-central-marker', 'attempt', 'receipts', 'v15',"
            " '2026-08-10T12:00:00-04:00')"
        )
        if schema_object_sql is not None:
            conn.execute(schema_object_sql)
        conn.commit()
        before = _v15_application_rows(conn)

    reopened = _driver(tmp_path)
    if governed:
        reopened.initialize_database("semantics")
    else:
        with pytest.raises(driver.error_type) as caught:
            reopened.initialize_database("semantics")
        assert _error_code(caught.value) == "store_schema_unmigratable:semantics"

    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        assert _v15_application_rows(conn) == before


# ---------------------------------------------------------------------------
# V16 — accepted ba890ec findings: exact autoindexes + marker-table grammar
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("surplus_autoindex_table", "governed"),
    (
        pytest.param(None, True, id="canonical-index-signatures"),
        pytest.param(
            "semantic_assertions",
            False,
            id="assertion-claim-surplus-autoindex",
        ),
        pytest.param(
            "semantic_attachments",
            False,
            id="attachment-provenance-surplus-autoindex",
        ),
        pytest.param(
            "semantic_evidence_objects",
            False,
            id="evidence-object-blob-surplus-autoindex",
        ),
        pytest.param(
            "semantic_adjudications",
            False,
            id="adjudication-authority-surplus-autoindex",
        ),
    ),
)
def test_v16_h1_autoindex_signatures_are_exact_for_every_governed_table(
    tmp_path: Path, surplus_autoindex_table: str | None, governed: bool
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(
        _semantic_record(assertion_id="v16-index-marker")
    )
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        if surplus_autoindex_table == "semantic_assertions":
            conn.execute(
                "ALTER TABLE semantic_assertions"
                " RENAME TO semantic_assertions_governed"
            )
            conn.execute(
                "CREATE TABLE semantic_assertions ("
                "assertion_id TEXT PRIMARY KEY, key TEXT, version INTEGER,"
                " claim TEXT, active INTEGER, evidence_id TEXT, UNIQUE(claim))"
            )
            conn.execute(
                "INSERT INTO semantic_assertions"
                " SELECT * FROM semantic_assertions_governed"
            )
            conn.execute("DROP TABLE semantic_assertions_governed")
        elif surplus_autoindex_table == "semantic_attachments":
            conn.execute(
                "ALTER TABLE semantic_attachments"
                " RENAME TO semantic_attachments_governed"
            )
            conn.execute(
                "CREATE TABLE semantic_attachments ("
                "evidence_id TEXT PRIMARY KEY, retrieved_at TEXT, provenance TEXT,"
                " retention TEXT, evidence_sha256 TEXT, evidence_bytes INTEGER,"
                " UNIQUE(provenance))"
            )
            conn.execute(
                "INSERT INTO semantic_attachments"
                " SELECT * FROM semantic_attachments_governed"
            )
            conn.execute("DROP TABLE semantic_attachments_governed")
        elif surplus_autoindex_table == "semantic_evidence_objects":
            conn.execute(
                "ALTER TABLE semantic_evidence_objects"
                " RENAME TO semantic_evidence_objects_governed"
            )
            conn.execute(
                "CREATE TABLE semantic_evidence_objects ("
                "evidence_sha256 TEXT PRIMARY KEY, evidence_blob BLOB,"
                " UNIQUE(evidence_blob))"
            )
            conn.execute(
                "INSERT INTO semantic_evidence_objects"
                " SELECT * FROM semantic_evidence_objects_governed"
            )
            conn.execute("DROP TABLE semantic_evidence_objects_governed")
        elif surplus_autoindex_table == "semantic_adjudications":
            conn.execute(
                "ALTER TABLE semantic_adjudications"
                " RENAME TO semantic_adjudications_governed"
            )
            conn.execute(
                "CREATE TABLE semantic_adjudications ("
                "adjudication_id TEXT PRIMARY KEY, key TEXT, authority TEXT,"
                " provenance TEXT, parents TEXT, effective_assertion_id TEXT,"
                " UNIQUE(authority))"
            )
            conn.execute(
                "INSERT INTO semantic_adjudications"
                " SELECT * FROM semantic_adjudications_governed"
            )
            conn.execute("DROP TABLE semantic_adjudications_governed")
        conn.commit()
        before_rows = _v15_application_rows(conn)
    before_bytes = _v5_main_wal_fingerprint(semantics)

    reopened = _driver(tmp_path)
    if governed:
        reopened.initialize_database("semantics")
    else:
        with pytest.raises(driver.error_type) as caught:
            reopened.initialize_database("semantics")
        assert _error_code(caught.value) == "store_schema_unmigratable:semantics"
        assert _v5_main_wal_fingerprint(semantics) == before_bytes

    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        assert _v15_application_rows(conn) == before_rows


@pytest.mark.parametrize(
    ("table_body", "insert_columns", "insert_values", "governed"),
    (
        pytest.param(
            "row_id TEXT PRIMARY KEY, offering_id TEXT UNIQUE, kind TEXT",
            "row_id, offering_id, kind",
            ("bootstrap-marker", "_bootstrap", "marker"),
            True,
            id="canonical-marker-table",
        ),
        pytest.param(
            "row_id TEXT PRIMARY KEY, offering_id TEXT UNIQUE",
            "row_id, offering_id",
            ("bootstrap-marker", "_bootstrap"),
            False,
            id="missing-kind-column",
        ),
        pytest.param(
            "row_id TEXT PRIMARY KEY, offering_id TEXT UNIQUE,"
            " kind TEXT, extra TEXT",
            "row_id, offering_id, kind, extra",
            ("bootstrap-marker", "_bootstrap", "marker", "surplus"),
            False,
            id="extra-column",
        ),
        pytest.param(
            "offering_id TEXT UNIQUE, row_id TEXT PRIMARY KEY, kind TEXT",
            "row_id, offering_id, kind",
            ("bootstrap-marker", "_bootstrap", "marker"),
            False,
            id="wrong-column-order",
        ),
        pytest.param(
            "row_id TEXT, offering_id TEXT UNIQUE, kind TEXT",
            "row_id, offering_id, kind",
            ("bootstrap-marker", "_bootstrap", "marker"),
            False,
            id="missing-row-id-primary-key",
        ),
        pytest.param(
            "row_id TEXT PRIMARY KEY, offering_id TEXT, kind TEXT",
            "row_id, offering_id, kind",
            ("bootstrap-marker", "_bootstrap", "marker"),
            False,
            id="missing-offering-id-unique",
        ),
        pytest.param(
            "row_id TEXT PRIMARY KEY, offering_id TEXT UNIQUE,"
            " kind TEXT, UNIQUE(kind)",
            "row_id, offering_id, kind",
            ("bootstrap-marker", "_bootstrap", "marker"),
            False,
            id="surplus-kind-autoindex",
        ),
        pytest.param(
            "row_id TEXT PRIMARY KEY, offering_id TEXT UNIQUE, kind TEXT NOT NULL",
            "row_id, offering_id, kind",
            ("bootstrap-marker", "_bootstrap", "marker"),
            False,
            id="kind-definition-suffix",
        ),
    ),
)
def test_v16_h2_marker_acquisitions_table_requires_exact_closed_grammar(
    tmp_path: Path,
    table_body: str,
    insert_columns: str,
    insert_values: tuple[str, ...],
    governed: bool,
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(
        _semantic_record(assertion_id="v16-marker-application-row")
    )
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute("ALTER TABLE acquisitions RENAME TO acquisitions_governed")
        conn.execute("CREATE TABLE acquisitions (" + table_body + ")")
        placeholders = ",".join("?" for _ in insert_values)
        conn.execute(
            f"INSERT INTO acquisitions ({insert_columns}) VALUES ({placeholders})",
            insert_values,
        )
        conn.execute("DROP TABLE acquisitions_governed")
        conn.commit()
        before_rows = _v15_application_rows(conn)
    before_bytes = _v5_main_wal_fingerprint(semantics)

    reopened = _driver(tmp_path)
    if governed:
        reopened.initialize_database("semantics")
    else:
        with pytest.raises(driver.error_type) as caught:
            reopened.initialize_database("semantics")
        assert _error_code(caught.value) == "store_schema_unmigratable:semantics"
        assert _v5_main_wal_fingerprint(semantics) == before_bytes

    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        assert _v15_application_rows(conn) == before_rows


# ---------------------------------------------------------------------------
# V17 — accepted 1e5492b findings: complete grammar + exact physical indexes
# ---------------------------------------------------------------------------


_V17_CANONICAL_SEMANTIC_BODIES = {
    "semantic_assertions": (
        "assertion_id TEXT PRIMARY KEY, key TEXT, version INTEGER,"
        " claim TEXT, active INTEGER, evidence_id TEXT"
    ),
    "semantic_attachments": (
        "evidence_id TEXT PRIMARY KEY, retrieved_at TEXT, provenance TEXT,"
        " retention TEXT, evidence_sha256 TEXT, evidence_bytes INTEGER"
    ),
    "semantic_evidence_objects": (
        "evidence_sha256 TEXT PRIMARY KEY, evidence_blob BLOB"
    ),
    "semantic_adjudications": (
        "adjudication_id TEXT PRIMARY KEY, key TEXT, authority TEXT,"
        " provenance TEXT, parents TEXT, effective_assertion_id TEXT"
    ),
}

_V17_CONSTRAINED_SEMANTIC_BODIES = {
    "semantic_assertions": (
        "assertion_id TEXT PRIMARY KEY, key TEXT,"
        " version INTEGER CHECK(version > 100), claim TEXT,"
        " active INTEGER, evidence_id TEXT"
    ),
    "semantic_attachments": (
        "evidence_id TEXT PRIMARY KEY, retrieved_at TEXT, provenance TEXT,"
        " retention TEXT, evidence_sha256 TEXT,"
        " evidence_bytes INTEGER CHECK(evidence_bytes < 0)"
    ),
    "semantic_evidence_objects": (
        "evidence_sha256 TEXT PRIMARY KEY,"
        " evidence_blob BLOB CHECK(length(evidence_blob) < 0)"
    ),
    "semantic_adjudications": (
        "adjudication_id TEXT PRIMARY KEY, key TEXT,"
        " authority TEXT CHECK(authority = 'nobody'), provenance TEXT,"
        " parents TEXT, effective_assertion_id TEXT"
    ),
}


def _v17_rebuild_empty_semantic_table(
    path: Path, table: str, body: str
) -> None:
    with contextlib.closing(sqlite3.connect(path)) as conn:
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
        conn.execute(f"ALTER TABLE {table} RENAME TO {table}_governed")
        conn.execute(f"CREATE TABLE {table} ({body})")
        conn.execute(f"DROP TABLE {table}_governed")
        conn.commit()


def _v17_exercise_semantic_writer(driver: Any, table: str) -> Any:
    if table != "semantic_adjudications":
        return driver.write_semantic_assertion(
            _semantic_record(assertion_id=f"v17-{table}")
        )
    return driver.write_semantic_adjudication(
        {
            "adjudication_id": "v17-adjudication",
            "key": SEMANTIC_KEY,
            "authority": "david",
            "provenance": "explicit-ruling",
            "parents": ["v17-old", "v17-new"],
            "effective_assertion_id": "v17-new",
        }
    )


@pytest.mark.parametrize(
    ("table", "constrained"),
    tuple(
        pytest.param(table, constrained, id=f"{table}-{'check' if constrained else 'canonical'}")
        for table in _V17_CANONICAL_SEMANTIC_BODIES
        for constrained in (False, True)
    ),
)
def test_v17_h1_every_semantic_table_has_closed_operational_grammar(
    tmp_path: Path, table: str, constrained: bool
) -> None:
    setup = _driver(tmp_path)
    if table == "semantic_adjudications":
        setup.write_semantic_assertion(
            _semantic_record(assertion_id="v17-old", version=1)
        )
        setup.write_semantic_assertion(
            _semantic_record(
                assertion_id="v17-new",
                claim="dynasty_startup",
                version=2,
            )
        )
    else:
        setup.initialize_database("semantics")
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    body = (
        _V17_CONSTRAINED_SEMANTIC_BODIES[table]
        if constrained
        else _V17_CANONICAL_SEMANTIC_BODIES[table]
    )
    _v17_rebuild_empty_semantic_table(semantics, table, body)
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        before_rows = _v15_application_rows(conn)
    before_bytes = _v5_main_wal_fingerprint(semantics)

    reopened = _driver(tmp_path)
    if not constrained:
        result = _v17_exercise_semantic_writer(reopened, table)
        assert _value(result, "status") == "written"
        return

    # One operational CHECK per writer branch proves the grammar is
    # load-bearing. In particular, the evidence-object case must not return
    # `written` after INSERT OR IGNORE silently omits the required bytes.
    try:
        result = _v17_exercise_semantic_writer(reopened, table)
    except reopened.error_type as caught:
        assert _error_code(caught) == "store_schema_unmigratable:semantics"
    else:
        if table == "semantic_evidence_objects":
            assert _value(result, "status") != "written", (
                "evidence bytes rejected by SQLite must never be reported written"
            )
        pytest.fail("closed semantic grammar must refuse before its writer branch")
    assert _v5_main_wal_fingerprint(semantics) == before_bytes
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        assert _v15_application_rows(conn) == before_rows


@pytest.mark.parametrize(
    ("case", "table", "statements", "governed"),
    (
        pytest.param(
            "assertion-pk-canonical",
            "semantic_assertions",
            ("CREATE TABLE semantic_assertions (assertion_id TEXT PRIMARY KEY, key TEXT)",),
            True,
            id="assertion-pk-canonical",
        ),
        pytest.param(
            "assertion-unique-substitute",
            "semantic_assertions",
            ("CREATE TABLE semantic_assertions (assertion_id TEXT UNIQUE, key TEXT)",),
            False,
            id="assertion-pk-replaced-by-unique",
        ),
        pytest.param(
            "assertion-nocase",
            "semantic_assertions",
            (
                "CREATE TABLE semantic_assertions ("
                "assertion_id TEXT PRIMARY KEY COLLATE NOCASE, key TEXT)",
            ),
            False,
            id="assertion-primary-key-nocase",
        ),
        pytest.param(
            "assertion-descending",
            "semantic_assertions",
            ("CREATE TABLE semantic_assertions (assertion_id TEXT PRIMARY KEY DESC, key TEXT)",),
            False,
            id="assertion-primary-key-descending",
        ),
        pytest.param(
            "assertion-partial",
            "semantic_assertions",
            (
                "CREATE TABLE semantic_assertions (assertion_id TEXT, key TEXT)",
                "CREATE UNIQUE INDEX assertion_partial"
                " ON semantic_assertions(assertion_id) WHERE key IS NOT NULL",
            ),
            False,
            id="assertion-partial-index",
        ),
        pytest.param(
            "assertion-expression",
            "semantic_assertions",
            (
                "CREATE TABLE semantic_assertions (assertion_id TEXT, key TEXT)",
                "CREATE UNIQUE INDEX assertion_expression"
                " ON semantic_assertions(lower(assertion_id))",
            ),
            False,
            id="assertion-expression-index",
        ),
        pytest.param(
            "assertion-wrong-column",
            "semantic_assertions",
            (
                "CREATE TABLE semantic_assertions (assertion_id TEXT, key TEXT)",
                "CREATE UNIQUE INDEX assertion_wrong ON semantic_assertions(key)",
            ),
            False,
            id="assertion-wrong-key-column",
        ),
        pytest.param(
            "assertion-composite",
            "semantic_assertions",
            (
                "CREATE TABLE semantic_assertions (assertion_id TEXT, key TEXT)",
                "CREATE UNIQUE INDEX assertion_composite"
                " ON semantic_assertions(assertion_id, key)",
            ),
            False,
            id="assertion-composite-column-sequence",
        ),
        pytest.param(
            "event-unique-canonical",
            "event_sequence",
            ("CREATE TABLE event_sequence (event_id TEXT UNIQUE, seq INTEGER)",),
            True,
            id="event-id-unique-canonical",
        ),
        pytest.param(
            "event-pk-substitute",
            "event_sequence",
            ("CREATE TABLE event_sequence (event_id TEXT PRIMARY KEY, seq INTEGER)",),
            False,
            id="event-unique-replaced-by-primary-key",
        ),
        pytest.param(
            "acquisitions-canonical",
            "acquisitions",
            (
                "CREATE TABLE acquisitions ("
                "row_id TEXT PRIMARY KEY, offering_id TEXT UNIQUE, kind TEXT)",
            ),
            True,
            id="acquisitions-origin-map-canonical",
        ),
        pytest.param(
            "acquisitions-swapped-origins",
            "acquisitions",
            (
                "CREATE TABLE acquisitions ("
                "row_id TEXT UNIQUE, offering_id TEXT PRIMARY KEY, kind TEXT)",
            ),
            False,
            id="acquisitions-pk-and-unique-origins-swapped",
        ),
    ),
)
def test_v17_h2_index_signatures_bind_physical_index_metadata(
    tmp_path: Path,
    case: str,
    table: str,
    statements: tuple[str, ...],
    governed: bool,
) -> None:
    driver = _driver(tmp_path)
    predicate = getattr(driver, "_index_signatures_governed", None)
    assert callable(predicate), "exact physical signature predicate required"
    with contextlib.closing(sqlite3.connect(":memory:")) as conn:
        for statement in statements:
            conn.execute(statement)
        indexes = list(conn.execute(f"PRAGMA index_list({table})"))
        assert indexes, "fixture must create a real SQLite index"
        expanded = {
            row[1]: list(conn.execute(f"PRAGMA index_xinfo({row[1]})"))
            for row in indexes
        }

        if case == "assertion-unique-substitute":
            assert {row[3] for row in indexes} == {"u"}
        elif case == "assertion-nocase":
            assert any(
                column[4].upper() == "NOCASE" and column[5] == 1
                for columns in expanded.values()
                for column in columns
            )
        elif case == "assertion-descending":
            assert any(
                column[3] == 1 and column[5] == 1
                for columns in expanded.values()
                for column in columns
            )
        elif case == "assertion-partial":
            assert any(row[4] == 1 for row in indexes)
        elif case == "assertion-expression":
            assert any(
                column[2] is None and column[5] == 1
                for columns in expanded.values()
                for column in columns
            )
        elif case == "assertion-wrong-column":
            assert any(
                column[2] == "key" and column[5] == 1
                for columns in expanded.values()
                for column in columns
            )
        elif case == "assertion-composite":
            assert any(
                [column[2] for column in columns if column[5] == 1]
                == ["assertion_id", "key"]
                for columns in expanded.values()
            )
        elif case == "event-pk-substitute":
            assert {row[3] for row in indexes} == {"pk"}
        elif case == "acquisitions-swapped-origins":
            origins = {
                column[2]: row[3]
                for row in indexes
                for column in expanded[row[1]]
                if column[5] == 1
            }
            assert origins == {"row_id": "u", "offering_id": "pk"}

        assert predicate(conn, table) is governed


_V17_CANONICAL_MARKER_BODY = (
    "row_id TEXT PRIMARY KEY, offering_id TEXT UNIQUE, kind TEXT"
)
_V17_LEGACY_MARKER_BODY = (
    _V17_CANONICAL_MARKER_BODY
    + ", retrieved_at TEXT, readiness TEXT, retention TEXT,"
    " content_vintage_id TEXT, archive_sha256 TEXT, archive_bytes INTEGER,"
    " analysis_ready INTEGER, signature BLOB"
)


@pytest.mark.parametrize(
    ("table_body", "suffix", "governed"),
    (
        pytest.param(
            _V17_CANONICAL_MARKER_BODY,
            " /* trailing comment is not a table option */",
            True,
            id="canonical-comment-only-suffix",
        ),
        pytest.param(
            _V17_LEGACY_MARKER_BODY,
            " -- trailing comment only\n",
            True,
            id="legacy-comment-only-suffix",
        ),
        pytest.param(
            _V17_CANONICAL_MARKER_BODY,
            " STRICT",
            False,
            id="canonical-strict-option",
        ),
        pytest.param(
            _V17_CANONICAL_MARKER_BODY,
            " WITHOUT ROWID",
            False,
            id="canonical-without-rowid-option",
        ),
        pytest.param(
            _V17_LEGACY_MARKER_BODY,
            " STRICT",
            False,
            id="legacy-strict-option",
        ),
        pytest.param(
            _V17_LEGACY_MARKER_BODY,
            " WITHOUT ROWID",
            False,
            id="legacy-without-rowid-option",
        ),
    ),
)
def test_v17_m3_marker_grammar_consumes_the_complete_table_ddl(
    tmp_path: Path, table_body: str, suffix: str, governed: bool
) -> None:
    driver = _driver(tmp_path)
    driver.write_semantic_assertion(
        _semantic_record(assertion_id="v17-marker-row")
    )
    semantics = tmp_path / RUNTIME_PATHS["semantics"]
    with contextlib.closing(sqlite3.connect(semantics)) as conn:
        conn.execute("ALTER TABLE acquisitions RENAME TO acquisitions_governed")
        conn.execute(f"CREATE TABLE acquisitions ({table_body}){suffix}")
        conn.execute(
            "INSERT INTO acquisitions(row_id, offering_id, kind)"
            " VALUES ('v17-marker', 'v17-offering', 'marker')"
        )
        conn.execute("DROP TABLE acquisitions_governed")
        conn.commit()
        before_rows = {
            table: (
                [
                    tuple(row)
                    for row in conn.execute(
                        "SELECT * FROM acquisitions ORDER BY row_id"
                    )
                ]
                if table == "acquisitions"
                else [
                    tuple(row)
                    for row in conn.execute(
                        f"SELECT * FROM {table} ORDER BY rowid"
                    )
                ]
            )
            for table in _V15_APPLICATION_TABLES
        }
    before_bytes = _v5_main_wal_fingerprint(semantics)

    reopened = _driver(tmp_path)
    if governed:
        reopened.initialize_database("semantics")
        with contextlib.closing(sqlite3.connect(semantics)) as conn:
            retained = conn.execute(
                "SELECT row_id, offering_id, kind FROM acquisitions"
                " WHERE row_id='v17-marker'"
            ).fetchone()
        assert retained == ("v17-marker", "v17-offering", "marker")
    else:
        with pytest.raises(driver.error_type) as caught:
            reopened.initialize_database("semantics")
        assert _error_code(caught.value) == "store_schema_unmigratable:semantics"
        assert _v5_main_wal_fingerprint(semantics) == before_bytes
        with contextlib.closing(sqlite3.connect(semantics)) as conn:
            after_rows = {
                table: (
                    [
                        tuple(row)
                        for row in conn.execute(
                            "SELECT * FROM acquisitions ORDER BY row_id"
                        )
                    ]
                    if table == "acquisitions"
                    else [
                        tuple(row)
                        for row in conn.execute(
                            f"SELECT * FROM {table} ORDER BY rowid"
                        )
                    ]
                )
                for table in _V15_APPLICATION_TABLES
            }
        assert after_rows == before_rows
