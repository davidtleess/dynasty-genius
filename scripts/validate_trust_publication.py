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


def validate_trust_publication_t1(
    root: Path | str,
    *,
    pinned_run_ids: dict[str, str],
) -> dict[str, Any]:
    """Validate the T1 published trust substrate. Raises on any violation.

    Checks (fail-loud):
      1. allowlist — no file under ``root`` outside ``T1_ALLOWED_FILES``;
      2. presence + loadability of each position's ``backtest_result_{POS}.json``;
      3. ``decision_supported`` is not True on any artifact or manifest entry;
      4. no market-derived model-INPUT leakage on model feature surfaces;
      5. manifest ``run_id`` per position equals the pinned input.
    Returns ``{"status": "pass", "positions": [...], "allowed_files": [...]}``.
    """
    root = Path(root)

    # 1. allowlist (phase-scoped): any tracked file outside the T1 allowlist is a leak.
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel not in T1_ALLOWED_FILES:
            raise TrustPublicationAuditError(
                f"unallowlisted file in published path: {rel}"
            )

    # 2. per-position artifacts: present, loadable, no decision-grade, no input leak.
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

    return {
        "status": "pass",
        "positions": list(POSITIONS),
        "allowed_files": sorted(T1_ALLOWED_FILES),
    }
