"""Subsystem 4 — Prospect ↔ NFL Bridge.

Cross-domain identity infrastructure: maps S3's pre-draft prospect_uuid
(opaque cpr_<uuid4>, confirmed only) to realized NFL gsis_id (from nflreadr
draft truth) at draft time. Manual-first review queue + promotion lifecycle;
per-file atomic writes; decision-log replay over genesis state per S3 §6.3.

Single-module implementation organized in labeled sections:
- Constants & versions
- Schema (Pydantic 2.x)
- Exceptions
- Validation (rules from spec §3.2)
- Atomic write helpers           (Task 2)
- Decision log + replay          (Task 2)
- Discovery / candidate matching (Task 3)
- Promotion lifecycle            (Task 4)

Spec: docs/superpowers/specs/2026-05-28-subsystem-4-backtest-harness-design.md
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeProspectRegistry,
    normalize_name,
)

# ======================================================================
# Constants & versions
# ======================================================================

BRIDGE_SCHEMA_VERSION: str = "prospect_nfl_bridge_v1.0.0"
NFL_DOMAIN_MATCHER_VERSION: str = "cpr_nfl_bridge_matcher_v1.0.0"


# ======================================================================
# Schema (Pydantic 2.x)
# ======================================================================


class ProspectNflBridgeEntry(BaseModel):
    """Spec §3.1: cross-domain bridge entry mapping pre-draft prospect_uuid →
    realized NFL identity. Accepted-only artifact entries (`confirm` and `udfa`
    decisions); rejects/defers live only in the decision log + review queue."""

    model_config = ConfigDict(extra="forbid")

    # identity
    prospect_uuid: str
    gsis_id: Optional[str] = None
    pfr_id: Optional[str] = None

    # context
    draft_year: int
    draft_pick_no: Optional[int] = None
    draft_round: Optional[int] = None
    nfl_team: Optional[str] = None
    udfa: bool

    # provenance of the nflreadr snapshot used at decision time (spec §3.1 + §3.2 rule 5)
    nflreadr_source: str
    nflreadr_season: int
    draft_truth_content_hash: str
    nflreadr_fetched_at: str

    evidence_snapshot: Optional[dict[str, Any]] = None

    # decision audit (no nested status_history; that's S3 vocabulary)
    event_id: str
    decided_at: str
    reviewer_id: str
    decision: Literal["confirm", "udfa"]
    note: Optional[str] = None


# ======================================================================
# Exceptions
# ======================================================================


class BridgeValidationError(RuntimeError):
    """Raised when a bridge graph validation reveals an inconsistency."""


class BridgeEvidenceRequiredError(ValueError):
    """`udfa` promotion requires non-empty --evidence per spec §3.3."""


class BridgeConflictingDecisionError(RuntimeError):
    """Same prospect_uuid already has a different ACCEPTED decision in the log
    (procedural decisions reject/defer do not conflict with later accepted)."""


# ======================================================================
# Validation (rules from spec §3.2, per-entry shape checks)
# ======================================================================


def validate_bridge_entry(entry: ProspectNflBridgeEntry) -> list[str]:
    """Per-entry shape validation. Returns a list of human-readable errors
    (empty list = valid). Cross-entry invariants (1:1) are checked in
    ``validate_bridge_graph``; S3 confirmation + draft_year invariants are
    checked in ``validate_against_s3`` (Round 2 patch 1)."""
    errors: list[str] = []
    if entry.udfa:
        # spec §3.2 rule 4: udfa=True ⇒ 5 strict null fields
        for field in ("gsis_id", "pfr_id", "draft_pick_no", "draft_round", "nfl_team"):
            if getattr(entry, field) is not None:
                errors.append(
                    f"udfa=True requires {field}=None (spec §3.2 rule 4); got "
                    f"{getattr(entry, field)!r}"
                )
    else:
        # spec §3.2 rule 5: udfa=False ⇒ 4 required NFL fields
        for field in ("gsis_id", "draft_pick_no", "draft_round", "nfl_team"):
            if getattr(entry, field) is None:
                errors.append(
                    f"udfa=False requires {field} present (spec §3.2 rule 5); "
                    f"got None"
                )
        # pfr_id is nullable secondary; not required even when udfa=False
    return errors


def validate_against_s3(
    entry: ProspectNflBridgeEntry,
    *,
    s3_registry: CollegeProspectRegistry,
) -> list[str]:
    """Round 2 patch 1 (Codex plan review): spec §3.2 rules 1 + 2 require S3
    knowledge at bridge write time. Caller passes a loaded S3
    ``CollegeProspectRegistry``.

    Returns errors if:
    - ``prospect_uuid`` is not present in S3 (unknown)
    - ``prospect_uuid`` is in S3 but not ``verification_status="confirmed"``
    - bridge entry's ``draft_year`` != S3 row's ``draft_class``
    """
    errors: list[str] = []
    s3_row = s3_registry.entries.get(entry.prospect_uuid)
    if s3_row is None:
        errors.append(
            f"prospect_uuid {entry.prospect_uuid} not in S3 registry (spec §3.2 rule 1)"
        )
        return errors  # can't check rule 2 without an S3 row
    if s3_row.verification_status != "confirmed":
        errors.append(
            f"prospect_uuid {entry.prospect_uuid} has S3 status="
            f"{s3_row.verification_status!r} (not confirmed; spec §3.2 rule 1)"
        )
    if entry.draft_year != s3_row.draft_class:
        errors.append(
            f"bridge draft_year={entry.draft_year} != S3 row's draft_class="
            f"{s3_row.draft_class} (spec §3.2 rule 2)"
        )
    return errors


# ======================================================================
# Atomic write helpers + decision log + replay (spec §3.2 rule 6, §3.3)
# ======================================================================

import json  # noqa: E402  (grouped with the persistence section it serves)
import os  # noqa: E402
from pathlib import Path  # noqa: E402

from pydantic import Field  # noqa: E402


class CollegeProspectBridge(BaseModel):
    """Container for accepted-only bridge entries (`confirm` + `udfa` decisions).
    Decision-log replay reconstructs this from missing/empty genesis."""

    model_config = ConfigDict(extra="forbid")

    metadata: dict[str, Any] = Field(default_factory=dict)
    entries: list[ProspectNflBridgeEntry] = Field(default_factory=list)


def load_bridge(path: Path) -> CollegeProspectBridge:
    """Spec parity with S3 load_registry: missing or empty file → empty bridge."""
    if not path.exists():
        return CollegeProspectBridge()
    text = path.read_text()
    if not text.strip():
        return CollegeProspectBridge()
    raw = json.loads(text)
    return CollegeProspectBridge.model_validate(raw)


def atomic_write_bridge(bridge: CollegeProspectBridge, path: Path) -> None:
    """Per-file atomic write via sibling .tmp then ``os.replace`` (S3 §6.4 pattern)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = {
        "metadata": bridge.metadata,
        "entries": [e.model_dump(mode="json") for e in bridge.entries],
    }
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True))
    os.replace(tmp, path)


def load_decision_log(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def atomic_write_decision_log(events: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = "\n".join(json.dumps(e, sort_keys=True) for e in events)
    if events:
        payload += "\n"
    tmp.write_text(payload)
    os.replace(tmp, path)


def apply_decision_event(event: dict[str, Any], bridge: CollegeProspectBridge) -> None:
    """Spec §3.2 rule 6: replay applies ONLY accepted (`confirm` and `udfa`)
    events to mutate the bridge artifact. `reject` and `defer` events are
    recorded in the log for audit but do NOT mutate the bridge."""
    decision = event.get("decision")
    if decision in ("confirm", "udfa"):
        entry_dict = event.get("entry")
        if entry_dict is None:
            return  # malformed event; skip
        entry = ProspectNflBridgeEntry.model_validate(entry_dict)
        bridge.entries.append(entry)
    # reject / defer: no mutation


def replay_decision_log(*, log_path: Path, bridge_path: Path) -> None:
    """Spec §3.2 rule 6: replay over GENESIS state (missing or empty bridge file).
    Applies events from the log in temporal order via ``apply_decision_event``,
    reconstructs the accepted-only artifact, atomic-writes the result.

    Round 2 patch 3 (Codex plan review): fail-closed on non-empty genesis.
    Replay must start from missing/empty bridge per spec §3.2 rule 6 — appending
    to a non-empty file would silently produce a different artifact than the
    live path and is the exact failure mode the spec language forbids.
    """
    bridge = load_bridge(bridge_path)
    if bridge.entries:
        raise BridgeValidationError(
            f"replay_decision_log requires missing or empty bridge genesis at "
            f"{bridge_path}; got {len(bridge.entries)} pre-existing entries "
            f"(spec §3.2 rule 6)"
        )
    events = load_decision_log(log_path)
    for event in events:
        apply_decision_event(event, bridge)
    atomic_write_bridge(bridge, bridge_path)


# ======================================================================
# Discovery / NFL-domain candidate matching (spec §3.3 stage i)
# ======================================================================

from dataclasses import dataclass  # noqa: E402

from src.dynasty_genius.identity.college_prospect_identity import (  # noqa: E402
    NormalizedCollegeProspectRow,
)
from src.dynasty_genius.identity.college_prospect_identity import (  # noqa: E402
    RegistryEntry as S3RegistryEntry,
)
from src.dynasty_genius.identity.college_prospect_identity import (  # noqa: E402
    score_candidate as s3_score_candidate,
)


class NflTruthRow(BaseModel):
    """A single row of nflreadr draft truth (column subset we care about)."""

    model_config = ConfigDict(extra="forbid")

    gsis_id: str
    pfr_id: Optional[str] = None
    full_name: str
    normalized_name: str
    position: str
    college: Optional[str] = None
    draft_year: int
    draft_pick_no: int
    draft_round: int
    nfl_team: str
    fetched_at: str


class NflreadrSchemaDriftError(ValueError):
    """A draft-truth source is missing a required column (fail loud, no guessing)."""


class NflreadrSourceContaminationError(ValueError):
    """A draft-truth source row's ``season`` does not match the requested draft_year."""


class NflreadrEmptyTruthError(ValueError):
    """A real/live draft-truth source yielded zero rows (fail closed, never empty-success)."""


class NflTruthLoadDiagnostics(BaseModel):
    """Counted, never-silent diagnostics for a draft-truth load (no silent defaults)."""

    model_config = ConfigDict(extra="forbid")

    truth_rows_loaded: int = 0
    skipped_missing_gsis_id: int = 0
    skipped_bad_pick: int = 0
    skipped_bad_round: int = 0
    skipped_missing_name: int = 0
    skipped_missing_position: int = 0
    skipped_missing_team: int = 0
    required_columns_seen: list[str] = Field(default_factory=list)


class NflreadrTruthLoadResult(BaseModel):
    """Typed result of a draft-truth load: mapped rows + load diagnostics."""

    rows: list[NflTruthRow]
    diagnostics: NflTruthLoadDiagnostics


# Required source columns for the draft-truth load (schema gate; no guessed columns).
_REQUIRED_DRAFT_COLUMNS: frozenset[str] = frozenset({
    "season", "round", "pick", "team", "gsis_id",
    "pfr_player_id", "pfr_player_name", "position", "college",
})


def _coerce_draft_truth_row_or_skip(
    row: dict[str, Any],
    *,
    draft_year: int,
    fetched_at: str,
    diagnostics: NflTruthLoadDiagnostics,
) -> Optional[NflTruthRow]:
    """Map one source row to an ``NflTruthRow`` or count a fail-closed per-row skip.

    Present-key/bad-value rows are skipped and tallied (never a silent default); the
    missing-column schema gate and season contamination are enforced by the caller
    before this. Numeric ``pick``/``round`` use ``type(...) is int`` so ``bool``
    (``type(True) is bool``), ``float``, and numeric strings are skipped, not coerced.
    """
    gsis_id = row["gsis_id"]
    if not isinstance(gsis_id, str) or not gsis_id:
        diagnostics.skipped_missing_gsis_id += 1
        return None

    pick = row["pick"]
    if type(pick) is not int:
        diagnostics.skipped_bad_pick += 1
        return None

    draft_round = row["round"]
    if type(draft_round) is not int:
        diagnostics.skipped_bad_round += 1
        return None

    pfr_player_name = row["pfr_player_name"]
    if not isinstance(pfr_player_name, str) or not pfr_player_name:
        diagnostics.skipped_missing_name += 1
        return None

    position = row["position"]
    if not isinstance(position, str) or not position:
        diagnostics.skipped_missing_position += 1
        return None

    team = row["team"]
    if not isinstance(team, str) or not team:
        diagnostics.skipped_missing_team += 1
        return None

    pfr_player_id = row["pfr_player_id"]
    college = row["college"]
    return NflTruthRow(
        gsis_id=gsis_id,
        pfr_id=pfr_player_id if pfr_player_id else None,
        full_name=pfr_player_name,
        normalized_name=normalize_name(pfr_player_name),
        position=position,
        college=college if college else None,
        draft_year=draft_year,
        draft_pick_no=pick,
        draft_round=draft_round,
        nfl_team=team,
        fetched_at=fetched_at,
    )


def _load_draft_truth_from_fixture(
    fixture_path: Path,
    *,
    draft_year: int,
    fetched_at_override: Optional[str],
) -> NflreadrTruthLoadResult:
    """Load + validate draft truth from a source-shaped fixture (real + fixture path)."""
    payload = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    rows = payload.get("rows", [])

    # Empty source fails closed — never a vacuous schema-gate pass / empty-success.
    if not rows:
        raise NflreadrEmptyTruthError(
            f"draft-truth fixture {fixture_path} contains zero rows"
        )

    # Schema gate: every required column KEY must be present in every source row.
    # A missing column is drift; a present key with a bad value is a counted skip.
    for column in _REQUIRED_DRAFT_COLUMNS:
        if not all(column in row for row in rows):
            raise NflreadrSchemaDriftError(
                f"draft-truth source missing required column '{column}'"
            )

    # fetched_at is supplied deterministically (raw rows carry none): override wins,
    # else the fixture's metadata.fetched_at, preserved verbatim (no normalization).
    fetched_at = fetched_at_override
    if fetched_at is None:
        fetched_at = payload.get("metadata", {}).get("fetched_at")
    if fetched_at is None:
        raise ValueError(
            f"draft-truth fixture {fixture_path} missing metadata.fetched_at "
            "and no fetched_at override supplied"
        )

    diagnostics = NflTruthLoadDiagnostics(
        required_columns_seen=sorted(_REQUIRED_DRAFT_COLUMNS),
    )
    truth_rows: list[NflTruthRow] = []
    for row in rows:
        # Season integrity is fail-loud and runs BEFORE per-row skip accounting:
        # a contaminated source must halt the load, not silently drop the bad row.
        # type(...) is int excludes bool (type(True) is bool); no int() coercion of
        # strings/floats — a wrong-typed season is contamination, never a rescued pass.
        season = row["season"]
        if type(season) is not int or season != draft_year:
            raise NflreadrSourceContaminationError(
                f"draft-truth source contamination: row gsis_id={row['gsis_id']!r} "
                f"has season {season!r} != requested draft_year {draft_year}"
            )
        truth_row = _coerce_draft_truth_row_or_skip(
            row,
            draft_year=draft_year,
            fetched_at=fetched_at,
            diagnostics=diagnostics,
        )
        if truth_row is not None:
            truth_rows.append(truth_row)
    diagnostics.truth_rows_loaded = len(truth_rows)

    return NflreadrTruthLoadResult(rows=truth_rows, diagnostics=diagnostics)


def load_nflreadr_draft_truth(
    draft_year: int,
    *,
    data_mode: str,
    fixture_path: Optional[Path] = None,
    fetched_at: Optional[str] = None,
) -> NflreadrTruthLoadResult:
    """Load draft-capital truth rows for a draft class, fail-closed.

    See ``docs/superpowers/specs/2026-06-01-s4-v2-draft-truth-loader-design.md``.
    Task 2 implements the fixture-backed path (``real`` + ``fixture_path``); the
    synthetic convention path and the live draft-source path arrive in later tasks.
    """
    if fixture_path is not None:
        return _load_draft_truth_from_fixture(
            fixture_path,
            draft_year=draft_year,
            fetched_at_override=fetched_at,
        )
    raise NotImplementedError(
        "load_nflreadr_draft_truth: only fixture-backed loading is implemented (Task 2)."
    )


# NFL-domain position taxonomy (different from S3's offense-only college whitelist).
# Frozen sets keep this auditable + immutable.
NFL_POSITION_WHITELIST: frozenset[frozenset[str]] = frozenset({
    # Pass-rush / linebacker transitions
    frozenset({"EDGE", "OLB"}),
    frozenset({"EDGE", "DE"}),
    frozenset({"DE", "DT"}),       # 3-4 vs 4-3 alignment differences
    # Secondary
    frozenset({"S", "FS"}),
    frozenset({"S", "SS"}),
    frozenset({"FS", "SS"}),
    frozenset({"CB", "NB"}),       # nickelback
    # Linebacker family
    frozenset({"ILB", "MLB"}),
    frozenset({"LB", "ILB"}),
    frozenset({"LB", "OLB"}),
    frozenset({"LB", "MLB"}),
    # Offense
    frozenset({"OG", "OT"}),       # interior swing
    frozenset({"OT", "OL"}),
    frozenset({"OG", "OL"}),
    frozenset({"C", "OG"}),
})

# Hard-block offense ↔ defense pairings (never compatible regardless of name match)
_NFL_OFFENSE: frozenset[str] = frozenset({
    "QB", "RB", "FB", "WR", "TE", "OL", "OT", "OG", "C",
})
_NFL_DEFENSE: frozenset[str] = frozenset({
    "DL", "DE", "DT", "EDGE", "LB", "ILB", "MLB", "OLB",
    "CB", "NB", "S", "FS", "SS", "DB",
})


def is_nfl_position_pair_compatible(college_pos: str, nfl_pos: str) -> bool:
    """NFL-domain position compatibility. Direct exact-match always allowed.
    Whitelist transitions allowed. Offense ↔ defense always blocked."""
    if college_pos.upper() == nfl_pos.upper():
        return True
    cu, nu = college_pos.upper(), nfl_pos.upper()
    if (cu in _NFL_OFFENSE and nu in _NFL_DEFENSE) or (
        cu in _NFL_DEFENSE and nu in _NFL_OFFENSE
    ):
        return False
    if frozenset({cu, nu}) in NFL_POSITION_WHITELIST:
        return True
    return False


@dataclass(frozen=True)
class NflBridgeCandidate:
    """Discovery output: a candidate pairing of college prospect → nflreadr row."""

    prospect_uuid: str
    gsis_id: str
    nfl_truth_row: dict[str, Any]
    match_score: float
    score_breakdown: dict[str, float]
    risk_flags: tuple[str, ...]
    matcher_algorithm_version: str


def score_nfl_candidate(
    college: S3RegistryEntry,
    nfl_truth: NflTruthRow,
) -> NflBridgeCandidate:
    """Score a college → NFL candidate using S3's score_candidate for name
    similarity, then apply NFL-domain position taxonomy."""
    # Adapt the NFL truth row into an S3-shaped row so we can call
    # s3_score_candidate for the name/school similarity scoring.
    nfl_as_college_shape = NormalizedCollegeProspectRow.model_validate({
        "raw_name": nfl_truth.full_name,
        "normalized_name": nfl_truth.normalized_name,
        "full_name": nfl_truth.full_name,
        "position": nfl_truth.position,
        "position_group": nfl_truth.position,
        "draft_class": nfl_truth.draft_year,
        "current_school": nfl_truth.college or "",
        "prior_schools": [],
        "cfbd_athlete_id": None,
        "cfb_player_id": None,
        "pfr_id": None,
        "gsis_id": None,
        "sleeper_id": None,
        "source": "nflreadr",
        "source_record_id": f"nflreadr_{nfl_truth.gsis_id}",
        "source_snapshot_id": f"nflreadr_{nfl_truth.draft_year}",
        "id_provenance": {
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        "notes": None,
    })

    # s3_score_candidate enforces draft_class equality (hard-zeros otherwise);
    # we set nfl_truth.draft_year == college.draft_class via the validated rows.
    s3_candidate = s3_score_candidate(nfl_as_college_shape, college)

    risk_flags: list[str] = list(s3_candidate.risk_flags)
    if not is_nfl_position_pair_compatible(college.position, nfl_truth.position):
        # Hard-block: drop score to 0
        return NflBridgeCandidate(
            prospect_uuid=college.prospect_uuid,
            gsis_id=nfl_truth.gsis_id,
            nfl_truth_row=nfl_truth.model_dump(),
            match_score=0.0,
            score_breakdown={**s3_candidate.score_breakdown, "nfl_position_block": 1.0},
            risk_flags=("position_hard_blocked",),
            matcher_algorithm_version=NFL_DOMAIN_MATCHER_VERSION,
        )

    if college.position.upper() != nfl_truth.position.upper():
        # Whitelist transition allowed
        risk_flags.append("position_transition_allowed")

    return NflBridgeCandidate(
        prospect_uuid=college.prospect_uuid,
        gsis_id=nfl_truth.gsis_id,
        nfl_truth_row=nfl_truth.model_dump(),
        match_score=s3_candidate.match_score,
        score_breakdown=s3_candidate.score_breakdown,
        risk_flags=tuple(risk_flags),
        matcher_algorithm_version=NFL_DOMAIN_MATCHER_VERSION,
    )


def surface_nfl_bridge_candidates(
    college: S3RegistryEntry,
    nfl_truth_rows: list[NflTruthRow],
    *,
    min_score: float = 0.75,
    top_k: int = 5,
) -> list[NflBridgeCandidate]:
    """Surface up to ``top_k`` NFL truth candidates above ``min_score`` for a
    given college prospect. Hard-blocked position pairings are excluded;
    whitelist transitions surface only when name match clears ``min_score``."""
    scored: list[NflBridgeCandidate] = []
    for nfl in nfl_truth_rows:
        if nfl.draft_year != college.draft_class:
            continue  # cross-class blocked
        cand = score_nfl_candidate(college, nfl)
        if cand.match_score >= min_score and "position_hard_blocked" not in cand.risk_flags:
            scored.append(cand)
    scored.sort(key=lambda c: c.match_score, reverse=True)
    return scored[:top_k]


# ======================================================================
# Promotion lifecycle (spec §3.3 stages ii–iii)
# ======================================================================

import uuid as _uuid  # noqa: E402  (grouped with the promotion section)
from datetime import datetime, timezone  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# Round 2 patch 2 (Codex plan review): differentiate accepted decisions
# (which alter the bridge artifact) from procedural decisions (which don't).
# A prior procedural never blocks a later accepted; an accepted-vs-different-accepted
# is a conflict.
_ACCEPTED_DECISIONS: frozenset[str] = frozenset({"confirm", "udfa"})
_PROCEDURAL_DECISIONS: frozenset[str] = frozenset({"reject", "defer"})


@dataclass(frozen=True)
class PromotionDecision:
    """Per spec §3.3: 4 decisions (confirm, udfa, reject, defer).
    ``confirm`` and ``udfa`` carry a populated ``entry`` (ProspectNflBridgeEntry sans
    auto-filled audit fields). ``reject`` and ``defer`` carry only ``prospect_uuid``
    and an optional note."""

    kind: Literal["confirm", "udfa", "reject", "defer"]
    entry: Optional[ProspectNflBridgeEntry] = None
    prospect_uuid: Optional[str] = None


@dataclass(frozen=True)
class PromotionResult:
    exit_code: int
    event_id: Optional[str] = None


def validate_bridge_graph(bridge: CollegeProspectBridge) -> list[str]:
    """Cross-entry invariants (spec §3.2 rule 3): 1:1 within draft_year for
    prospect_uuid and non-null gsis_id."""
    errors: list[str] = []
    seen_uuids: set[str] = set()
    seen_gsis: set[str] = set()
    for entry in bridge.entries:
        if entry.prospect_uuid in seen_uuids:
            errors.append(
                f"duplicate prospect_uuid {entry.prospect_uuid} in bridge entries"
            )
        seen_uuids.add(entry.prospect_uuid)
        if entry.gsis_id is not None:
            if entry.gsis_id in seen_gsis:
                errors.append(
                    f"duplicate gsis_id {entry.gsis_id} in bridge entries"
                )
            seen_gsis.add(entry.gsis_id)
    return errors


def _close_review_queue_row(
    identity_dir: Path,
    draft_year: int,
    review_id: str,
    decision_kind: str,
    decided_at: str,
    event_id: str,
    note: Optional[str],
) -> None:
    """Spec §3.3 third leg of three-point logging."""
    for path in identity_dir.glob(f"prospect_nfl_review_queue_{draft_year}_*.jsonl"):
        lines = path.read_text().splitlines()
        updated: list[str] = []
        changed = False
        for line in lines:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("review_id") == review_id and row.get("decision") is None:
                row["decision"] = decision_kind
                row["decided_at"] = decided_at
                row["event_id"] = event_id
                if note is not None:
                    row["note"] = note
                changed = True
            updated.append(json.dumps(row, sort_keys=True))
        if changed:
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text("\n".join(updated) + "\n")
            os.replace(tmp, path)
            return


def promote_bridge_candidate(
    *,
    review_id: Optional[str],
    decision: PromotionDecision,
    identity_dir: Path,
    draft_year: int,
    reviewer_id: str,
    evidence: Optional[str],
    note: Optional[str],
    s3_registry: Optional[CollegeProspectRegistry] = None,
) -> PromotionResult:
    """Spec §3.3: the only blessed write path for bridge decisions. Three-point
    logging in dependency-safe order: decision_log → bridge_artifact →
    review_queue closure.

    Round 2 patch 1 (Codex plan review): for ``confirm``/``udfa`` decisions, an
    ``s3_registry`` MUST be supplied so spec §3.2 rules 1+2 can be validated
    (prospect_uuid confirmed in S3; draft_year == S3 draft_class). When the
    parameter is omitted for an accepted decision, the function returns
    exit_code=1; the CLI loads S3 and passes it through.

    Round 2 patch 2: conflict semantics differentiate ACCEPTED decisions
    (confirm, udfa) from PROCEDURAL decisions (reject, defer). Procedural prior
    does NOT block a later accepted. Accepted-vs-different-accepted DOES conflict.
    Same-decision rerun is idempotent.

    Round 2 patch 7: ``entry.draft_year`` MUST equal the ``draft_year`` kwarg
    (which selects the artifact file). Without this guard, a mismatched library
    call could silently write a wrong-year entry into the wrong artifact file.
    """
    if decision.kind == "udfa" and not (evidence and evidence.strip()):
        raise BridgeEvidenceRequiredError(
            "udfa promotion requires non-empty --evidence per spec §3.3"
        )

    identity_dir.mkdir(parents=True, exist_ok=True)
    bridge_path = identity_dir / f"prospect_to_nfl_bridge_{draft_year}.json"
    log_path = identity_dir / f"prospect_nfl_bridge_decision_log_{draft_year}.jsonl"

    # Determine the prospect_uuid being acted on
    if decision.kind in _ACCEPTED_DECISIONS:
        if decision.entry is None:
            return PromotionResult(exit_code=1)
        if s3_registry is None:
            return PromotionResult(exit_code=1)  # Round 2 patch 1: required for accepted
        acted_uuid = decision.entry.prospect_uuid
    else:  # reject / defer
        if decision.prospect_uuid is None:
            return PromotionResult(exit_code=1)
        acted_uuid = decision.prospect_uuid

    # Idempotency / conflict check — Round 2 patch 2 semantics
    existing_log = load_decision_log(log_path)
    for prior in existing_log:
        if prior.get("prospect_uuid") != acted_uuid:
            continue
        prior_kind = prior.get("decision")
        # Idempotent: identical decision is a no-op
        if prior_kind == decision.kind:
            return PromotionResult(exit_code=0, event_id=prior.get("event_id"))
        # Procedural prior never blocks (later run may bring better evidence)
        if prior_kind in _PROCEDURAL_DECISIONS:
            continue
        # Accepted prior + different new decision → conflict
        if prior_kind in _ACCEPTED_DECISIONS:
            raise BridgeConflictingDecisionError(
                f"prospect_uuid {acted_uuid} already has accepted decision="
                f"{prior_kind!r}; refusing to apply {decision.kind}"
            )

    decided_at = _now_iso()
    event_id = f"ev_{_uuid.uuid4()}"

    event: dict[str, Any] = {
        "event_id": event_id,
        "decision": decision.kind,
        "prospect_uuid": acted_uuid,
        "decided_at": decided_at,
        "reviewer_id": reviewer_id,
        "evidence": evidence,
        "note": note,
    }

    bridge = load_bridge(bridge_path)

    if decision.kind in _ACCEPTED_DECISIONS:
        # Build the persistent entry with auto-filled audit fields
        entry_dict = decision.entry.model_dump()
        entry_dict["event_id"] = event_id
        entry_dict["decided_at"] = decided_at
        entry_dict["reviewer_id"] = reviewer_id
        if note is not None:
            entry_dict["note"] = note
        final_entry = ProspectNflBridgeEntry.model_validate(entry_dict)

        # Round 2 patch 7: entry draft_year MUST match the artifact-selecting
        # draft_year arg. Locks the library invariant.
        if final_entry.draft_year != draft_year:
            raise BridgeValidationError(
                f"entry.draft_year={final_entry.draft_year} != promote draft_year="
                f"{draft_year} (artifact selector mismatch; Round 2 patch 7)"
            )

        # Round 2 patch 1: S3 confirmed + draft_year validation (spec §3.2 rules 1+2)
        s3_errors = validate_against_s3(final_entry, s3_registry=s3_registry)
        if s3_errors:
            raise BridgeValidationError("; ".join(s3_errors))

        # Per-entry shape validation
        per_errors = validate_bridge_entry(final_entry)
        if per_errors:
            raise BridgeValidationError("; ".join(per_errors))

        bridge.entries.append(final_entry)

        # Cross-entry validation
        graph_errors = validate_bridge_graph(bridge)
        if graph_errors:
            raise BridgeValidationError("; ".join(graph_errors))

        event["entry"] = final_entry.model_dump(mode="json")

    # Dependency-safe per-file atomic write order
    existing_log.append(event)
    atomic_write_decision_log(existing_log, log_path)
    if decision.kind in _ACCEPTED_DECISIONS:
        atomic_write_bridge(bridge, bridge_path)
    if review_id:
        _close_review_queue_row(
            identity_dir, draft_year, review_id, decision.kind, decided_at, event_id, note
        )

    return PromotionResult(exit_code=0, event_id=event_id)
