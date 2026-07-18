"""QB-1 fail-closed guards: output path, No-Verdict scan, dataset/manifest shape.

Spec rows implemented here (v8, SHA 8fa244c1…):
- F24 ``validate_output_path`` — artifacts land ONLY under the governed study
  root; arg/env overrides are refused (``output_path_violation``).
- F9/F26 ``scan_banned_language`` — recursive ``decision_supported=False`` and
  banned-lexicon enforcement over serialized output INCLUDING field names (the
  round-2 lesson: a field literally named "verdict" fails its own scan).
- F14 ``validate_dataset_shape`` — wrong-type / missing-column / empty frames
  fail closed with a named reason per shape class; no partial parse.
- F15 ``validate_manifest_columns`` — an absent pinned manifest column fails the
  build (``manifest_column_missing``); never a silent substitute.
- F19 ``validate_as_of_dates`` — per-lane as-of law: model features ≤ end-t−1,
  market snapshots ≤ the registered kickoff-t comparison date.
- F26 ``validate_report_output`` — the report passes the No-Verdict scan and is
  returned byte-identical: deltas stay unclamped, negatives stay raw.

Signatures follow the Codex behavioral RED (the reviewer's contract stands per
the 2026-07-16 20:23 reconciliation ruling): frame-first positionals with
``dataset``/``required`` keywords, and ``validate_output_path`` deriving the
repo root itself.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure

# The one governed output root (spec D5/F24/F31). Relative to the repo root.
OUTPUT_ROOT = Path("app") / "data" / "backtest" / "qb_validation"

# guards.py → qb_validation → eval → dynasty_genius → src → repo root.
_REPO_ROOT = Path(__file__).resolve().parents[4]

# No-Verdict lexicon (constitution: descriptive tools issue no verdicts).
# Word-boundary, case-insensitive; scanned over keys AND string values.
_BANNED_TERMS = (
    "buy",
    "sell",
    "hold",
    "verdict",
    "recommended",
    "recommendation",
    "safe to",
    "must buy",
    "must sell",
    "keep",
    "cut",
)
_BANNED_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(term) for term in _BANNED_TERMS) + r")\b",
    re.IGNORECASE,
)


def validate_output_path(candidate: Path | str, repo_root: Path | None = None) -> Path:
    """Resolve ``candidate`` and refuse anything outside the governed root (F24)."""
    allowed = (Path(repo_root) if repo_root is not None else _REPO_ROOT) / OUTPUT_ROOT
    allowed = allowed.resolve()
    resolved = Path(candidate).resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise QBValidationFailure(
            "output_path_violation",
            f"{resolved} is outside the governed study root {allowed}",
        )
    return resolved


def _walk(payload: Any, path: str) -> Iterable[tuple[str, Any]]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield f"{path}.{key}" if path else str(key), key
            yield from _walk(value, f"{path}.{key}" if path else str(key))
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            yield from _walk(value, f"{path}[{index}]")
    else:
        yield path, payload


def scan_banned_language(payload: dict[str, Any]) -> None:
    """Enforce the No-Verdict Line mechanically over a report payload (F9/F26).

    Refusals (all named, all fail-closed):
    - ``decision_supported_missing`` — the root lacks the field;
    - ``decision_supported_not_false`` — the root, or ANY nested mapping that
      carries the field, has anything but exactly ``False``;
    - ``banned_language`` — a banned lexicon term appears in any key or string
      value (field NAMES are scanned too).
    """
    if not isinstance(payload, dict):
        raise QBValidationFailure(
            "report_not_a_mapping", f"payload is {type(payload).__name__}"
        )
    if "decision_supported" not in payload:
        raise QBValidationFailure(
            "decision_supported_missing", "root payload lacks decision_supported"
        )

    violations: list[str] = []
    missing_on_model: list[str] = []

    def _check_ds(node: Any, path: str, is_model: bool) -> None:
        if isinstance(node, dict):
            if "decision_supported" in node and node["decision_supported"] is not False:
                violations.append(
                    f"decision_supported at {path or 'root'} is "
                    f"{node['decision_supported']!r}, not False"
                )
            elif is_model and "decision_supported" not in node:
                # D5: the flag is required on the root AND every nested model.
                # Mechanically, a nested model is any mapping that is a LIST
                # element (folds[], comparisons[], case_panel[] rows); plain
                # sub-mappings (metadata, ci95, audit fields) are not models.
                missing_on_model.append(path or "root")
            for key, value in node.items():
                _check_ds(value, f"{path}.{key}" if path else str(key), False)
        elif isinstance(node, (list, tuple)):
            for index, value in enumerate(node):
                _check_ds(value, f"{path}[{index}]", True)

    _check_ds(payload, "", False)
    if violations:
        raise QBValidationFailure("decision_supported_not_false", "; ".join(violations))
    if missing_on_model:
        raise QBValidationFailure(
            "decision_supported_missing_on_model",
            "nested models lack decision_supported: " + "; ".join(missing_on_model),
        )

    for location, value in _walk(payload, ""):
        if isinstance(value, str) and _BANNED_PATTERN.search(value):
            raise QBValidationFailure(
                "banned_language",
                f"banned term in {location or 'root'}: {value!r}",
            )


def validate_dataset_shape(
    frame: Any, required_columns: Iterable[str] = (), *, dataset: str = "dataset"
) -> None:
    """Fail closed on malformed adapter output, one named reason per class (F14)."""
    columns = getattr(frame, "columns", None)
    if columns is None:
        raise QBValidationFailure(
            "wrong_type_frame",
            f"{dataset}: expected a dataframe, got {type(frame).__name__}",
        )
    missing = [column for column in required_columns if column not in list(columns)]
    if missing:
        raise QBValidationFailure(
            "missing_required_column", f"{dataset}: {', '.join(missing)}"
        )
    if len(frame) == 0:
        raise QBValidationFailure("empty_frame", f"{dataset}: zero rows")


def _available_columns(source: Any) -> set[str]:
    """Column names from a dataframe, a mapping, or a plain iterable of names."""
    columns = getattr(source, "columns", None)
    if columns is not None:
        return {str(column) for column in list(columns)}
    if isinstance(source, Mapping):
        return {str(key) for key in source.keys()}
    return {str(item) for item in source}


def validate_manifest_columns(
    frame: Any, required: Iterable[str], *, dataset: str = "dataset"
) -> None:
    """An absent pinned manifest column fails the build — never substitute (F15)."""
    available = _available_columns(frame)
    absent = [column for column in required if column not in available]
    if absent:
        raise QBValidationFailure(
            "manifest_column_missing", f"{dataset}: {', '.join(absent)}"
        )


def _parse_iso_date(value: Any, field: str) -> date:
    # datetime IS a date subclass — normalize it first, or a datetime/date mix
    # later raises a raw TypeError on comparison (the H1 wrong-type row).
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise QBValidationFailure(
            "as_of_date_unparseable", f"{field}: {value!r}"
        ) from exc


def validate_as_of_dates(
    *,
    model_feature_date: str | date,
    model_cutoff: str | date,
    market_date: str | date,
    market_cutoff: str | date,
) -> None:
    """Per-lane as-of enforcement (F19); a date ON the cutoff is legal, after is not.

    Model lane: features strictly from seasons ≤ t−1, so every feature date must
    be on/before the end-of-t−1 cutoff. H5 market lane: the snapshot must be
    on/before the registered kickoff-t comparison date (the after-date ban).
    """
    feature = _parse_iso_date(model_feature_date, "model_feature_date")
    feature_cutoff = _parse_iso_date(model_cutoff, "model_cutoff")
    market = _parse_iso_date(market_date, "market_date")
    market_bound = _parse_iso_date(market_cutoff, "market_cutoff")
    violations: list[str] = []
    if feature > feature_cutoff:
        violations.append(
            f"model lane: feature date {feature.isoformat()} is after the "
            f"end-t-1 cutoff {feature_cutoff.isoformat()}"
        )
    if market > market_bound:
        violations.append(
            f"market lane: snapshot {market.isoformat()} is after the registered "
            f"comparison date {market_bound.isoformat()}"
        )
    if violations:
        raise QBValidationFailure("as_of_violation", "; ".join(violations))


def validate_report_output(report: dict[str, Any]) -> dict[str, Any]:
    """No-Verdict-validate a report and return it UNTOUCHED (F26).

    The scan enforces recursive ``decision_supported=False`` and the banned
    lexicon. The report object itself is returned as-is — never a normalized or
    clamped copy, so raw negative deltas survive by construction.
    """
    scan_banned_language(report)
    return report
