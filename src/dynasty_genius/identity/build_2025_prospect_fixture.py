"""S3 Task 10A — cohort-truth-driven 2025 prospect fixture builder (spec §4/§6).

Builds the provisional 2025 college-prospect fixture from the frozen, hashed
source stack produced by ``freeze_2025_prospect_sources``. The cohort is defined
by *draft truth*: iterate the drafted **skill** picks (the actual dynasty-decision
cohort) and locate each pick's CFBD college identity. The builder is identity-only
— it emits ``NormalizedCollegeProspectRow`` rows with the CFBD athlete id populated
and **all cross-IDs null** (no pre-bridging; S4 bridge entries come only via
``build_prospect_nfl_bridge.py`` + David promotion).

Membership + review semantics (spec §4):

- Iterate **drafted picks**, not CFBD roster rows. Undrafted CFBD rows are not
  cohort members and are silently excluded.
- A drafted pick whose position is a skill group (QB/RB/WR/TE) is matched to CFBD.
- A drafted pick in a **fantasy-ambiguous** position (``ATH``, and ``FB`` — never
  auto-admitted as RB) becomes a ``unresolved_draft_pick_position`` review row
  (fantasy-relevance is David's call).
- **EVERY other drafted position is silently excluded** (not a review row): all OL /
  defense / special-teams codes incl. real nflverse spellings (``SAF``, ``G``, …) and
  any future/unknown non-skill code. (Inverted 2026-06-02 — an enumerated non-skill set
  previously missed ``SAF``/``G`` and wrongly routed them to review.)

Match pipeline (spec §4 — final classification runs LAST):

1. primary-key match: normalized name + position group + normalized school
   (with an injected ``school_aliases`` map),
2. **if** the drafted-skill unmatched rate exceeds the fallback threshold, run the
   deterministic ``collegeAthleteId`` → CFBD roster ``id`` fallback,
3. **then** classify each skill pick: 0 → ``draft_truth_match_missing`` (the pick is
   never silently dropped), >1 → ``draft_truth_match_ambiguous``, 1 → emit.

Robustness boundary (spec §4 D4): the top-level frozen-inputs shape **fails loud**
(missing required keys raise ``KeyError``); an individual malformed source record
(a matched CFBD row missing its ``id``) **fails closed** into a
``malformed_source_record`` review row rather than crashing. Never a fuzzy- or
memory-filled identity.
"""
from __future__ import annotations

from typing import Any

from src.dynasty_genius.identity.college_prospect_identity import (
    IdProvenance,
    NormalizedCollegeProspectRow,
    normalize_name,
)

# Manifest dict key for the CFBD roster input (spec §6 — builder dereferences by key).
_CFBD_MANIFEST_KEY = "cfbd_roster"

# Drafted-pick position classification (spec §4; INVERTED 2026-06-02 for robustness —
# review the fantasy-AMBIGUOUS codes ONLY and silently exclude everything else, so real
# nflverse codes (SAF, G, …) and any future/unknown non-skill code never pollute the review
# queue. An enumerated clearly-non-skill set previously missed SAF/G and routed them to review.)
# Emittable skill groups: matched to CFBD and (on a clean 1:1) emitted.
_EMITTABLE_SKILL_GROUPS: frozenset[str] = frozenset({"QB", "RB", "WR", "TE"})
# Fantasy-ambiguous drafted positions -> unresolved_draft_pick_position review row (David's
# call; FB never auto-admitted as RB). EVERY other non-skill position is silently excluded.
_FANTASY_AMBIGUOUS: frozenset[str] = frozenset({"ATH", "FB"})

# Required structural fields on a drafted-pick source record (spec §4 D-1). A pick
# missing any of these is malformed source data → fail closed (operating-loop §8).
_REQUIRED_DRAFT_FIELDS: tuple[str, ...] = (
    "season",
    "position",
    "pfr_player_name",
    "college",
    "pfr_player_id",
)

_DEFAULT_FALLBACK_THRESHOLD = 0.05


def _norm_school(school: str, aliases: dict[str, str]) -> str:
    """Lowercase/strip then apply the injected school-alias map (spec §4)."""
    normalized = (school or "").strip().lower()
    return aliases.get(normalized, normalized)


def _cfbd_full_name(cfbd_row: dict) -> str:
    return f"{cfbd_row.get('firstName', '')} {cfbd_row.get('lastName', '')}".strip()


def _review_row(pick: dict, reason: str) -> dict:
    """Pick-keyed review row (spec §4). Keyed on the draft pick's id."""
    return {
        "source_record_id": str(pick.get("pfr_player_id", "")),
        "reason": reason,
        "raw_name": str(pick.get("pfr_player_name", "")),
        "raw_position": str(pick.get("position", "")),
        "draft_class": pick.get("season"),
        "pick": pick.get("pick"),
        "action": "manual_review_required",
    }


def _malformed_review_row(pick: dict) -> dict:
    """Fail-closed review row for a matched-but-malformed CFBD source record (spec §4 D4)."""
    return {
        "source_record_id": f"{_CFBD_MANIFEST_KEY}:<missing>",
        "reason": "malformed_source_record",
        "raw_name": str(pick.get("pfr_player_name", "")),
        "raw_position": str(pick.get("position", "")),
        "draft_class": pick.get("season"),
        "pick": pick.get("pick"),
        "action": "manual_review_required",
    }


def _draft_malformed_review_row(pick: Any) -> dict:
    """Fail-closed review row for a malformed drafted-pick source record (spec §4 D-1/D-3).

    Handles both a dict missing a required field and a non-dict record. Keyed by the
    pick's ``pfr_player_id`` when present, else ``nflverse_draft_picks:<missing>``.
    """
    is_dict = isinstance(pick, dict)
    pfr_player_id = pick.get("pfr_player_id") if is_dict else None
    source_record_id = (
        str(pfr_player_id)
        if pfr_player_id is not None
        else "nflverse_draft_picks:<missing>"
    )
    return {
        "source_record_id": source_record_id,
        "reason": "malformed_source_record",
        "raw_name": str(pick.get("pfr_player_name", "")) if is_dict else "",
        "raw_position": str(pick.get("position", "")) if is_dict else "",
        "draft_class": pick.get("season") if is_dict else None,
        "pick": pick.get("pick") if is_dict else None,
        "action": "manual_review_required",
    }


def _malformed_cfbd_index_review_row() -> dict:
    """Fail-closed review row for a non-dict CFBD roster record (spec §4 D-3).

    A non-dict roster element carries no identifiable fields, so it is keyed
    ``cfbd_roster:<missing>`` with empty name/position.
    """
    return {
        "source_record_id": f"{_CFBD_MANIFEST_KEY}:<missing>",
        "reason": "malformed_source_record",
        "raw_name": "",
        "raw_position": "",
        "draft_class": None,
        "pick": None,
        "action": "manual_review_required",
    }


def _emit_row(
    cfbd_row: dict,
    pick: dict,
    *,
    source_name: str,
    source_snapshot_id_str: str,
    provenance_source: str,
) -> dict:
    """Build a validated identity-only registry-shaped row (cross-IDs null)."""
    cfbd_id = str(cfbd_row["id"])
    raw_name = _cfbd_full_name(cfbd_row)
    year = cfbd_row.get("year")
    row = NormalizedCollegeProspectRow(
        raw_name=raw_name,
        normalized_name=normalize_name(raw_name),
        full_name=raw_name,
        position=str(cfbd_row.get("position", "")).upper(),
        position_group=str(cfbd_row.get("position", "")).upper(),
        draft_class=int(pick["season"]),
        class_year=None if year is None else str(year),
        current_school=str(cfbd_row.get("team", "")),
        prior_schools=[],
        cfbd_athlete_id=cfbd_id,
        cfb_player_id=None,
        pfr_id=None,
        gsis_id=None,
        sleeper_id=None,
        source=source_name,
        source_record_id=cfbd_id,
        source_snapshot_id=source_snapshot_id_str,
        id_provenance=IdProvenance(
            cfbd_athlete_id={"source": provenance_source, "source_record_id": cfbd_id},
        ),
        notes=None,
    )
    return row.model_dump()


def build_2025_prospect_fixture(
    frozen_inputs: dict[str, Any],
    *,
    school_aliases: dict[str, str] | None = None,
    drafted_unmatched_fallback_threshold: float = _DEFAULT_FALLBACK_THRESHOLD,
) -> tuple[list[dict], list[dict]]:
    """Build ``(rows, review_queue)`` from the frozen 2025 source stack (spec §4/§6).

    ``rows`` are emit-ready ``NormalizedCollegeProspectRow`` dicts (identity-only,
    cross-IDs null). ``review_queue`` holds pick-keyed manual-review rows for missing,
    ambiguous, unresolved-position, and malformed-source cases.
    """
    aliases = {str(k).strip().lower(): v for k, v in (school_aliases or {}).items()}

    # --- top-level shape: fail LOUD (spec §4 D4/D-3) — required keys accessed directly ---
    cfbd_rows = frozen_inputs["cfbd_roster"]
    draft_rows = frozen_inputs["nflverse_draft_picks"]["rows"]
    manifest_cfbd = frozen_inputs["manifest"][_CFBD_MANIFEST_KEY]
    source_snapshot_id_str = manifest_cfbd["source_snapshot_id_str"]
    source_snapshot_id = manifest_cfbd["source_snapshot_id"]

    # A rows-container that is not a list is API misuse → fail LOUD before any iteration
    # (spec §4 D-3 boundary; distinct from a malformed individual element, which fails closed).
    if not isinstance(cfbd_rows, list):
        raise TypeError("frozen_inputs['cfbd_roster'] must be a list of records")
    if not isinstance(draft_rows, list):
        raise TypeError("frozen_inputs['nflverse_draft_picks']['rows'] must be a list of records")

    # Single source of truth: the year-qualified artifact name is the str's prefix.
    source_name = source_snapshot_id_str.split(":", 1)[0]
    endpoint_base = str(source_snapshot_id["endpoint"]).split("?", 1)[0]
    provenance_source = f"CFBD {endpoint_base} {source_snapshot_id['api_version']}"

    review_queue: list[dict] = []

    # --- index CFBD rows by match key and by athlete id (for the fallback pass) ---
    # A non-dict roster element is a malformed individual record → fail closed (spec §4 D-3),
    # never an AttributeError; it is skipped from the index.
    cfbd_by_key: dict[tuple[str, str, str], list[dict]] = {}
    cfbd_by_id: dict[str, dict] = {}
    for cfbd_row in cfbd_rows:
        if not isinstance(cfbd_row, dict):
            review_queue.append(_malformed_cfbd_index_review_row())
            continue
        key = (
            normalize_name(_cfbd_full_name(cfbd_row)),
            str(cfbd_row.get("position", "")).upper(),
            _norm_school(str(cfbd_row.get("team", "")), aliases),
        )
        cfbd_by_key.setdefault(key, []).append(cfbd_row)
        cfbd_id = cfbd_row.get("id")
        if cfbd_id is not None:
            cfbd_by_id[str(cfbd_id)] = cfbd_row

    # --- classify drafted picks: silently-excluded / unresolved-position / skill ---
    skill_picks: list[dict] = []
    for pick in draft_rows:
        if not isinstance(pick, dict) or any(
            pick.get(field) is None for field in _REQUIRED_DRAFT_FIELDS
        ):
            review_queue.append(_draft_malformed_review_row(pick))  # fail closed (spec §4 D-1/D-3)
            continue
        position = str(pick.get("position", "")).upper()
        if position in _EMITTABLE_SKILL_GROUPS:
            skill_picks.append(pick)
        elif position in _FANTASY_AMBIGUOUS:
            review_queue.append(_review_row(pick, "unresolved_draft_pick_position"))
        else:
            continue  # clearly non-skill / non-cohort (incl. SAF, G, any unknown) — silently excluded

    # --- primary-key match pass for skill picks ---
    matched: dict[int, list[dict]] = {}
    for index, pick in enumerate(skill_picks):
        key = (
            normalize_name(str(pick.get("pfr_player_name", ""))),
            str(pick.get("position", "")).upper(),
            _norm_school(str(pick.get("college", "")), aliases),
        )
        matched[index] = list(cfbd_by_key.get(key, []))

    # --- collegeAthleteId fallback (only when unmatched rate exceeds threshold) ---
    unmatched = [index for index, rows in matched.items() if not rows]
    total_skill = len(skill_picks)
    unmatched_rate = (len(unmatched) / total_skill) if total_skill else 0.0
    if total_skill and unmatched_rate > drafted_unmatched_fallback_threshold:
        for index in unmatched:
            college_athlete_id = skill_picks[index].get("collegeAthleteId")
            if college_athlete_id is not None and str(college_athlete_id) in cfbd_by_id:
                matched[index] = [cfbd_by_id[str(college_athlete_id)]]

    # --- final per-pick classification (LAST) ---
    # emit_candidates[index] = (cfbd_row, cfbd_id) for picks with a clean 1:1 match.
    emit_candidates: dict[int, tuple[dict, str]] = {}
    for index, pick in enumerate(skill_picks):
        candidates = matched[index]
        if not candidates:
            review_queue.append(_review_row(pick, "draft_truth_match_missing"))
        elif len(candidates) > 1:
            review_queue.append(_review_row(pick, "draft_truth_match_ambiguous"))
        elif candidates[0].get("id") is None:
            review_queue.append(_malformed_review_row(pick))  # fail closed (spec §4 D4)
        else:
            emit_candidates[index] = (candidates[0], str(candidates[0]["id"]))

    # --- inverse-collision pass (spec §4 D-2): one CFBD identity claimed by >1 pick ---
    picks_by_cfbd_id: dict[str, list[int]] = {}
    for index, (_cfbd_row, cfbd_id) in emit_candidates.items():
        picks_by_cfbd_id.setdefault(cfbd_id, []).append(index)

    rows: list[dict] = []
    for indices in picks_by_cfbd_id.values():
        if len(indices) > 1:
            # >1 drafted pick claims the same CFBD identity → fail closed, none emitted.
            for index in indices:
                review_queue.append(
                    _review_row(skill_picks[index], "draft_truth_match_ambiguous")
                )
        else:
            index = indices[0]
            cfbd_row, _cfbd_id = emit_candidates[index]
            rows.append(
                _emit_row(
                    cfbd_row,
                    skill_picks[index],
                    source_name=source_name,
                    source_snapshot_id_str=source_snapshot_id_str,
                    provenance_source=provenance_source,
                )
            )

    return rows, review_queue
