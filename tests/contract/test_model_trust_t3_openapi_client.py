from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_SNAPSHOT = REPO_ROOT / "frontend" / "openapi.json"
TYPES_GEN = REPO_ROOT / "frontend" / "src" / "lib" / "api" / "types.gen.ts"
ZOD_GEN = REPO_ROOT / "frontend" / "src" / "lib" / "api" / "zod.gen.ts"

PUBLIC_MODEL_CARD_FIELDS = {
    "position",
    "backtest_run_id",
    "generated_at",
    "is_experimental",
    "intended_use",
    "out_of_scope_uses",
    "caveats",
    "known_failure_modes",
}

FORBIDDEN_PUBLIC_KEYS = {
    "model_version",
    "model_artifact_hash",
    "git_sha",
    "metrics",
    "feature_list",
    "subgroup_results",
    "calibration",
    "ethical_considerations",
}


def _model_card_response_block(text: str) -> str:
    match = re.search(
        r"export type GetModelCardApiTrustSurfacePositionModelCardGetResponses = "
        r"\{(?P<body>.*?)\n\};",
        text,
        re.S,
    )
    assert match, "model-card generated response type block is missing"
    return match.group("body")


def test_openapi_snapshot_defines_curated_model_card_response() -> None:
    snapshot = json.loads(OPENAPI_SNAPSHOT.read_text(encoding="utf-8"))
    components = snapshot["components"]["schemas"]

    assert "ModelCardResponse" in components
    schema = components["ModelCardResponse"]
    assert set(schema["properties"]) == PUBLIC_MODEL_CARD_FIELDS
    assert set(schema["required"]) == PUBLIC_MODEL_CARD_FIELDS
    assert FORBIDDEN_PUBLIC_KEYS.isdisjoint(schema["properties"])

    route_schema = snapshot["paths"]["/api/trust-surface/{position}/model-card"][
        "get"
    ]["responses"]["200"]["content"]["application/json"]["schema"]
    assert route_schema == {"$ref": "#/components/schemas/ModelCardResponse"}


def test_generated_client_uses_typed_model_card_response_not_record_unknown() -> None:
    types_text = TYPES_GEN.read_text(encoding="utf-8")
    zod_text = ZOD_GEN.read_text(encoding="utf-8")

    assert "export type ModelCardResponse = {" in types_text
    assert "export const zModelCardResponse = z.object({" in zod_text

    response_block = _model_card_response_block(types_text)
    assert "200: ModelCardResponse;" in response_block
    assert "[key: string]: unknown" not in response_block

    assert (
        "export const zGetModelCardApiTrustSurfacePositionModelCardGetResponse = "
        "zModelCardResponse;"
    ) in zod_text
    assert (
        "zGetModelCardApiTrustSurfacePositionModelCardGetResponse = "
        "z.record(z.string(), z.unknown())"
    ) not in zod_text
