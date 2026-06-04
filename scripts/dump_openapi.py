"""Dump the FastAPI OpenAPI schema to ``frontend/openapi.json`` (canonical snapshot).

This is the single regeneration path for the frontend Hey API codegen seam. The
committed snapshot must byte-match ``json.dumps(app.openapi(), indent=2,
sort_keys=True) + "\\n"`` — enforced by
``tests/contract/test_openapi_drift_contract.py``.

Run it through the documented command ``npm --prefix frontend run openapi-gen``
(which runs ``../.venv/bin/python3.14 ../scripts/dump_openapi.py`` then ``openapi-ts``),
or directly with the project interpreter::

    .venv/bin/python3.14 scripts/dump_openapi.py

The npm script pins the project interpreter (``../.venv/bin/python3.14``) so the app
dependencies are present without an activated shell. CI does not regenerate — it
consumes the committed snapshot + client — so this is a developer-only regen path.
"""

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
# app.main resolves relative paths (e.g. the conditional `frontend/dist` SPA mount) from
# the process cwd; pin it to the repo root so the schema is identical regardless of the
# invocation directory (the npm script runs this with cwd=frontend).
os.chdir(REPO_ROOT)

# Delayed import on purpose: app.main is imported only AFTER sys.path + os.chdir are set,
# so the generated OpenAPI schema is deterministic regardless of the invocation cwd. Both
# E402 (late import) and I001 (this trailing import block) are intentional here.
from app.main import app  # noqa: E402, I001

OPENAPI_SNAPSHOT = REPO_ROOT / "frontend" / "openapi.json"


def main() -> None:
    text = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    OPENAPI_SNAPSHOT.write_text(text, encoding="utf-8")
    print(f"Wrote {OPENAPI_SNAPSHOT.relative_to(REPO_ROOT)} ({len(text)} bytes)")


if __name__ == "__main__":
    main()
