"""H2 Increment 1 — team-color module generator (spec v3 §2, Codex F1 drift contract).

Reads the checked-in team map under app/config and emits the committed
frontend module `frontend/src/generated/teamColors.ts`. The frontend imports
ONLY the generated module (the frontend-sources ban on reading the JSON
directly stays intact); a contract test canonically regenerates and fails on
any divergence, so the JSON remains the single source of truth.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_JSON = REPO_ROOT / "app" / "config" / "team_colors.json"
OUTPUT_MODULE = REPO_ROOT / "frontend" / "src" / "generated" / "teamColors.ts"


def canonical_sha256(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def render_module(payload: dict) -> str:
    schema_version = payload["schema_version"]
    sha = canonical_sha256(payload)
    teams = payload["teams"]
    lines = [
        "// GENERATED FILE — do not edit by hand.",
        "// Source: the checked-in team map under app/config (single source of",
        "// truth); regenerate with scripts/generate_team_color_module.py.",
        "// A contract test fails on any divergence between source and module.",
        "export const TEAM_COLORS_META = {",
        f'  schema_version: "{schema_version}",',
        f'  source_sha256: "{sha}",',
        "} as const;",
        "",
        "export const TEAM_COLORS: Record<",
        "  string,",
        "  { primary: string; secondary: string }",
        "> = {",
    ]
    for team_id in sorted(teams):
        colors = teams[team_id]
        lines.append(
            f'  {team_id}: {{ primary: "{colors["primary"]}", '
            f'secondary: "{colors["secondary"]}" }},'
        )
    lines.append("};")
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    OUTPUT_MODULE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MODULE.write_text(render_module(payload), encoding="utf-8")
    print(f"wrote {OUTPUT_MODULE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
