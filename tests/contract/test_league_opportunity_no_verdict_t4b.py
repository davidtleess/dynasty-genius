from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPENAPI = ROOT / "frontend" / "openapi.json"
GENERATED_TYPES = ROOT / "frontend" / "src" / "lib" / "api" / "types.gen.ts"
GENERATED_ZOD = ROOT / "frontend" / "src" / "lib" / "api" / "zod.gen.ts"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_t4b_generated_clients_match_v2_openapi_contract() -> None:
    """T4b must regenerate the FE client from the committed v2 OpenAPI artifact."""
    openapi = _text(OPENAPI)
    generated = "\n".join([_text(GENERATED_TYPES), _text(GENERATED_ZOD)])

    required_v2_tokens = [
        "LeaguePulseCardSectionCount",
        "card_section_counts",
        "roster_capacity_candidate_pools",
        "roster_capacity_candidates",
        "LeaguePulseCapacityCandidate",
        "LeaguePulseCapacityCandidatePool",
        "evidence_status",
        "sort_key",
        "sort_value",
        "UNROSTERED_MODEL_MARKET_DIVERGENCE",
        "TAXI_LONG_TERM_VALUE_PRESENT",
    ]
    stale_tokens = [
        "LeaguePulseRecommendedDrop",
        "recommended_drop",
        "recommended_drops",
        "recommended_drop_name",
        "opportunity_score",
        "WAIVER_CANDIDATE",
        "TAXI_ACTIVATION_CANDIDATE",
    ]

    for token in required_v2_tokens:
        assert token in openapi, f"OpenAPI fixture unexpectedly lacks {token}"
        assert token in generated, (
            f"generated FE client lacks {token}; run npm --prefix frontend "
            "run openapi-gen"
        )

    for token in stale_tokens:
        assert token not in openapi, f"OpenAPI fixture still contains stale {token}"
        assert token not in generated, (
            f"generated FE client still contains stale {token}; run npm --prefix "
            "frontend run openapi-gen"
        )
