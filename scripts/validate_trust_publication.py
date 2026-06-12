"""Trust-surface publication audit (Model Trust Console substrate).

Fail-loud validators over the published trust substrate at
``app/data/backtest/trust_surface/latest/``. T1 audits the published
``BacktestResult`` artifacts + ``manifest.json``; T2 (added later) audits the
provenance-aligned model-card source. Read-only, descriptive,
``decision_supported``-absent/false: this validates a governed *published* substrate,
it does not compute or value anything.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.dynasty_genius.eval.backtest_artifact import BacktestResult

POSITIONS: tuple[str, ...] = ("QB", "RB", "WR", "TE")

# Curated-allowlist for the T1 phase: exactly the 4 published BacktestResult files
# + the provenance manifest. Anything else under the published path is a leak
# (e.g. broad runs/ contents). T2 extends this allowlist with the model-card sources.
T1_ALLOWED_FILES: frozenset[str] = frozenset(
    {f"backtest_result_{pos}.json" for pos in POSITIONS} | {"manifest.json"}
)

# T2 extends the allowlist with the 4 published model-card sources (9 files total).
T2_ALLOWED_FILES: frozenset[str] = frozenset(
    T1_ALLOWED_FILES | {f"model_card_source_{pos}.json" for pos in POSITIONS}
)

# The on-disk PublishedModelCardSource shape: the 8 public ModelCardResponse fields
# + 3 audit-internal provenance fields. Any other key is 9-section leakage.
_PUBLIC_CARD_FIELDS: frozenset[str] = frozenset(
    {
        "position",
        "backtest_run_id",
        "generated_at",
        "is_experimental",
        "intended_use",
        "out_of_scope_uses",
        "caveats",
        "known_failure_modes",
    }
)
_SOURCE_ALLOWED_FIELDS: frozenset[str] = frozenset(
    _PUBLIC_CARD_FIELDS | {"model_version", "model_artifact_hash", "git_sha"}
)

# Market-derived MODEL-INPUT leakage tokens. These are disallowed only on model
# feature surfaces (fold ``feature_coefficients`` keys, a ``model_feature_list``);
# legitimate market *comparison/provenance* fields (``market_source``,
# ``market_source_label``, ``market_snapshot_dates``, fold ``ndcg_at_*_market``)
# are NOT leakage and are never scanned here.
_MARKET_INPUT_TOKENS: tuple[str, ...] = ("market", "fantasycalc", "ktc", "adp", "ecr")


class TrustPublicationAuditError(RuntimeError):
    """Raised when the published trust substrate violates a publication invariant."""


def _is_market_input_token(name: str) -> bool:
    low = name.lower()
    return any(token in low for token in _MARKET_INPUT_TOKENS)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_substrate(
    root: Path,
    pinned_run_ids: dict[str, str],
    *,
    allowed_files: frozenset[str],
    check_model_cards: bool,
) -> dict[str, Any]:
    """Shared fail-loud validator for the published trust substrate (T1 and T2)."""
    # 1. allowlist (phase-scoped): any tracked file outside the allowlist is a leak.
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel not in allowed_files:
            raise TrustPublicationAuditError(
                f"unallowlisted file in published path: {rel}"
            )

    # 2. per-position artifacts: present, loadable, no decision-grade, no input leak.
    artifacts: dict[str, dict[str, Any]] = {}
    for pos in POSITIONS:
        artifact_path = root / f"backtest_result_{pos}.json"
        if not artifact_path.is_file():
            raise TrustPublicationAuditError(
                f"missing published artifact for {pos}: {artifact_path.name}"
            )
        # Schema validation (hard stop): the artifact must load as a `BacktestResult`.
        # Catches both corrupt JSON and JSON-valid-but-schema-invalid files (e.g. a
        # missing `promotion_gate`), not just unparseable JSON.
        try:
            BacktestResult.load(artifact_path)
        except (ValidationError, ValueError, OSError) as exc:
            raise TrustPublicationAuditError(
                f"cannot load published artifact for {pos}: {exc}"
            ) from exc
        # Raw scan for decision-grade + market-input extras (fields not on the typed
        # model, so they survive `BacktestResult.load` and must be checked on the JSON).
        artifact = _load_json(artifact_path)

        if artifact.get("decision_supported") is True:
            raise TrustPublicationAuditError(
                f"decision_supported=True in published artifact for {pos}"
            )

        for fold in artifact.get("folds") or []:
            for key in (fold.get("feature_coefficients") or {}):
                if _is_market_input_token(key):
                    raise TrustPublicationAuditError(
                        f"market-derived model input leak in {pos} "
                        f"feature_coefficients: {key}"
                    )
        for entry in artifact.get("model_feature_list") or []:
            if isinstance(entry, str) and _is_market_input_token(entry):
                raise TrustPublicationAuditError(
                    f"market-derived model input leak in {pos} "
                    f"model_feature_list: {entry}"
                )
        artifacts[pos] = artifact

    # 3. manifest: present, pinned run_ids match, no decision-grade.
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise TrustPublicationAuditError("missing publication manifest.json")
    try:
        manifest = _load_json(manifest_path)
    except (json.JSONDecodeError, OSError) as exc:
        raise TrustPublicationAuditError(
            f"cannot load publication manifest.json: {exc}"
        ) from exc

    manifest_positions = manifest.get("positions") or {}
    for pos in POSITIONS:
        meta = manifest_positions.get(pos) or {}
        if str(meta.get("run_id")) != str(pinned_run_ids.get(pos)):
            raise TrustPublicationAuditError(
                f"pinned run_id mismatch for {pos}: manifest run_id "
                f"{meta.get('run_id')!r} != pinned {pinned_run_ids.get(pos)!r}"
            )
        if meta.get("decision_supported") is True:
            raise TrustPublicationAuditError(
                f"decision_supported=True in manifest for {pos}"
            )

    # 4. (T2) per-position model-card sources: provenance-aligned + curated-only.
    if check_model_cards:
        for pos in POSITIONS:
            source_path = root / f"model_card_source_{pos}.json"
            if not source_path.is_file():
                raise TrustPublicationAuditError(
                    f"missing model card source for {pos}: {source_path.name}"
                )
            source = _load_json(source_path)
            # Decision-grade first (so the error names the field before curated-only).
            if source.get("decision_supported") is True:
                raise TrustPublicationAuditError(
                    f"decision_supported=True in model card source for {pos}"
                )
            # Key-set completeness: every required field must be present — a missing
            # field would runtime-KeyError the route's curated filter.
            missing = sorted(_SOURCE_ALLOWED_FIELDS - set(source))
            if missing:
                raise TrustPublicationAuditError(
                    f"missing required field(s) {missing} in model card source for {pos}"
                )
            # Curated-only: no 9-section leakage on the published source.
            for key in source:
                if key not in _SOURCE_ALLOWED_FIELDS:
                    raise TrustPublicationAuditError(
                        f"curated-only violation: model card source for {pos} "
                        f"carries non-curated key {key!r} (9-section leakage)"
                    )
            # Provenance equality vs the published BacktestResult for the position.
            artifact = artifacts[pos]
            provenance = {
                "position": (source.get("position"), pos),
                "backtest_run_id": (
                    str(source.get("backtest_run_id")),
                    str(artifact["run_id"]),
                ),
                "model_version": (
                    source.get("model_version"),
                    artifact["model_version"],
                ),
                "model_artifact_hash": (
                    source.get("model_artifact_hash"),
                    artifact["model_artifact_hash"],
                ),
                "git_sha": (source.get("git_sha"), artifact.get("git_sha")),
            }
            for field, (got, expected) in provenance.items():
                if got != expected:
                    raise TrustPublicationAuditError(
                        f"{field} mismatch for {pos}: model card source {got!r} "
                        f"!= published {expected!r}"
                    )

    return {
        "status": "pass",
        "positions": list(POSITIONS),
        "allowed_files": sorted(allowed_files),
    }


def validate_trust_publication_t1(
    root: Path | str,
    *,
    pinned_run_ids: dict[str, str],
) -> dict[str, Any]:
    """Validate the T1 substrate (4 BacktestResult + manifest). Raises on violation."""
    return _validate_substrate(
        Path(root),
        pinned_run_ids,
        allowed_files=T1_ALLOWED_FILES,
        check_model_cards=False,
    )


def validate_trust_publication_t2(
    root: Path | str,
    *,
    pinned_run_ids: dict[str, str],
) -> dict[str, Any]:
    """Validate the T2 substrate (T1 + 4 provenance-aligned model-card sources)."""
    return _validate_substrate(
        Path(root),
        pinned_run_ids,
        allowed_files=T2_ALLOWED_FILES,
        check_model_cards=True,
    )
