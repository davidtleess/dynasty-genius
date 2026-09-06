"""Affirmative pairing of the scored file, the evaluation and the manifest (round-2 review,
item 4). A consumer must be able to prove — from identifiers and hashes, never from prose —
that the evaluation it grades describes the model that produced the scored file. Any
disagreement raises; a passing check returns a block the manifest carries verbatim."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

__all__ = ["sha256_file", "verify_pairing"]


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_pairing(*, manifest: dict, evaluation: dict, scores: pd.DataFrame, evaluation_sha256: str) -> dict:
    """Raise ValueError on any mismatch; return the consistent pairing block otherwise."""
    policy = manifest.get("model_policy")
    if not policy:
        raise ValueError("manifest carries no model_policy")
    if evaluation.get("policy_id") != policy:
        raise ValueError(f"policy mismatch: manifest {policy!r} vs evaluation {evaluation.get('policy_id')!r}")
    if "model_policy" not in scores or not (scores["model_policy"] == policy).all():
        raise ValueError(f"policy mismatch: scored rows do not all carry model_policy {policy!r}")
    if "evaluation_sha256" not in scores or not (scores["evaluation_sha256"] == evaluation_sha256).all():
        raise ValueError("evaluation sha256 mismatch: scored rows do not carry the canonical evaluation's hash")
    arm = manifest.get("scoring_arm_id")
    if not arm:
        raise ValueError("manifest carries no scoring_arm_id")
    if arm not in set(evaluation.get("arm_ids", [])):
        raise ValueError(f"arm mismatch: scoring arm {arm!r} is not among the evaluation's arms {evaluation.get('arm_ids')}")
    if "scoring_arm_id" not in scores or not (scores["scoring_arm_id"] == arm).all():
        raise ValueError(f"arm mismatch: scored rows do not all carry scoring_arm_id {arm!r}")
    return {"status": "consistent", "model_policy": policy, "scoring_arm_id": arm, "evaluation_sha256": evaluation_sha256,
            "checked": ["manifest.model_policy == evaluation.policy_id == scores.model_policy",
                        "manifest.scoring_arm_id in evaluation.arm_ids and == scores.scoring_arm_id",
                        "scores.evaluation_sha256 == sha256(evaluation.json)"]}
