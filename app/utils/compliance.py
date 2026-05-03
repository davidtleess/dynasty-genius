from __future__ import annotations

import os

RANK_1_GROUND_TRUTH = 1
RANK_2_VALIDATED_ANALYST = 2
RANK_3_MARKET_SIGNAL = 3
PASSING_QUANTITATIVE_RATIO = 65.0
MLFLOW_ENABLED_ENV = "DYNASTY_MLFLOW_TRACKING_ENABLED"
MLFLOW_EXPERIMENT_ENV = "DYNASTY_MLFLOW_EXPERIMENT"


def _weight(item: dict) -> float:
    value = item.get("weight", 1.0)
    return max(float(value), 0.0)


def _is_quantitative(item: dict) -> bool:
    value = item.get("kind", item.get("type", "quantitative"))
    return str(value).lower() in {"quant", "quantitative", "metric"}


def _source_rank(item: dict) -> int | None:
    value = item.get("source_rank")
    if value is None:
        return None
    return int(value)


def calculate_compliance_ratio(metrics: list[dict], notes: list[dict] | list[str]) -> str:
    weighted_items: list[dict] = [*metrics]
    for note in notes:
        if isinstance(note, dict):
            weighted_items.append(note)
        else:
            weighted_items.append(
                {
                    "name": str(note),
                    "kind": "qualitative",
                    "source_rank": RANK_2_VALIDATED_ANALYST,
                    "weight": 1.0,
                }
            )

    total_weight = sum(_weight(item) for item in weighted_items)
    if total_weight <= 0:
        return "Compliance: 0% / 0% (FAIL)"

    passing_quant_weight = sum(
        _weight(item)
        for item in weighted_items
        if _is_quantitative(item)
        and _source_rank(item) in {RANK_1_GROUND_TRUTH, RANK_2_VALIDATED_ANALYST}
    )
    qualitative_weight = sum(
        _weight(item)
        for item in weighted_items
        if not _is_quantitative(item)
    )

    quant_pct = round((passing_quant_weight / total_weight) * 100)
    qual_pct = round((qualitative_weight / total_weight) * 100)
    status = "PASS" if quant_pct >= PASSING_QUANTITATIVE_RATIO else "FAIL"
    compliance_header = f"Compliance: {quant_pct}% / {qual_pct}% ({status})"
    log_valuation_run(
        compliance_ratio=quant_pct,
        source_rank=min(
            (_source_rank(item) for item in weighted_items if _source_rank(item) is not None),
            default=RANK_3_MARKET_SIGNAL,
        ),
        compliance_header=compliance_header,
    )
    return compliance_header


def log_valuation_run(
    *,
    compliance_ratio: int,
    source_rank: int,
    compliance_header: str,
) -> None:
    if os.getenv(MLFLOW_ENABLED_ENV) != "1":
        return

    try:
        import mlflow
    except ImportError as exc:
        raise RuntimeError("MLflow tracking requested but mlflow is not installed") from exc

    experiment_name = os.getenv(MLFLOW_EXPERIMENT_ENV, "dynasty-genius-valuations")
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name="valuation_compliance"):
        mlflow.log_param("compliance_ratio", compliance_ratio)
        mlflow.log_param("source_rank", source_rank)
        mlflow.log_param("compliance_header", compliance_header)
