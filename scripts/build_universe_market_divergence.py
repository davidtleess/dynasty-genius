"""Build Phase 17.4 full-universe market divergence artifacts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.adapters.fantasycalc_adapter import (
    fetch_with_cache,  # noqa: E402
)
from src.dynasty_genius.universe_market_divergence import (  # noqa: E402
    build_universe_market_divergence,
    write_market_divergence_artifacts,
)

UNIVERSE_PVO_PATH = ROOT / "app" / "data" / "valuation" / "universe_pvo_latest.json"
OUTPUT_DIR = ROOT / "app" / "data" / "valuation"


def main() -> None:
    universe_pvo = json.loads(UNIVERSE_PVO_PATH.read_text())
    fc_response, fetch_caveats = fetch_with_cache()
    captured_at = datetime.now(timezone.utc).isoformat()
    divergence = build_universe_market_divergence(
        universe_pvo,
        fc_response,
        fetch_caveats=fetch_caveats,
        captured_at=captured_at,
    )
    run_id = datetime.now(timezone.utc).strftime("phase17-4-%Y%m%dT%H%M%SZ")
    paths = write_market_divergence_artifacts(divergence, output_dir=OUTPUT_DIR, run_id=run_id)
    print(f"Wrote Phase 17.4 market divergence: {paths['batch']}")
    print(f"Wrote Phase 17.4 market divergence coverage: {paths['coverage']}")


if __name__ == "__main__":
    main()
