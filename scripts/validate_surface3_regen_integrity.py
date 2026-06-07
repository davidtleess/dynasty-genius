"""Surface-3 (T3a) regeneration integrity audit.

Compares pre/post regeneration artifact roots and asserts that the ONLY changes
are the explicit Surface-3 allowlist (allowlist-complement contract): everything
else must be byte/value-identical. Any out-of-allowlist drift — model fields,
rankings, stable provenance, coverage counts, new un-allowlisted keys, or a `.js`
payload that diverges from its `.json` — raises ``IntegrityAuditError`` (the T3b
HARD STOP). Logic is validated by ``tests/test_surface3_regen_integrity.py`` on
small synthetic fixtures; no production artifacts or 12k-row rebuild are involved.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable

PHASE15_REPORT = "docs/validation/phase15-2026-rookie-rank-refresh.md"
PROSPECT_JSON = "resources/prospect_cards.json"
PROSPECT_JS = "resources/prospect_cards.js"
UNIVERSE_JSON = "app/data/valuation/universe_pvo_latest.json"
UNIVERSE_COVERAGE = "app/data/valuation/universe_pvo_coverage_latest.json"

# Order is contractual (asserted by the audit test).
CHECKED_ARTIFACTS = [
    PROSPECT_JSON,
    PROSPECT_JS,
    UNIVERSE_JSON,
    UNIVERSE_COVERAGE,
    PHASE15_REPORT,
]

# --- Per-artifact allowlists (everything NOT listed must be byte/value-identical) ---
PROSPECT_IDENTITY_KEYS = ("sleeper_id", "player_id")
# `assembled_at` is a regen timestamp written to every card; `counter_argument`
# may change ONLY on the cleaned QB/TE rows (the §2.4 rewrite touches just those
# high-value templates). A counter_argument change on any other row is drift.
CLEANED_PROSPECT_IDS = {"13269", "13330"}
PROSPECT_ROW_ALLOWED_CHANGE = {"assembled_at"}
PROSPECT_ALLOWED_NEW: set[str] = set()

UNIVERSE_IDENTITY_KEYS = ("sleeper_player_id", "dg_player_id")
UNIVERSE_TOP_ALLOWED_CHANGE = {"captured_at"}
UNIVERSE_ROW_ALLOWED_CHANGE = {"captured_at", "pipeline_run_id"}
# The 10 §2.1 keys are the ONLY new keys permitted to appear on a universe row.
SURFACE3_NEW_KEYS = {
    "counter_argument",
    "risk_flags",
    "top_drivers",
    "caveats",
    "draft_class",
    "nfl_draft_pick",
    "nfl_draft_round",
    "projection_1y",
    "projection_2y",
    "projection_3y",
}

# Banned-vocabulary scan (spec §2.4 / §6): emitted evidence TEXT must carry zero
# banned standalone words / phrases post-regen. Source of truth is the same vocab
# file the frontend linter uses.
BANNED_VOCAB_PATH = (
    Path(__file__).resolve().parents[1] / "frontend" / "src" / "shell" / "banned_vocabulary.json"
)
EVIDENCE_TEXT_FIELDS = ("counter_argument", "top_drivers", "risk_flags", "caveats")


class IntegrityAuditError(Exception):
    """Raised when a regeneration diff falls outside the Surface-3 allowlist."""


def _load_json(root: Path, rel_path: str) -> Any:
    return json.loads((root / rel_path).read_text())


def _require_dict(value: Any, artifact: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IntegrityAuditError(
            f"{artifact}: malformed shape — expected JSON object, got {type(value).__name__}"
        )
    return value


def _require_list_of_dicts(value: Any, artifact: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise IntegrityAuditError(
            f"{artifact}: malformed shape — expected a JSON list of objects"
        )
    return value


def _load_banned_vocabulary() -> tuple[list[str], list[str]]:
    data = json.loads(BANNED_VOCAB_PATH.read_text())
    return (
        list(data.get("banned_standalone_words", [])),
        list(data.get("banned_phrases", [])),
    )


def _scan_text_for_banned(
    text: str, standalone: list[str], phrases: list[str]
) -> str | None:
    lowered = text.lower()
    # Standalone words use word-boundary matching so 'robust' does not trip 'bust'.
    for word in standalone:
        if re.search(rf"\b{re.escape(word.lower())}\b", lowered):
            return word
    for phrase in phrases:
        if phrase.lower() in lowered:
            return phrase
    return None


def _iter_evidence_strings(row: dict[str, Any]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for field in EVIDENCE_TEXT_FIELDS:
        value = row.get(field)
        if isinstance(value, str):
            found.append((field, value))
        elif isinstance(value, list):
            found.extend((field, item) for item in value if isinstance(item, str))
    return found


def _check_banned_evidence(post: Path) -> None:
    standalone, phrases = _load_banned_vocabulary()
    prospect = _load_json(post, PROSPECT_JSON)
    universe = _load_json(post, UNIVERSE_JSON)
    rows: list[dict[str, Any]] = []
    if isinstance(prospect, list):
        rows.extend(r for r in prospect if isinstance(r, dict))
    if isinstance(universe, dict):
        rows.extend(r for r in (universe.get("players") or []) if isinstance(r, dict))
    for row in rows:
        for field, text in _iter_evidence_strings(row):
            hit = _scan_text_for_banned(text, standalone, phrases)
            if hit is not None:
                raise IntegrityAuditError(
                    f"post evidence contains banned term '{hit}' in field "
                    f"'{field}': {text!r}"
                )

    # The phase15 report also carries counter_argument evidence text (spec §2.4/§6),
    # and the structural report check allows cleaned-row edits — so scan it too.
    marker = "counter_argument:"
    for index, line in enumerate(
        (post / PHASE15_REPORT).read_text().splitlines(), start=1
    ):
        pos = line.find(marker)
        if pos == -1:
            continue
        hit = _scan_text_for_banned(line[pos + len(marker) :], standalone, phrases)
        if hit is not None:
            raise IntegrityAuditError(
                f"post report contains banned term '{hit}' in counter_argument "
                f"line {index}: {line!r}"
            )


def _identity(row: dict[str, Any], keys: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple(row.get(k) for k in keys)


def _index_by_identity(
    rows: list[dict[str, Any]], keys: tuple[str, ...]
) -> dict[tuple[Any, ...], dict[str, Any]]:
    return {_identity(row, keys): row for row in rows}


def _check_identity_closure(
    pre_rows: list[dict[str, Any]],
    post_rows: list[dict[str, Any]],
    keys: tuple[str, ...],
    artifact: str,
) -> None:
    """Fail-closed row-set closure: no duplicate identities, exact multiset match.

    Done as multiset (not set) checks so a duplicated row or a row-count change
    cannot slip past identity validation before per-row comparison.
    """
    pre_ids = [_identity(row, keys) for row in pre_rows]
    post_ids = [_identity(row, keys) for row in post_rows]
    for label, ids in (("pre", pre_ids), ("post", post_ids)):
        dups = sorted({i for i in ids if ids.count(i) > 1}, key=str)
        if dups:
            raise IntegrityAuditError(
                f"{artifact}: duplicate identity in {label} rows ({keys}): {dups}"
            )
    if sorted(pre_ids, key=str) != sorted(post_ids, key=str):
        raise IntegrityAuditError(
            f"{artifact}: identity set changed ({keys}): "
            f"{sorted(set(pre_ids) ^ set(post_ids), key=str)}"
        )


def _deepest_diff_key(pre: Any, post: Any, fallback: str) -> str:
    """Return the deepest differing dict key, or ``fallback`` for a leaf/list diff."""
    if isinstance(pre, dict) and isinstance(post, dict):
        for key in set(pre) | set(post):
            if key not in pre or key not in post:
                return key
            if pre[key] != post[key]:
                return _deepest_diff_key(pre[key], post[key], key)
    return fallback


def _compare_row(
    pre_row: dict[str, Any],
    post_row: dict[str, Any],
    *,
    allowed_change: set[str],
    allowed_new: set[str],
    artifact: str,
) -> None:
    pre_keys = set(pre_row)
    post_keys = set(post_row)

    illegal_new = (post_keys - pre_keys) - allowed_new
    if illegal_new:
        raise IntegrityAuditError(
            f"{artifact}: unexpected new key(s) outside allowlist: {sorted(illegal_new)}"
        )
    removed = pre_keys - post_keys
    if removed:
        raise IntegrityAuditError(
            f"{artifact}: key(s) removed during regen: {sorted(removed)}"
        )

    for key in pre_keys:
        if key in allowed_change:
            continue
        if pre_row[key] != post_row[key]:
            deep = _deepest_diff_key(pre_row[key], post_row[key], key)
            # Name both the row key and the deepest differing key so the message
            # surfaces e.g. 'valuation' -> 'dynasty_value_score' and
            # 'source_versions' -> 'identity_source'.
            raise IntegrityAuditError(
                f"{artifact}: out-of-allowlist field drift in '{key}' (at '{deep}')"
            )


def _check_prospect(pre: list[dict[str, Any]], post: list[dict[str, Any]]) -> None:
    _require_list_of_dicts(pre, "prospect_cards.json (pre)")
    _require_list_of_dicts(post, "prospect_cards.json (post)")
    _check_identity_closure(pre, post, PROSPECT_IDENTITY_KEYS, "prospect_cards.json")
    post_idx = _index_by_identity(post, PROSPECT_IDENTITY_KEYS)
    for ident, pre_row in _index_by_identity(pre, PROSPECT_IDENTITY_KEYS).items():
        # counter_argument is row-scoped: only the cleaned QB/TE ids may change it.
        allowed_change = set(PROSPECT_ROW_ALLOWED_CHANGE)
        if str(pre_row.get("sleeper_id")) in CLEANED_PROSPECT_IDS:
            allowed_change.add("counter_argument")
        _compare_row(
            pre_row,
            post_idx[ident],
            allowed_change=allowed_change,
            allowed_new=PROSPECT_ALLOWED_NEW,
            artifact="prospect_cards.json",
        )


def _check_universe(pre: dict[str, Any], post: dict[str, Any]) -> None:
    _require_dict(pre, "universe_pvo (pre)")
    _require_dict(post, "universe_pvo (post)")
    pre_rows = pre.get("players") or []
    post_rows = post.get("players") or []
    _require_list_of_dicts(pre_rows, "universe_pvo players (pre)")
    _require_list_of_dicts(post_rows, "universe_pvo players (post)")
    _check_identity_closure(pre_rows, post_rows, UNIVERSE_IDENTITY_KEYS, "universe_pvo")
    post_idx = _index_by_identity(post_rows, UNIVERSE_IDENTITY_KEYS)
    for ident, pre_row in _index_by_identity(pre_rows, UNIVERSE_IDENTITY_KEYS).items():
        _compare_row(
            pre_row,
            post_idx[ident],
            allowed_change=UNIVERSE_ROW_ALLOWED_CHANGE,
            allowed_new=SURFACE3_NEW_KEYS,
            artifact="universe_pvo",
        )

    # Top-level key-set closure FIRST (explicit set check — a value comparison
    # would let a new key whose value is None slip past), then value comparison.
    pre_top = set(pre) - {"players"}
    post_top = set(post) - {"players"}
    new_top = post_top - pre_top
    if new_top:
        raise IntegrityAuditError(
            f"universe_pvo: unexpected new top-level key(s): {sorted(new_top)}"
        )
    removed_top = pre_top - post_top
    if removed_top:
        raise IntegrityAuditError(
            f"universe_pvo: top-level key(s) removed during regen: {sorted(removed_top)}"
        )
    for key in pre_top:
        if key in UNIVERSE_TOP_ALLOWED_CHANGE:
            continue
        if pre[key] != post[key]:
            deep = _deepest_diff_key(pre[key], post[key], key)
            raise IntegrityAuditError(
                f"universe_pvo: out-of-allowlist top-level drift in '{key}' (at '{deep}')"
            )


def _check_coverage(pre: dict[str, Any], post: dict[str, Any]) -> None:
    # Coverage MUST be zero-delta: the 10 preserved row keys are evidence fields
    # and may not move any coverage count.
    _require_dict(pre, "universe_pvo_coverage (pre)")
    _require_dict(post, "universe_pvo_coverage (post)")
    if pre != post:
        deep = _deepest_diff_key(pre, post, "coverage")
        raise IntegrityAuditError(
            f"universe_pvo_coverage: zero-delta violated — coverage drift at '{deep}'"
        )


def _parse_js_payload(js_text: str) -> Any:
    marker = "window.PROSPECT_CARDS"
    marker_at = js_text.find(marker)
    if marker_at == -1:
        raise IntegrityAuditError("prospect_cards.js: missing window.PROSPECT_CARDS payload")
    eq_at = js_text.find("=", marker_at)
    if eq_at == -1:
        raise IntegrityAuditError("prospect_cards.js: malformed payload assignment")
    payload = js_text[eq_at + 1 :].strip()
    if payload.endswith(";"):
        payload = payload[:-1].rstrip()
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise IntegrityAuditError(f"prospect_cards.js: unparseable payload ({exc})") from exc


def _check_js(post_root: Path, post_prospect: Any) -> None:
    js_payload = _parse_js_payload((post_root / PROSPECT_JS).read_text())
    if js_payload != post_prospect:
        raise IntegrityAuditError(
            "prospect_cards.js: embedded payload does not match prospect_cards.json"
        )


def _is_generated_at_line(line: str) -> bool:
    # The real phase15 report uses 'Generated: <ts>'; the optional ' at' keeps the
    # synthetic 'Generated at:' fixture form valid too.
    return re.match(r"^Generated(\s+at)?\s*:", line.lstrip()) is not None


def _report_counter_argument_id(line: str) -> str | None:
    """Return the row id of a report counter_argument line, else None.

    Report row shape: ``- <id> counter_argument: <text>``. The id is PARSED (the
    token after ``- ``), not substring-matched, so a line that merely *mentions* a
    cleaned id elsewhere in its text is not treated as that row.
    """
    stripped = line.strip()
    if "counter_argument:" not in stripped or not stripped.startswith("- "):
        return None
    rest = stripped[2:].lstrip()
    if not rest:
        return None
    return rest.split(None, 1)[0]


def _check_report(pre_root: Path, post_root: Path) -> None:
    # Structural allowlist: same line count + order; a differing line is allowed
    # ONLY when BOTH pre/post are the generated-at line OR both are a cleaned-id
    # counter_argument line. Added/removed/substituted other lines are HARD STOP.
    # (Dropping lines by substring would let arbitrary added lines slip past.)
    pre_lines = (pre_root / PHASE15_REPORT).read_text().splitlines()
    post_lines = (post_root / PHASE15_REPORT).read_text().splitlines()
    if len(pre_lines) != len(post_lines):
        raise IntegrityAuditError(
            f"{PHASE15_REPORT}: line count changed "
            f"({len(pre_lines)} -> {len(post_lines)}); only timestamp/cleaned-row "
            f"edits are allowed (no added/removed lines)"
        )
    for index, (pre_line, post_line) in enumerate(zip(pre_lines, post_lines), start=1):
        if pre_line == post_line:
            continue
        both_generated = _is_generated_at_line(pre_line) and _is_generated_at_line(post_line)
        pre_ca_id = _report_counter_argument_id(pre_line)
        post_ca_id = _report_counter_argument_id(post_line)
        both_cleaned = (
            pre_ca_id is not None
            and pre_ca_id == post_ca_id
            and pre_ca_id in CLEANED_PROSPECT_IDS
        )
        if not (both_generated or both_cleaned):
            raise IntegrityAuditError(
                f"{PHASE15_REPORT}: out-of-allowlist line drift at line {index}: "
                f"{pre_line!r} -> {post_line!r}"
            )


def validate_regen_integrity(pre_root: str | Path, post_root: str | Path) -> dict[str, Any]:
    """Audit a Surface-3 regeneration; raise IntegrityAuditError on any drift.

    Returns ``{"status": "pass", "checked_artifacts": [...]}`` when every diff is
    within the per-artifact allowlist.
    """
    pre = Path(pre_root)
    post = Path(post_root)

    post_prospect = _load_json(post, PROSPECT_JSON)
    _check_prospect(_load_json(pre, PROSPECT_JSON), post_prospect)
    _check_js(post, post_prospect)
    _check_universe(_load_json(pre, UNIVERSE_JSON), _load_json(post, UNIVERSE_JSON))
    _check_coverage(
        _load_json(pre, UNIVERSE_COVERAGE), _load_json(post, UNIVERSE_COVERAGE)
    )
    _check_report(pre, post)
    _check_banned_evidence(post)

    return {"status": "pass", "checked_artifacts": list(CHECKED_ARTIFACTS)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit a Surface-3 artifact regeneration (T3b hard-stop gate)."
    )
    parser.add_argument("pre_root", help="Pre-regen snapshot root (Preflight copy).")
    parser.add_argument("post_root", help="Post-regen root (the working tree).")
    args = parser.parse_args(argv)

    runner: Callable[[str, str], dict[str, Any]] = validate_regen_integrity
    try:
        result = runner(args.pre_root, args.post_root)
    except IntegrityAuditError as exc:
        print(f"INTEGRITY AUDIT FAILED — HARD STOP: {exc}")
        return 1
    print(f"INTEGRITY AUDIT PASSED: {result['checked_artifacts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
