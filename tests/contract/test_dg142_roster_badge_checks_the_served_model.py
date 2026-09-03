"""DG-142 RED: the roster badge must check the model that is serving, not a version string.

``load_model_status_by_position`` guarded freshness with
``result.model_version != manifest[pos]``. Both sides are the generic string
``"engine_b_v2"`` on all four positions, so that branch was unreachable by
construction: the badge could not notice that the deployed ``.pkl`` had been
replaced. Live on 2026-09-03 the roster page said RB, TE and WR "passed its
accuracy checks" from artifacts measured 2026-05-31, against bundles written
2026-08-31 16:44:58 — four hash mismatches, no caveat, ``status: "active"``.

The correct guard already existed (``eval/served_model_alignment.check_served_alignment``:
it sha256s the deployed bundle and compares to the artifact's recorded
``model_artifact_hash``) and was wired into only one of the two consumers.

These tests pin the guard into the second consumer, and they are written to stay
true AFTER the backtests are re-run against the served bundles — none of them
hardcodes today's four-way failure. The invariant is: a position is proven if and
only if the published figures describe the binary that is answering.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.api.routes import roster_audit_models as ram
from src.dynasty_genius.eval import served_model_alignment as sma

REAL = Path("app/data/backtest/trust_surface/latest")
MANIFEST = Path("app/data/models/engine_b/v2_manifest.json")
POSITIONS = ("QB", "RB", "WR", "TE")


def _served_hash(position: str) -> str:
    """sha256 of the bundle actually deployed for ``position``.

    The manifest and the .pkl bundles are gitignored, so this is unavailable in a
    fresh clone or a tree the land gate builds elsewhere. Skip there rather than
    erroring — a test that hard-fails off one laptop stops being evidence.
    """
    if not MANIFEST.is_file():
        pytest.skip(
            "engine_b v2 manifest is local-only (gitignored); absent in this tree"
        )
    bundle = Path(json.loads(MANIFEST.read_text())[position])
    if not bundle.is_file():
        pytest.skip(
            f"the deployed bundle for {position} is local-only; absent in this tree"
        )
    return hashlib.sha256(bundle.read_bytes()).hexdigest()


def _trust_dir(tmp_path: Path, position: str, artifact_hash: str) -> Path:
    """A copy of the live trust tree with ONE position's recorded model identity set.

    ``model_version`` is left matching the manifest, so the old string comparison
    clears it — the only thing that can refuse it is the served-bytes check.
    """
    d = tmp_path / "trust"
    shutil.copytree(REAL, d)
    path = d / f"backtest_result_{position}.json"
    artifact = json.loads(path.read_text())
    artifact["model_artifact_hash"] = artifact_hash
    path.write_text(json.dumps(artifact))
    manifest = json.loads((d / "manifest.json").read_text())
    assert (
        manifest["positions"][position]["model_version"] == artifact["model_version"]
    ), (
        "fixture precondition: the version strings must MATCH, so that only the "
        "served-bytes check can refuse this position"
    )
    return d


# ── the defect itself ────────────────────────────────────────────────────────────────


def test_a_replaced_binary_is_refused_even_though_the_version_strings_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact live shape: same `engine_b_v2` on both sides, different bytes."""
    d = _trust_dir(tmp_path, "WR", "0" * 64)
    monkeypatch.setattr(ram, "TRUST_DIR", d)

    status, caveats = ram.load_model_status_by_position(["WR"])

    assert status["WR"] == "EXPERIMENTAL"
    assert "trust_status_stale" in caveats


def test_an_artifact_measured_on_the_served_bytes_keeps_its_earned_badge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other half of the invariant — this is what the re-run will produce.

    No mocking: the recorded hash really is the sha256 of the deployed bundle, so
    the real guard returns aligned=True and the artifact's own status stands.
    """
    d = _trust_dir(tmp_path, "WR", _served_hash("WR"))
    monkeypatch.setattr(ram, "TRUST_DIR", d)

    published = json.loads((d / "backtest_result_WR.json").read_text())
    earned = published["promotion_gate"]["model_status"]

    status, caveats = ram.load_model_status_by_position(["WR"])

    assert status["WR"] == earned
    assert "trust_status_stale" not in caveats


def test_the_badge_is_not_proven_if_and_only_if_the_served_model_disagrees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Against the LIVE tree, whatever state it is in — true before and after a re-run.

    This is deliberately not "all four are EXPERIMENTAL today": that would fail the
    moment the backtests are re-run, which is the outcome this ticket is meant to
    enable rather than block.
    """
    monkeypatch.setattr(ram, "TRUST_DIR", REAL)
    status, _ = ram.load_model_status_by_position(list(POSITIONS))

    for pos in POSITIONS:
        artifact = json.loads((REAL / f"backtest_result_{pos}.json").read_text())
        aligned = sma.check_served_alignment(
            pos, artifact["model_artifact_hash"]
        ).aligned
        earned = artifact["promotion_gate"]["model_status"]
        assert status[pos] == (earned if aligned else "EXPERIMENTAL"), (
            f"{pos}: aligned={aligned} but badge reads {status[pos]}"
        )


# ── fail-closed on every way the check can come back unhappy ─────────────────────────


@pytest.mark.parametrize(
    ("published", "served", "expected_caveat"),
    [
        pytest.param(
            "a" * 64, "b" * 64, "trust_status_stale", id="compared_and_they_differ"
        ),
        pytest.param(
            None, None, "trust_status_unavailable", id="artifact_records_no_identity"
        ),
        pytest.param(
            "a" * 64, None, "trust_status_unavailable", id="manifest_unreadable"
        ),
        pytest.param(
            "a" * 64, None, "trust_status_unavailable", id="no_model_deployed"
        ),
        pytest.param(
            "a" * 64, None, "trust_status_unavailable", id="bundle_unreadable"
        ),
    ],
)
def test_every_unaligned_answer_refuses_and_names_the_cause_it_established(
    published: str | None,
    served: str | None,
    expected_caveat: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refusal is unconditional; only the CAVEAT depends on what could be read.

    Claiming "measured on a different build" when the manifest was simply unreadable
    would repeat this ticket's own defect — asserting a cause nothing established.
    """
    monkeypatch.setattr(ram, "TRUST_DIR", REAL)
    monkeypatch.setattr(
        ram,
        "check_served_alignment",
        lambda position, published_hash: sma.ServedModelAlignment(
            position=position,
            aligned=False,
            reason="irrelevant — the consumer must not read this",
            published_hash=published,
            served_hash=served,
        ),
    )

    status, caveats = ram.load_model_status_by_position(["RB"])

    assert status["RB"] == "EXPERIMENTAL"
    assert expected_caveat in caveats


def test_an_exception_from_the_alignment_check_still_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The guard is documented never to raise. If it ever does, refuse rather than pass."""

    def boom(position, published_hash):
        raise RuntimeError("unreadable")

    monkeypatch.setattr(ram, "TRUST_DIR", REAL)
    monkeypatch.setattr(ram, "check_served_alignment", boom)

    status, caveats = ram.load_model_status_by_position(["TE"])

    assert status["TE"] == "EXPERIMENTAL"
    assert caveats  # named, never silent


def test_the_guard_is_actually_consulted_not_reimplemented() -> None:
    """One module owns 'do these figures describe the served model'.

    A second hand-rolled comparison in this file is how the two consumers drifted
    apart in the first place.
    """
    source = Path(ram.__file__).read_text()
    assert "check_served_alignment" in source
    assert "from src.dynasty_genius.eval.served_model_alignment import" in source
    assert "hashlib" not in source, "the consumer must not hash bundles itself"


# ── the product consequence, pinned ───────────────────────────────────────────────────


def test_the_stale_token_is_renderable_without_any_new_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DG-142 adds no copy: the token it emits must already be in the allowlist."""
    d = _trust_dir(tmp_path, "WR", "0" * 64)
    monkeypatch.setattr(ram, "TRUST_DIR", d)

    _, caveats = ram.load_model_status_by_position(["WR"])

    assert "trust_status_stale" in caveats
    for token in ("trust_status_stale", "trust_status_unavailable"):
        assert token in ram.SAFE_TOKENS, f"{token} must already be renderable"


def _clean_audit() -> dict:
    """A roster payload with nothing wrong with it: no dropped rows, no bad QB card.

    Any `degraded` this yields can only have come from the trust caveat.
    """
    return {
        "status": "active",
        "engine": "pvo_assembler_v1",
        "reason": "ok",
        "caveats": [],
        "players": [
            {
                "player_id": "p",
                "full_name": "WR",
                "position": "WR",
                "engine_used": "engine_b",
                "model_grade": "ACTIVE_B",
                "counter_argument": "solid floor",
                "top_drivers": ["target_share"],
                "risk_flags": [],
                "caveats": [],
                "roster_audit": {
                    "signal": "at_cliff",
                    "signal_drivers": [],
                    "decision_supported": True,
                },
            }
        ],
        "qb_context_cards": [],
    }


def test_an_unproven_badge_degrades_the_whole_roster_read_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The caveat → degraded step, through the real assembler.

    This is the step David actually sees ("Heads up: this roster read came back
    degraded"). Before this test, deleting `if trust_caveats: status = "degraded"`
    left the ENTIRE suite green — a silent path back to "active" over four
    unproven badges, which is a quieter version of the defect this ticket fixes.
    """
    monkeypatch.setattr(ram, "TRUST_DIR", _trust_dir(tmp_path, "WR", "0" * 64))

    response = ram.assemble_response(_clean_audit())

    assert response.status == "degraded"
    assert "trust_status_stale" in response.caveats
    assert response.dropped_player_count == 0, (
        "the degrade must come from trust, not a drop"
    )


def test_a_proven_badge_leaves_the_roster_read_active_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other direction — otherwise the test above passes on any always-degrade bug.

    This is also the state the trust re-publication is meant to restore.
    """
    monkeypatch.setattr(
        ram, "TRUST_DIR", _trust_dir(tmp_path, "WR", _served_hash("WR"))
    )

    response = ram.assemble_response(_clean_audit())

    assert response.status == "active"
    assert "trust_status_stale" not in response.caveats
