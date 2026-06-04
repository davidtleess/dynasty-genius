from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = REPO_ROOT / "frontend"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

EXPECTED_DEPENDENCIES = {
    "react": "19.2.7",
    "react-dom": "19.2.7",
    "zod": "4.4.3",
}

EXPECTED_DEV_DEPENDENCIES = {
    "@biomejs/biome": "2.4.16",
    "@testing-library/dom": "10.4.1",
    "@testing-library/react": "16.3.2",
    "@types/react": "19.2.16",
    "@types/react-dom": "19.2.3",
    "jsdom": "29.1.1",
    "typescript": "6.0.3",
    "vite": "8.0.16",
    "vitest": "4.1.8",
}

EXPECTED_SCRIPTS = {
    "build": "vite build",
    "lint": "biome check .",
    "test": "vitest run --passWithNoTests",
    "typecheck": "tsc --noEmit",
}

BANNED_DEPENDENCIES = {
    "@hey-api/openapi-ts",
    "@tailwindcss/vite",
    "@tanstack/react-query",
    "@tanstack/react-router",
    "canvas",
    "chart.js",
    "cmdk",
    "d3",
    "lightweight-charts",
    "recharts",
    "tailwindcss",
}


def _read_json(path: Path) -> dict[str, Any]:
    assert path.exists(), f"Missing required frontend file: {path.relative_to(REPO_ROOT)}"
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_exact_pin(package_name: str, version: str) -> None:
    assert version, f"{package_name} must have an explicit version pin"
    assert not version.startswith(("^", "~")), (
        f"{package_name} must be exact-pinned, got {version!r}"
    )


def test_frontend_package_manifest_is_minimal_exact_pinned_stack_a() -> None:
    package_json = _read_json(FRONTEND_ROOT / "package.json")

    assert package_json["type"] == "module"
    assert package_json["packageManager"] == "npm@11.14.0"
    assert package_json["dependencies"] == EXPECTED_DEPENDENCIES
    assert package_json["devDependencies"] == EXPECTED_DEV_DEPENDENCIES
    assert package_json["scripts"] == EXPECTED_SCRIPTS

    all_dependencies = package_json["dependencies"] | package_json["devDependencies"]
    for package_name, version in all_dependencies.items():
        _assert_exact_pin(package_name, version)

    assert BANNED_DEPENDENCIES.isdisjoint(all_dependencies), (
        "S2 scaffold must not introduce Tailwind, command palettes, charting/canvas, "
        "TanStack, or deferred Hey API codegen dependencies"
    )


def test_frontend_scaffold_required_files_and_node_runtime_pin_exist() -> None:
    required_files = (
        ".gitignore",
        ".node-version",
        "biome.json",
        "index.html",
        "package-lock.json",
        "src/App.tsx",
        "src/main.tsx",
        "tsconfig.json",
        "vite.config.ts",
    )

    for relative_path in required_files:
        assert (FRONTEND_ROOT / relative_path).exists(), (
            f"Missing required frontend scaffold file: frontend/{relative_path}"
        )

    assert (FRONTEND_ROOT / ".node-version").read_text(encoding="utf-8").strip() == (
        "24.15.0"
    )

    gitignore = (FRONTEND_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "node_modules/" in gitignore
    assert "dist/" in gitignore


def test_frontend_typescript_and_biome_configs_are_strict_and_scoped() -> None:
    tsconfig = _read_json(FRONTEND_ROOT / "tsconfig.json")
    compiler_options = tsconfig["compilerOptions"]

    assert compiler_options["strict"] is True
    assert compiler_options["noUncheckedIndexedAccess"] is True
    assert compiler_options["exactOptionalPropertyTypes"] is True
    assert compiler_options["verbatimModuleSyntax"] is True

    biome = _read_json(FRONTEND_ROOT / "biome.json")
    files = biome.get("files", {})
    includes = files.get("includes") or files.get("include")
    assert includes, "Biome must be scoped to the frontend workspace"
    assert all(
        str(include).startswith(("src/", "*.html", "*.ts", "*.tsx", "vite.config.ts"))
        for include in includes
    ), f"Biome includes must stay frontend-scoped, got {includes!r}"


def test_frontend_ci_job_builds_workspace_before_claiming_green() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "frontend-checks:" in workflow
    assert "actions/setup-node@" in workflow
    assert 'node-version-file: "frontend/.node-version"' in workflow
    assert "working-directory: frontend" in workflow
    assert "npm ci" in workflow
    assert "npm run typecheck" in workflow
    assert "npm run lint" in workflow
    assert "npm run test" in workflow
    assert "npm run build" in workflow
    assert "test -f dist/index.html" in workflow


def test_frontend_build_output_exists_after_local_build() -> None:
    dist_index = FRONTEND_ROOT / "dist" / "index.html"

    if not dist_index.exists():
        pytest.skip(
            "frontend/dist is a gitignored build artifact; the frontend-checks CI job "
            "and local npm run build are responsible for generating it"
        )

    assert dist_index.is_file()
