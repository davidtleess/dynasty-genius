"""RED — Layer 1 PFF intake/indexer: payload-grain intake, backfill, dual-axis marker.

Scope ruled by Codex across w#cqzx5ug0-1 / w#cgos97fu-1 / w#7ejx3etr-1 / w#caznobyv-1, after my
first two proposals were reversed. The corrections that shaped this file, recorded so the reasoning
is not lost:

  * Layer 1's job is to LOSE NOTHING. Scope-basis selection, duplicate-winner selection, and
    filtering to `accepted` are all SELECTION decisions and belong to a later layer. I proposed all
    three; each would have silently discarded real data. Measured on the private tree: choosing
    REGPO as a single basis drops 1 player present only in REG (ncaa/receiving_summary/2017), and
    the "semantically identical" duplicate payloads actually differ on 1-2 rows.
  * Two identities are REQUIRED by the data, not chosen: 307 offerings map to 149 distinct payload
    SHAs. Payload identity is the SHA-256; offering identity is the sidecar record.
  * A four-file "atomic update" is a faux transaction. One SQLite metadata ledger transaction is the
    commit point.
  * CI fixtures here are SYNTHETIC and carry no paid headers or rows. The real 149 are validated
    only by a private, untracked acceptance run. "All 149" can never be a CI test, because a clean
    runner has no subscriber data — that is verbatim the defect shipped in c55e645 and repaired in
    27adf0c, and it is not to be repeated here.

DELIBERATELY OUT OF SCOPE: any GREEN, the private backfill run, any daily_control edit, any provider
contact or paid path, any normalized/player-row query store, any consumer rewiring, any edit to the
active Phase 13/16 manifests, and any promotion of PFF grades to a model or query surface.

The module under test does not exist yet. Every test that exercises it FAILS (it does not skip —
`pytest.importorskip` would let a GREEN pass with no implementation, a mistake already made once in
this program).
"""
from __future__ import annotations

import csv
import hashlib
import importlib
import json
import re
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

MODULE = "src.dynasty_genius.sources.pff_intake"

#: Transport vocabulary is pinned LITERALLY here, by Codex's ruling. It is deliberately NOT derived
#: from `daily_control.SUCCESS_STATUSES`: deriving it would make producer and consumer move together,
#: so removing `ok` from that set would silently adapt this contract instead of failing it.
MARKER_STATUS_OK = "ok"
MARKER_STATUS_FAILED = "failed"

#: Evidence-quality vocabulary — orthogonal to transport.
REVIEW_CLEAR = "clear"
REVIEW_REQUIRED = "review_required"

#: The six status labels already present in the governed inventory. They are EVIDENCE labels, and an
#: implementation that filters to `accepted` destroys retained evidence.
LEGACY_STATUSES = (
    "accepted",
    "accepted_extra_history",
    "accepted_with_export_drift",
    "partial_vendor_coverage",
    "scope_mismatch_retained",
    "superseded_basis_retained",
)

#: New offerings default here. Schema recognition alone must never manufacture `accepted`.
DEFAULT_NEW_STATUS = "pending_review"

#: F2 — the EXISTING canonical convention, read off the governed download map:
#:   raw/{league}/{report}/{scope}/{season}/{retrieved-date}_{sha12}.csv
#: Pinned so a new importer cannot quietly create a second, incompatible private tree while still
#: satisfying a loose "somewhere under store_root" assertion.
CANONICAL_RE = re.compile(
    r"^raw/(?P<league>[a-z0-9]+)/(?P<report>[a-z0-9_]+)/(?P<scope>[A-Z]+)/(?P<season>\d{4})/"
    r"(?P<date>\d{4}-\d{2}-\d{2})_(?P<sha12>[0-9a-f]{12})\.csv$"
)
#: Unknown schemas land in a quarantine namespace under the SAME immutable SHA identity.
QUARANTINE_RE = re.compile(
    r"^quarantine/(?P<league>[a-z0-9]+)/(?P<report>[a-z0-9_]+)/(?P<scope>[A-Z]+)/(?P<season>\d{4})/"
    r"(?P<date>\d{4}-\d{2}-\d{2})_(?P<sha12>[0-9a-f]{12})\.csv$"
)

#: Ontology guard: the only statuses that may ever enter the canonical ledger.
ALLOWED_STATUSES = frozenset(LEGACY_STATUSES) | {DEFAULT_NEW_STATUS, "review_required"}


def _mod():
    """Import the module under test, failing loudly when it is absent.

    Deliberately not `pytest.importorskip`: a skip is not a RED, and a suite of skips would let a
    GREEN land with nothing implemented.
    """
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:  # pragma: no cover - this IS the red state
        pytest.fail(f"{MODULE} does not exist yet (RED): {exc}")


# ----------------------------------------------------------------------------------
# Synthetic fixtures. NO paid content: invented column names, invented ids, 2 data rows.
# ----------------------------------------------------------------------------------

SYNTH_HEADER = ["player_id", "player", "team", "synthetic_metric_a", "synthetic_metric_b"]


def _write_csv(path: Path, rows: list[list[str]], header: list[str] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header or SYNTH_HEADER)
        w.writerows(rows)
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


#: The digest of THIS header under the governed algorithm. Pinned as a literal so the test helper
#: and any future producer cannot drift together into agreeing on a wrong algorithm.
EXPECTED_SYNTH_SCHEMA_SHA = "7ab5f9967d081c61c831602bea520d840fa73fb6c7ae0568f09f4f511c786f4f"


def _schema_hash(header: list[str]) -> str:
    """SHA-256 of the NEWLINE-joined header — the governed PFF algorithm.

    An earlier draft used `"\x1f".join(...)`, which is wrong and would have been catastrophic in a
    quiet way: the synthetic catalog would recognise synthetic fixtures while every one of the 12
    REAL governed schemas hashed to something else and quarantined. Verified against the shipped
    artifacts — newline-join reproduces the recorded `schema_sha256` exactly:
        scripts/build_provider_contract_bundle.py:257  sha256("\n".join(columns))
        src/dynasty_genius/adapters/pff_te_export.py:165  sha256("\n".join(headers))
    """
    return hashlib.sha256("\n".join(header).encode("utf-8")).hexdigest()


def _offering(
    source: Path,
    *,
    league: str = "ncaa",
    report: str = "receiving_summary",
    scope: str = "REG",
    season: str = "2019",
    retrieved_at: str = "2026-08-08T01:00:00-04:00",
    status: str | None = None,
    offering_id: str | None = None,
) -> dict:
    rec = {
        "offering_id": offering_id or f"off-{source.stem}",
        "source_path": str(source),
        "league": league,
        "report": report,
        "scope": scope,
        "season": season,
        "retrieved_at": retrieved_at,
    }
    if status is not None:
        rec["status"] = status
    return rec


def _sidecar(path: Path, offerings: list[dict], batch_id: str = "batch-001") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"batch_id": batch_id, "offerings": offerings}, indent=2))
    return path


#: F4 — the ledger's table names are part of the contract, because the failure seam and the
#: rollback assertions address them directly.
PAYLOAD_TABLE = "payload"
OFFERING_TABLE = "offering"


def _seed_ledger(m, env) -> None:
    """Run one REAL successful intake so the implementation creates its own full schema."""
    src = _write_csv(env["staging"] / "_seed.csv", [["seed", "S", "SSS", "0", "0"]])
    seeded = _run(
        m, env,
        _sidecar(env["root"] / "_seed.json",
                 [_offering(src, offering_id="seed", season="1999")], batch_id="seed-batch"),
    )
    assert seeded.status == MARKER_STATUS_OK, "fixture precondition: the seed batch must succeed"


def _install_offering_abort(env, offering_id: str) -> None:
    """Abort the transaction ON A LATER OFFERING, proving genuine rollback.

    F4: a read-only ledger (my previous seam) fails on the FIRST write after the copy, so "zero
    committed rows" is equally consistent with no partial transaction ever having existed — it
    cannot distinguish a real rollback from a write that never started. It is also a filesystem
    permission proxy, not a statement about the DB transaction the design promises.

    A trigger that raises ABORT on a later offering forces earlier payload/offering writes to be
    ATTEMPTED first and then undone. Verified directly: earlier inserts do not survive the abort.
    """
    con = sqlite3.connect(env["ledger"])
    con.execute(
        f"create trigger if not exists _abort_offering before insert on {OFFERING_TABLE} "
        f"when new.offering_id = '{offering_id}' "
        f"begin select raise(ABORT, 'induced offering failure'); end"
    )
    con.commit()
    con.close()


def _drop_offering_abort(env) -> None:
    con = sqlite3.connect(env["ledger"])
    con.execute("drop trigger if exists _abort_offering")
    con.commit()
    con.close()


def _table_counts(env) -> tuple[int, int]:
    con = sqlite3.connect(env["ledger"])
    try:
        return (
            con.execute(f"select count(*) from {PAYLOAD_TABLE}").fetchone()[0],
            con.execute(f"select count(*) from {OFFERING_TABLE}").fetchone()[0],
        )
    finally:
        con.close()


@pytest.fixture
def env(tmp_path):
    """A complete synthetic intake environment: staging, canonical root, ledger, marker."""
    staging = tmp_path / "staging"
    staging.mkdir()
    return {
        "staging": staging,
        "store_root": tmp_path / "canonical",
        "ledger": tmp_path / "ledger" / "pff_metadata.db",
        # R1: TWO markers. One `status_latest` is insufficient — a later failed batch would
        # overwrite it and daily_control would forget the prior good vintage. The ready marker is
        # the LAST-GOOD clock and advances only on status=ok. This mirrors the nflverse
        # `*.ready.json` pattern already shipped in this program.
        "marker": tmp_path / "ops" / "pff_intake_status_latest.json",
        "ready": tmp_path / "ops" / "pff_intake.ready.json",
        "quarantine": tmp_path / "canonical" / "quarantine",
        "catalog": tmp_path / "catalog" / "known_schemas.json",
        "known_schemas": {_schema_hash(SYNTH_HEADER)},
        "root": tmp_path,
    }


def _run(m, env, sidecar: Path, **kw):
    return m.intake(
        batch_manifest=sidecar,
        store_root=env["store_root"],
        ledger_path=env["ledger"],
        marker_path=env["marker"],
        ready_marker_path=env["ready"],
        repo_root=env["root"],
        known_schemas=kw.pop("known_schemas", env["known_schemas"]),
        **kw,
    )


def test_a0_schema_hash_helper_matches_the_governed_algorithm():
    """F1 — the test helper must hash headers the way the GOVERNED code does.

    A `\x1f` join (my first draft) recognises synthetic fixtures while every real governed schema
    hashes elsewhere and quarantines — a silent, total failure. Two independent anchors so the
    helper and a future producer cannot drift together:
      1. a pinned literal digest for the synthetic header;
      2. agreement with the shipped `pff_te_export._header_hash`, which is the governed producer.
    """
    assert _schema_hash(SYNTH_HEADER) == EXPECTED_SYNTH_SCHEMA_SHA, (
        "the synthetic header's digest changed; if the algorithm moved, the governed catalog moved too"
    )
    governed = importlib.import_module("src.dynasty_genius.adapters.pff_te_export")
    assert _schema_hash(SYNTH_HEADER).startswith(governed._header_hash(SYNTH_HEADER)), (
        "the helper must agree with the governed producer's header hash"
    )


# ================== A1 — provenance is DECLARED, never inferred =====================


def test_a1_offering_without_declared_provenance_is_refused(env):
    """Provenance must come from the sidecar. Inference is what produced every wrong claim I made
    about this data, so the implementation is forbidden from guessing it."""
    m = _mod()
    src = _write_csv(env["staging"] / "some_export.csv", [["p1", "A", "AAA", "1", "2"]])
    bad = dict(_offering(src))
    del bad["scope"]
    sidecar = _sidecar(env["root"] / "batch.json", [bad])
    with pytest.raises(m.PFFIntakeError) as exc:
        _run(m, env, sidecar)
    assert "scope" in str(exc.value), f"the missing provenance field must be named; got {exc.value}"


def test_a1b_a_parseable_filename_does_not_substitute_for_missing_provenance(env):
    """A filename that LOOKS like provenance is not provenance.

    R5: an earlier draft invented an `extra_paths` scan parameter purely to express this, which
    would have forced a directory-scanning API the design does not want. A record whose SOURCE
    FILENAME encodes every field, while the sidecar omits them, proves the same thing without
    inventing API: the implementation must refuse rather than parse the name.
    """
    m = _mod()
    src = _write_csv(
        env["staging"] / "ncaa_receiving_summary_REG_2017.csv", [["p1", "A", "AAA", "1", "2"]]
    )
    rec = {"offering_id": "off-1", "source_path": str(src)}  # every provenance field absent
    sidecar = _sidecar(env["root"] / "batch.json", [rec])
    with pytest.raises(m.PFFIntakeError) as exc:
        _run(m, env, sidecar)
    msg = str(exc.value)
    assert any(f in msg for f in ("league", "report", "scope", "season")), (
        f"the missing provenance fields must be named, not parsed from the filename; got {msg}"
    )


# ============ A2/A3 — offering identity vs payload identity (307 -> 149) ============


def test_a2_replaying_the_same_offering_is_a_complete_no_op(env):
    """Replay must add zero payloads AND zero provenance rows. Recording provenance on every replay
    would append the same mapping forever."""
    m = _mod()
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    sidecar = _sidecar(env["root"] / "batch.json", [_offering(src, offering_id="off-A")])
    first = _run(m, env, sidecar)
    assert first.payloads_indexed == 1
    assert first.provenance_added == 1
    second = _run(m, env, sidecar)
    assert second.payloads_indexed == 0, "replay must add no payload"
    assert second.provenance_added == 0, (
        f"replay must add no provenance mapping; added {second.provenance_added}"
    )
    assert second.status == MARKER_STATUS_OK, "an idempotent replay is a success, not a failure"


def test_a3_new_offering_of_already_held_bytes_adds_provenance_only(env):
    """The 307->149 shape: distinct offerings of identical bytes. Exactly one provenance mapping,
    zero new payloads."""
    m = _mod()
    a = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    b = _write_csv(env["staging"] / "b.csv", [["p1", "A", "AAA", "1", "2"]])  # identical bytes
    assert _sha256(a) == _sha256(b), "fixture precondition: identical payload bytes"
    _run(m, env, _sidecar(env["root"] / "b1.json", [_offering(a, offering_id="off-A")]))
    second = _run(
        m,
        env,
        _sidecar(env["root"] / "b2.json", [_offering(b, offering_id="off-B")], batch_id="batch-002"),
    )
    assert second.payloads_indexed == 0, "identical bytes are one payload"
    assert second.provenance_added == 1, (
        f"a genuinely new offering must add exactly one mapping; added {second.provenance_added}"
    )


def test_a2b_reusing_an_offering_identity_with_different_bytes_is_a_hard_conflict(env):
    """R2 — offering identity is (batch_id, offering_id). Exact replay is a no-op; reusing that
    identity for DIFFERENT bytes must be a hard conflict, never a silent remap."""
    m = _mod()
    a = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    b = _write_csv(env["staging"] / "b.csv", [["p1", "A", "AAA", "1", "9"]])
    _run(m, env, _sidecar(env["root"] / "b1.json",
                          [_offering(a, offering_id="dup")], batch_id="B1"))
    with pytest.raises(m.PFFIdentityConflict) as exc:
        _run(m, env, _sidecar(env["root"] / "b2.json",
                              [_offering(b, offering_id="dup")], batch_id="B1"))
    assert "dup" in str(exc.value), f"the conflicting offering identity must be named; got {exc.value}"


def test_a2c_reusing_an_offering_identity_with_changed_provenance_is_a_hard_conflict(env):
    """R2 — same bytes, same identity, but a different declared grain is still a conflict: it would
    silently relabel an already-indexed observation."""
    m = _mod()
    a = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    _run(m, env, _sidecar(env["root"] / "b1.json",
                          [_offering(a, offering_id="dup", season="2019")], batch_id="B1"))
    with pytest.raises(m.PFFIdentityConflict):
        _run(m, env, _sidecar(env["root"] / "b2.json",
                              [_offering(a, offering_id="dup", season="2020")], batch_id="B1"))


def test_a2d_reusing_a_batch_id_with_a_changed_manifest_is_a_hard_conflict(env):
    """R2 — a batch_id identifies a manifest. Reusing it with different contents must conflict."""
    m = _mod()
    a = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    b = _write_csv(env["staging"] / "b.csv", [["p2", "B", "BBB", "3", "4"]])
    _run(m, env, _sidecar(env["root"] / "b1.json", [_offering(a, offering_id="o1")], batch_id="B1"))
    with pytest.raises(m.PFFIdentityConflict):
        _run(m, env, _sidecar(env["root"] / "b2.json",
                              [_offering(a, offering_id="o1"), _offering(b, offering_id="o2")],
                              batch_id="B1"))


def test_a4_distinct_sha_at_the_same_grain_retains_BOTH(env):
    """The direct guard against the duplicate-winner selection I proposed. Measured on the real
    tree, such variants differ on 1-2 rows, so choosing one silently discards observations."""
    m = _mod()
    v1 = _write_csv(env["staging"] / "v1.csv", [["p1", "A", "AAA", "1", "2"]])
    v2 = _write_csv(env["staging"] / "v2.csv", [["p1", "A", "AAA", "1", "3"]])  # one row differs
    assert _sha256(v1) != _sha256(v2)
    grain = {"league": "ncaa", "report": "receiving_depth", "scope": "REGPO", "season": "2017"}
    sidecar = _sidecar(
        env["root"] / "batch.json",
        [
            _offering(v1, offering_id="off-1", **grain),
            _offering(v2, offering_id="off-2", **grain),
        ],
    )
    result = _run(m, env, sidecar)
    assert result.payloads_indexed == 2, (
        "both vintages at the same semantic grain must be retained; "
        f"indexed {result.payloads_indexed} (an implementation that picks a winner fails here)"
    )


# ==================== A5 — the original input is never touched =====================


def test_a5_original_staged_input_is_never_moved_deleted_or_modified(env):
    """Intake COPIES. The human's download is not ours to relocate."""
    m = _mod()
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    before_bytes, before_sha = src.read_bytes(), _sha256(src)
    _run(m, env, _sidecar(env["root"] / "batch.json", [_offering(src)]))
    assert src.exists(), "the original staged input must still exist"
    assert src.read_bytes() == before_bytes, "the original must be byte-identical"
    assert _sha256(src) == before_sha


# =============== A6/A7 — evidence states survive; none are manufactured ============


def test_a6_all_six_legacy_status_labels_survive_intake(env):
    """Statuses are evidence labels, not permission to discard. An implementation that filters to
    `accepted` fails here — that filter was my proposal, and it would have dropped 32 payloads."""
    m = _mod()
    offerings = []
    for i, status in enumerate(LEGACY_STATUSES):
        src = _write_csv(env["staging"] / f"s{i}.csv", [[f"p{i}", "A", "AAA", str(i), "2"]])
        offerings.append(_offering(src, offering_id=f"off-{i}", season=str(2017 + i), status=status))
    result = _run(m, env, _sidecar(env["root"] / "batch.json", offerings))
    assert result.payloads_indexed == len(LEGACY_STATUSES)
    observed = {r["status"] for r in m.list_payloads(ledger_path=env["ledger"])}
    assert set(LEGACY_STATUSES) <= observed, (
        f"every legacy status must survive; missing {set(LEGACY_STATUSES) - observed}"
    )


def test_a7_new_offering_defaults_to_pending_review_not_accepted(env):
    """Schema recognition alone must never manufacture `accepted`. A recognised schema means we can
    read the file, not that a human has blessed it."""
    m = _mod()
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    sidecar = _sidecar(env["root"] / "batch.json", [_offering(src)])  # no status declared
    _run(m, env, sidecar)
    rows = m.list_payloads(ledger_path=env["ledger"])
    assert len(rows) == 1
    assert rows[0]["status"] == DEFAULT_NEW_STATUS, (
        "an undeclared new offering with a KNOWN schema must default to pending_review, "
        f"never accepted; got {rows[0]['status']!r}"
    )


# ============= A8 — unknown schema quarantines the PAYLOAD, not the family =========


def test_a8_known_schemas_intake_and_an_unknown_schema_quarantines_only_that_payload(env):
    """All six known passing_pressure schemas intake because payload rows are NOT flattened; only a
    NEW schema quarantines, and it must not take the rest of the batch with it."""
    m = _mod()
    known_headers = [SYNTH_HEADER + [f"synthetic_extra_{i}" for i in range(n)] for n in range(6)]
    known = {_schema_hash(h) for h in known_headers}
    offerings = []
    for i, header in enumerate(known_headers):
        src = _write_csv(
            env["staging"] / f"k{i}.csv", [["p" + str(i)] + ["x"] * (len(header) - 1)], header=header
        )
        offerings.append(
            _offering(src, offering_id=f"off-k{i}", report="passing_pressure", season=str(2017 + i))
        )
    unknown_header = SYNTH_HEADER + ["synthetic_never_seen_before"]
    u = _write_csv(
        env["staging"] / "u.csv",
        [["pU"] + ["x"] * (len(unknown_header) - 1)],
        header=unknown_header,
    )
    offerings.append(
        _offering(u, offering_id="off-u", report="passing_pressure", season="2099")
    )
    result = _run(m, env, _sidecar(env["root"] / "batch.json", offerings), known_schemas=known)

    assert result.payloads_indexed == len(known_headers) + 1, (
        "the unknown payload must still be INDEXED (as review_required), never dropped"
    )
    quarantined = [r for r in m.list_payloads(ledger_path=env["ledger"]) if r["status"] == REVIEW_REQUIRED]
    assert len(quarantined) == 1, f"exactly one payload quarantines; got {len(quarantined)}"
    qpath = Path(quarantined[0]["canonical_path"])
    assert not qpath.is_absolute(), "canonical path must be repo-relative"
    qrel = (env["root"] / qpath).resolve().relative_to(env["store_root"].resolve()).as_posix()
    assert QUARANTINE_RE.match(qrel), (
        f"quarantine layout must mirror the canonical convention under quarantine/; got {qrel!r}"
    )
    assert QUARANTINE_RE.match(qrel).group("sha12") == quarantined[0]["sha256"][:12], (
        "a quarantined payload keeps the SAME immutable SHA identity"
    )
    others = [r for r in m.list_payloads(ledger_path=env["ledger"]) if r["status"] != REVIEW_REQUIRED]
    assert len(others) == len(known_headers), (
        "the other offerings in the batch must be unaffected — quarantine isolates the PAYLOAD, "
        "never the family"
    )


def test_a8b_a_sidecar_cannot_bless_an_unknown_schema_as_accepted(env):
    """R6 — an offering that DECLARES `accepted` while carrying a schema the governed catalog does
    not recognise must still persist as review_required. A sidecar is a provenance declaration, not
    a schema authority."""
    m = _mod()
    unknown_header = SYNTH_HEADER + ["synthetic_never_seen_before"]
    src = _write_csv(
        env["staging"] / "u.csv", [["pU", "A", "AAA", "1", "2", "z"]], header=unknown_header
    )
    sidecar = _sidecar(
        env["root"] / "batch.json", [_offering(src, offering_id="u", status="accepted")]
    )
    result = _run(m, env, sidecar)
    assert result.review_state == REVIEW_REQUIRED
    rows = m.list_payloads(ledger_path=env["ledger"])
    assert len(rows) == 1
    assert rows[0]["status"] == REVIEW_REQUIRED, (
        "a declared `accepted` must NOT override an unrecognised schema; "
        f"persisted status was {rows[0]['status']!r}"
    )


def test_a8c_a_status_outside_the_governed_ontology_is_refused(env):
    """Arbitrary strings must never enter the canonical ledger. The permitted set is the six legacy
    labels plus pending_review / review_required."""
    m = _mod()
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    rec = _offering(src, status="totally_invented_status")
    with pytest.raises(m.PFFIntakeError) as exc:
        _run(m, env, _sidecar(env["root"] / "batch.json", [rec]))
    assert "totally_invented_status" in str(exc.value), (
        f"the rejected status must be named; got {exc.value}"
    )


def test_a8d_every_persisted_status_is_inside_the_governed_ontology(env):
    m = _mod()
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    _run(m, env, _sidecar(env["root"] / "batch.json", [_offering(src)]))
    for row in m.list_payloads(ledger_path=env["ledger"]):
        assert row["status"] in ALLOWED_STATUSES, (
            f"persisted status {row['status']!r} is outside the governed ontology {sorted(ALLOWED_STATUSES)}"
        )


# ============= A9/A10 — ONE transaction; marker only after the commit ==============


def test_a9_metadata_commit_is_one_transaction_and_leaves_no_partial_index(env):
    """Four file renames cannot be a transaction. One DB commit is the commit point, and an induced
    failure must leave NO partial index."""
    m = _mod()
    srcs = [
        _write_csv(env["staging"] / f"t{i}.csv", [[f"p{i}", "A", "AAA", str(i), "2"]])
        for i in range(3)
    ]
    sidecar = _sidecar(
        env["root"] / "batch.json",
        [_offering(s, offering_id=f"off-{i}", season=str(2017 + i)) for i, s in enumerate(srcs)],
    )

    _seed_ledger(m, env)
    before = _table_counts(env)
    # abort on the LAST offering, so the first two are written and must be rolled back
    _install_offering_abort(env, "off-2")
    result = _run(m, env, sidecar)
    _drop_offering_abort(env)

    assert result.status == MARKER_STATUS_FAILED, "an aborted transaction is a transport failure"
    assert _table_counts(env) == before, (
        f"BOTH tables must return to their pre-batch counts; before={before} after={_table_counts(env)}"
    )
    for s in srcs:
        assert s.exists(), "originals must survive a failed transaction"


def test_a9b_retry_after_an_injected_failure_reuses_the_unindexed_object_and_commits(env):
    """R3 — the failure must be RECOVERABLE. A retry reconciles the already-copied
    content-addressed object rather than orphaning or re-fetching it, and then commits."""
    m = _mod()
    src = _write_csv(env["staging"] / "r.csv", [["p1", "A", "AAA", "1", "2"]])
    sidecar = _sidecar(env["root"] / "batch.json", [_offering(src, offering_id="retry-1")],
                       batch_id="retry-batch")
    _seed_ledger(m, env)
    _install_offering_abort(env, "retry-1")
    failed = _run(m, env, sidecar)
    assert failed.status == MARKER_STATUS_FAILED
    assert failed.unindexed_objects, "fixture precondition: the copy landed before the abort"

    _drop_offering_abort(env)
    retried = _run(m, env, sidecar)
    assert retried.status == MARKER_STATUS_OK, "a retry after a transport failure must succeed"
    assert retried.payloads_indexed == 1
    assert not retried.unindexed_objects, (
        f"the retry must reconcile the previously unindexed object; got {retried.unindexed_objects!r}"
    )


def test_a10_raw_copy_without_a_committed_transaction_is_reported_as_unindexed(env):
    """If a canonical copy landed but the DB transaction failed, that object must be RECONCILED as
    unindexed — never silently orphaned, and never deleted."""
    m = _mod()
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    sidecar = _sidecar(env["root"] / "batch.json", [_offering(src, offering_id="off-a")])
    _seed_ledger(m, env)
    _install_offering_abort(env, "off-a")
    result = _run(m, env, sidecar)
    _drop_offering_abort(env)
    assert result.status == MARKER_STATUS_FAILED
    assert result.unindexed_objects, (
        "a raw copy present without a committed transaction must be reported as an unindexed "
        f"object; got {result.unindexed_objects!r}"
    )
    assert src.exists() and src.read_text(), "the original input is never deleted"


# =========== A11 — DUAL AXES, transport pinned LITERALLY, through the real consumer ==========


def test_a11_quarantined_but_preserved_batch_is_transport_ok_and_advances_last_success(env):
    """The correction that matters most. A batch fully preserved and indexed, containing one unknown
    schema, is a REAL acquisition. Writing a non-success transport status would make
    daily_control report freshness `unknown` — erasing an acquisition that genuinely happened.

    Transport is asserted as the LITERAL "ok" and then passed through the REAL
    daily_control.marker_last_success. It is deliberately NOT derived from SUCCESS_STATUSES:
    deriving it would let someone delete "ok" from that set and have this contract silently adapt.
    """
    m = _mod()
    good = _write_csv(env["staging"] / "g.csv", [["p1", "A", "AAA", "1", "2"]])
    unknown_header = SYNTH_HEADER + ["synthetic_never_seen_before"]
    bad = _write_csv(env["staging"] / "u.csv", [["p2", "B", "BBB", "1", "2", "z"]], header=unknown_header)
    sidecar = _sidecar(
        env["root"] / "batch.json",
        [_offering(good, offering_id="g"), _offering(bad, offering_id="u", season="2020")],
    )
    result = _run(m, env, sidecar)

    assert result.status == MARKER_STATUS_OK, (
        "everything was durably preserved and indexed, so transport is literally 'ok'; "
        f"got {result.status!r}"
    )
    assert result.review_state == REVIEW_REQUIRED
    assert result.review_required_count == 1

    payload = json.loads(env["marker"].read_text())
    assert payload["status"] == MARKER_STATUS_OK, "the serialized marker pins the literal transport"
    assert payload["review_state"] == REVIEW_REQUIRED
    assert payload["review_required_count"] == 1

    # ...and the REAL consumer must advance on it.
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    entry = daily_control.ManifestEntry(
        source="pff",
        mode="manual_download",
        refresh_target="daily",
        connection_method="manual_export_download",
        success_marker=str(env["marker"]),
    )
    assert daily_control.marker_last_success(entry) is not None, (
        "a preserved-and-indexed batch must ADVANCE last-success even when review is required"
    )
    assert daily_control.marker_freshness(entry) != "unknown", (
        "freshness must not read as unknown for an acquisition that genuinely happened"
    )
    # Complementary, not a substitute for the literal above.
    assert MARKER_STATUS_OK in daily_control.SUCCESS_STATUSES

    # R1: the LAST-GOOD marker advances on ok, and daily_control must be able to read BOTH clocks.
    assert env["ready"].exists(), "status=ok must advance the last-good ready marker"
    ready = json.loads(env["ready"].read_text())
    assert ready["status"] == MARKER_STATUS_OK
    # CROSS-MODULE CONTRACT, discovered by probing the shipped consumer rather than assuming it:
    # `daily_control._last_good_success` requires a nonempty `run_id` AND `captured_at`, by design
    # ("an arbitrary JSON that happens to carry a timestamp must not license a freshness claim").
    # A ready marker written with status/finished_at alone is SILENTLY IGNORED — the GREEN would
    # look correct and the last-good clock would never advance.
    assert str(ready.get("run_id") or "").strip(), (
        "the ready marker must carry a nonempty run_id or daily_control ignores it entirely"
    )
    assert str(ready.get("captured_at") or "").strip(), (
        "the ready marker must carry captured_at or daily_control ignores it entirely"
    )
    both = daily_control.ManifestEntry(
        source="pff",
        mode="manual_download",
        refresh_target="daily",
        connection_method="manual_export_download",
        success_marker=str(env["marker"]),
        last_good_marker=str(env["ready"]),
    )
    assert daily_control.marker_last_success(both) is not None


def test_a11c_a_failed_batch_after_a_good_one_preserves_the_last_good_vintage(env):
    """R1 — the reason two markers exist. With ONE marker, a later failed batch overwrites it and
    daily_control forgets a real prior acquisition. The ready marker must survive byte-identical."""
    m = _mod()
    good = _write_csv(env["staging"] / "g.csv", [["p1", "A", "AAA", "1", "2"]])
    ok_result = _run(m, env, _sidecar(env["root"] / "good.json",
                                      [_offering(good, offering_id="g")], batch_id="GOOD"))
    assert ok_result.status == MARKER_STATUS_OK
    ready_bytes = env["ready"].read_bytes()

    later = _write_csv(env["staging"] / "l.csv", [["p2", "B", "BBB", "3", "4"]])
    _install_offering_abort(env, "l")
    failed = _run(m, env, _sidecar(env["root"] / "bad.json",
                                   [_offering(later, offering_id="l", season="2021")],
                                   batch_id="BAD"))
    _drop_offering_abort(env)

    assert failed.status == MARKER_STATUS_FAILED
    assert env["ready"].read_bytes() == ready_bytes, (
        "a later FAILED batch must leave the last-good marker byte-identical — otherwise the prior "
        "good vintage is forgotten, which is the whole reason for a second marker"
    )
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    entry = daily_control.ManifestEntry(
        source="pff",
        mode="manual_download",
        refresh_target="daily",
        connection_method="manual_export_download",
        success_marker=str(env["marker"]),
        last_good_marker=str(env["ready"]),
    )
    assert daily_control.marker_last_success(entry) is not None, (
        "the prior good vintage must still be readable after a failed attempt"
    )


def test_a11b_a_failed_attempt_does_not_ADVANCE_the_clock_but_leaves_it_readable(env):
    """F5 — the correct expectation for this fixture.

    The previous version installed a prior GOOD ready marker (via the seed batch) and then omitted
    `last_good_marker` from the ManifestEntry while asserting None. That asserts the opposite of the
    two-marker contract: it tested a misconfiguration, not the design. Under the contract a failed
    latest attempt must NOT ADVANCE the clock, while the prior last-good timestamp stays readable.
    """
    m = _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    _seed_ledger(m, env)
    assert env["ready"].exists(), "fixture precondition: the seed batch advanced the last-good clock"
    before = json.loads(env["ready"].read_text())["captured_at"]

    entry = daily_control.ManifestEntry(
        source="pff",
        mode="manual_download",
        refresh_target="daily",
        connection_method="manual_export_download",
        success_marker=str(env["marker"]),
        last_good_marker=str(env["ready"]),
    )
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    _install_offering_abort(env, "off-fail")
    result = _run(
        m, env,
        _sidecar(env["root"] / "batch.json",
                 [_offering(src, offering_id="off-fail", season="2021")], batch_id="FAIL"),
    )
    _drop_offering_abort(env)

    assert result.status == MARKER_STATUS_FAILED
    after = daily_control.marker_last_success(entry)
    assert after == before, (
        "a failed attempt must leave the clock at the PRIOR good vintage — neither advanced nor "
        f"erased; before={before!r} after={after!r}"
    )
    if env["marker"].exists():
        assert json.loads(env["marker"].read_text())["status"] == MARKER_STATUS_FAILED


def test_a11d_a_first_ever_failure_with_no_prior_good_vintage_reports_none(env):
    """F5 counter-case — with no ready marker at all there IS no prior vintage, so the honest answer
    is None. This is what distinguishes 'failed once over good data' from 'never succeeded'."""
    m = _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    # Deliberately NOT seeded: no prior success, so no ready marker may exist.
    # The failure is induced by making the canonical root UNCREATABLE — a file sits where the
    # directory must go — so the copy itself cannot succeed. That is a genuine durability failure.
    # A `force_transport_failure=True` argument was rejected here: a test-only parameter in the
    # production signature is the same defect as the `extra_paths` scan already removed from A1b.
    env["store_root"].parent.mkdir(parents=True, exist_ok=True)
    env["store_root"].write_text("not a directory")
    sidecar = _sidecar(env["root"] / "batch.json", [_offering(src, offering_id="off-first")])
    result = _run(m, env, sidecar)
    assert result.status == MARKER_STATUS_FAILED
    assert not env["ready"].exists(), "a first-ever failure must not fabricate a last-good marker"
    entry = daily_control.ManifestEntry(
        source="pff",
        mode="manual_download",
        refresh_target="daily",
        connection_method="manual_export_download",
        success_marker=str(env["marker"]),
        last_good_marker=str(env["ready"]),
    )
    assert daily_control.marker_last_success(entry) is None, (
        "never-succeeded must report None, not an invented vintage"
    )


# ==================== A12/A13 — path truth and honest absence ======================


def test_a12_canonical_paths_are_persisted_repo_relative(env):
    """External source paths stay private provenance; canonical paths are repo-relative so the
    ledger is portable."""
    m = _mod()
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    _run(m, env, _sidecar(env["root"] / "batch.json", [_offering(src)]))
    for row in m.list_payloads(ledger_path=env["ledger"]):
        cp = Path(row["canonical_path"])
        # R5: "not absolute" is insufficient — `../escape.csv` satisfies it. The path must be
        # ANCHORED under the canonical root and must not traverse out of it.
        assert not cp.is_absolute(), f"canonical_path must be repo-relative; got {cp!r}"
        assert ".." not in cp.parts, f"canonical_path must not traverse; got {cp!r}"
        resolved = (env["root"] / cp).resolve()
        assert resolved.is_relative_to(env["store_root"].resolve()), (
            f"canonical_path must anchor under the canonical root; {resolved} escapes "
            f"{env['store_root'].resolve()}"
        )
        # F2: the EXACT existing convention, not merely "somewhere under the root". Without this a
        # new importer can build a second, incompatible private tree and still pass.
        rel = resolved.relative_to(env["store_root"].resolve()).as_posix()
        assert CANONICAL_RE.match(rel), (
            f"canonical layout must be raw/{{league}}/{{report}}/{{scope}}/{{season}}/"
            f"{{date}}_{{sha12}}.csv; got {rel!r}"
        )
        assert CANONICAL_RE.match(rel).group("sha12") == row["sha256"][:12], (
            "the filename's sha12 must be the payload's own SHA — immutable identity"
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("league", "../../etc"),
        ("report", "../escape"),
        ("scope", ".."),
        ("season", "../../.."),
    ],
)
def test_a12b_traversal_in_declared_provenance_is_rejected(env, field, value):
    """R5 — provenance fields become path components. A `..` in any of them would write outside the
    canonical root, so each must be rejected rather than sanitised silently."""
    m = _mod()
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    rec = _offering(src)
    rec[field] = value
    with pytest.raises(m.PFFIntakeError) as exc:
        _run(m, env, _sidecar(env["root"] / "batch.json", [rec]))
    assert field in str(exc.value), f"the offending field must be named; got {exc.value}"


def test_a13_absent_marker_is_unknown_and_the_axes_are_never_inferred_from_each_other(env):
    """The same honesty contract the clean-runner fix landed: absence is `unknown`, never an
    invented age. And neither axis may be derived from the other."""
    m = _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    entry = daily_control.ManifestEntry(
        source="pff",
        mode="manual_download",
        refresh_target="daily",
        connection_method="manual_export_download",
        success_marker=str(env["marker"]),
    )
    assert not env["marker"].exists()
    assert daily_control.marker_last_success(entry) is None
    assert daily_control.marker_freshness(entry) == "unknown"

    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    result = _run(m, env, _sidecar(env["root"] / "batch.json", [_offering(src)]))
    assert result.status == MARKER_STATUS_OK
    assert result.review_state == REVIEW_CLEAR, (
        "a fully-known-schema batch is review-clear; review_state must be computed from evidence, "
        "not inferred from transport success"
    )
    assert result.review_required_count == 0


# ============================ SUITE B — backfill contract ==========================


def _governed_fixtures(root: Path) -> tuple[Path, Path, list[Path]]:
    """Synthetic stand-ins for the governed inventory + download map, in the real column shape."""
    canonical_root = root / "canonical"
    objects, inv_rows, map_rows = [], [], []
    # three payloads; the third is offered TWICE, mirroring the 307->149 shape
    specs = [("ncaa", "receiving_summary", "REG", "2019"), ("nfl", "rushing_summary", "REGPO", "2020"),
             ("ncaa", "passing_summary", "REGPO", "2021")]
    for i, (league, report, scope, season) in enumerate(specs):
        p = _write_csv(
            canonical_root / "raw" / league / report / scope / season / f"2026-08-08_obj{i}.csv",
            [[f"p{i}", "A", "AAA", str(i), "2"]],
        )
        objects.append(p)
        sha = _sha256(p)
        # F3: the EXACT governed inventory header, all 17 columns, read off the real artifact.
        # `canonical_path` is stored ABSOLUTE in the real file, which is precisely why backfill
        # needs a repo_root and must normalize.
        inv_rows.append(
            {"league": league, "report": report, "scope": scope, "season": season,
             "retrieved_at": "2026-08-08T01:00:00-04:00", "rows": "1",
             "columns": str(len(SYNTH_HEADER)), "bytes": str(p.stat().st_size), "sha256": sha,
             "schema_sha256": _schema_hash(SYNTH_HEADER),
             "duplicate_download_count": "0", "variant_count_for_selection": "1",
             "preferred_for_selection": "True", "status": "accepted", "quality_note": "",
             "canonical_path": str(p.resolve()),  # ABSOLUTE, as in the governed artifact
             "original_files": f"obj{i}.csv"}
        )
        offerings = 2 if i == 2 else 1
        for k in range(offerings):
            map_rows.append(
                {"original_file": f"obj{i}_{k}.csv", "original_path": f"/private/dl/obj{i}_{k}.csv",
                 "report": report, "league": league, "scope": scope, "season": season,
                 "retrieved_at": "2026-08-08T01:00:00-04:00", "rows": "1",
                 "columns": str(len(SYNTH_HEADER)), "bytes": str(p.stat().st_size), "sha256": sha,
                 "schema_sha256": _schema_hash(SYNTH_HEADER),
                 # NOTE: every row is flagged True on purpose — see test_b4.
                 "is_exact_duplicate": "True", "status": "accepted", "canonical_path": str(p)}
            )
    inv = root / "inventory.csv"
    with inv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(inv_rows[0]))
        w.writeheader()
        w.writerows(inv_rows)
    dm = root / "download_map.csv"
    with dm.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(map_rows[0]))
        w.writeheader()
        w.writerows(map_rows)
    return inv, dm, objects


def test_b1_backfill_indexes_in_place_without_copying_moving_or_rewriting(env):
    """Backfill is NOT intake. The 149 are already canonical; requiring a sidecar for them would be
    wrong, and copying them would duplicate 68.9 MiB of paid data for nothing."""
    m = _mod()
    inv, dm, objects = _governed_fixtures(env["root"] / "gov")
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in objects}
    result = m.backfill(inventory_csv=inv, download_map_csv=dm, ledger_path=env["ledger"],
                       repo_root=env["root"], store_root=env["root"] / "gov" / "canonical")
    assert result.payloads_indexed == 3
    for p, (data, mtime) in before.items():
        assert p.exists(), "backfill must not move or delete a canonical object"
        assert p.read_bytes() == data, "backfill must not rewrite a canonical object"
        assert p.stat().st_mtime_ns == mtime, "backfill must not even touch mtime"


def test_b2_backfill_validates_recorded_hashes_against_the_objects(env):
    """A recorded hash that no longer matches its object is a corruption signal, not a detail."""
    m = _mod()
    inv, dm, objects = _governed_fixtures(env["root"] / "gov")
    tampered_sha = _sha256(objects[0])
    objects[0].write_text(objects[0].read_text() + "tampered,x,x,x,x\n")
    result = m.backfill(inventory_csv=inv, download_map_csv=dm, ledger_path=env["ledger"],
                       repo_root=env["root"], store_root=env["root"] / "gov" / "canonical")
    assert result.hash_mismatches, (
        "a tampered object must be reported as a hash mismatch, never indexed as valid"
    )
    # R4: REPORTING a mismatch is not enough — a broken GREEN could report it and index anyway.
    indexed = {r["sha256"] for r in m.list_payloads(ledger_path=env["ledger"])}
    assert tampered_sha not in indexed, (
        "the mismatched payload must remain UNCOMMITTED, not merely reported"
    )
    offerings = m.list_offerings(ledger_path=env["ledger"])
    assert all(o["sha256"] != tampered_sha for o in offerings), (
        "every offering referencing the mismatched payload must remain unresolved"
    )
    # ...while the independent, valid payloads still index.
    assert len(indexed) == 2, (
        f"the two untampered payloads must still index independently; indexed {len(indexed)}"
    )


def test_b3_backfill_replay_is_a_no_op(env):
    m = _mod()
    inv, dm, _ = _governed_fixtures(env["root"] / "gov")
    m.backfill(inventory_csv=inv, download_map_csv=dm, ledger_path=env["ledger"],
                       repo_root=env["root"], store_root=env["root"] / "gov" / "canonical")
    second = m.backfill(inventory_csv=inv, download_map_csv=dm, ledger_path=env["ledger"],
                       repo_root=env["root"], store_root=env["root"] / "gov" / "canonical")
    assert second.payloads_indexed == 0, "an exact replay must index nothing new"
    assert second.provenance_added == 0


def test_b1b_backfill_normalizes_absolute_canonical_paths_to_anchored_repo_relative(env):
    """F3 — the governed inventory stores ABSOLUTE canonical paths (verified against the real
    artifact). Persisting them verbatim makes the ledger machine-specific, which is the same
    portability defect that turned main red earlier tonight. Backfill must anchor and normalize."""
    m = _mod()
    inv, dm, _ = _governed_fixtures(env["root"] / "gov")
    import csv as _csv
    recorded = [r["canonical_path"] for r in _csv.DictReader(open(inv))]
    assert all(Path(x).is_absolute() for x in recorded), (
        "fixture precondition: the governed inventory stores ABSOLUTE paths"
    )
    m.backfill(inventory_csv=inv, download_map_csv=dm, ledger_path=env["ledger"],
               repo_root=env["root"], store_root=env["root"] / "gov" / "canonical")
    for row in m.list_payloads(ledger_path=env["ledger"]):
        cp = Path(row["canonical_path"])
        assert not cp.is_absolute(), f"backfill must persist repo-relative paths; got {cp!r}"
        assert ".." not in cp.parts, f"backfill must not persist traversal; got {cp!r}"
        assert (env["root"] / cp).resolve().is_relative_to(
            (env["root"] / "gov" / "canonical").resolve()
        ), f"{cp!r} must anchor under the canonical root"


def test_b4_acceptance_invariant_uses_counts_and_resolvability_never_duplicate_flag_arithmetic(env):
    """MEASURED FINDING, and the reason this test exists.

    In the real governed artifacts the `is_exact_duplicate` flag does NOT partition offerings into
    firsts and duplicates: True=234 / False=73 across 307 offerings, and 76 of the 149 payloads have
    NO offering flagged False at all. So an invariant of the form "149 first-offerings" or "158
    duplicates by flag" FAILS against evidence that is perfectly correct.

    The fixture above therefore flags EVERY row True, reproducing that shape. The supported
    invariant is offering-count, distinct-payload-count, and full resolvability.
    """
    m = _mod()
    inv, dm, _ = _governed_fixtures(env["root"] / "gov")
    result = m.backfill(inventory_csv=inv, download_map_csv=dm, ledger_path=env["ledger"],
                       repo_root=env["root"], store_root=env["root"] / "gov" / "canonical")
    assert result.offerings_seen == 4, f"4 offering rows in the fixture; got {result.offerings_seen}"
    assert result.payloads_indexed == 3, "3 distinct payload SHAs"
    assert result.unresolved_offerings == [], (
        f"every offering sha must resolve to an indexed payload; unresolved {result.unresolved_offerings!r}"
    )
    with sqlite3.connect(env["ledger"]) as conn:
        flags = conn.execute("select count(*) from payload where status is null").fetchone()[0]
    assert flags == 0, "backfill must carry the governed status through for every payload"


# ==================================================================================
# SUITE E — the OPERATOR-CALLABLE CONTROL PLANE
#
# Added after review: every test above exercises only the Python module, so the suite could go
# GREEN with a perfect library and NO runnable importer — leaving daily_control truthfully stuck at
# `missing_importer` and the Layer 1 objective unmet. A library nobody can invoke is not ingestion.
#
# The inbox is declared EXPLICITLY here rather than inferred. `app/data/pff_exports/` is gitignored
# (.gitignore:173), so the inbox beneath it is private by construction. Falling back to the
# canonical raw destination would conflate the human drop point with the content-addressed store,
# and inferring `~/Downloads` would be exactly the filename/location guessing A1 forbids.
# ==================================================================================

CLI_PATH = "scripts/run_pff_intake.py"
PFF_INBOX = "app/data/pff_exports/inbox"


def _cli_argv(env, sidecar: Path) -> list[str]:
    """Every path configurable, so CI never needs a production or private location."""
    return [
        CLI_PATH,
        "--batch-manifest", str(sidecar),
        "--store-root", str(env["store_root"]),
        "--ledger-path", str(env["ledger"]),
        "--status-marker", str(env["marker"]),
        "--ready-marker", str(env["ready"]),
        "--repo-root", str(env["root"]),
        "--known-schema-catalog", str(env["catalog"]),
    ]


def _write_catalog(env) -> Path:
    env["catalog"].parent.mkdir(parents=True, exist_ok=True)
    env["catalog"].write_text(json.dumps([{"schema_sha256": _schema_hash(SYNTH_HEADER)}]))
    return env["catalog"]


def _run_cli(env, argv: list[str]) -> subprocess.CompletedProcess:
    """Invoke the CLI as a real child process, so the assertion is on TRUE process exit.

    `sys.executable` — never a hardcoded `.venv/bin/python3.14`. That hardcoding is precisely what
    turned main red in c55e645: `.venv/` is gitignored, so it does not exist on a clean runner.
    """
    return subprocess.run(
        [sys.executable, *argv],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
    )


def test_e1_cli_exists_and_is_invocable_on_a_clean_runner(env):
    """The control plane must exist as a script, not only as an importable module."""
    _mod()
    assert (_REPO_ROOT / CLI_PATH).is_file(), f"{CLI_PATH} must exist — a library nobody can run is not ingestion"
    proc = _run_cli(env, [CLI_PATH, "--help"])
    assert proc.returncode == 0, f"--help must succeed; stderr={proc.stderr[:400]}"
    for flag in (
        "--batch-manifest", "--store-root", "--ledger-path",
        "--status-marker", "--ready-marker", "--repo-root",
        "--backfill-existing", "--inventory-csv", "--download-map-csv",
    ):
        assert flag in proc.stdout, f"{flag} must be an accepted option; help was:\n{proc.stdout[:800]}"


def test_e2_cli_intake_exits_zero_for_a_durable_ok_batch_and_emits_both_axes(env):
    m = _mod()
    _write_catalog(env)
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    sidecar = _sidecar(env["root"] / "batch.json", [_offering(src)])
    proc = _run_cli(env, _cli_argv(env, sidecar))
    assert proc.returncode == 0, f"a durable ok batch must exit 0; stderr={proc.stderr[:400]}"
    summary = json.loads(proc.stdout)
    assert summary["status"] == MARKER_STATUS_OK
    assert summary["review_state"] == REVIEW_CLEAR
    assert "review_required_count" in summary, "the JSON summary must carry BOTH axes"
    assert m is not None


def test_e3_cli_exits_zero_when_review_is_required_because_transport_succeeded(env):
    """review_required is an evidence state, NOT a transport failure. Exiting nonzero here would
    make a scheduler treat a real, durably-preserved acquisition as a failed job."""
    _mod()
    _write_catalog(env)
    unknown_header = SYNTH_HEADER + ["synthetic_never_seen_before"]
    src = _write_csv(env["staging"] / "u.csv", [["pU", "A", "AAA", "1", "2", "z"]], header=unknown_header)
    sidecar = _sidecar(env["root"] / "batch.json", [_offering(src)])
    proc = _run_cli(env, _cli_argv(env, sidecar))
    assert proc.returncode == 0, (
        f"durable preservation with review_required must still exit 0; stderr={proc.stderr[:400]}"
    )
    summary = json.loads(proc.stdout)
    assert summary["status"] == MARKER_STATUS_OK
    assert summary["review_state"] == REVIEW_REQUIRED
    assert summary["review_required_count"] == 1


@pytest.mark.parametrize("case", ["invalid_sidecar", "identity_conflict"])
def test_e4_cli_exits_nonzero_for_failure_classes(env, case):
    _mod()
    _write_catalog(env)
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    if case == "invalid_sidecar":
        bad = dict(_offering(src))
        del bad["season"]
        sidecar = _sidecar(env["root"] / "batch.json", [bad])
    else:
        first = _sidecar(env["root"] / "b1.json", [_offering(src, offering_id="dup")], batch_id="B1")
        assert _run_cli(env, _cli_argv(env, first)).returncode == 0
        other = _write_csv(env["staging"] / "b.csv", [["p1", "A", "AAA", "1", "9"]])
        sidecar = _sidecar(env["root"] / "b2.json", [_offering(other, offering_id="dup")], batch_id="B1")
    proc = _run_cli(env, _cli_argv(env, sidecar))
    assert proc.returncode != 0, f"{case} must exit nonzero; stdout={proc.stdout[:300]}"


def test_e5_cli_backfill_mode_takes_configurable_paths_and_exits_nonzero_on_corruption(env):
    _mod()
    inv, dm, objects = _governed_fixtures(env["root"] / "gov")
    argv = [
        CLI_PATH, "--backfill-existing",
        "--inventory-csv", str(inv), "--download-map-csv", str(dm),
        "--ledger-path", str(env["ledger"]), "--repo-root", str(env["root"]),
        "--store-root", str(env["root"] / "gov" / "canonical"),
        "--status-marker", str(env["marker"]), "--ready-marker", str(env["ready"]),
    ]
    assert _run_cli(env, argv).returncode == 0, "a clean backfill must exit 0"

    objects[0].write_text(objects[0].read_text() + "tampered,x,x,x,x\n")
    fresh = env["root"] / "ledger2.db"
    proc = _run_cli(env, [x if x != str(env["ledger"]) else str(fresh) for x in argv])
    assert proc.returncode != 0, "backfill corruption must exit nonzero, never a silent success"


def test_e6_no_network_path_exists_in_either_cli_mode(env, monkeypatch):
    """PFF is a manual_download source. If any fetch boundary is reachable, a future edit could turn
    a manual route into a silent network call. Run IN-PROCESS with the boundaries armed to raise —
    a subprocess would not inherit these patches."""
    _mod()
    cli = importlib.import_module("scripts.run_pff_intake")
    _write_catalog(env)

    def _forbidden(*a, **k):  # noqa: ANN002, ANN003
        raise AssertionError("network access attempted by a manual_download source")

    monkeypatch.setattr(socket, "socket", _forbidden)
    monkeypatch.setattr(socket, "create_connection", _forbidden)
    monkeypatch.setattr(subprocess, "run", _forbidden)
    monkeypatch.setattr(subprocess, "Popen", _forbidden)
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", _forbidden)

    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    sidecar = _sidecar(env["root"] / "batch.json", [_offering(src)])
    assert cli.main(_cli_argv(env, sidecar)[1:]) == 0, "intake must complete with all fetch boundaries armed"

    inv, dm, _ = _governed_fixtures(env["root"] / "gov2")
    # EVERY path must be pinned into the sandbox. Omitting --status-marker/--ready-marker fell
    # through to the CLI's PRODUCTION defaults and wrote synthetic fixture timestamps into the
    # developer's real app/data/ops markers — corrupting the live freshness signal from a test run.
    # A contract test must never be able to touch production state.
    assert cli.main([
        "--backfill-existing", "--inventory-csv", str(inv), "--download-map-csv", str(dm),
        "--ledger-path", str(env["root"] / "l2.db"), "--repo-root", str(env["root"]),
        "--store-root", str(env["root"] / "gov2" / "canonical"),
        "--status-marker", str(env["root"] / "ops2" / "status.json"),
        "--ready-marker", str(env["root"] / "ops2" / "ready.json"),
    ]) == 0, "backfill must complete with all fetch boundaries armed"


def test_e7_daily_control_manifest_names_the_cli_inbox_and_BOTH_markers():
    """STANDING RED BY DESIGN — this one does not go green with the library.

    Ruled: daily_control is edited only AFTER GREEN plus a successful private backfill. Until then
    this test stays red, and that is the gate, not a defect. It exists so the manifest cannot be
    left saying `missing_importer` once a real importer exists.
    """
    _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    entry = next(e for e in daily_control.build_manifest() if e.source == "pff")
    # EXACT TUPLE EQUALITY. The previous `CLI_PATH in entry.importer` was VACUOUS: against a bare
    # string that is substring membership, which passes for any superstring — and it passed while
    # the real preflight was emitting 23 `importer_not_found:<character>` errors.
    assert entry.importer == (CLI_PATH,), (
        f"importer must be the exact tuple ({CLI_PATH!r},) per the declared collection contract; "
        f"got {entry.importer!r}"
    )
    assert entry.drop_location == PFF_INBOX, (
        "drop_location must be the human INBOX, never the canonical raw destination and never an "
        f"inferred ~/Downloads; got {entry.drop_location!r}"
    )
    assert entry.success_marker, "the latest-attempt marker must be named"
    assert entry.last_good_marker, "the last-good marker must be named"

    # Route completeness proven through the REAL preflight, not by inspecting fields.
    status = daily_control.entry_status(entry)
    assert not any("importer_not_found" in x for x in status.missing), (
        f"no importer component may be missing; got {status.missing!r}"
    )
    assert status.ok, f"the pff route must be complete in preflight; missing={status.missing!r}"


# ==================================================================================
# SUITE F — the MANUAL FRESHNESS CLOCK
#
# The defect this suite exists to prevent, verified directly against the shipped consumer:
#
#     _COMPLETION_KEYS = ('finished_at', 'completed_at', 'captured_at', 'retrieved_at', 'ingested_at')
#
# `finished_at` and `completed_at` OUTRANK `retrieved_at`. So a marker carrying a generic
# run-completion time shadows the real acquisition time. Measured: a marker declaring
# finished_at=2026-08-08 alongside retrieved_at=2026-05-16 reports age_days=0.033 and freshness
# `current` — a three-month-old subscriber download reading as acquired today.
#
# For a manual_download source the honest clock is WHEN THE HUMAN DOWNLOADED THE DATA, not when we
# happened to build an index over it. "Age since we ran the importer" is not freshness; it is a
# measurement of our own activity wearing freshness's clothes.
# ==================================================================================

#: Execution time is still recorded — under a key daily_control does NOT consume for freshness.
EXECUTION_KEY = "indexed_at"
#: Keys the marker must NEVER emit, because they outrank the semantic clock.
FORBIDDEN_COMPLETION_KEYS = ("finished_at", "completed_at")


def test_f1_intake_marker_reports_SOURCE_retrieval_time_not_import_time(env):
    """The freshness key consumed by daily_control must be the maximum DECLARED offering
    `retrieved_at`, and no earlier-precedence key may shadow it."""
    m = _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    older, newer = "2026-01-04T09:00:00+00:00", "2026-05-16T07:23:11+00:00"
    a = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    b = _write_csv(env["staging"] / "b.csv", [["p2", "B", "BBB", "3", "4"]])
    sidecar = _sidecar(env["root"] / "batch.json", [
        _offering(a, offering_id="o1", season="2019", retrieved_at=older),
        _offering(b, offering_id="o2", season="2020", retrieved_at=newer),
    ])
    result = _run(m, env, sidecar)
    assert result.status == MARKER_STATUS_OK

    payload = json.loads(env["marker"].read_text())
    for forbidden in FORBIDDEN_COMPLETION_KEYS:
        assert forbidden not in payload, (
            f"{forbidden!r} outranks retrieved_at in daily_control._COMPLETION_KEYS, so emitting it "
            "makes an old manual download read as freshly acquired"
        )
    assert EXECUTION_KEY in payload, "execution time must still be recorded, just not as freshness"

    entry = daily_control.ManifestEntry(
        source="pff", mode="manual_download", refresh_target="daily",
        connection_method="manual_export_download",
        success_marker=str(env["marker"]), last_good_marker=str(env["ready"]),
    )
    assert daily_control.marker_last_success(entry) == newer, (
        "the consumed clock must be the MAX declared source retrieval time across the committed "
        f"ledger; got {daily_control.marker_last_success(entry)!r}, expected {newer!r}"
    )


def test_f2_ready_marker_captured_at_is_the_source_clock_not_wall_clock(env):
    """The last-good identity contract requires `captured_at`; it must carry the SOURCE time."""
    m = _mod()
    newer = "2026-05-16T07:23:11+00:00"
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    _run(m, env, _sidecar(env["root"] / "batch.json",
                          [_offering(src, offering_id="o1", retrieved_at=newer)]))
    ready = json.loads(env["ready"].read_text())
    assert ready["captured_at"] == newer, (
        f"ready captured_at must be the source retrieval clock, not import wall-clock; got {ready['captured_at']!r}"
    )
    assert str(ready.get("run_id") or "").strip(), "the last-good identity contract still requires run_id"


def test_f3_ingesting_older_history_never_moves_the_freshness_clock_backward(env):
    """Backfilling 2017 history after holding 2026 data must not make the source look staler."""
    m = _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    entry = daily_control.ManifestEntry(
        source="pff", mode="manual_download", refresh_target="daily",
        connection_method="manual_export_download",
        success_marker=str(env["marker"]), last_good_marker=str(env["ready"]),
    )
    newer, older = "2026-05-16T07:23:11+00:00", "2017-03-01T09:00:00+00:00"
    a = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    _run(m, env, _sidecar(env["root"] / "b1.json",
                          [_offering(a, offering_id="o1", retrieved_at=newer)], batch_id="B1"))
    after_first = daily_control.marker_last_success(entry)
    assert after_first == newer

    b = _write_csv(env["staging"] / "b.csv", [["p2", "B", "BBB", "3", "4"]])
    _run(m, env, _sidecar(env["root"] / "b2.json",
                          [_offering(b, offering_id="o2", season="2017", retrieved_at=older)],
                          batch_id="B2"))
    assert daily_control.marker_last_success(entry) == newer, (
        "ingesting OLDER history must not move the clock backward — the newest acquisition is still "
        f"the newest; got {daily_control.marker_last_success(entry)!r}"
    )


def test_f4_replay_does_not_move_the_freshness_clock_at_all(env):
    """An idempotent replay acquires nothing new, so it must not refresh the clock."""
    m = _mod()
    daily_control = importlib.import_module("src.dynasty_genius.sources.daily_control")
    entry = daily_control.ManifestEntry(
        source="pff", mode="manual_download", refresh_target="daily",
        connection_method="manual_export_download",
        success_marker=str(env["marker"]), last_good_marker=str(env["ready"]),
    )
    when = "2026-05-16T07:23:11+00:00"
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    sidecar = _sidecar(env["root"] / "batch.json", [_offering(src, offering_id="o1", retrieved_at=when)])
    _run(m, env, sidecar)
    before = daily_control.marker_last_success(entry)
    ready_before = env["ready"].read_bytes()
    replay = _run(m, env, sidecar)
    assert replay.payloads_indexed == 0
    assert daily_control.marker_last_success(entry) == before, "replay must not advance the clock"
    assert env["ready"].read_bytes() == ready_before, "replay must not rewrite the last-good marker"


def test_f5_cli_backfill_writes_both_markers_and_reports_the_source_clock(env):
    """Point 4 — the CLI backfill is a control-plane surface and must produce the same honest
    clock, with both axes in its summary."""
    _mod()
    inv, dm, _ = _governed_fixtures(env["root"] / "gov")
    proc = _run_cli(env, [
        CLI_PATH, "--backfill-existing",
        "--inventory-csv", str(inv), "--download-map-csv", str(dm),
        "--ledger-path", str(env["ledger"]), "--repo-root", str(env["root"]),
        "--store-root", str(env["root"] / "gov" / "canonical"),
        "--status-marker", str(env["marker"]), "--ready-marker", str(env["ready"]),
    ])
    assert proc.returncode == 0, f"a clean backfill must exit 0; stderr={proc.stderr[:400]}"
    assert env["marker"].exists(), "backfill must write the latest-attempt marker"
    assert env["ready"].exists(), "a clean backfill must advance the last-good marker"
    summary = json.loads(proc.stdout)
    assert summary["status"] == MARKER_STATUS_OK
    assert "review_state" in summary and "review_required_count" in summary
    assert summary["source_retrieved_at"] == "2026-08-08T01:00:00-04:00", (
        "the summary must report the SOURCE retrieval clock, not import time; "
        f"got {summary.get('source_retrieved_at')!r}"
    )
    for forbidden in FORBIDDEN_COMPLETION_KEYS:
        assert forbidden not in json.loads(env["marker"].read_text())


def test_f6_a_failed_backfill_preserves_a_prior_ready_marker_byte_identical(env):
    """Point 5 — corruption must not disturb a previously-earned last-good vintage."""
    _mod()
    inv, dm, objects = _governed_fixtures(env["root"] / "gov")
    base = [
        CLI_PATH, "--backfill-existing",
        "--inventory-csv", str(inv), "--download-map-csv", str(dm),
        "--repo-root", str(env["root"]),
        "--store-root", str(env["root"] / "gov" / "canonical"),
        "--status-marker", str(env["marker"]), "--ready-marker", str(env["ready"]),
    ]
    assert _run_cli(env, [*base, "--ledger-path", str(env["ledger"])]).returncode == 0
    ready_before = env["ready"].read_bytes()

    objects[0].write_text(objects[0].read_text() + "tampered,x,x,x,x\n")
    proc = _run_cli(env, [*base, "--ledger-path", str(env["root"] / "ledger2.db")])
    assert proc.returncode != 0, "backfill corruption must exit nonzero"
    assert env["ready"].read_bytes() == ready_before, (
        "a failed backfill must leave the prior last-good marker byte-identical"
    )


def test_f7_a_first_ever_failed_backfill_creates_no_ready_marker(env):
    """Point 5 counter-case — with no prior success there is no vintage to report."""
    _mod()
    inv, dm, objects = _governed_fixtures(env["root"] / "gov")
    objects[0].write_text(objects[0].read_text() + "tampered,x,x,x,x\n")
    proc = _run_cli(env, [
        CLI_PATH, "--backfill-existing",
        "--inventory-csv", str(inv), "--download-map-csv", str(dm),
        "--ledger-path", str(env["ledger"]), "--repo-root", str(env["root"]),
        "--store-root", str(env["root"] / "gov" / "canonical"),
        "--status-marker", str(env["marker"]), "--ready-marker", str(env["ready"]),
    ])
    assert proc.returncode != 0
    assert not env["ready"].exists(), (
        "a first-ever failed backfill must not fabricate a last-good marker"
    )


# ==================================================================================
# SUITE G — CROSS-ROOT MARKER/STORE CONTAMINATION (PFF-C1)
#
# This suite exists because the defect ACTUALLY HAPPENED during verification, and was caught
# independently from two directions. A run passed a temporary --ledger-path and --store-root but
# left the marker paths at their production defaults. It wrote SYNTHETIC fixture timestamps
# (2026-08-08T01:00:00-04:00) into the live app/data/ops markers, overwriting a real freshness
# clock with a vintage the production ledger had never seen — while the production DB correctly
# held max(retrieved_at)=2026-08-01T09:23:59.
#
# A test that can reach production state is not isolated, and a CLI that lets it is not safe. The
# store case is worse than the marker case: it writes payload BYTES into the governed archive.
# ==================================================================================


def test_g1_isolated_run_refuses_to_keep_production_marker_defaults(env, tmp_path):
    """An isolated ledger/store with defaulted markers must be REFUSED, not guessed."""
    _mod()
    cli = importlib.import_module("scripts.run_pff_intake")
    inv, dm, _ = _governed_fixtures(env["root"] / "gov")
    rc = cli.main([
        "--backfill-existing", "--inventory-csv", str(inv), "--download-map-csv", str(dm),
        "--ledger-path", str(tmp_path / "isolated.db"),
        "--store-root", str(env["root"] / "gov" / "canonical"),
        "--repo-root", str(_REPO_ROOT),          # production repo root...
        # ...and NO marker paths. Under the defect this wrote real app/data/ops markers.
    ])
    assert rc != 0, "an isolated run with production marker defaults must be refused"


def test_g2_markers_must_be_supplied_as_a_pair(env, tmp_path):
    """Half a clock is not a clock: a last-good vintage with no corresponding status marker."""
    _mod()
    cli = importlib.import_module("scripts.run_pff_intake")
    inv, dm, _ = _governed_fixtures(env["root"] / "gov")
    rc = cli.main([
        "--backfill-existing", "--inventory-csv", str(inv), "--download-map-csv", str(dm),
        "--ledger-path", str(tmp_path / "l.db"),
        "--store-root", str(env["root"] / "gov" / "canonical"),
        "--repo-root", str(_REPO_ROOT),
        "--status-marker", str(tmp_path / "status.json"),  # ready-marker deliberately omitted
    ])
    assert rc != 0, "supplying only one marker must be refused"


def test_g3_a_relocated_repo_root_relocates_every_derived_path(env):
    """Rule 1: everything derives from --repo-root, so an isolated root is coherently isolated
    without the caller having to enumerate each path."""
    _mod()
    cli = importlib.import_module("scripts.run_pff_intake")
    args = cli.build_parser().parse_args([
        "--backfill-existing", "--repo-root", str(env["root"]),
    ])
    paths = cli._resolve_paths(args)
    for key in ("store_root", "ledger_path", "status_marker", "ready_marker"):
        assert Path(paths[key]).resolve().is_relative_to(Path(env["root"]).resolve()), (
            f"{key} must derive from the relocated repo root; got {paths[key]}"
        )


def test_g4_a_private_run_cannot_mutate_production_markers_or_store(env, tmp_path):
    """The end-to-end proof Codex required: capture production state, run a fully isolated batch,
    and require production to be byte-identical afterwards."""
    _mod()
    cli = importlib.import_module("scripts.run_pff_intake")
    prod_status = _REPO_ROOT / "app" / "data" / "ops" / "pff_intake_status_latest.json"
    prod_ready = _REPO_ROOT / "app" / "data" / "ops" / "pff_intake.ready.json"
    prod_store = _REPO_ROOT / "app" / "data" / "pff_exports" / "raw"
    before = {
        "status": prod_status.read_bytes() if prod_status.exists() else None,
        "ready": prod_ready.read_bytes() if prod_ready.exists() else None,
        "store": sorted(p.name for p in prod_store.rglob("*.csv")) if prod_store.exists() else [],
    }

    _write_catalog(env)
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    sidecar = _sidecar(env["root"] / "batch.json", [_offering(src)])
    rc = cli.main(_cli_argv(env, sidecar)[1:])
    assert rc == 0, "a properly isolated run must still succeed"

    after = {
        "status": prod_status.read_bytes() if prod_status.exists() else None,
        "ready": prod_ready.read_bytes() if prod_ready.exists() else None,
        "store": sorted(p.name for p in prod_store.rglob("*.csv")) if prod_store.exists() else [],
    }
    assert after["status"] == before["status"], "an isolated run must not touch the production status marker"
    assert after["ready"] == before["ready"], "an isolated run must not touch the production ready marker"
    assert after["store"] == before["store"], "an isolated run must not add objects to the production store"


# ==================================================================================
# SUITE H — defects found by reproducing PRODUCTION SHAPES against the implementation.
# Every one of these was demonstrated to fail before its fix; none was hypothetical.
# ==================================================================================


def test_h1_two_byte_identical_offerings_in_ONE_batch_yield_one_payload_two_mappings(env):
    """PFF-C2 — the 307->149 shape inside a single batch.

    `_stage_payloads` consulted only the pre-transaction ledger, so two byte-identical offerings in
    the same batch were both marked new, the transaction inserted one SHA twice, and the whole
    batch rolled back: status=failed, payloads=0, offerings=0. An honest manual drop containing the
    same export twice was REJECTED — and duplication is the norm here, not an edge case.
    """
    m = _mod()
    a = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    b = _write_csv(env["staging"] / "b.csv", [["p1", "A", "AAA", "1", "2"]])
    assert _sha256(a) == _sha256(b), "fixture precondition: identical bytes"
    result = _run(m, env, _sidecar(env["root"] / "batch.json", [
        _offering(a, offering_id="o1"), _offering(b, offering_id="o2"),
    ]))
    assert result.status == MARKER_STATUS_OK, f"an honest duplicate-in-batch drop must succeed; {result.status}"
    assert result.payloads_indexed == 1, f"identical bytes are ONE payload; got {result.payloads_indexed}"
    assert result.provenance_added == 2, f"both offerings must be recorded; got {result.provenance_added}"


def test_h2_cli_defaults_to_the_governed_schema_catalog(env):
    """PFF-C3 — the documented production route must not quarantine everything.

    With `--known-schema-catalog` defaulting to None the canonical invocation produced an empty
    known set, so every payload quarantined even when its schema is in the governed catalog.
    """
    _mod()
    cli = importlib.import_module("scripts.run_pff_intake")
    assert cli.DEFAULT_SCHEMA_CATALOG == (
        _REPO_ROOT / "app" / "data" / "pff_exports" / "pff_schema_catalog.json"
    ), "the production route must default to the governed catalog"
    args = cli.build_parser().parse_args(["--backfill-existing"])
    assert args.known_schema_catalog == cli.DEFAULT_SCHEMA_CATALOG


def test_h3_a_malformed_or_absent_catalog_fails_SAFE_by_quarantining(env, tmp_path):
    """PFF-C3 counter-case — the fail direction must be quarantine, never bless."""
    _mod()
    cli = importlib.import_module("scripts.run_pff_intake")
    assert cli._load_known_schemas(tmp_path / "nope.json") == set()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert cli._load_known_schemas(bad) == set(), "a malformed catalog must yield an EMPTY set"


def test_h4_a_later_validation_failure_cannot_strand_an_earlier_canonical_copy(env):
    """PFF-C4 — validation and copying are two phases.

    Interleaved, a batch whose SECOND offering had a missing source raised AFTER the first was
    already copied: one unindexed object in the canonical tree, no marker, and nothing reported.
    """
    m = _mod()
    good = _write_csv(env["staging"] / "g.csv", [["p1", "A", "AAA", "1", "2"]])
    sidecar = _sidecar(env["root"] / "batch.json", [
        _offering(good, offering_id="o1"),
        _offering(env["staging"] / "MISSING.csv", offering_id="o2", season="2020"),
    ])
    with pytest.raises(m.PFFIntakeError):
        _run(m, env, sidecar)
    written = list(env["store_root"].rglob("*.csv")) if env["store_root"].exists() else []
    assert written == [], (
        f"phase 1 validates everything before any copy, so nothing may be stranded; found {written}"
    )


def test_h5_an_existing_canonical_object_is_never_blindly_overwritten(env):
    """PFF-C4 — content-addressed immutability. A destination holding DIFFERENT bytes is an
    inconsistent store, and that must surface rather than be papered over by a write."""
    m = _mod()
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    sha = _sha256(src)
    rel = f"raw/ncaa/receiving_summary/REG/2019/2026-05-16_{sha[:12]}.csv"
    victim = env["store_root"] / rel
    victim.parent.mkdir(parents=True, exist_ok=True)
    victim.write_text("pre-existing DIFFERENT content\n")
    with pytest.raises(m.PFFIntakeError) as exc:
        _run(m, env, _sidecar(env["root"] / "batch.json", [
            _offering(src, offering_id="o1", retrieved_at="2026-05-16T07:23:11+00:00"),
        ]))
    assert "overwrite" in str(exc.value).lower()
    assert victim.read_text() == "pre-existing DIFFERENT content\n", "the existing object is untouched"


@pytest.mark.parametrize("bad", [
    "../../../../../../escaped",     # traversal-shaped: became a path component by string slicing
    "2026-05-16T07:23:11",           # naive: an age computed against it is a guess
    "not-a-timestamp",
    "",
])
def test_h6_retrieved_at_must_be_a_timezone_aware_iso_instant(env, bad):
    """PFF-C5 — retrieved_at is BOTH a path component and the source freshness clock.

    Unvalidated, `retrieved_at='../../../../../../escaped'` sliced to `../../../` and wrote
    `raw/ncaa/._<sha12>.csv`, escaping the declared report/scope/season layout while returning
    status=ok — and persisting a clock daily_control cannot use.
    """
    m = _mod()
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    rec = _offering(src)
    rec["retrieved_at"] = bad
    with pytest.raises(m.PFFIntakeError):
        _run(m, env, _sidecar(env["root"] / "batch.json", [rec]))
    written = list(env["store_root"].rglob("*.csv")) if env["store_root"].exists() else []
    assert written == [], f"refusal happens BEFORE any copy; found {written}"


def test_h7_a_valid_offset_timestamp_preserves_its_declared_calendar_date(env):
    """PFF-C5 counter-case — the canonical date comes from the PARSED instant and keeps the
    declared local date; it is not string-sliced and not UTC-shifted."""
    m = _mod()
    src = _write_csv(env["staging"] / "a.csv", [["p1", "A", "AAA", "1", "2"]])
    result = _run(m, env, _sidecar(env["root"] / "batch.json", [
        _offering(src, offering_id="o1", retrieved_at="2026-08-08T01:00:00-04:00"),
    ]))
    assert result.status == MARKER_STATUS_OK
    row = m.list_payloads(ledger_path=env["ledger"])[0]
    expected = f"raw/ncaa/receiving_summary/REG/2019/2026-08-08_{row['sha256'][:12]}.csv"
    actual = (env["root"] / row["canonical_path"]).resolve().relative_to(
        env["store_root"].resolve()
    ).as_posix()
    assert actual == expected, f"expected {expected}, got {actual}"


@pytest.mark.parametrize("argv,label", [
    (["--ledger-path", "app/data/pff_exports/test.db"], "custom ledger inside app/data"),
    (["--store-root", "app/data/pff_exports_test"], "custom store inside app/data"),
])
def test_g5_isolation_is_ANY_deviation_from_the_canonical_pair_not_merely_outside_app_data(argv, label):
    """PFF-C1 residual — the first guard defined isolation as "outside repo_root/app/data", which
    still allowed BOTH of these to write the production clock, and allowed a test ledger to be
    mixed with the governed raw store. Isolation is any deviation from the exact canonical
    (store, ledger) pair for the selected repo root."""
    _mod()
    cli = importlib.import_module("scripts.run_pff_intake")
    args = cli.build_parser().parse_args(["--backfill-existing", *argv])
    with pytest.raises(cli.IsolationError):
        cli._resolve_paths(args)


def test_g6_pure_production_defaults_remain_allowed():
    """The guard must not break the real operator route."""
    _mod()
    cli = importlib.import_module("scripts.run_pff_intake")
    paths = cli._resolve_paths(cli.build_parser().parse_args(["--backfill-existing"]))
    assert paths["status_marker"] == cli.DEFAULT_STATUS_MARKER
    assert paths["ready_marker"] == cli.DEFAULT_READY_MARKER
