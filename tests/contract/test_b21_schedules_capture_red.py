"""RED v8 — B21 `schedules`: one global provider offering, retained losslessly, finality unverified.

SUPERSEDES pin `a1e41fa286c91b43a7dc06e20798e5f402d5124ad5b2e40732b8735a38d00ccb`, and before it
`38fceec11f9a4d623b53dee986fb59efe96fbf12429e18a2950190c9eca9cb86` — which was independently CLEARED,
and which the FIRST REAL RUN OF THE ROUTE THEN FALSIFIED. Earlier still:
`ba5aeaf308ff…` (one source-time class), `abf9ff5f…` (one residual), `c2a6181088ec…` (five), and
`51067f0e…` (nine).

WHAT A CLEARED CONTRACT SUITE STILL GOT WRONG, AND IT IS THE MOST IMPORTANT LESSON IN THIS FILE:
**56 green contracts described a route that could not perform a single capture.** GitHub answers the
release URL with a 302 to a signed asset on `release-assets.githubusercontent.com`. S8 had asserted
that any final URL differing from the requested one was substitution, so the real CLI retrieved the
valid 517,546-byte Parquet and then **exited 1 on our own rule**. Measured 2026-08-09 by an
independent `curl -I` and a real run against a temporary root.

No amount of internal consistency would have found that. Only contact with the provider did — which
is exactly why the ticket's close condition is a real capture and not a green suite.

Two more, from independent probes against the GREEN rather than against this file:

  * **A content-addressed store that trusts its own addresses is not content-addressed.** Seeding
    `content/<sha-of-payload>.parquet` with `b"wrong bytes"` and then recording the valid payload
    reported SUCCESS: the marker claimed the incoming hash, `partial_artifacts()` was empty, and
    `read_raw` returned something else. Silent corruption of the EVIDENCE, which is worse than any
    wrong derived view. Now P3/P3b.
  * **The atomicity contract exercised only the route's own exception.** `FailingAt` raised
    `PublishError` before writing anything, while a production filesystem raises `OSError` from
    `mkdir`, temp writes, links, copies and `os.replace`. Injected for real, it escaped
    unnormalised, rollback never ran, nothing was audited, and orphan artifacts were left behind.
    E1 now carries a `fault` dimension covering the production-shaped exception.

AND TWO MORE, FOUND BY RUNNING THE REPAIRED ROUTE AGAINST THE REAL PROVIDER:

  * **A successful capture wrote SHORT-LIVED CREDENTIALS TO DISK.** The F1 repair recorded the
    delivery URL verbatim, and GitHub's signed asset URL carries signature and JWT query parameters,
    so they landed in the vintage, the marker and the ledger — inside a store that is a REQUIRED
    entry in the backup manifest, so the next daily run would have shipped them offsite. Provenance
    needs scheme, host and path; it never needed the query. Now S9/S9b.
  * **`FailingAt` still raised BEFORE the filesystem was touched**, so even the `os_error` case could
    not reproduce a half-finished write. A probe that wrote `.index.json.tmp` and then raised left
    that temp file behind — falsifying E1's own no-partials invariant while every other assertion in
    it passed. Now the `mid_write` fault.

WHAT v5 GOT WRONG: IT MADE A CONTRACT OUT OF ITS OWN IGNORANCE. Unable to verify the lexical shape
of `gametime` offline, v5 accepted either a time-of-day or an ISO-8601 datetime and called the
widening safe. It was not safe in either direction. Codex then measured the provider's own file at
an immutable revision, and both halves of that guess were wrong:

  * `nfldata/data/games.csv` @ `793d10a99154e8e21240ef03554a0366f98dbe21` (committed
    2026-08-08T22:35:12Z), read with `csv.DictReader`: **7,548 rows / 46 columns**. `gametime` is
    **empty in 259** and non-empty in **7,289**, and **7,289 of 7,289** non-empty values are strict
    24-hour `HH:MM`. **Zero** take any other form. The 2026 subset is 272 rows, none empty. The
    published `load_schedules` reference agrees (`gametime <chr>`, e.g. `20:20`, `13:00`).

  1. **The ISO alternative admitted a drift that has never happened** — so it is withdrawn, and the
     exact shape v4's fixture used is now a MUTANT that must be refused (G9).
  2. **Far worse, v5 never established that a MISSING kickoff time is valid** — and 259 held rows
     have one. Because the offering is GLOBAL, those rows arrive in the very first capture even
     though 2026 itself is fully populated. A GREEN could have passed all 52 contracts and then
     failed on contact with the real asset (G9b).

BOUNDARY OF THAT MEASUREMENT, STATED BECAUSE IT CHANGES WHAT CAN BE PINNED. It was taken on the
provider's upstream **CSV**, while B21 captures the **Parquet** release asset. They are different
physical artifacts from the same family, and nobody has yet read the Parquet one. In a CSV an absent
value is an empty STRING; in Parquet the same absence would normally be a NULL. So G9b contracts
**both** forms as valid-and-retained rather than betting on one. That is not hedging: it is the
narrowest contract that cannot be falsified by whichever form the asset actually uses, and neither
form is a time, so nothing is admitted that could be mistaken for one.

STILL UNMEASURED, AND NOT ASSUMED AWAY: whether `gameday` is ever empty in the same file. This
contract requires it to parse as a date, which is the stricter reading, and the count is requested
from the lane that already holds the measurement rather than guessed here.

WHAT v4 GOT WRONG, kept because the lesson is a different one: A SPECIAL CASE PROVED AS A RULE. Its
field-validation mutants covered `away_team` but not `home_team`, and `gameday` but not `gametime`,
so a GREEN validating one side of each pair passed a suite that reads as though it validated both.
Both mutant tables are now symmetric by construction, each carries its own positive control, and the
`game_id` field — which v4 never tested empty or null at all — has mutants of its own.

WHAT v3 GOT WRONG, AND IT IS ONE IDEA IN FIVE PLACES: A TEST WHOSE ORACLE COMES FROM THE THING UNDER
TEST PROVES NOTHING. v3 checked losslessness by comparing COLUMN NAMES, checked the schema hash
against another value the same GREEN returned, compared the store's parser to the store's own
persisted output, and asserted one dtype out of forty-six. Each passes against a GREEN that keeps
every key and corrupts every value. Every one of those oracles is now derived independently, from
the payload bytes, by this file (`_expected_rows`, `_expected_dtypes`, `_expected_schema_hash`).
The remaining two were coverage holes of the same family: only CONFLICTING duplicates were refused,
and only score dtypes and `observed_at` were type-checked, leaving `season`, `week`, the teams, the
source kickoff time and the transport's own `retrieved_at` free to be anything at all.

The two STRUCTURAL errors of the original draft are recorded below, because both were *modelling*
errors — a contract that describes a source boundary the provider does not have would have pinned a
fiction whatever the implementation did.

  1. IT MODELLED A PER-WEEK JSON OFFERING. THE PROVIDER PUBLISHES ONE GLOBAL PARQUET FILE.
     Measured, offline, from the installed client:
       `.venv/lib/python3.14/site-packages/nflreadpy/load_schedules.py:30` calls
       `downloader.download("nflverse-data", "schedules/games")`;
       `downloader.py:38-48` resolves that to exactly
       `https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet`
       and `:85-88` parses the response body as Parquet. `load_schedules.py:36-40` then filters
       seasons IN MEMORY — proof there is one download for all seasons, not one per season and
       certainly not one per week.
     Consequence for this contract: the offering, the check and the content vintage are GLOBAL.
     `(season, week)` is a DERIVED PROJECTION of one retained vintage, never a fetch parameter and
     never a caller-declared fact.

  2. IT LET A GREEN PASS WITHOUT EVER ACQUIRING ANYTHING. Every test began after bytes already
     existed. A module can satisfy that suite without a URL, a retrieval, or a runnable route —
     the adapter-without-data failure this repo has now recorded twice. The transport is therefore
     an INJECTED COLLABORATOR that is CONTRACTED here: exact provider URL, exactly one retrieval
     per check, retrieval time taken from the response rather than the wall clock, error handling,
     and a CLI that runs fetch -> raw -> parse -> publish.

  ALSO NOTE, because it changes how a GREEN must be built: the installed client CANNOT be used as
  the transport. `downloader._download_file` returns a parsed `pl.DataFrame` and never surfaces the
  response body, so a route built on it has no raw bytes to retain and no way to prove what the
  provider sent. Source-first requires our own retrieval of the same asset.

WHAT THIS FILE NO LONGER CONTAINS, AND WHERE IT WENT (Codex finding 4, accepted).
The v2 draft built expected-membership baselines and terminal-evidence evaluation here. Those are
CONSUMER judgments over retained data, and the agreed sequence puts the governed cadence inputs and
the Realized Outcome migration AFTER this capture. Worse, v2's `baseline_already_frozen` refused
every conflicting re-freeze forever, so a real flex or membership correction would have left the
baseline permanently stale. Membership selection, terminal joins and versioned baselines are handed
to those separately reviewed gates.

THE FINDING THAT PRODUCED THIS TICKET SURVIVES THE NARROWING, AS A NEGATIVE INVARIANT.
nflverse `schedules` carries NO terminal-status field and NO end-time, and per Codex's telemetry may
publish interim scores inside its update cycle. A populated score proves play was OBSERVED, never
that play ENDED. `scripts/run_realized_outcome_scoring.py:345-347` already reads
`"final" if home_score is populated` — a live defect — and the v1 draft encoded that same rule into
a contract, which would have pinned the defect as correct. So B21 declares
`finality_capability="unverified"`, retains every score the source publishes, and emits NO derived
status field at all (G7, D2). It cannot certify a week complete because it has no evidence that
could; that is the design refusing to invent a fact the source does not publish.

CORROBORATED LOCALLY, NOT ASSUMED: the catalog's own B21 row
(`docs/layer-1-data-inventory-catalog.md:749`) already lists "exact source/finality provenance
before first prediction-bearing run" as OPEN, and `run_realized_outcome_scoring.py:339-364` computes
`expected_game_count` as `len(games)` from the same frame it validates — a separate self-certifying
defect, sequenced after this ticket.

FIELD COVERAGE — WHY THIS FILE PINS NO FIELD COUNT (Codex finding 3, accepted in substance).
The review asks for lossless retention of the provider's declared 45 fields. The requirement is
accepted; the CONSTANT is not pinned, because it is an external number this session cannot measure
offline and "assert from expectation instead of measuring" is the exact defect class this lane
logged four times today. F1 instead derives the invariant from the payload itself — EVERY column
present in the retained bytes must survive to the record — which is strictly stronger than any
count: 45 columns in and 45 out would still pass while silently substituting one.

IDENTIFIER SHAPE — MEASURED, NOT CITED. v2's fixture built `game_id` as `season_week_home_away`.
nflverse defines it as `season_week_AWAY_HOME`, and that was verified locally against held raw
snapshots rather than taken from the dictionary: across the 285 distinct games in
`app/data/nflverse_usage/raw/snap_counts_2024_*.json`, the 71 whose `pfr_game_id` suffix maps to a
known club (PFR keys its id by the HOME stadium) agree with the 4th `game_id` component in 71 of 71
cases and disagree in none — e.g. `2024_01_BAL_KC` / `202409050kan`, team `KC`, opponent `BAL`.
*(That path is gitignored, so the measurement is reproducible only where the data is present. The
fixtures below are self-contained and assert nothing about it.)*

SYNTHETIC BYTES, REAL FORMAT, REAL FILESYSTEM. Fixtures are Parquet built in-test with polars, so
the capture boundary is exercised against the provider's actual wire format; storage goes through
`tmp_path`. Nothing reads the gitignored store, so every contract here means the same thing on a
clean CI runner.

SCOPE. NFL only; no FBS inference. OUT OF SCOPE: any GREEN, scheduler change, paid call, provider
contact, governed-input artifact, Realized Outcome rewiring, and any consumer.

SCOPE OF THIS FILE, WITHOUT AN AUTHORITY ARGUMENT IN IT (Codex F5). This file defines what a valid
capture looks like. It makes no network call, writes nothing outside `tmp_path`, and authorizes
nothing. Whether and when the first real 2026 capture runs is David's to say and is tracked in the
ledger and on the board — not in a test docstring, which was never a gate and should not have been
written as though it were. Scheduler installation, provider contact and any downstream consumer
remain separate acts under every reading.

The module does not exist. Tests that exercise it FAIL; they do not skip. D1 passes today and is
DISCLOSED as a regression guard.
"""
from __future__ import annotations

import hashlib
import importlib
import io
import json
import socket
from pathlib import Path

import polars as pl
import pytest

MODULE = "src.dynasty_genius.sources.schedules_capture"
REPO_ROOT = Path(__file__).resolve().parents[2]

#: The exact asset the installed client resolves. Assembled here the same way `_build_url` does,
#: so a drift in either place is visible rather than silently tolerated.
EXPECTED_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet"
)

SEASON, WEEK = 2026, 1

T0 = "2026-09-01T00:00:00+00:00"   # schedule published, nothing played
T1 = "2026-09-15T06:00:00+00:00"
T2 = "2026-09-15T12:00:00+00:00"

#: The ten columns this repo already consumes by name (`run_realized_outcome_scoring.py:347-357`
#: reads `game_id`, `gameday`, the scores; the cadence engine needs season/week/kickoff/type).
#: A REQUIRED SUBSET, never the whole schema — F1 owns losslessness.
REQUIRED_COLUMNS = (
    "game_id", "season", "week", "game_type", "gameday", "gametime",
    "away_team", "home_team", "away_score", "home_score",
)


def _mod():
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:  # pragma: no cover - this IS the red state
        pytest.fail(f"{MODULE} does not exist yet (RED): {exc}")


def _game_id(away: str, home: str, season: int = SEASON, week: int = WEEK) -> str:
    """`season_week_AWAY_HOME` — the measured provider shape (see module docstring)."""
    return f"{season}_{week:02d}_{away}_{home}"


def _row(away: str, home: str, *, away_score=None, home_score=None,
         season: int = SEASON, week: int = WEEK, game_type: str = "REG",
         kickoff: str = "2026-09-14T17:00:00+00:00", game_id: str | None = None) -> dict:
    """One SOURCE-SHAPED schedule row, deliberately WIDE.

    The extra columns are not decoration: they are the ones a narrow parser silently drops
    (`result`, `total`, `overtime`, venue, weather, rest, and every provider cross-id). F1 derives
    its assertion from this row's own keys, so widening the fixture strengthens the contract without
    pinning any provider field count.
    """
    return {
        "game_id": game_id if game_id is not None else _game_id(away, home, season, week),
        "season": season, "game_type": game_type, "week": week,
        "gameday": kickoff[:10], "weekday": "Sunday", "gametime": kickoff[11:16],
        "away_team": away, "away_score": away_score,
        "home_team": home, "home_score": home_score,
        "location": "Home", "result": None, "total": None, "overtime": None,
        "old_game_id": "2026091400", "gsis": None, "nfl_detail_id": None,
        "pfr": "202609140kan", "pff": None, "espn": "401671800", "ftn": None,
        "away_rest": 7, "home_rest": 7,
        "away_moneyline": None, "home_moneyline": None,
        "spread_line": None, "away_spread_odds": None, "home_spread_odds": None,
        "total_line": None, "under_odds": None, "over_odds": None,
        "div_game": 0, "roof": "outdoors", "surface": "grass",
        "temp": None, "wind": None,
        "away_qb_id": None, "home_qb_id": None,
        "away_qb_name": None, "home_qb_name": None,
        "away_coach": None, "home_coach": None,
        "referee": None, "stadium_id": "KAN00", "stadium": "GEHA Field",
    }


#: Score columns are nullable integers pre-game; polars would otherwise infer a Null column from an
#: all-None fixture and the retained dtypes would describe the fixture instead of the source.
_SCORE_SCHEMA = {"away_score": pl.Int64, "home_score": pl.Int64}


def _parquet(rows, schema_overrides=None) -> bytes:
    """Real Parquet bytes — the provider's wire format, constructed offline."""
    buf = io.BytesIO()
    pl.DataFrame(rows, schema_overrides={**_SCORE_SCHEMA, **(schema_overrides or {})}) \
        .write_parquet(buf)
    return buf.getvalue()


def _unplayed() -> bytes:
    return _parquet([_row("BUF", "KC"), _row("DAL", "PHI"), _row("SF", "SEA")])


def _scored() -> bytes:
    return _parquet([
        _row("BUF", "KC", away_score=17, home_score=24),
        _row("DAL", "PHI", away_score=10, home_score=13),
        _row("SF", "SEA", away_score=27, home_score=20),
    ])


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _frame(raw: bytes) -> pl.DataFrame:
    """An INDEPENDENT read of the payload. The oracle for losslessness and schema evidence must not
    come from the store being tested — v3 compared the store's parser against the store's own
    persisted output, which a GREEN satisfies by agreeing with itself."""
    return pl.read_parquet(io.BytesIO(raw))


def _expected_rows(raw: bytes) -> list[dict]:
    return _frame(raw).to_dicts()


def _expected_dtypes(raw: bytes) -> list[list[str]]:
    """Ordered `[column, dtype]` pairs. Order is part of the evidence: a reordered schema is a
    different schema, and a map alone cannot express that."""
    return [[name, str(dtype)] for name, dtype in _frame(raw).schema.items()]


def _expected_schema_hash(raw: bytes) -> str:
    """PINS THE DEFINITION, not just the existence, of the schema hash.

    A hash whose canonical form is left to the implementation cannot be recomputed by a reviewer, so
    the acceptance packet's "measured schema hash" would mean nothing. This is the exact
    representation a GREEN must hash: the ordered [column, dtype] pairs, compact JSON, UTF-8."""
    canonical = json.dumps(_expected_dtypes(raw), separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


#: Shaped like the real thing and deliberately obvious. GitHub's signed asset URL carries signature
#: and JWT query parameters; these are invented stand-ins, never a captured value.
_SECRET_QUERY = "?X-Amz-Signature=deadbeefcafe0123456789&token=eyJhbGciOiJIUzI1NiJ9.SYNTHETIC"
#: The OTHER place a URL can carry a credential, and the one this file first missed: `user:pw@host`
#: is authority-component material, not query material, so a rule written as "strip everything after
#: `?`" leaves it untouched. Both carriers are now exercised on every surface.
_SECRET_USERINFO = "dgxuser:dgxsecretpw"
_SECRET_MARKERS = ("X-Amz-Signature", "deadbeefcafe0123456789", "token=", "eyJhbGciOiJIUzI1NiJ9",
                   "dgxsecretpw", "dgxuser:")


def _store_text(store) -> str:
    """Every byte the route wrote, as text — vintage, marker, index, ledger, and anything else."""
    chunks = []
    for path in sorted(store.root.rglob("*")):
        if path.is_file() and path.suffix != ".parquet":
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def _store(tmp_path):
    """NOT a fixture. As a fixture, `_mod()`'s `pytest.fail` fired during SETUP, so tests reported
    as ERRORS and never reached their assertions — no usable RED evidence."""
    m = _mod()
    return m.ScheduleStore(root=tmp_path / "b21")


def _fetcher(*bodies, retrieved_at=T1):
    """A recording transport collaborator. Each call serves the next body and records the URL it was
    asked for, so 'was the provider actually contacted, once, at the right address?' is assertable
    without a network."""
    m = _mod()
    return m.RecordingFetcher(bodies=list(bodies), retrieved_at=retrieved_at)


# ============ S — the SOURCE boundary: a real retrieval of a real asset ==========


def test_s1_the_route_retrieves_the_EXACT_nflverse_asset_exactly_once(tmp_path):
    """Finding 2. A capture that never names its provider cannot be audited, and a capture that
    fetches twice per check has two chances to disagree with itself. Both are pinned."""
    store = _store(tmp_path)
    fetcher = _fetcher(_unplayed())
    rec = store.capture(fetcher=fetcher, observed_at=T1)
    assert fetcher.calls == [EXPECTED_URL], (
        f"expected exactly one retrieval of {EXPECTED_URL}; got {fetcher.calls!r}"
    )
    assert rec.source_url == EXPECTED_URL


def test_s2_the_capture_boundary_retains_RAW_PROVIDER_BYTES_not_a_parsed_frame(tmp_path):
    """A module fed an already-parsed frame has no source boundary: it cannot prove what the
    provider sent and cannot re-derive its own parse. Bytes in, hash first, interpret after.

    This is also why the installed client cannot be the transport — it returns a DataFrame and
    discards the response body (`downloader.py:85-88`)."""
    store = _store(tmp_path)
    m = _mod()
    raw = _unplayed()
    rec = store.record_offering(observed_at=T0, raw=raw, source_url=EXPECTED_URL)
    assert rec.raw_sha256 == _sha(raw), "the retained hash must be of the PROVIDER's bytes"
    assert store.read_raw(rec.check_id) == raw, "exact source bytes must be retained verbatim"
    assert rec.byte_count == len(raw)
    with pytest.raises(m.CaptureError) as exc:
        store.record_offering(observed_at=T1, raw=[{"game_id": "x"}], source_url=EXPECTED_URL)
    assert exc.value.code == "raw_bytes_required"


def test_s3_the_raw_artifact_lands_at_an_EXACT_canonical_path(tmp_path):
    """Finding 8. `startswith(root)` accepted any descendant, which is not a layout — a later
    implementation could scatter vintages anywhere under the root and still pass. The path must be
    derivable from the capture identity so an audit can find it without a database."""
    store = _store(tmp_path)
    raw = _unplayed()
    rec = store.record_offering(observed_at=T0, raw=raw, source_url=EXPECTED_URL)
    path = store.raw_path(rec.check_id)
    assert path.is_file(), f"raw bytes were not persisted at {path}"
    assert path.read_bytes() == raw
    assert path == store.root / "raw" / f"{rec.check_id}.parquet", (
        f"canonical layout not honoured: {path}"
    )


def test_s4_the_PARSE_is_reproducible_AND_matches_an_INDEPENDENT_read(tmp_path):
    """The retained artifact is the evidence; the parse is a view of it. If re-parsing the stored
    bytes does not reproduce the stored rows, the store has drifted from its own source.

    v3 stopped there, and that was self-confirming: a parser that corrupts a value corrupts it
    identically on both sides and passes. Both sides are now anchored to an independent read."""
    store = _store(tmp_path)
    raw = _scored()
    rec = store.record_offering(observed_at=T1, raw=raw, source_url=EXPECTED_URL)
    reparsed = store.parse(store.read_raw(rec.check_id))
    assert reparsed == store.get_vintage(rec.vintage_id)["rows"]
    assert reparsed == _expected_rows(raw), "the parse disagrees with an independent read"


def test_s5_a_TRANSPORT_FAILURE_is_audited_and_publishes_nothing(tmp_path):
    """Finding 2/6. A fetch that errors is still evidence that we looked. Recording nothing makes a
    persistently failing route indistinguishable from one nobody ever scheduled."""
    store = _store(tmp_path)
    m = _mod()
    fetcher = m.RecordingFetcher(bodies=[], error="connection reset", retrieved_at=T1)
    with pytest.raises(m.FetchError) as exc:
        store.capture(fetcher=fetcher, observed_at=T1)
    assert exc.value.code == "fetch_failed"
    assert store.failed_check_count() == 1
    assert store.vintage_count() == 0
    assert store.successful_check_count() == 0
    assert store.marker() is None


def test_s6_the_RETRIEVAL_TIME_comes_from_the_response_not_the_wall_clock(tmp_path):
    """Provenance must describe the fetch, not the moment a later process happened to run. A route
    that stamps `now()` cannot answer 'how old is this evidence?' after any replay."""
    store = _store(tmp_path)
    fetcher = _fetcher(_unplayed(), retrieved_at=T2)
    rec = store.capture(fetcher=fetcher, observed_at=T1)
    assert rec.retrieved_at == T2, "retrieval time must be the transport's, not the caller's"
    assert store.marker()["retrieved_at"] == T2


@pytest.mark.parametrize("bad", ["2026-09-15T06:00:00", "whenever"])
def test_s7_a_NAIVE_or_MALFORMED_retrieval_time_is_REFUSED(bad, tmp_path):
    """Codex F4. S6 accepted one good value and never rejected a bad one, so a transport handing
    back a naive or unparseable timestamp would have been recorded as provenance. A retrieval time
    that cannot be ordered against anything else makes every freshness answer built on it
    meaningless — and `2026-09-15T06:00:00`, with no offset, is the shape that looks fine right up
    until it is compared with something."""
    store = _store(tmp_path)
    m = _mod()
    with pytest.raises(m.CaptureError) as exc:
        store.capture(fetcher=_fetcher(_unplayed(), retrieved_at=bad), observed_at=T1)
    assert exc.value.code == "retrieved_at_invalid", f"accepted retrieved_at {bad!r}"
    assert store.vintage_count() == 0
    assert store.marker() is None


def test_s8_the_SANCTIONED_github_release_redirect_is_ACCEPTED_and_its_chain_RECORDED(tmp_path):
    """FALSIFIED BY LIVE EVIDENCE, AND THIS IS THE REPAIR.

    The previous pin asserted that any final URL differing from the requested one was substitution.
    That is simply false for this provider: GitHub answers the release URL with a 302 to a signed
    asset on `release-assets.githubusercontent.com`, measured 2026-08-09 by an independent `curl -I`
    and then by a real CLI run that retrieved the valid 517,546-byte Parquet and **exited 1** on our
    own rule. The contract, not the provider, was wrong — the production route could not have made a
    single capture.

    So the sanctioned delivery chain is accepted, and BOTH ends of it are recorded: what we asked
    for, and what actually served the bytes. Provenance that collapses the two cannot answer "where
    did this really come from?" after any later dispute."""
    store = _store(tmp_path)
    delivered_path = (
        "https://release-assets.githubusercontent.com/github-production-release-asset/"
        "0/games.parquet"
    )
    signed = delivered_path.replace("https://", f"https://{_SECRET_USERINFO}@")
    fetcher = _mod().RecordingFetcher(bodies=[_scored()], retrieved_at=T1,
                                      final_url=f"{signed}{_SECRET_QUERY}")
    rec = store.capture(fetcher=fetcher, observed_at=T1)

    assert fetcher.calls == [EXPECTED_URL], "the request must still go to the sanctioned URL"
    assert rec.created_vintage is True, "a normal provider redirect must not fail the capture"
    assert rec.source_url == EXPECTED_URL, "provenance records what we ASKED for"
    # The SANITIZED delivery, not the raw one: the signed query is credential material and S9 owns
    # that rule. Both ends of the chain are still recorded; what is recorded is non-secret.
    assert rec.delivered_from == delivered_path, "and separately what actually SERVED it"
    marker = store.marker()
    assert marker["source_url"] == EXPECTED_URL and marker["delivered_from"] == delivered_path


def test_s9_SIGNED_CREDENTIAL_material_is_never_persisted(tmp_path):
    """A REAL PRODUCTION RUN PUT SECRETS ON DISK, AND THIS STORE IS BACKED UP OFFSITE.

    The F1 repair recorded the delivery URL verbatim. GitHub's signed asset URL carries signature and
    JWT query parameters, so a successful capture wrote short-lived credentials into the vintage, the
    marker and the ledger — and `app/data/sources/nflverse_schedules` is a REQUIRED entry in the
    backup manifest, so the next daily run would have shipped them to cloud storage too.

    Provenance needs the scheme, host and path. It has never needed the query string. Both ends are
    still recorded (S8); what is recorded is now non-secret."""
    store = _store(tmp_path)
    delivered = (
        f"https://{_SECRET_USERINFO}@release-assets.githubusercontent.com/"
        f"github-production-release-asset/0/games.parquet{_SECRET_QUERY}"
    )
    rec = store.capture(
        fetcher=_mod().RecordingFetcher(bodies=[_scored()], retrieved_at=T1, final_url=delivered),
        observed_at=T1,
    )
    assert rec.created_vintage is True, "sanitizing must not break the sanctioned redirect"
    assert rec.delivered_from == (
        "https://release-assets.githubusercontent.com/github-production-release-asset/0/games.parquet"
    ), "provenance must keep scheme/host/path and drop the query"

    written = _store_text(store)
    for secret in _SECRET_MARKERS:
        assert secret not in rec.delivered_from, f"{secret!r} survived into the record"
        assert secret not in written, f"{secret!r} was persisted somewhere under the store root"


def test_s9b_a_REJECTED_delivery_leaks_no_credentials_into_the_audit_trail(tmp_path):
    """The failure path is the easier one to forget: the refusal message names the URL that was
    refused, and a foreign or malicious host is exactly the case whose URL is most likely to carry
    credential material. An audit record is still a record."""
    store = _store(tmp_path)
    m = _mod()
    fetcher = m.RecordingFetcher(bodies=[_unplayed()], retrieved_at=T1,
                                 final_url=f"https://{_SECRET_USERINFO}@example.invalid/"
                                           f"games.parquet{_SECRET_QUERY}")
    with pytest.raises(m.CaptureError) as exc:
        store.capture(fetcher=fetcher, observed_at=T1)
    assert exc.value.code == "source_identity_unexpected"

    written = _store_text(store) + str(exc.value)
    assert store.failed_check_count() == 1, "the refusal must still be audited"
    for secret in _SECRET_MARKERS:
        assert secret not in written, f"{secret!r} leaked through the refusal path"


def test_s9c_a_TRANSPORT_FAILURE_message_cannot_carry_credentials_into_the_ledger(tmp_path):
    """The path neither S9 nor S9b covers, and the easiest of the three to miss.

    A transport exception routinely embeds the URL it failed on — `requests` does exactly this — and
    the URL it failed on is the SIGNED one. So the failure detail is a third way credential material
    reaches the ledger, arriving inside an exception message rather than through any field we chose
    to record. Scrubbing therefore belongs at the point every failure is written, not at each of the
    three call sites that happen to exist today."""
    store = _store(tmp_path)
    m = _mod()
    doomed = (f"https://{_SECRET_USERINFO}@release-assets.githubusercontent.com/0/"
              f"games.parquet{_SECRET_QUERY}")
    fetcher = m.RecordingFetcher(bodies=[], retrieved_at=T1,
                                 error=f"ConnectionError: failed to reach {doomed}")
    with pytest.raises(m.FetchError) as exc:
        store.capture(fetcher=fetcher, observed_at=T1)

    assert store.failed_check_count() == 1, "the transport failure must still be audited"
    # BOTH surfaces. The first repair scrubbed the ledger and RE-RAISED the original exception, so
    # the secret still reached stderr — and this assertion, checking only the store, passed anyway.
    # Verifying one surface and claiming the leak closed is the failure mode; the raised exception
    # is as much an output as the file.
    written = _store_text(store) + "\n" + str(exc.value)
    for secret in _SECRET_MARKERS:
        assert secret not in written, f"{secret!r} survived in the ledger or the raised exception"


@pytest.mark.parametrize("foreign", [
    "https://example.invalid/games.parquet",
    "https://release-assets.githubusercontent.com.evil.example/games.parquet",
])
def test_s8b_a_FOREIGN_host_in_the_delivery_chain_is_REFUSED(foreign, tmp_path):
    """The other half: widening the rule to admit the real redirect must not widen it to admit a
    mirror. `01` §Source Adapter Rules forbids silent substitution outright.

    The second case is the reason a suffix check must be anchored to a DOT boundary — a naive
    `endswith("githubusercontent.com")` accepts `…githubusercontent.com.evil.example`, which is the
    classic way an allowlist stops meaning anything."""
    store = _store(tmp_path)
    m = _mod()
    fetcher = m.RecordingFetcher(bodies=[_unplayed()], retrieved_at=T1, final_url=foreign)
    with pytest.raises(m.CaptureError) as exc:
        store.capture(fetcher=fetcher, observed_at=T1)
    assert exc.value.code == "source_identity_unexpected"
    assert store.vintage_count() == 0
    assert store.marker() is None


# ============ A — check / vintage identity, and no-change replay =================


def test_a1_identical_BYTES_are_a_new_CHECK_with_no_new_VINTAGE(tmp_path):
    """nflverse republishes on a five-minute cycle, so most checks find nothing new. A vintage per
    check would fabricate a change history the source never had, and every downstream 'when did this
    last change?' answer would be wrong. Vintage identity is the RAW HASH."""
    store = _store(tmp_path)
    raw = _unplayed()
    first = store.capture(fetcher=_fetcher(raw, retrieved_at=T0), observed_at=T0)
    second = store.capture(fetcher=_fetcher(raw, retrieved_at=T1), observed_at=T1)
    assert second.vintage_id == first.vintage_id and second.created_vintage is False
    assert second.check_id != first.check_id
    assert store.vintage_count() == 1 and store.check_count() == 2


def test_a2_a_no_change_check_ADVANCES_last_checked_and_FREEZES_last_changed(tmp_path):
    """Finding 7. The monitoring half of A1: a successful check that found nothing new is still a
    successful check. Collapsing it loses the only evidence the route is alive, and advancing
    `last_changed` would report a revision that never happened."""
    store = _store(tmp_path)
    raw = _unplayed()
    store.capture(fetcher=_fetcher(raw, retrieved_at=T0), observed_at=T0)
    before = json.loads(json.dumps(store.marker()))
    store.capture(fetcher=_fetcher(raw, retrieved_at=T1), observed_at=T1)
    after = store.marker()
    assert after["last_checked_at"] == T1 and before["last_checked_at"] == T0
    assert after["last_changed_at"] == before["last_changed_at"] == T0
    assert after["vintage_id"] == before["vintage_id"]
    assert after["raw_sha256"] == before["raw_sha256"]


def test_a3_a_REVISION_creates_a_new_vintage_and_RETAINS_the_prior(tmp_path):
    """Layer 1 loses nothing. A corrected score or a rescheduled game is new information, and the
    superseded vintage is the only record that a revision occurred. Season assets are known to be
    mutable in place, so an overwrite is unrecoverable."""
    store = _store(tmp_path)
    first = store.capture(fetcher=_fetcher(_unplayed(), retrieved_at=T0), observed_at=T0)
    second = store.capture(fetcher=_fetcher(_scored(), retrieved_at=T1), observed_at=T1)
    assert second.created_vintage is True and second.vintage_id != first.vintage_id
    assert store.vintage_count() == 2
    assert store.get_vintage(first.vintage_id) is not None
    assert store.read_raw(first.check_id) == _unplayed(), "the prior raw evidence was destroyed"
    assert store.marker()["last_changed_at"] == T1


def test_a4_REPLAY_of_a_retained_offering_creates_NO_new_check(tmp_path):
    """Finding 7, the other half. Re-deriving the parse from retained bytes is an audit operation,
    not a retrieval. If replay minted check identities, the route's own history would inflate every
    time anybody re-read it."""
    store = _store(tmp_path)
    rec = store.capture(fetcher=_fetcher(_scored()), observed_at=T1)
    replayed = store.replay(rec.check_id)
    assert replayed["rows"] == store.get_vintage(rec.vintage_id)["rows"]
    assert store.check_count() == 1 and store.vintage_count() == 1
    assert store.marker()["last_checked_at"] == T1, "replay must not advance the check clock"


def test_a5_a_stored_vintage_is_IMMUTABLE_against_later_caller_mutation(tmp_path):
    """A store that hands out references to its own structures passes every other test here while
    letting a caller silently rewrite recorded history."""
    store = _store(tmp_path)
    rec = store.capture(fetcher=_fetcher(_scored()), observed_at=T1)
    snapshot = json.loads(json.dumps(store.get_vintage(rec.vintage_id)))
    got = store.get_vintage(rec.vintage_id)
    got["rows"][0]["home_score"] = 999
    got["rows"].append({"game_id": "INJECTED"})
    assert store.get_vintage(rec.vintage_id) == snapshot, "recorded history was mutated"


# ============ F — LOSSLESS retention of the provider's own schema ================


def test_f1_EVERY_source_VALUE_survives_to_the_record(tmp_path):
    """Finding 3, AND THE MOST IMPORTANT ASSERTION IN THIS FILE. A parser that keeps ten fields
    silently discards `result`, `total`, overtime, venue, weather, rest and every provider
    cross-id — and nothing downstream can tell, because the discarded columns never appear in an
    error.

    v3 compared only the SET OF COLUMN NAMES, which a GREEN passes while replacing every value it
    retains (Codex F1). The oracle is now an independent `pl.read_parquet` of the same bytes, and
    the comparison is on VALUES. Derived from the payload itself, so it holds for any provider
    schema and pins no field count this session cannot measure."""
    store = _store(tmp_path)
    raw = _scored()
    expected = _expected_rows(raw)
    assert len(expected[0]) > 40, "fixture precondition: the payload is genuinely wide"
    rec = store.record_offering(observed_at=T2, raw=raw, source_url=EXPECTED_URL)
    rows = store.get_vintage(rec.vintage_id)["rows"]

    missing = set(expected[0]) - set(rows[0])
    assert not missing, f"the parser silently discarded source columns: {sorted(missing)}"
    assert rows == expected, "a retained value differs from an independent read of the same bytes"
    # Named sentinels drawn from columns NO other test touches, so a corruption confined to the
    # unasserted tail of the schema fails loudly and legibly rather than as a whole-row diff.
    for field, value in (("pfr", "202609140kan"), ("stadium_id", "KAN00"),
                         ("away_rest", 7), ("roof", "outdoors")):
        assert rows[0][field] == value, f"non-required source field {field!r} was corrupted"


def test_f0_the_STORED_vintage_holds_METADATA_ONLY_and_derives_its_rows(tmp_path):
    """DAVID'S RULING, 2026-08-09: parsed rows do not belong on disk beside the bytes they came from.

    Measured on the first real capture: the vintage file was 9.1 MB, of which the actual metadata —
    ids, hashes, dtypes, schema hash, timestamps, provenance — was **1,719 bytes**. The other 9.1 MB
    was the parsed rows, which are fully derivable from the retained Parquet in 196 ms. At the
    provider's measured ~7-day cadence that is ~44 MB/year of permanent history bought for a fifth of
    a second.

    It is also a correctness argument, not only a storage one: S4 exists because the parse must be a
    VIEW of the retained bytes. Persisting both creates a second source of truth that can drift from
    the first, and nothing would detect it.

    The behavioural contract is unchanged — `get_vintage()` still returns rows, and every other test
    in this file still reads them. Only the STORAGE changes."""
    store = _store(tmp_path)
    raw = _scored()
    rec = store.record_offering(observed_at=T2, raw=raw, source_url=EXPECTED_URL)

    on_disk = json.loads(store.vintage_path(rec.vintage_id).read_text(encoding="utf-8"))
    assert "rows" not in on_disk, "parsed rows were persisted beside the bytes they derive from"
    assert store.vintage_path(rec.vintage_id).stat().st_size < 16_384, (
        "the stored vintage must be metadata, not a payload copy"
    )
    # ...and the derived view is still complete, still lossless, still the independent read.
    assert store.get_vintage(rec.vintage_id)["rows"] == _expected_rows(raw)


def test_f0b_a_MISSING_content_object_is_a_NAMED_REFUSAL_not_a_partial_vintage(tmp_path):
    """THE COST OF MAKING THE PARQUET THE ONLY PAYLOAD TRUTH: it must now be verified on every read.

    Independently reproduced against the shipped module: deleting the content object made
    `get_vintage()` return a dictionary that still claimed `row_count=3` and carried the original
    `raw_sha256` — with no `rows` key at all. Silent partial success, in a store that is a REQUIRED
    backup entry, so a restore that missed one object would be served as a vintage rather than
    refused."""
    store = _store(tmp_path)
    m = _mod()
    rec = store.record_offering(observed_at=T2, raw=_scored(), source_url=EXPECTED_URL)
    assert len(store.get_vintage(rec.vintage_id)["rows"]) == 3, "precondition: it reads normally"

    store.content_path(rec.raw_sha256).unlink()
    with pytest.raises(m.CaptureError) as exc:
        store.get_vintage(rec.vintage_id)
    assert exc.value.code == "content_missing"


def test_f0c_a_SUBSTITUTED_content_object_is_REFUSED(tmp_path):
    """The same defect's louder half, and the one that returns WRONG DATA rather than none.

    Reproduced: replacing the content object with a VALID Parquet returned the substituted score
    while the vintage kept its original count, raw hash, schema hash and identity. *(The original
    reproduction used a one-row payload; this fixture is now a same-length three-row mutant, because
    a differently-sized substitute could be caught on byte count alone and so could not force the
    SHA comparison this case is for.)* Removing the stored rows was supposed to END a second source of truth; unverified, it
    only moved the disagreement to metadata-versus-derived-rows."""
    store = _store(tmp_path)
    m = _mod()
    raw = _scored()
    rec = store.record_offering(observed_at=T2, raw=raw, source_url=EXPECTED_URL)

    # SAME LENGTH, SAME SHAPE, DIFFERENT BYTES. The first cut of this test substituted a one-row
    # payload of a different size, which a reader comparing only `byte_count` would have caught —
    # so it could not force the SHA comparison it claims to. Measured: both payloads are 13,499
    # bytes with identical row/column/schema shape and different SHA-256.
    substitute = _parquet([
        _row("BUF", "KC", away_score=17, home_score=24),
        _row("DAL", "PHI", away_score=10, home_score=13),
        _row("SF", "SEA", away_score=28, home_score=20),      # 27 -> 28: one digit, same width
    ])
    assert len(substitute) == len(raw), "fixture precondition: byte_count cannot discriminate"
    assert _sha(substitute) != _sha(raw), "fixture precondition: the bytes really do differ"
    assert _expected_schema_hash(substitute) == _expected_schema_hash(raw), (
        "fixture precondition: the schema hash cannot discriminate either"
    )
    store.content_path(rec.raw_sha256).write_bytes(substitute)

    with pytest.raises(m.CaptureError) as exc:
        store.get_vintage(rec.vintage_id)
    assert exc.value.code == "content_integrity_mismatch"


@pytest.mark.parametrize("claim", ["row_count", "column_count", "byte_count",
                                   "dtypes_one_pair", "dtypes_order_swap", "schema_hash"])
def test_f0d_a_vintage_whose_METADATA_disagrees_with_the_derived_rows_is_REFUSED(claim, tmp_path):
    """Byte identity alone is not agreement. If the retained bytes are intact but the vintage's own
    claims about them have drifted — row count, column count, ordered dtypes, schema hash — then the
    two sources still disagree and neither is authoritative. Fail closed rather than pick one."""
    store = _store(tmp_path)
    m = _mod()
    rec = store.record_offering(observed_at=T2, raw=_scored(), source_url=EXPECTED_URL)
    path = store.vintage_path(rec.vintage_id)

    # POSITIVE CONTROL first: untouched metadata still reads, so no case here can pass by refusing
    # everything.
    assert len(store.get_vintage(rec.vintage_id)["rows"]) == 3

    # EVERY claim is mutated on its own. The first cut mutated only `row_count`, which a GREEN
    # checking only `row_count` would satisfy while ignoring the other three.
    meta = json.loads(path.read_text(encoding="utf-8"))
    field = "dtypes" if claim.startswith("dtypes") else claim
    before = json.dumps(meta[field], sort_keys=True)
    if claim == "row_count":
        meta[field] = meta[field] + 1
    elif claim == "column_count":
        meta[field] = meta[field] - 1
    elif claim == "byte_count":
        # The CONTENT is untouched; only the claim about its size moves. Without this case, a reader
        # that verifies the full SHA and every derived claim but ignores `byte_count` passes — which
        # is what making f0c same-length quietly allowed.
        meta[field] = meta[field] + 1
    elif claim == "dtypes_one_pair":
        # MINIMAL: exactly one middle entry changes. Mutating all 46 (the first cut) is caught by a
        # reader comparing only the FIRST dtype — which reopens the very one-sampled-dtype defect
        # this case exists to close.
        idx = len(meta[field]) // 2
        pairs = [list(x) for x in meta[field]]
        pairs[idx][1] = "Float64" if pairs[idx][1] != "Float64" else "Int64"
        meta[field] = pairs
    elif claim == "dtypes_order_swap":
        # ORDER ONLY: same multiset of pairs, two adjacent entries transposed. A reader comparing
        # dtypes as an unordered mapping passes this; an ordered comparison does not.
        pairs = [list(x) for x in meta[field]]
        idx = len(pairs) // 2
        pairs[idx], pairs[idx + 1] = pairs[idx + 1], pairs[idx]
        meta[field] = pairs
    else:
        # ONE NIBBLE, still valid hex, so a prefix-only comparison cannot pass.
        h = meta[field]
        meta[field] = h[:-1] + ("0" if h[-1] != "0" else "1")
    assert json.dumps(meta[field], sort_keys=True) != before, f"fixture precondition: {claim} changed"
    if claim == "dtypes_order_swap":
        assert sorted(map(tuple, meta[field])) == sorted(
            map(tuple, json.loads(before))), "precondition: order-only, same pairs"
    path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(m.CaptureError) as exc:
        store.get_vintage(rec.vintage_id)
    assert exc.value.code == "vintage_metadata_inconsistent", f"{claim} drift was accepted"


@pytest.mark.parametrize("break_", ["content_swap", "renamed_file"])
def test_f0f_a_vintage_IDENTITY_must_bind_to_the_bytes_it_names(break_, tmp_path):
    """THE GAP EVERY OTHER CHECK IN THIS FILE MISSES, and it took a second valid vintage to see it.

    Independently reproduced: with TWO valid same-schema three-row vintages on disk, repointing
    vintage A's metadata at B's content — and copying B's byte count, hash, counts and schema claims
    while keeping A's `vintage_id` — is accepted. Every derived comparison agrees, because they are
    all now B's. A reader implementing content existence, byte count, full SHA, row/column counts,
    dtypes AND schema hash still serves B's scores under A's identity.

    What is missing is the BINDING: the vintage id is derived from the content hash, so
    `vintage_id == "v-" + raw_sha256[:16]` is a checkable invariant, and the id asked for must equal
    the id stored. Without it, "which capture is this?" has no answer that the store enforces.

    `renamed_file` is the same break from the other end: a vintage file moved to another id's path
    keeps its own `vintage_id`, so the requested and stored identities diverge."""
    store = _store(tmp_path)
    m = _mod()
    a = store.record_offering(observed_at=T1, raw=_unplayed(), source_url=EXPECTED_URL)
    b_raw = _scored()
    b = store.record_offering(observed_at=T2, raw=b_raw, source_url=EXPECTED_URL)
    assert a.vintage_id != b.vintage_id, "fixture precondition: two distinct valid vintages"
    assert len(store.get_vintage(a.vintage_id)["rows"]) == 3, "positive control: A reads normally"

    if break_ == "content_swap":
        # A's metadata now describes B completely — hash, size, counts, dtypes, schema — while
        # keeping A's own id. Every derived claim will agree with the bytes it points at.
        path = store.vintage_path(a.vintage_id)
        meta_a = json.loads(path.read_text(encoding="utf-8"))
        meta_b = json.loads(store.vintage_path(b.vintage_id).read_text(encoding="utf-8"))
        for field in ("raw_sha256", "byte_count", "schema_hash", "dtypes",
                      "row_count", "column_count"):
            meta_a[field] = meta_b[field]
        assert meta_a["vintage_id"] == a.vintage_id, "fixture precondition: A keeps its own id"
        path.write_text(json.dumps(meta_a, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        requested = a.vintage_id
    else:
        # B's whole vintage file is moved onto A's path; its stored id still says B.
        store.vintage_path(a.vintage_id).write_text(
            store.vintage_path(b.vintage_id).read_text(encoding="utf-8"), encoding="utf-8")
        requested = a.vintage_id

    with pytest.raises(m.CaptureError) as exc:
        store.get_vintage(requested)
    assert exc.value.code == "vintage_identity_mismatch", f"{break_} was accepted"


def test_f0e_an_UNSUPPORTED_parser_version_is_REFUSED_not_silently_reinterpreted(tmp_path):
    """Codex P1, and it is an overclaim in this module's own docstring rather than only a gap.

    The module states that `parser_version` plus the retained bytes reconstructs a past parse. It
    does not: `get_vintage()` always invokes the CURRENT parser. With rows no longer stored, that
    version boundary became load-bearing — a vintage written by a future parser would be silently
    reinterpreted by today's rules while still reporting the other version. Refuse it, or stop
    claiming reconstruction."""
    store = _store(tmp_path)
    m = _mod()
    rec = store.record_offering(observed_at=T2, raw=_scored(), source_url=EXPECTED_URL)
    path = store.vintage_path(rec.vintage_id)
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta["parser_version"] = "unknown.future.parser"
    path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(m.CaptureError) as exc:
        store.get_vintage(rec.vintage_id)
    assert exc.value.code == "parser_version_unsupported"


def test_f2_the_vintage_carries_a_RECOMPUTABLE_schema_hash_and_the_FULL_dtype_map(tmp_path):
    """Column names alone cannot detect a type change. A schema hash makes drift a comparable fact;
    the dtype map makes it a readable one, so 'the provider changed something' is answerable without
    re-downloading a vintage that no longer exists.

    v3 compared the hash to another value from the same GREEN and checked ONE dtype, so a constant
    hash and a partly fabricated map passed (Codex F2). The expected hash and the full ordered map
    are now derived independently — which also pins the hash's CANONICAL FORM, without which no
    reviewer could ever recompute the number an acceptance packet reports."""
    store = _store(tmp_path)
    raw = _scored()
    rec = store.record_offering(observed_at=T2, raw=raw, source_url=EXPECTED_URL)
    vintage = store.get_vintage(rec.vintage_id)
    for meta in ("vintage_id", "raw_sha256", "byte_count", "schema_hash", "dtypes",
                 "observed_at", "retrieved_at", "source_url", "parser_version"):
        assert meta in vintage, f"the vintage must carry its own {meta}"
    assert [list(pair) for pair in vintage["dtypes"]] == _expected_dtypes(raw), (
        "the dtype map must be the payload's full ordered schema, not a sample of it"
    )
    assert vintage["schema_hash"] == _expected_schema_hash(raw)
    assert vintage["schema_hash"] == rec.schema_hash


def test_f2b_a_DTYPE_CHANGE_changes_the_schema_hash(tmp_path):
    """Counterexample to F2, so the hash cannot be a constant that happens to match. Same columns,
    same order, same values — only `away_rest`'s dtype differs, and that must be visible.

    Deliberately NOT a score dtype: G5 governs what a valid score looks like, and a counterexample
    that also has to survive that rule would be testing two things at once."""
    store = _store(tmp_path)
    ints = _parquet([_row("BUF", "KC", away_score=17, home_score=24)])
    floats = _parquet([_row("BUF", "KC", away_score=17, home_score=24)],
                      schema_overrides={"away_rest": pl.Float64})
    assert _frame(ints).columns == _frame(floats).columns, "fixture precondition: same columns"
    assert _expected_schema_hash(ints) != _expected_schema_hash(floats), (
        "fixture precondition: the two fixtures really do differ in dtype"
    )
    first = store.record_offering(observed_at=T1, raw=ints, source_url=EXPECTED_URL)
    second = store.record_offering(observed_at=T2, raw=floats, source_url=EXPECTED_URL)
    assert first.schema_hash != second.schema_hash


def test_f3_a_MISSING_REQUIRED_COLUMN_is_refused_and_a_complete_payload_is_accepted(tmp_path):
    """Fail-closed on the columns this repo consumes by name, with the positive control in the same
    test so the guard cannot pass by refusing everything."""
    store = _store(tmp_path)
    m = _mod()
    assert store.record_offering(
        observed_at=T0, raw=_unplayed(), source_url=EXPECTED_URL
    ).created_vintage is True, "positive control: a complete payload must be accepted"

    stripped = [
        {k: v for k, v in _row("BUF", "KC").items() if k != "gametime"},
    ]
    with pytest.raises(m.CaptureError) as exc:
        store.record_offering(observed_at=T1, raw=_parquet(stripped), source_url=EXPECTED_URL)
    assert exc.value.code == "schema_missing_column"
    assert "gametime" in str(exc.value)


def test_f4_the_required_subset_is_present_on_every_retained_row(tmp_path):
    """Guards F3 against a drift where validation passes but the projection drops a column
    afterwards."""
    store = _store(tmp_path)
    rec = store.record_offering(observed_at=T2, raw=_scored(), source_url=EXPECTED_URL)
    for row in store.get_vintage(rec.vintage_id)["rows"]:
        for field in REQUIRED_COLUMNS:
            assert field in row, f"the source schema must retain {field}"


# ============ G — fail-closed semantic validation, each with a counterexample ====


def test_g1_an_EMPTY_payload_is_refused(tmp_path):
    """Zero rows is a provider fault or a truncated download, never a valid schedule. Accepting it
    would publish an empty vintage that reads downstream as 'no games exist'."""
    store = _store(tmp_path)
    m = _mod()
    with pytest.raises(m.CaptureError) as exc:
        store.record_offering(observed_at=T1, raw=_parquet([]), source_url=EXPECTED_URL)
    assert exc.value.code == "raw_empty"
    assert store.vintage_count() == 0


def test_g2_MALFORMED_bytes_are_refused_and_RETAINED_for_audit(tmp_path):
    """Finding 6. Bytes that arrived but will not parse are the most valuable evidence a route ever
    holds — they are the only proof of what the provider actually served on a bad day. Refusing to
    accept them is correct; discarding them destroys the diagnosis."""
    store = _store(tmp_path)
    m = _mod()
    garbage = b"PAR1-not-really-a-parquet-file"
    with pytest.raises(m.CaptureError) as exc:
        store.record_offering(observed_at=T1, raw=garbage, source_url=EXPECTED_URL)
    assert exc.value.code == "raw_unparseable"
    assert store.vintage_count() == 0, "an unparseable payload must not become a vintage"
    quarantined = store.quarantined_raw(_sha(garbage))
    assert quarantined is not None and quarantined.read_bytes() == garbage
    assert store.failed_check_count() == 1


@pytest.mark.parametrize("second_score", [21, 24])
def test_g3_ANY_repeated_game_id_is_refused_identical_or_conflicting(second_score, tmp_path):
    """Two rows claiming the same game cannot both be true, and a store that accepts them makes
    every later read order-dependent.

    v3 tested only the CONFLICTING case (different scores), which a GREEN passes while accepting two
    byte-identical rows and silently inflating every week slice and row count built on them (Codex
    F3). `second_score=24` is the identical-duplicate mutant; `21` is the conflicting one. The
    source-boundary rule is the strict one: at this grain a `game_id` appears at most once."""
    store = _store(tmp_path)
    m = _mod()
    dup = [
        _row("BUF", "KC", away_score=17, home_score=24),
        _row("BUF", "KC", away_score=17 if second_score == 24 else 21, home_score=second_score),
    ]
    if second_score == 24:
        assert dup[0] == dup[1], "fixture precondition: this mutant is a byte-identical duplicate"
    else:
        assert dup[0] != dup[1], "fixture precondition: this mutant genuinely conflicts"
    with pytest.raises(m.CaptureError) as exc:
        store.record_offering(observed_at=T1, raw=_parquet(dup), source_url=EXPECTED_URL)
    assert exc.value.code == "duplicate_game_id"
    assert "2026_01_BUF_KC" in str(exc.value)


def test_g4_a_game_id_INCONSISTENT_with_its_own_row_is_refused(tmp_path):
    """`season_week_AWAY_HOME`, measured (see module docstring). A row whose identifier disagrees
    with its own season, week or teams is either a provider fault or our parse mis-aligning columns;
    both are fail-closed. The positive control is the accepted payload above it."""
    store = _store(tmp_path)
    m = _mod()
    assert store.record_offering(
        observed_at=T0, raw=_unplayed(), source_url=EXPECTED_URL
    ).created_vintage is True, "positive control: consistent identifiers must be accepted"

    swapped = [_row("BUF", "KC", game_id=_game_id("KC", "BUF"))]   # home/away inverted
    with pytest.raises(m.CaptureError) as exc:
        store.record_offering(observed_at=T1, raw=_parquet(swapped), source_url=EXPECTED_URL)
    assert exc.value.code == "game_id_inconsistent"


def test_g5_a_NON_NUMERIC_or_NON_FINITE_score_is_refused_but_a_NULL_score_is_valid(tmp_path):
    """A null score is the normal pre-game state and must never be an error. A string or a NaN in a
    score column is schema drift, and silently coercing it is how a fabricated number reaches a
    consumer."""
    store = _store(tmp_path)
    m = _mod()
    assert store.record_offering(
        observed_at=T0, raw=_unplayed(), source_url=EXPECTED_URL
    ).created_vintage is True, "positive control: null scores are the pre-game state"

    as_text = _parquet([_row("BUF", "KC", away_score="17", home_score="24")],
                       schema_overrides={"away_score": pl.String, "home_score": pl.String})
    with pytest.raises(m.CaptureError) as exc:
        store.record_offering(observed_at=T1, raw=as_text, source_url=EXPECTED_URL)
    assert exc.value.code == "score_type_invalid"

    non_finite = _parquet([_row("DAL", "PHI", away_score=float("nan"), home_score=13.0)],
                          schema_overrides={"away_score": pl.Float64, "home_score": pl.Float64})
    with pytest.raises(m.CaptureError) as exc:
        store.record_offering(observed_at=T2, raw=non_finite, source_url=EXPECTED_URL)
    assert exc.value.code == "score_type_invalid"


def test_g6_an_INVALID_observed_at_is_refused(tmp_path):
    """A capture whose timestamp is unparseable or naive cannot be ordered against any other
    evidence, which makes every freshness and revision answer built on it meaningless."""
    store = _store(tmp_path)
    m = _mod()
    for bad in ("not-a-timestamp", "2026-09-15T06:00:00"):
        with pytest.raises(m.CaptureError) as exc:
            store.record_offering(observed_at=bad, raw=_unplayed(), source_url=EXPECTED_URL)
        assert exc.value.code == "observed_at_invalid", f"accepted {bad!r}"


def _null_game_id_row() -> dict:
    """`_row` treats `game_id=None` as 'derive it', so a literal null has to be set afterwards."""
    row = _row("BUF", "KC")
    row["game_id"] = None
    return row


#: Built LAZILY. Constructing fixtures inside `parametrize` evaluates them at import, so a fixture
#: bug becomes a COLLECTION ERROR — which would break the suite-wide zero-collection-errors
#: invariant and, worse, hide every other test in this file behind it.
#:
#: SYMMETRIC BY CONSTRUCTION. v4 proved `away_team` and left `home_team` and `game_id` untested, so a
#: GREEN validating one side passed — the special-case-proved-as-a-rule defect (Codex v4 residual).
#: Both teams and both null/empty forms of the identifier are now mutants of their own.
_REQUIRED_FIELD_MUTANTS = {
    "season_is_text": lambda: ([_row("BUF", "KC")], {"season": pl.String}),
    # An Int64 column carrying a NULL, not a Null-dtype column — the difference between "the
    # provider sent nothing here" and "the provider sent no such column".
    "week_is_null": lambda: ([_row("BUF", "KC", week=None, game_id="2026_01_BUF_KC")],
                             {"week": pl.Int64}),
    "empty_away_team": lambda: ([_row("", "KC", game_id="2026_01__KC")], None),
    "empty_home_team": lambda: ([_row("BUF", "", game_id="2026_01_BUF_")], None),
    "empty_game_id": lambda: ([_row("BUF", "KC", game_id="")], None),
    "null_game_id": lambda: ([_null_game_id_row()], {"game_id": pl.String}),
}


@pytest.mark.parametrize("label", sorted(_REQUIRED_FIELD_MUTANTS))
def test_g8_a_REQUIRED_FIELD_of_the_wrong_TYPE_or_EMPTY_is_refused(label, tmp_path):
    """Codex F4. v3 validated score dtypes and `observed_at` and stopped there, so a GREEN could
    accept a string `season`, a null `week` or an empty team and still pass — and those three fields
    are exactly what the week projection and the future cadence input are derived from. A required
    field that is present but unusable is not a lesser defect than a missing one.

    THIS ALSO PINS CHECK ORDER, deliberately. A null `week`, an empty team or a missing `game_id`
    cannot have a consistent identifier by construction, so demanding `required_field_type_invalid`
    requires the type/null check to run BEFORE the identifier-consistency check of G4. That is the
    right order — an unusable field is a more basic fact than a disagreement between two fields — and
    it makes the diagnostic name the cause rather than a downstream symptom."""
    store = _store(tmp_path)
    m = _mod()
    assert store.record_offering(
        observed_at=T0, raw=_unplayed(), source_url=EXPECTED_URL
    ).created_vintage is True, "positive control: a well-formed payload must still be accepted"

    rows, overrides = _REQUIRED_FIELD_MUTANTS[label]()
    with pytest.raises(m.CaptureError) as exc:
        store.record_offering(observed_at=T1, raw=_parquet(rows, schema_overrides=overrides),
                              source_url=EXPECTED_URL)
    assert exc.value.code == "required_field_type_invalid", f"{label} was accepted"


#: BOTH halves of the kickoff, and both failure shapes (unparseable, and well-shaped but impossible).
#: v4 proved `gameday` only, so a GREEN validating the date and ignoring the time passed — and the
#: time is half of the instant the cadence engine will eventually key on.
#:
#: `gametime_iso_datetime` is the shape v4's own fixture used. It is now a MUTANT, on measured
#: evidence (see the module docstring): zero of 7,289 held non-null values take that form, so a GREEN
#: that accepted it would be admitting a provider semantic drift that has never occurred.
_SOURCE_TIME_MUTANTS = {
    "gameday_unparseable": ("gameday", "not-a-date"),
    "gameday_impossible": ("gameday", "2026-13-45"),
    "gametime_unparseable": ("gametime", "kickoff-ish"),
    "gametime_impossible": ("gametime", "25:00"),
    "gametime_iso_datetime": ("gametime", "2026-09-14T17:00:00+00:00"),
}


@pytest.mark.parametrize("label", sorted(_SOURCE_TIME_MUTANTS))
def test_g9_a_MALFORMED_SOURCE_SCHEDULE_TIME_is_refused(label, tmp_path):
    """Distinct from `observed_at_invalid`: this is the SOURCE's own kickoff, which the cadence
    engine will read as the game clock. A separate code so a provider fault is never mistaken for a
    fault in our own capture provenance.

    THE DOMAIN IS NOW MEASURED, so v5's admissive "time-of-day OR ISO datetime" rule is withdrawn.
    A non-null `gametime` must be a valid 24-hour `HH:MM` and nothing else. See the module docstring
    for the measurement and its boundary. NULL/UNPUBLISHED values are a separate contract — G9b —
    and are VALID."""
    store = _store(tmp_path)
    m = _mod()
    assert store.record_offering(
        observed_at=T0, raw=_unplayed(), source_url=EXPECTED_URL
    ).created_vintage is True, "positive control: a well-formed kickoff must still be accepted"

    field, bad = _SOURCE_TIME_MUTANTS[label]
    broken = [_row("BUF", "KC")]
    broken[0][field] = bad
    with pytest.raises(m.CaptureError) as exc:
        store.record_offering(observed_at=T1, raw=_parquet(broken), source_url=EXPECTED_URL)
    assert exc.value.code == "source_time_invalid", f"accepted {field} {bad!r}"


#: An UNPUBLISHED kickoff time, in both physical forms it can arrive as. The measurement was taken
#: on the provider's CSV with `csv.DictReader`, where an absent value is an empty STRING; the
#: artifact B21 actually captures is Parquet, where the same absence would normally materialize as a
#: NULL. Nobody has read the Parquet asset, so both forms are contracted rather than one guessed.
_UNPUBLISHED_KICKOFF = {
    "provider_null": (None, {"gametime": pl.String}),
    "provider_empty_string": ("", None),
}


@pytest.mark.parametrize("label", sorted(_UNPUBLISHED_KICKOFF))
def test_g9b_an_UNPUBLISHED_kickoff_time_is_VALID_and_RETAINED_VERBATIM(label, tmp_path):
    """THE CAPTURE-BLOCKING HALF OF THE MEASUREMENT, and the reason this round mattered.

    259 of 7,548 held rows carry no `gametime`. The offering is GLOBAL, so those rows arrive in the
    very first capture even though 2026 itself is fully populated — a GREEN that treats a missing
    kickoff time as a fault would pass every other test in this file and then fail on contact with
    the real asset.

    An unpublished kickoff is not a defect: it is the provider declining to claim something, which
    is the one kind of missingness this route must never overwrite. So it is accepted, and it is
    retained VERBATIM — not coerced to midnight, not blanked, not dropped.

    NOT symmetric with G8's empty `game_id`, deliberately. An unidentifiable row cannot be stored at
    any grain; a game whose kickoff time has not been announced is an ordinary, truthful state."""
    store = _store(tmp_path)
    value, overrides = _UNPUBLISHED_KICKOFF[label]
    row = _row("BUF", "KC")
    row["gametime"] = value
    assert _frame(_parquet([row], schema_overrides=overrides)).to_dicts()[0]["gametime"] == value, (
        "fixture precondition: the payload really carries the unpublished form under test"
    )

    rec = store.record_offering(observed_at=T1, raw=_parquet([row], schema_overrides=overrides),
                                source_url=EXPECTED_URL)
    assert rec.created_vintage is True, f"{label}: an unpublished kickoff was rejected"
    retained = store.get_vintage(rec.vintage_id)["rows"][0]
    assert retained["gametime"] == value, (
        f"{label}: the unpublished kickoff was rewritten to {retained['gametime']!r}"
    )
    assert retained["gameday"] == row["gameday"], "the date must survive a missing time"


def test_g10_a_FOREIGN_provider_identity_is_REFUSED(tmp_path):
    """Codex F5. `01` §Source Adapter Rules: silent substitution is forbidden. Every v3 fixture
    passed the expected URL, so a store that accepts any caller-supplied provider would have passed
    the whole suite — and a route that will accept bytes from anywhere is not a source adapter."""
    store = _store(tmp_path)
    m = _mod()
    with pytest.raises(m.CaptureError) as exc:
        store.record_offering(observed_at=T1, raw=_unplayed(),
                              source_url="https://example.invalid/games.parquet")
    assert exc.value.code == "source_identity_unexpected"
    assert store.vintage_count() == 0


def test_g7_NO_DERIVED_STATUS_reaches_a_retained_row(tmp_path):
    """The surviving half of the finality finding. B21 retains what the source published and adds
    no interpretation of it — in particular no `status`, which is the derived finality claim
    `run_realized_outcome_scoring.py:345-347` invents from a populated score."""
    store = _store(tmp_path)
    rec = store.record_offering(observed_at=T2, raw=_scored(), source_url=EXPECTED_URL)
    row = store.get_vintage(rec.vintage_id)["rows"][0]
    for leaked in ("status", "final", "complete", "expected_game_count",
                   "prediction", "dvs", "points", "scoring"):
        assert leaked not in row, (
            f"consumer vocabulary {leaked!r} leaked into a Layer 1 record; `status` in particular "
            "is the derived finality claim this design refuses to make"
        )
    assert row["home_score"] == 24 and row["away_score"] == 17, (
        "refusing to CERTIFY finality is not a licence to DISCARD the scores"
    )


# ============ W — the (season, week) PROJECTION is derived, never declared =======


def test_w1_a_week_slice_is_DERIVED_from_one_vintage_and_carries_its_provenance(tmp_path):
    """Finding 1/5. The provider publishes one global file, so a week is a VIEW of a retained
    vintage. v2 took `season`/`week` as capture parameters and never reconciled them to the rows,
    which let 2025 Week 2 rows be published under a 2026 Week 1 path."""
    store = _store(tmp_path)
    rec = store.capture(fetcher=_fetcher(_scored()), observed_at=T2)
    week = store.week_slice(vintage_id=rec.vintage_id, season=SEASON, week=WEEK)
    assert week.vintage_id == rec.vintage_id
    assert week.source_sha256 == rec.raw_sha256
    assert week.row_count == 3
    for row in week.rows:
        assert row["season"] == SEASON and row["week"] == WEEK


def test_w2_a_week_slice_NEVER_returns_a_row_from_another_week(tmp_path):
    """The mis-filing defect made mechanical: a payload spanning two weeks must split, not leak."""
    store = _store(tmp_path)
    mixed = _parquet([
        _row("BUF", "KC", away_score=17, home_score=24),
        _row("DAL", "PHI", week=2, season=2025, away_score=10, home_score=13),
    ])
    rec = store.record_offering(observed_at=T2, raw=mixed, source_url=EXPECTED_URL)
    week = store.week_slice(vintage_id=rec.vintage_id, season=SEASON, week=WEEK)
    assert {r["game_id"] for r in week.rows} == {_game_id("BUF", "KC")}


def test_w3_an_ABSENT_week_is_honest_emptiness_not_a_fabrication(tmp_path):
    """A week the vintage does not cover returns nothing and says so. Raising would be wrong (a bye
    or an unpublished week is a normal state) and inventing rows would be a fiction."""
    store = _store(tmp_path)
    rec = store.record_offering(observed_at=T2, raw=_scored(), source_url=EXPECTED_URL)
    week = store.week_slice(vintage_id=rec.vintage_id, season=SEASON, week=18)
    assert week.rows == [] and week.row_count == 0
    assert week.membership_evidence == "absent_from_vintage"


# ============ D — a DEDICATED, RUNNABLE route ====================================


def test_d1_schedules_is_ABSENT_from_the_generic_build_streams():
    """DISCLOSED REGRESSION GUARD — passes today. `schedules` is revision-bearing: rows change after
    the fact when scores are corrected or games rescheduled, which the generic append/replace path
    does not model. Adding it there later would look like progress and would silently discard
    revision history. Non-vacuous: `build_streams` returns 13 other streams."""
    nflverse_usage = importlib.import_module("src.dynasty_genius.nflverse_usage")
    names = {s.name for s in nflverse_usage.build_streams()}
    assert len(names) >= 13, "fixture precondition: build_streams is populated"
    assert "schedules" not in names


def test_d2_the_route_DECLARES_its_source_scope_and_its_finality_ceiling():
    """A descriptor is how the daily controller and the cadence engine learn what this route can and
    cannot answer. `finality_capability` is the machine-readable form of the finding: this feed
    cannot certify that a game ended, and no consumer may infer otherwise from its presence."""
    m = _mod()
    route = m.route_descriptor()
    assert route.name == "b21_schedules"
    assert route.competition == "nfl", "NFL only; this route makes no FBS claim"
    assert route.source_url == EXPECTED_URL
    assert route.offering_scope == "global", "one asset covers every season; not per-season"
    assert route.revision_bearing is True
    assert route.finality_capability == "unverified"
    assert route.finality_reason, "the ceiling must carry its reason, not just its value"
    cli = REPO_ROOT / route.entrypoint
    assert cli.is_file(), f"the route's entrypoint does not exist: {cli}"
    assert cli.suffix == ".py"


def test_d3_the_CLI_runs_fetch_to_publish_and_touches_NO_REAL_NETWORK(tmp_path, monkeypatch):
    """Finding 2. The route must be executable, not merely described — and this test proves the
    whole path (retrieval, raw retention, parse, marker) with the socket layer armed to raise, so a
    GREEN cannot pass by quietly reaching the real internet."""
    m = _mod()
    cli = importlib.import_module("scripts.run_schedules_capture")

    def _forbidden(*a, **k):  # noqa: ANN002, ANN003
        raise AssertionError("real network access attempted inside a contract test")

    monkeypatch.setattr(socket, "socket", _forbidden)
    monkeypatch.setattr(socket, "create_connection", _forbidden)
    monkeypatch.setattr(
        m, "default_fetcher",
        lambda: m.RecordingFetcher(bodies=[_scored()], retrieved_at=T1),
    )
    root = tmp_path / "b21"
    assert cli.main(["--root", str(root), "--observed-at", T1]) == 0

    store = m.ScheduleStore(root=root)
    assert store.vintage_count() == 1 and store.successful_check_count() == 1
    assert store.marker() is not None and store.ledger_path().is_file()


def test_d6_the_CLI_prints_NO_CREDENTIALS_on_a_failed_run(tmp_path, monkeypatch, capsys):
    """The end of the leak path, tested where a human actually sees it. Whatever the route raises is
    printed by the CLI and lands in a terminal, a log file, or a scheduler's captured output — so the
    no-secrets rule has to hold on stdout and stderr, not only on disk."""
    m = _mod()
    cli = importlib.import_module("scripts.run_schedules_capture")
    doomed = (f"https://{_SECRET_USERINFO}@release-assets.githubusercontent.com/0/"
              f"games.parquet{_SECRET_QUERY}")
    monkeypatch.setattr(
        m, "default_fetcher",
        lambda: m.RecordingFetcher(bodies=[], retrieved_at=T1,
                                   error=f"ConnectionError: failed to reach {doomed}"),
    )
    assert cli.main(["--root", str(tmp_path / "b21"), "--observed-at", T1]) != 0
    printed = capsys.readouterr()
    for secret in _SECRET_MARKERS:
        assert secret not in printed.out, f"{secret!r} was printed to stdout"
        assert secret not in printed.err, f"{secret!r} was printed to stderr"


def test_d4_the_CLI_exits_NONZERO_on_a_transport_failure(tmp_path, monkeypatch):
    """A route that fails silently with exit 0 is worse than one that never ran: the scheduler and
    the daily controller both read exit state."""
    m = _mod()
    cli = importlib.import_module("scripts.run_schedules_capture")
    monkeypatch.setattr(
        m, "default_fetcher",
        lambda: m.RecordingFetcher(bodies=[], error="connection reset", retrieved_at=T1),
    )
    root = tmp_path / "b21"
    assert cli.main(["--root", str(root), "--observed-at", T1]) != 0

    store = m.ScheduleStore(root=root)
    assert store.failed_check_count() == 1 and store.vintage_count() == 0


def test_d5_the_marker_carries_COMPLETE_PROVENANCE(tmp_path):
    """Finding 8. A marker naming only a hash cannot answer 'what did we ask for, how much came
    back, and what parsed it?' — the three questions a stale or corrupted capture raises first."""
    store = _store(tmp_path)
    raw = _scored()
    rec = store.capture(fetcher=_fetcher(raw), observed_at=T1)
    marker = store.marker()
    assert marker["source_url"] == EXPECTED_URL
    assert marker["raw_sha256"] == rec.raw_sha256 == _sha(raw)
    assert marker["byte_count"] == len(raw)
    assert marker["schema_hash"] == rec.schema_hash
    assert marker["vintage_id"] == rec.vintage_id
    assert marker["parser_version"], "a marker without a parser version cannot explain a re-parse"
    assert marker["retrieved_at"] == T1
    assert store.ledger_path().is_file(), "the route needs its own metadata ledger"


# ============ E — atomic publication, and last-good survival =====================


@pytest.mark.parametrize("fault", ["route_error", "os_error", "mid_write"])
@pytest.mark.parametrize("boundary", ["raw", "store", "index", "marker"])
def test_e1_a_failure_at_ANY_boundary_leaves_the_PRIOR_capture_intact(boundary, fault, tmp_path):
    """Findings 6. Exercised through an INJECTED FAILING STORAGE COLLABORATOR against real files —
    not a `fail_at` parameter, which would ship a fault-injection hook into the route itself.

    v2 started from an EMPTY store, so it proved only that nothing appeared from nothing. The real
    hazard is a second run half-succeeding over a good one: parametrized so a fix at one boundary
    cannot mask the other three, and the pre-existing marker is compared BYTE for BYTE.

    THE `fault` DIMENSION EXISTS BECAUSE EACH EARLIER VERSION PROVED SOMETHING WEAKER THAN IT CLAIMED.

      `route_error` — the collaborator raises the ROUTE'S OWN exception before writing. This is the
        weakest case and was once the only one: it exercises only the path the route already expects.
      `os_error`    — the production-shaped exception. A real filesystem raises `OSError` from
        `mkdir`, a temp write, a link, a copy or `os.replace`; injected for real, one escaped
        unnormalised with rollback skipped, nothing audited, and orphan artifacts left behind.
      `mid_write`   — **the failure that actually happens on a full disk.** Both cases above still
        raise BEFORE the boundary touches the filesystem, so neither reproduces a half-completed
        write. An independent probe wrote `.index.json.tmp` and then raised: everything else held —
        `PublishError`, marker unchanged, prior vintage intact, failure audited — but the temp file
        survived, falsifying this test's own no-partials invariant. Rollback must clean up what a
        partially-completed write left behind, not only what it can attribute to itself."""
    m = _mod()
    root = tmp_path / "b21"
    storage = m.FilesystemStorage(root=root)
    good = m.ScheduleStore(root=root, storage=storage)
    first = good.capture(fetcher=_fetcher(_unplayed(), retrieved_at=T0), observed_at=T0)
    marker_before = good.marker_path().read_bytes()

    failing = m.ScheduleStore(root=root,
                              storage=m.FailingAt(storage, boundary=boundary, fault=fault))
    with pytest.raises(m.PublishError) as exc:
        failing.capture(fetcher=_fetcher(_scored(), retrieved_at=T1), observed_at=T1)
    assert exc.value.boundary == boundary

    audit = m.ScheduleStore(root=root, storage=storage)
    assert audit.vintage_count() == 1, f"{boundary}: a second vintage survived"
    assert audit.successful_check_count() == 1, f"{boundary}: a false success survived"
    assert audit.marker_path().read_bytes() == marker_before, (
        f"{boundary}: the last-good marker was mutated by a failed run"
    )
    assert audit.get_vintage(first.vintage_id) is not None
    # The attempt is still audit-retained: a route failing every night must not look identical to
    # one that was never scheduled.
    assert audit.failed_check_count() == 1, (
        f"{boundary}: the failed attempt must remain in the audit trail"
    )
    assert audit.partial_artifacts() == [], f"{boundary}: partial files were left behind"


def test_e2_a_SUCCESSFUL_publish_writes_raw_store_index_and_marker(tmp_path):
    """Counter-test, so E1 is not satisfied by a publish that never writes anything."""
    m = _mod()
    store = m.ScheduleStore(root=tmp_path / "b21")
    rec = store.capture(fetcher=_fetcher(_scored()), observed_at=T1)
    assert store.raw_path(rec.check_id).is_file()
    assert store.vintage_count() == 1
    assert store.successful_check_count() == 1
    assert store.marker() is not None
    assert store.ledger_path().is_file()


# ============ P — provenance safety and irreplaceability ========================


def test_p1_an_UNSAFE_identifier_cannot_escape_the_route_root(tmp_path):
    """Finding 8. Capture identities are composed from provider-influenced material, and a
    `retrieved_at` string-sliced into a path is exactly how this repo let a traversal value escape a
    layout once already (PFF intake, 2026-08-08). Refuse the identifier; write nothing."""
    store = _store(tmp_path)
    m = _mod()
    for unsafe in ("../escape", "/etc/passwd", "a/../../b"):
        with pytest.raises(m.CaptureError) as exc:
            store.raw_path(unsafe)
        assert exc.value.code == "unsafe_identifier", f"accepted {unsafe!r}"
    escaped = [
        path for path in tmp_path.rglob("*")
        if path.is_file() and (tmp_path / "b21") not in path.resolve().parents
    ]
    assert escaped == [], f"a refused identifier still wrote outside the route root: {escaped}"


def test_p3_a_PRE_EXISTING_content_object_with_the_WRONG_BYTES_is_refused(tmp_path):
    """A CONTENT-ADDRESSED STORE THAT TRUSTS ITS OWN ADDRESSES IS NOT CONTENT-ADDRESSED.

    Independently reproduced: seeding the content path with `b"wrong bytes"` and then recording the
    valid payload reported SUCCESS. `partial_artifacts()` was empty, the marker and record claimed
    the hash of the INCOMING bytes, and `read_raw` returned something else entirely — a retained raw
    that is not the provider's, and a replay that no longer reproduces. That is the worst failure
    this route can have: it is silent, and it corrupts the evidence rather than the derived view.

    A pre-existing object at the address of an incoming payload can come from a crash mid-write, a
    truncated copy, or a restore of the wrong file. Whatever the cause, the address is a CLAIM about
    the bytes, and a claim is verified before it is reused — never assumed from the filename."""
    store = _store(tmp_path)
    m = _mod()
    raw = _scored()
    seed_path = store.content_path(_sha(raw))
    seed_path.parent.mkdir(parents=True, exist_ok=True)
    seed_path.write_bytes(b"wrong bytes")
    assert _sha(seed_path.read_bytes()) != _sha(raw), "fixture precondition: the seed is wrong"

    with pytest.raises(m.CaptureError) as exc:
        store.record_offering(observed_at=T1, raw=raw, source_url=EXPECTED_URL)
    assert exc.value.code == "content_integrity_mismatch"
    assert store.marker() is None, "a false marker was published over corrupted evidence"
    assert store.vintage_count() == 0
    assert store.successful_check_count() == 0
    assert store.failed_check_count() == 1, "the integrity refusal must be audited, not swallowed"


def test_p3b_a_CORRUPTED_CHECK_LINK_is_refused_and_the_prior_capture_survives(tmp_path):
    """The same rule one level down. The check link is a second address for the same bytes, and a
    re-run of an identical offering must verify it rather than assume that a file being present at
    the expected path means the right bytes are behind it.

    The prior good capture must come through untouched: an integrity refusal is a refusal to ADD,
    never a licence to damage what is already retained."""
    store = _store(tmp_path)
    m = _mod()
    raw = _scored()
    rec = store.record_offering(observed_at=T1, raw=raw, source_url=EXPECTED_URL)
    marker_before = store.marker_path().read_bytes()

    # Replaced, not written in place: the link shares an inode with the content object, so an
    # in-place write would corrupt both and prove nothing about the link check.
    corrupted = store.raw_path(rec.check_id)
    corrupted.unlink()
    corrupted.write_bytes(b"wrong bytes")

    with pytest.raises(m.CaptureError) as exc:
        store.record_offering(observed_at=T1, raw=raw, source_url=EXPECTED_URL)
    assert exc.value.code == "content_integrity_mismatch"
    assert store.marker_path().read_bytes() == marker_before, "the prior marker was mutated"
    assert store.vintage_count() == 1, "the prior vintage must survive an integrity refusal"


def test_p2_the_RAW_STORE_is_covered_by_the_BACKUP_MANIFEST():
    """The standing manifest-coverage law (`02` §Standing Infrastructure ruling 2). A retained
    schedules vintage is irreplaceable: the provider serves ONE mutable global asset, and this repo
    measured on 2026-08-06 that nflverse rewrites published season assets in place, so 'we can
    always re-download it' is false. Losing a vintage loses the only record of what was published.

    Bound to the module's own declared root so the two cannot drift apart."""
    m = _mod()
    declared = Path(m.DEFAULT_ROOT).resolve().relative_to(REPO_ROOT).as_posix()
    manifest = json.loads((REPO_ROOT / "app/config/backup_manifest.json").read_text())
    covered = {entry["path"].rstrip("/") for entry in manifest["required"]}
    assert declared.rstrip("/") in covered, (
        f"the B21 raw store {declared!r} is irreplaceable point-in-time evidence and is not "
        f"covered by app/config/backup_manifest.json"
    )
