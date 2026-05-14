---
document: Phase 9.5 — Prospect Identity Join
version: 1.0.0
last_updated: 2026-05-14
author: Claude Code
status: APPROVED FOR IMPLEMENTATION (patched 2026-05-14 — examples corrected to true 2026 class)
phase: 9.5
depends_on: Phase 9 (Market Overlay, PR #25 merged)
---

# Phase 9.5 — Prospect Identity Join

## Problem Statement

After Phase 9, `market_overlay` is `None` for every pre-draft prospect on the Rookie Board.
The join key is `pvo.sleeper_id → fc_entry["player"]["sleeperId"]`.
`_map_prospect_to_pvo` builds a `PlayerIdentity` with `sleeper_id=None`, so no join is
ever attempted. This is the largest user-visible gap: dynasty values for 2026 prospects
(Jeanty, Sanders, Abdul-Quddus, etc.) exist in FantasyCalc but never surface in the product.

## Resolution Path (Priority Order)

Three stages. Each stage falls through to the next only on no-match.

```
Stage 1 — Explicit sleeper_id on request
  └─ Caller passes sleeper_id directly in ProspectRequest
  └─ Resolution method: "explicit"

Stage 2 — Alias bridge lookup
  └─ Human-curated JSON file: app/data/prospect_alias_bridge.json
  └─ Key: normalized_name (lowercase, no punctuation) + position + draft_class
  └─ Resolution method: "alias_bridge"

Stage 3 — Unresolved: log and skip
  └─ Write one line to app/data/prospect_identity_review.jsonl
  └─ Return (None, "unresolved_logged")
  └─ overlay stays None — correct and honest
```

**Name fuzzy matching (edit-distance, phonetic, etc.) is NOT implemented in this phase.**
If Stage 2 fails, the prospect joins the review log. A human curates the bridge.

## Alias Bridge Schema

**File:** `app/data/prospect_alias_bridge.json`

```json
{
  "bridge_version": "2026-05-14",
  "notes": "Human-curated. Seeded from resources/prospect_identity_2026.json (nfl_data_py verified, snapshot 2026-05-09) plus Sleeper API confirmation for Jr./II suffix entries. Update before each rookie draft.",
  "entries": [
    {
      "dg_name": "Fernando Mendoza",
      "normalized_name": "fernando mendoza",
      "position": "QB",
      "draft_class": 2026,
      "sleeper_id": "13269",
      "nfl_team": "LVR",
      "verification": "sleeper_api_confirmed"
    },
    {
      "dg_name": "Omar Cooper Jr.",
      "normalized_name": "omar cooper jr",
      "position": "WR",
      "draft_class": 2026,
      "sleeper_id": "13276",
      "nfl_team": "NYJ",
      "verification": "sleeper_api_confirmed",
      "notes": "Sleeper stores as 'Omar Cooper' (no suffix) — normalized forms differ; bridge is the source of truth"
    }
  ]
}
```

Fields:
- `dg_name` — display name for human readability
- `normalized_name` — lowercase, single spaces, no punctuation (join key)
- `position` — uppercase two-char position (join key)
- `draft_class` — year of NFL draft (join key)
- `sleeper_id` — Sleeper player_id string (the FC join key)
- `nfl_team` — optional, informational only
- `verification` — `"sleeper_api_confirmed"` | `"manual_lookup"` | `"unverified"`

**Normalization rule:** `re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()`
Applies to both bridge entries and incoming `ProspectRequest.name` at lookup time.

## Review Log Schema

**File:** `app/data/prospect_identity_review.jsonl` (newline-delimited JSON, append-only)

```json
{"ts": "2026-05-14T02:47:11Z", "name": "Tetairoa McMillan", "normalized_name": "tetairoa mcmillan", "position": "WR", "draft_class": 2026, "stage_reached": "alias_bridge_miss", "sleeper_id_resolved": null, "reviewer": null}
```

- Append on every Stage 3 miss. Never truncate the file.
- `reviewer` is null until a human curates the entry and adds the resolved id to the alias bridge.

## New / Changed Files

| File | Action |
|------|--------|
| `src/dynasty_genius/adapters/prospect_identity_resolver.py` | **New** — three-stage resolver |
| `app/data/prospect_alias_bridge.json` | **New** — curated bridge (seed with top ~20 2026 prospects) |
| `app/data/prospect_identity_review.jsonl` | **New** (created on first miss, gitignored) |
| `app/api/routes/rookies.py` | **Modify** — add optional `sleeper_id` to `ProspectRequest`; call resolver |
| `tests/contract/test_prospect_identity_resolver.py` | **New** — 8 contract tests |
| `.gitignore` | **Modify** — add `app/data/prospect_identity_review.jsonl` |

## Resolver Module Interface

```python
# src/dynasty_genius/adapters/prospect_identity_resolver.py

def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation, collapse spaces."""

def resolve_prospect_sleeper_id(
    name: str,
    position: str,
    draft_class: int,
    explicit_sleeper_id: str | None = None,
) -> tuple[str | None, str]:
    """
    Returns (sleeper_id | None, resolution_method).

    resolution_method is one of:
      "explicit"            — caller supplied sleeper_id directly
      "alias_bridge"        — matched in prospect_alias_bridge.json
      "unresolved_logged"   — no match; review entry written
    """

def load_alias_bridge() -> dict:
    """Load and parse prospect_alias_bridge.json. Cached after first load."""
```

The resolver is **pure I/O** — no network calls, no FC data dependency.
The FC join still happens inside `compute_divergence` exactly as before.

## Route Change: ProspectRequest

```python
class ProspectRequest(BaseModel):
    name: str
    position: str
    pick: int
    round: int
    age: float
    sleeper_id: Optional[str] = None        # new — explicit override
    draft_class: Optional[int] = None       # new — defaults to current year
```

```python
def _map_prospect_to_pvo(prospect: ProspectRequest):
    from src.dynasty_genius.adapters.prospect_identity_resolver import resolve_prospect_sleeper_id
    draft_class = prospect.draft_class or date.today().year
    resolved_sid, _ = resolve_prospect_sleeper_id(
        prospect.name,
        prospect.position,
        draft_class,
        explicit_sleeper_id=prospect.sleeper_id,
    )
    identity = PlayerIdentity(
        dg_id=f"prospect_{prospect.position}_{prospect.pick}",
        full_name=prospect.name,
        position=prospect.position,
        nfl_team=None,
        sleeper_id=resolved_sid,          # populated when resolvable
        verification_status="UNVERIFIED"
    )
    ...
```

## Contract Tests (8 required)

| # | Test | Expected |
|---|------|----------|
| 1 | `normalize_name` strips punctuation and lowercases | `"Tetairoa McMillan"` → `"tetairoa mcmillan"` |
| 2 | `normalize_name` collapses apostrophes (e.g. De'Zhaun Stribling) | `"De'Zhaun Stribling"` → `"dezhaun stribling"` — apostrophe and case removed |
| 3 | Stage 1: explicit sleeper_id short-circuits bridge lookup | returns `("9999", "explicit")` |
| 4 | Stage 2: alias bridge hit returns correct sleeper_id | returns `(expected_sid, "alias_bridge")` for seeded fixture entry |
| 5 | Stage 2: misspelled name ("Carnel Tate" vs "Carnell Tate") returns unresolved — no fuzzy match | returns `(None, "unresolved_logged")` |
| 6 | Stage 3: unresolved miss writes entry to review log | review log file exists and contains one matching JSON line |
| 7 | Resolver is idempotent — calling twice for same miss appends two lines, not one | review log has two entries |
| 8 | Integration: `_map_prospect_to_pvo` sets `pvo.sleeper_id` when alias bridge matches | `pvo.sleeper_id == expected_sid` |

## Governance Constraints

- **No fuzzy matching.** Edit-distance, soundex, and similar are NOT in scope. They produce
  silent wrong joins that corrupt market overlay data. The review log is the right fallback.
- **Bridge is human-curated.** No agent may auto-populate `sleeper_id` by calling Sleeper API
  at request time. Sleeper API calls belong in a data pipeline, not in a hot request path.
- **Review log is append-only and gitignored.** It contains real player-name lookups and is
  operational state, not source code.
- **Bridge file IS committed.** It is human-reviewed configuration, versioned with the codebase.
- **Market overlay leakage rule unchanged.** The resolver only supplies a join key — no FC value
  enters Engine A or Engine B training.
- **Verification status.** `PlayerIdentity.verification_status` for prospects resolved via alias
  bridge should be `"PENDING"` (not `"VERIFIED"`) until David manually confirms the mapping.

## Implementation Order (TDD gates)

```
Task 9.5.0 — Resolver + bridge
  RED:  write 7 contract tests (tests 1-7) against not-yet-created resolver
  GREEN: create prospect_alias_bridge.json + prospect_identity_resolver.py
  COMMIT: "feat(phase9.5): prospect identity resolver + alias bridge"

Task 9.5.1 — Route wiring
  RED:  write test 8 (integration: pvo.sleeper_id set for aliased prospect)
  GREEN: update ProspectRequest + _map_prospect_to_pvo in rookies.py
  COMMIT: "feat(phase9.5): wire resolver into Rookie Board route"

Task 9.5.2 — .gitignore + full suite
  Add app/data/prospect_identity_review.jsonl to .gitignore
  Run full suite — verify 376+ tests pass, 0 fail
  COMMIT: "chore(phase9.5): gitignore review log, postflight"
```

## Open Questions (do not resolve without David input)

1. **Sleeper ID sourcing.** Initial bridge is seeded from `resources/prospect_identity_2026.json`
   (nfl_data_py verified, 2026-05-09 snapshot) — 75 entries with confirmed IDs. Five Jr./II
   suffix entries (Omar Cooper Jr., Chris Brazzell II, Mike Washington Jr., Kevin Coleman Jr.,
   Emmanuel Henderson Jr.) confirmed by David via Sleeper API lookup and included at bridge
   version 2026-05-14.

2. **Bridge update cadence.** The alias bridge will need updates after the 2026 draft clears
   (players get assigned to teams, IDs may be recycled or reassigned). Who is responsible?

3. **Stage 3 as eventual Stage 2.** The review log is the input queue for new alias bridge
   entries. Should there be a helper script (`tools/promote_review_to_bridge.py`) to make
   that workflow frictionless? Defer unless David asks.

4. **`draft_class` default.** Defaulting to `date.today().year` is correct for the pre-draft
   window but ambiguous in January (2026 class or 2027?). Accept the ambiguity for now and
   revisit when the 2027 class becomes relevant.
