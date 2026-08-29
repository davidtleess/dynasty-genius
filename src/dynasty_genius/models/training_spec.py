"""TrainingSpec — the one hashed training specification (§8.2, DG-057).

Master Proposal 3 §8.2: a single ``TrainingSpec`` is the sole definition of
what a model was trained on and how — feature set/version, target and label
horizon, cohort filter, preprocessing and missing-data policy, estimator
family, tuning policy, time-split/grouping policy, evaluation baselines, and
calibration method. Training, evaluation, final refit, and serving
compatibility all consume this spec, and its hash is embedded in every
candidate and final artifact so serving can refuse an incompatible one.

Hash contract:
- ``spec_hash()`` is the sha256 hex digest of the spec's canonical JSON —
  sorted keys, no insignificant whitespace, ASCII-only, NaN forbidden — so
  the same spec always hashes identically regardless of dict insertion order
  or formatting. Bare hex, matching the style of ``model_registry.json``.
- Any semantic field change (including ``spec_schema_version``) changes the
  hash. There is no way to mutate a spec in place; build a new one.

The CURRENTLY deployed artifacts predate this spec and are grandfathered via
``app/config/pre_spec_grandfather.json`` (see
``src/dynasty_genius/models/artifact_verification.py``); they have no
TrainingSpec and never will. Every artifact trained after this module landed
must be spec-hashed at training time.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from typing import Any, Mapping

__all__ = ["TrainingSpec"]


@dataclass(frozen=True)
class TrainingSpec:
    """The nine §8.2 clauses plus identity and schema version.

    Field values must be JSON-serializable (str / int / float / bool / None,
    plus dicts, lists and tuples of the same) — ``spec_hash()`` raises
    ``TypeError`` otherwise. Tuples serialize as JSON lists.
    """

    # Identity — which model family this spec governs.
    engine: str
    model_id: str

    # §8.2 clause 1: feature set and version.
    feature_set: tuple[str, ...]
    feature_set_version: str

    # §8.2 clause 2: target definition and label horizon.
    target: str
    label_horizon: str

    # §8.2 clause 3: eligibility/cohort filter.
    cohort_filter: str

    # §8.2 clause 4: preprocessing and missing-data policy.
    preprocessing: Mapping[str, Any]

    # §8.2 clause 5: estimator family.
    estimator_family: str

    # §8.2 clause 6: hyperparameter/tuning policy.
    tuning_policy: Mapping[str, Any]

    # §8.2 clause 7: time-split and grouping policy.
    time_split: Mapping[str, Any]

    # §8.2 clause 8: evaluation baselines.
    evaluation_baselines: tuple[str, ...]

    # §8.2 clause 9: calibration method.
    calibration_method: str

    # Schema version of the TrainingSpec object itself.
    spec_schema_version: int = 1

    def __post_init__(self) -> None:
        # Normalize list-typed inputs to tuples so equal specs compare equal
        # and the dataclass stays effectively immutable.
        object.__setattr__(self, "feature_set", tuple(self.feature_set))
        object.__setattr__(
            self, "evaluation_baselines", tuple(self.evaluation_baselines)
        )

    # ── Serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-able dict (tuples become lists)."""
        return {
            "engine": self.engine,
            "model_id": self.model_id,
            "feature_set": list(self.feature_set),
            "feature_set_version": self.feature_set_version,
            "target": self.target,
            "label_horizon": self.label_horizon,
            "cohort_filter": self.cohort_filter,
            "preprocessing": dict(self.preprocessing),
            "estimator_family": self.estimator_family,
            "tuning_policy": dict(self.tuning_policy),
            "time_split": dict(self.time_split),
            "evaluation_baselines": list(self.evaluation_baselines),
            "calibration_method": self.calibration_method,
            "spec_schema_version": self.spec_schema_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TrainingSpec":
        """Rebuild a spec from ``to_dict()`` output (e.g. a sidecar file).

        Refuses missing or unknown fields loudly: a spec that does not
        round-trip exactly must never hash quietly to something else.
        """
        field_names = {f.name for f in fields(cls)}
        missing = sorted(field_names - set(data))
        if missing:
            raise ValueError(f"TrainingSpec missing required fields: {missing}")
        unknown = sorted(set(data) - field_names)
        if unknown:
            raise ValueError(f"TrainingSpec has unknown fields: {unknown}")
        return cls(**{name: data[name] for name in field_names})

    # ── Hashing ──────────────────────────────────────────────────────────────

    def to_canonical_json(self) -> str:
        """Deterministic JSON: sorted keys, compact separators, ASCII, no NaN."""
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )

    def spec_hash(self) -> str:
        """sha256 hex digest of the canonical JSON. Bare hex, 64 chars."""
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()
