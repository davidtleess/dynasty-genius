"""DG-057 — artifact spec verification: refuse the wrong artifact.

TDD RED: fails until src/dynasty_genius/models/artifact_verification.py and
app/config/pre_spec_grandfather.json exist.

Covers both directions the ticket demands:
- wrong-hash refusal (spec mismatch, content tamper, invalid sidecar,
  unverifiable artifact, pinned pointer with no sidecar), and
- grandfathered pass-through (explicit pre-spec allowlist → disclosed
  "pre_spec_artifact" state, never a refusal).

Also gates the grandfather config itself against model_registry.json so the
allowlist can never silently drift from what is actually deployed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

GRANDFATHER_CONFIG = ROOT / "app" / "config" / "pre_spec_grandfather.json"
MODEL_REGISTRY = ROOT / "app" / "config" / "model_registry.json"


def _make_spec(**overrides):
    from src.dynasty_genius.models.training_spec import TrainingSpec

    kwargs = dict(
        engine="engine_a",
        model_id="engine_a:WR",
        feature_set=("pick", "round", "age"),
        feature_set_version="v2",
        target="y24_ppg",
        label_horizon="second_nfl_season",
        cohort_filter="drafted_prospects_with_outcomes",
        preprocessing={"missing_data": "refuse_incomplete_rows", "scaling": "none"},
        estimator_family="ridge",
        tuning_policy={"alpha": "fixed", "search": "none"},
        time_split={"scheme": "draft_class_holdout", "grouping": "draft_class"},
        evaluation_baselines=("pick_only_linear",),
        calibration_method="empirical_p90_ceiling",
    )
    kwargs.update(overrides)
    return TrainingSpec(**kwargs)


@pytest.fixture
def artifact(tmp_path):
    """A synthetic model artifact file (content is irrelevant to hashing)."""
    p = tmp_path / "WR_model.pkl"
    p.write_bytes(b"synthetic-model-bytes-v1")
    return p


# ── Sidecar write + verified pass ────────────────────────────────────────────

def test_sidecar_write_then_verify_verified(artifact):
    from src.dynasty_genius.models.artifact_verification import (
        STATE_VERIFIED,
        verify_artifact,
        write_spec_sidecar,
    )

    spec = _make_spec()
    sidecar = write_spec_sidecar(artifact, spec)
    assert sidecar.exists()
    assert sidecar.name == "WR_model.pkl.spec.json"

    verdict = verify_artifact(
        artifact,
        expected_spec_hash=spec.spec_hash(),
        grandfathered_sha256s=frozenset(),
    )
    assert verdict.state == STATE_VERIFIED
    assert verdict.spec_hash == spec.spec_hash()
    assert len(verdict.artifact_sha256) == 64


def test_unpinned_pointer_accepts_any_consistent_sidecar(artifact):
    """expected_spec_hash=None → internal consistency still fully checked."""
    from src.dynasty_genius.models.artifact_verification import (
        STATE_VERIFIED,
        verify_artifact,
        write_spec_sidecar,
    )

    spec = _make_spec()
    write_spec_sidecar(artifact, spec)
    verdict = verify_artifact(
        artifact, expected_spec_hash=None, grandfathered_sha256s=frozenset()
    )
    assert verdict.state == STATE_VERIFIED
    assert verdict.spec_hash == spec.spec_hash()


# ── Refusals ─────────────────────────────────────────────────────────────────

def test_wrong_expected_spec_hash_refused(artifact):
    from src.dynasty_genius.models.artifact_verification import (
        ArtifactSpecRefusal,
        verify_artifact,
        write_spec_sidecar,
    )

    write_spec_sidecar(artifact, _make_spec())
    wrong = _make_spec(feature_set_version="v99")
    with pytest.raises(ArtifactSpecRefusal) as exc:
        verify_artifact(
            artifact,
            expected_spec_hash=wrong.spec_hash(),
            grandfathered_sha256s=frozenset(),
        )
    assert exc.value.reason == "spec_hash_mismatch"


def test_tampered_artifact_bytes_refused(artifact):
    from src.dynasty_genius.models.artifact_verification import (
        ArtifactSpecRefusal,
        verify_artifact,
        write_spec_sidecar,
    )

    spec = _make_spec()
    write_spec_sidecar(artifact, spec)
    artifact.write_bytes(b"synthetic-model-bytes-TAMPERED")
    with pytest.raises(ArtifactSpecRefusal) as exc:
        verify_artifact(
            artifact,
            expected_spec_hash=spec.spec_hash(),
            grandfathered_sha256s=frozenset(),
        )
    assert exc.value.reason == "content_hash_mismatch"


def test_hand_edited_sidecar_refused(artifact):
    """A sidecar whose embedded spec no longer hashes to its spec_hash."""
    from src.dynasty_genius.models.artifact_verification import (
        ArtifactSpecRefusal,
        verify_artifact,
        write_spec_sidecar,
    )

    spec = _make_spec()
    sidecar = write_spec_sidecar(artifact, spec)
    payload = json.loads(sidecar.read_text())
    payload["training_spec"]["target"] = "hand_edited"
    sidecar.write_text(json.dumps(payload))
    with pytest.raises(ArtifactSpecRefusal) as exc:
        verify_artifact(
            artifact,
            expected_spec_hash=spec.spec_hash(),
            grandfathered_sha256s=frozenset(),
        )
    assert exc.value.reason == "sidecar_invalid"


def test_malformed_sidecar_json_refused(artifact):
    from src.dynasty_genius.models.artifact_verification import (
        ArtifactSpecRefusal,
        verify_artifact,
    )

    (artifact.parent / f"{artifact.name}.spec.json").write_text("{not json")
    with pytest.raises(ArtifactSpecRefusal) as exc:
        verify_artifact(
            artifact, expected_spec_hash=None, grandfathered_sha256s=frozenset()
        )
    assert exc.value.reason == "sidecar_invalid"


def test_no_sidecar_not_grandfathered_refused(artifact):
    from src.dynasty_genius.models.artifact_verification import (
        ArtifactSpecRefusal,
        verify_artifact,
    )

    with pytest.raises(ArtifactSpecRefusal) as exc:
        verify_artifact(
            artifact, expected_spec_hash=None, grandfathered_sha256s=frozenset()
        )
    assert exc.value.reason == "unverifiable_artifact"


def test_pinned_pointer_ignores_grandfathering(artifact):
    """Once a pointer pins a spec hash, only a verified sidecar satisfies it —
    a grandfathered content hash cannot answer for a pinned spec."""
    import hashlib

    from src.dynasty_genius.models.artifact_verification import (
        ArtifactSpecRefusal,
        verify_artifact,
    )

    content_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    with pytest.raises(ArtifactSpecRefusal) as exc:
        verify_artifact(
            artifact,
            expected_spec_hash=_make_spec().spec_hash(),
            grandfathered_sha256s=frozenset({content_sha}),
        )
    assert exc.value.reason == "unverifiable_artifact"


# ── Grandfathered pass-through ───────────────────────────────────────────────

def test_no_sidecar_grandfathered_passes_disclosed(artifact):
    import hashlib

    from src.dynasty_genius.models.artifact_verification import (
        STATE_PRE_SPEC,
        verify_artifact,
    )

    content_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    verdict = verify_artifact(
        artifact,
        expected_spec_hash=None,
        grandfathered_sha256s=frozenset({content_sha}),
    )
    assert verdict.state == STATE_PRE_SPEC
    assert verdict.spec_hash is None  # pre-spec artifacts have no spec, disclosed
    assert verdict.artifact_sha256 == content_sha


# ── The grandfather config itself ────────────────────────────────────────────

def test_grandfather_config_exists_and_loads():
    from src.dynasty_genius.models.artifact_verification import (
        load_pre_spec_grandfather,
    )

    shas = load_pre_spec_grandfather()
    assert isinstance(shas, frozenset)
    assert len(shas) >= 9  # the nine registered artifacts at freeze time
    assert all(len(s) == 64 for s in shas)


def test_grandfather_config_matches_model_registry():
    """Every registered deployed artifact is grandfathered under the exact
    sha256 the registry records — the allowlist cannot drift from deployment."""
    registry = json.loads(MODEL_REGISTRY.read_text())
    grandfather = json.loads(GRANDFATHER_CONFIG.read_text())
    gf_by_id = {a["artifact_id"]: a["sha256"] for a in grandfather["artifacts"]}
    for entry in registry["artifacts"]:
        assert entry["artifact_id"] in gf_by_id, entry["artifact_id"]
        assert gf_by_id[entry["artifact_id"]] == entry["sha256"], entry["artifact_id"]


def test_grandfather_config_is_frozen_schema():
    grandfather = json.loads(GRANDFATHER_CONFIG.read_text())
    assert grandfather["grandfather_schema_version"] == 1
    assert grandfather["frozen_date"]
    assert grandfather["ticket"] == "DG-057"
    for entry in grandfather["artifacts"]:
        assert set(entry) == {"artifact_id", "sha256", "source"}
        assert len(entry["sha256"]) == 64


def test_grandfather_list_is_frozen_byte_for_byte():
    """Pre-land review minor: the FROZEN contract was unenforced — a
    same-commit edit adding or swapping an entry would pass every test. The
    exact (artifact_id, sha256) set as measured 2026-08-28 is pinned here;
    growing or changing this list is a deliberate two-file diff forever."""
    import json
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    d = json.loads((repo_root / "app/config/pre_spec_grandfather.json").read_text())
    frozen = {
        ("engine_a:QB", "2e55c31e7609f5647a36246ac529c689668eaf9dcedfd736451fa29054fcb49a"),
        ("engine_a:RB", "3f390cb1de362ad79ae868cbe06b03a248a5e27472bbaf1f4240cabe58a5f99b"),
        ("engine_a:TE", "4a70aa48429c7355eb4dac48f45328da6be81ab81217e3871e553fcd1d1b76cc"),
        ("engine_a:WR", "bd51c69a522643593af7c7b4726b537c2c32690d851c76103f2373bb64b9444d"),
        ("engine_b:qb_v2", "d7acb6808e4a6caf412ec05b41aa90324e04f90ef219bbf78f680f66ea7d304f"),
        ("engine_b:rb_v2", "5507e37feda9ba9d8f2bda7f1f259df5a59edcb2880e7ff7af6938d34401c4f9"),
        ("engine_b:wr_v2", "3b83bbf98118d272196a0942a4190cc539b08409cbb3b23da570ed42b4ec873e"),
        ("engine_b:te_v3", "e8f5d7451aa0524aeb17dbc80992c35bfa97f9428366085330643bbb3109389b"),
        ("head_a:te_v3", "9e1b0b7fc7f707fba9831662fd792067f26e37370fb5aa5fd6532c02cf3e8618"),
        ("engine_b:v1_fallback", "5c52f811d7f9a4a78f564e822013ace7001275b6209063f9f4854577482c23d0"),
    }
    actual = {(a["artifact_id"], a["sha256"]) for a in d["artifacts"]}
    assert actual == frozen
    assert len(d["artifacts"]) == 10
    assert d["frozen_date"] == "2026-08-28"
