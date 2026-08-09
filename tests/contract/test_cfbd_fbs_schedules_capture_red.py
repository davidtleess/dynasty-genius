"""RED contract for a source-authentic CFBD FBS schedules capture.

Layer 1 only.  The offering is CFBD API v5.21.0 ``GET /games`` with the exact
competition-scoped query ``year=2026&seasonType=both&classification=fbs``.  It
returns one JSON array of Game objects; the route retains the exact response
bytes before interpreting them and never stores the bearer credential.

The FBS filter is a competition selection, not a promise that both opponents
are FBS.  An FBS-vs-FCS game is therefore a positive control.  At least one
side must be classified FBS; accepting an all-FCS row would silently widen the
offering beyond the requested competition.

``startDate`` is retained verbatim.  CFBD has historically emitted provider-
naive lexical values even though the OpenAPI says ``date-time``; this Layer 1
contract validates parseability but does not invent a timezone.  Likewise,
``completed`` and both score fields are provider facts retained verbatim.  No
derived finality or status field is legal here.

Falsification matrix seeded before GREEN:

* valid nominal: FBS/FBS and FBS/FCS, aware and naive startDate, nullable scores;
* boundary: postseason, week zero, response call-limit zero;
* missing/null/wrong type: every identity, scope, season, date and completion field;
* malformed shape: non-JSON, top-level object, empty array, changed object membership;
* duplicate/conflict: any repeated provider game id is refused;
* cross-component: exact request/query/authorization, redirect identity, CLI, manifest;
* numeric edge: bool is not an integer id, non-finite JSON is refused;
* synthetic/override: injected transport and four publication boundaries.

Out of scope: scheduler installation, governed cadence inputs, model/feature
use, and any attempt to infer terminal evidence beyond CFBD's own ``completed``
field.  The module and CLI do not exist when this RED is authored; failures are
intentional and skips are not.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

MODULE = "src.dynasty_genius.sources.cfbd_schedules_capture"
CLI_MODULE = "scripts.run_cfbd_schedules_capture"
REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPO_ROOT / "docs" / "provider-contracts" / "cfbd" / "openapi.json"
OPENAPI_SHA256 = "f6274010fb8f3d11c4c574fd4d648fd33e6c47e0eca2cfb61b481b20ca482ea3"

YEAR = 2026
ENDPOINT = "https://api.collegefootballdata.com/games"
EXPECTED_URL = (
    f"{ENDPOINT}?year={YEAR}&seasonType=both&classification=fbs"
)
QUERY = {"year": YEAR, "seasonType": "both", "classification": "fbs"}
T0 = "2026-08-09T12:00:00+00:00"
T1 = "2026-08-09T13:00:00+00:00"
PROVIDER_DATE = "Sun, 09 Aug 2026 12:00:00 GMT"
SECRET = "CFBD_TEST_BEARER_DO_NOT_RETAIN"

REQUIRED_FIELDS = (
    "id",
    "season",
    "week",
    "seasonType",
    "startDate",
    "startTimeTBD",
    "completed",
    "neutralSite",
    "conferenceGame",
    "attendance",
    "venueId",
    "venue",
    "homeId",
    "homeTeam",
    "homeConference",
    "homeClassification",
    "homePoints",
    "homeLineScores",
    "homePostgameWinProbability",
    "homePregameElo",
    "homePostgameElo",
    "awayId",
    "awayTeam",
    "awayConference",
    "awayClassification",
    "awayPoints",
    "awayLineScores",
    "awayPostgameWinProbability",
    "awayPregameElo",
    "awayPostgameElo",
    "excitementIndex",
    "highlights",
    "notes",
    "playoff",
)


def _mod():
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:  # pragma: no cover - this is the RED state
        pytest.fail(f"{MODULE} does not exist yet (RED): {exc}")


def _game(
    game_id: int,
    *,
    home: str = "Georgia",
    away: str = "Clemson",
    home_classification: str | None = "fbs",
    away_classification: str | None = "fbs",
    season: int = YEAR,
    week: int = 1,
    season_type: str = "regular",
    start_date: str = "2026-09-05T19:30:00.000Z",
    completed: bool = False,
    home_points: int | None = None,
    away_points: int | None = None,
) -> dict:
    # Ordered exactly as the committed OpenAPI Game schema's required list.
    return {
        "id": game_id,
        "season": season,
        "week": week,
        "seasonType": season_type,
        "startDate": start_date,
        "startTimeTBD": False,
        "completed": completed,
        "neutralSite": True,
        "conferenceGame": False,
        "attendance": None,
        "venueId": 4013,
        "venue": "Mercedes-Benz Stadium",
        "homeId": 61,
        "homeTeam": home,
        "homeConference": "SEC",
        "homeClassification": home_classification,
        "homePoints": home_points,
        "homeLineScores": [7.0, 14.0, 7.0, 14.0] if completed else None,
        "homePostgameWinProbability": None,
        "homePregameElo": 1800,
        "homePostgameElo": None,
        "awayId": 228,
        "awayTeam": away,
        "awayConference": "ACC",
        "awayClassification": away_classification,
        "awayPoints": away_points,
        "awayLineScores": [0.0, 0.0, 7.0, 0.0] if completed else None,
        "awayPostgameWinProbability": None,
        "awayPregameElo": 1750,
        "awayPostgameElo": None,
        "excitementIndex": None,
        "highlights": None,
        "notes": "source-value-sentinel",
        "playoff": (
            {
                "competition": "cfp",
                "format": "12-team",
                "round": "first_round",
                "roundName": "First Round",
                "bracketSlot": "1",
                "homeSeed": 1,
                "awaySeed": 12,
                "bowlName": None,
            }
            if season_type == "postseason"
            else None
        ),
    }


def _games() -> list[dict]:
    return [
        _game(401752001),
        _game(
            401752002,
            home="Alabama",
            away="Mercer",
            home_classification="fbs",
            away_classification="fcs",
            week=0,
            season_type="postseason",
            start_date="2026-08-29T18:00:00",
            completed=True,
            home_points=42,
            away_points=7,
        ),
    ]


def _body(rows: list[dict] | None = None) -> bytes:
    return json.dumps(
        _games() if rows is None else rows,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _json_type(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise AssertionError(type(value))


def _expected_schema(rows: list[dict]) -> list[list[object]]:
    ordered = sorted(rows[0])
    assert all(set(row) == set(ordered) for row in rows), "fixture schema membership drifted"
    return [
        [field, sorted({_json_type(row[field]) for row in rows})]
        for field in ordered
    ]


def _expected_schema_hash(rows: list[dict]) -> str:
    encoded = json.dumps(
        _expected_schema(rows), separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fetcher(
    mod,
    *,
    body: bytes | None = None,
    retrieved_at: str = T0,
    final_url: str = EXPECTED_URL,
    call_limit_remaining: object = 74999,
    content_type: str = "application/json; charset=utf-8",
    error: str | None = None,
    request_count: int = 1,
):
    return mod.RecordingFetcher(
        bodies=[] if body is None and error else [body if body is not None else _body()],
        retrieved_at=retrieved_at,
        provider_date=PROVIDER_DATE,
        call_limit_remaining=call_limit_remaining,
        content_type=content_type,
        final_url=final_url,
        error=error,
        request_count=request_count,
    )


def _capture(tmp_path: Path, *, body: bytes | None = None, **fetcher_kwargs):
    mod = _mod()
    fetcher = _fetcher(mod, body=body, **fetcher_kwargs)
    record = mod.CfbdScheduleStore(tmp_path).capture(
        fetcher=fetcher,
        api_key=SECRET,
        year=YEAR,
    )
    return mod, fetcher, record


def _all_text(root: Path) -> str:
    chunks: list[str] = []
    for path in root.rglob("*"):
        if path.is_file():
            try:
                chunks.append(path.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                pass
    return "\n".join(chunks)


def _assert_empty(root: Path) -> None:
    assert not (root / "status_latest.json").exists()
    assert not (root / "index.json").exists()
    for relative in ("raw/content", "raw/checks", "vintages"):
        directory = root / relative
        assert not list(directory.glob("*")) if directory.exists() else True


def _canonical_census(root: Path) -> dict[str, str]:
    paths: list[Path] = []
    for relative in ("raw/content", "raw/checks", "vintages"):
        directory = root / relative
        if directory.exists():
            paths.extend(path for path in directory.rglob("*") if path.is_file())
    paths.extend(
        path for path in (root / "index.json", root / "status_latest.json") if path.is_file()
    )
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
    }


def test_o1_committed_openapi_pins_the_games_response_and_required_schema():
    """DISCLOSED passing source-contract control; it does not exercise GREEN."""
    raw = OPENAPI_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == OPENAPI_SHA256
    document = json.loads(raw)
    assert document["info"]["version"] == "5.21.0"
    operation = document["paths"]["/games"]["get"]
    parameters = {item["name"] for item in operation["parameters"]}
    assert {"year", "seasonType", "classification"} <= parameters
    response = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response == {"items": {"$ref": "#/components/schemas/Game"}, "type": "array"}
    assert tuple(document["components"]["schemas"]["Game"]["required"]) == REQUIRED_FIELDS


def test_s1_descriptor_pins_provider_report_family_and_exact_query():
    mod = _mod()
    descriptor = mod.route_descriptor(YEAR)
    assert descriptor.name == "cfbd_fbs_schedules"
    assert descriptor.provider == "College Football Data API"
    assert descriptor.report_family == "games"
    assert descriptor.competition == "fbs"
    assert descriptor.endpoint == ENDPOINT
    assert descriptor.query == QUERY
    assert descriptor.request_url == EXPECTED_URL
    assert descriptor.openapi_version == "5.21.0"
    assert descriptor.openapi_sha256 == OPENAPI_SHA256
    assert descriptor.offering_scope == "season"


def test_s2_exactly_one_authenticated_request_is_made_and_key_is_header_only(tmp_path):
    _, fetcher, _ = _capture(tmp_path)
    assert len(fetcher.calls) == 1
    call = fetcher.calls[0]
    assert call["url"] == EXPECTED_URL
    assert call["headers"] == {
        "Accept": "application/json",
        "Authorization": f"Bearer {SECRET}",
    }
    assert SECRET not in call["url"]


def test_s2b_production_fetcher_uses_exact_http_contract_and_surfaces_headers(
    monkeypatch
):
    mod = _mod()
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        request = httpx.Request("GET", url, headers=kwargs["headers"])
        return httpx.Response(
            200,
            content=_body(),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Date": PROVIDER_DATE,
                "X-CallLimit-Remaining": "74999",
            },
            request=request,
        )

    monkeypatch.setattr(mod.httpx, "get", fake_get)
    result = mod.default_fetcher().fetch(EXPECTED_URL, api_key=SECRET)

    assert calls == [
        (
            EXPECTED_URL,
            {
                "headers": {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {SECRET}",
                },
                "follow_redirects": True,
                "timeout": 60.0,
            },
        )
    ]
    assert result.body == _body()
    assert result.requested_url == EXPECTED_URL
    assert result.final_url == EXPECTED_URL
    assert result.provider_date == PROVIDER_DATE
    assert result.content_type == "application/json; charset=utf-8"
    assert result.call_limit_remaining == "74999"
    assert result.request_count == 1
    assert result.retrieved_at.endswith("+00:00")


def test_s2c_production_fetcher_retries_only_shared_transient_policy(monkeypatch):
    mod = _mod()
    request = httpx.Request("GET", EXPECTED_URL)
    outcomes = [
        httpx.ReadTimeout("timeout", request=request),
        httpx.Response(503, request=request),
        httpx.Response(
            200,
            content=_body(),
            headers={"Content-Type": "application/json"},
            request=request,
        ),
    ]
    calls = []

    def fake_get(*_args, **_kwargs):
        outcome = outcomes[len(calls)]
        calls.append(outcome)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(mod.httpx, "get", fake_get)
    monkeypatch.setattr(mod.cfbd_http.time, "sleep", lambda _seconds: None)

    result = mod.default_fetcher().fetch(EXPECTED_URL, api_key=SECRET)

    assert len(calls) == 3
    assert result.request_count == 3


@pytest.mark.parametrize("status", [400, 401, 403, 404, 501])
def test_s2d_production_fetcher_does_not_retry_deterministic_status(
    status, monkeypatch
):
    mod = _mod()
    calls = []

    def fake_get(url, **_kwargs):
        calls.append(url)
        return httpx.Response(status, request=httpx.Request("GET", url))

    monkeypatch.setattr(mod.httpx, "get", fake_get)
    with pytest.raises(mod.FetchError) as exc:
        mod.default_fetcher().fetch(EXPECTED_URL, api_key=SECRET)
    assert len(calls) == 1
    assert exc.value.request_count == 1
    assert SECRET not in str(exc.value)


def test_s2e_production_fetcher_exhaustion_reports_actual_attempts_without_key(
    monkeypatch,
):
    mod = _mod()
    request = httpx.Request("GET", EXPECTED_URL)
    calls = []

    def fail(*_args, **_kwargs):
        calls.append(True)
        raise httpx.ReadTimeout("provider timeout", request=request)

    monkeypatch.setattr(mod.httpx, "get", fail)
    monkeypatch.setattr(mod.cfbd_http.time, "sleep", lambda _seconds: None)
    with pytest.raises(mod.FetchError) as exc:
        mod.default_fetcher().fetch(EXPECTED_URL, api_key=SECRET)
    assert len(calls) == 3
    assert exc.value.request_count == 3
    assert SECRET not in str(exc.value)


def test_s2f_production_fetcher_surfaces_redirect_destination_for_store_policy(
    monkeypatch,
):
    mod = _mod()
    delivered = "https://evil.example/swapped.json?token=SECRET_REDIRECT"

    def fake_get(_url, **_kwargs):
        return httpx.Response(
            200,
            content=_body(),
            headers={"Content-Type": "application/json"},
            request=httpx.Request("GET", delivered),
        )

    monkeypatch.setattr(mod.httpx, "get", fake_get)
    result = mod.default_fetcher().fetch(EXPECTED_URL, api_key=SECRET)
    assert result.requested_url == EXPECTED_URL
    assert result.final_url == delivered


def test_s3_raw_response_bytes_are_retained_exactly_before_parse(tmp_path):
    raw = b"[\n" + json.dumps(_games(), indent=2).encode()[1:]
    _, _, record = _capture(tmp_path, body=raw)
    expected_sha = hashlib.sha256(raw).hexdigest()
    assert record.raw_sha256 == expected_sha
    assert record.raw_bytes == len(raw)
    assert (tmp_path / "raw" / "content" / f"{expected_sha}.json").read_bytes() == raw
    assert (tmp_path / "raw" / "checks" / f"{record.check_id}.json").read_bytes() == raw


def test_s4_retrieval_and_provider_response_times_are_response_provenance(tmp_path):
    _, _, record = _capture(tmp_path, retrieved_at=T1)
    marker = json.loads((tmp_path / "status_latest.json").read_text())
    assert record.retrieved_at == T1
    assert marker["retrieved_at"] == T1
    assert marker["provider_date"] == PROVIDER_DATE


def test_s5_response_call_accounting_is_retained_without_a_second_usage_call(tmp_path):
    _, fetcher, record = _capture(tmp_path, call_limit_remaining=0)
    marker = json.loads((tmp_path / "status_latest.json").read_text())
    assert len(fetcher.calls) == 1
    assert record.request_count == 1
    assert record.call_limit_remaining_after == 0
    assert marker["request_count"] == 1
    assert marker["call_limit_remaining_after"] == 0
    assert marker["call_accounting_quality"] == "request_count_and_remaining_header"


@pytest.mark.parametrize(
    ("remaining", "quality"),
    [
        (None, "request_count_only_header_absent"),
        ("unknown", "request_count_only_header_invalid"),
        (-1, "request_count_only_header_invalid"),
        (True, "request_count_only_header_invalid"),
    ],
)
def test_s5b_missing_or_invalid_call_limit_is_nullable_telemetry(
    remaining, quality, tmp_path
):
    mod = _mod()
    record = mod.CfbdScheduleStore(tmp_path).capture(
        fetcher=_fetcher(mod, call_limit_remaining=remaining),
        api_key=SECRET,
        year=YEAR,
    )
    marker = json.loads((tmp_path / "status_latest.json").read_text())
    assert record.call_limit_remaining_after is None
    assert marker["call_limit_remaining_after"] is None
    assert marker["call_accounting_quality"] == quality
    assert marker["request_count"] == 1


def test_s5c_transport_attempt_count_is_not_hard_coded_to_one_on_failure(tmp_path):
    mod = _mod()
    with pytest.raises(mod.CaptureError):
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, error="three transient attempts exhausted", request_count=3),
            api_key=SECRET,
            year=YEAR,
        )
    ledger = [json.loads(line) for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert len(ledger) == 1
    assert ledger[0]["status"] == "failed"
    assert ledger[0]["request_count"] == 3
    assert ledger[0]["reason"] == "fetch_failed"


@pytest.mark.parametrize("content_type", ["text/html", "application/octet-stream", ""])
def test_s6_non_json_content_type_is_refused_and_retrieved_bytes_are_quarantined(
    content_type, tmp_path
):
    mod = _mod()
    raw = _body()
    fetcher = _fetcher(mod, body=raw, content_type=content_type)
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(fetcher=fetcher, api_key=SECRET, year=YEAR)
    assert exc.value.code == "content_type_unexpected"
    assert (tmp_path / "quarantine" / f"{hashlib.sha256(raw).hexdigest()}.json").read_bytes() == raw
    assert not (tmp_path / "status_latest.json").exists()


@pytest.mark.parametrize(
    "final_url",
    [
        "https://evil.example/games?year=2026&seasonType=both&classification=fbs",
        "http://api.collegefootballdata.com/games?year=2026&seasonType=both&classification=fbs",
        "https://api.collegefootballdata.com.evil.example/games?year=2026&seasonType=both&classification=fbs",
        "https://api.collegefootballdata.com/teams?year=2026&seasonType=both&classification=fbs",
    ],
)
def test_s7_redirect_or_substitution_outside_the_exact_provider_route_is_refused(
    final_url, tmp_path
):
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, final_url=final_url), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "source_identity_unexpected"
    _assert_empty(tmp_path)


def test_s8_credentials_never_reach_success_artifacts(tmp_path):
    _capture(tmp_path)
    retained = _all_text(tmp_path)
    assert SECRET not in retained
    assert "Authorization" not in retained
    assert "Bearer" not in retained


def test_s9_credentials_and_url_userinfo_are_scrubbed_from_store_failures(tmp_path):
    mod = _mod()
    poison = (
        f"failed {SECRET} at https://user:password@api.collegefootballdata.com/"
        "games?authorization=BearerSecret#jwt"
    )
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, error=poison), api_key=SECRET, year=YEAR
        )
    combined = str(exc.value) + _all_text(tmp_path)
    for marker in (SECRET, "user:password", "BearerSecret", "#jwt"):
        assert marker not in combined
    assert "?<redacted>" in combined


def test_s10_rejected_delivery_url_credentials_never_reach_retained_diagnostics(tmp_path):
    mod = _mod()
    poisoned = (
        "https://user:password@api.collegefootballdata.com/games?"
        "year=2026&seasonType=both&classification=fbs&token=DELIVERY_SECRET#jwt"
    )
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, final_url=poisoned), api_key=SECRET, year=YEAR
        )
    combined = str(exc.value) + _all_text(tmp_path)
    for marker in ("user:password", "DELIVERY_SECRET", "#jwt", SECRET):
        assert marker not in combined
    assert exc.value.code == "source_identity_unexpected"


@pytest.mark.parametrize(
    ("final_url", "secret_marker"),
    [
        (
            "https://user:pw@api.collegefootballdata.com/games?"
            "year=2026&seasonType=both&classification=fbs",
            "user:pw",
        ),
        (EXPECTED_URL + "#FRAGMENT_SECRET", "FRAGMENT_SECRET"),
        (
            "https://api.collegefootballdata.com:444/games?"
            "year=2026&seasonType=both&classification=fbs",
            None,
        ),
        (
            "https://api.collegefootballdata.com:bad/games?"
            "year=2026&seasonType=both&classification=fbs",
            None,
        ),
    ],
)
def test_s10b_each_nonexact_url_identity_component_is_refused_and_audited(
    final_url, secret_marker, tmp_path
):
    mod = _mod()
    raw = _body()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=raw, final_url=final_url),
            api_key=SECRET,
            year=YEAR,
        )
    assert exc.value.code == "source_identity_unexpected"
    sha = hashlib.sha256(raw).hexdigest()
    assert (tmp_path / "quarantine" / f"{sha}.json").read_bytes() == raw
    _assert_empty(tmp_path)
    ledger = [json.loads(line) for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert len(ledger) == 1
    assert ledger[0]["reason"] == "source_identity_unexpected"
    assert ledger[0]["raw_sha256"] == sha
    combined = str(exc.value) + _all_text(tmp_path)
    assert SECRET not in combined
    if secret_marker is not None:
        assert secret_marker not in combined


def test_f1_every_source_key_and_value_survives_canonicalization(tmp_path):
    rows = _games()
    mod, _, record = _capture(tmp_path, body=_body(rows))
    vintage = mod.CfbdScheduleStore(tmp_path).load_vintage(record.vintage_id)
    assert vintage["games"] == rows
    assert vintage["games"][0]["notes"] == "source-value-sentinel"


def test_f1b_additive_provider_field_is_schema_drift_not_silently_promoted(tmp_path):
    rows = _games()
    for row in rows:
        row["newProviderField"] = {"nested": [1, None, "sentinel"]}
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=_body(rows)), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "schema_drift"


def test_f2_full_ordered_schema_and_recomputable_type_hash_are_retained(tmp_path):
    rows = _games()
    mod, _, record = _capture(tmp_path, body=_body(rows))
    vintage = mod.CfbdScheduleStore(tmp_path).load_vintage(record.vintage_id)
    assert vintage["schema"] == _expected_schema(rows)
    assert record.schema_hash == _expected_schema_hash(rows)
    assert vintage["schema_hash"] == _expected_schema_hash(rows)


def test_f3_a_type_change_changes_the_schema_hash(tmp_path):
    rows = _games()
    baseline = _expected_schema_hash(rows)
    rows[1]["attendance"] = "unknown"
    assert _expected_schema_hash(rows) != baseline
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=_body(rows)), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "required_field_type_invalid"


def test_f4_json_member_reordering_does_not_change_logical_schema(tmp_path):
    rows = _games()
    second = rows[1]
    rows[1] = {key: second[key] for key in reversed(second)}
    assert set(rows[0]) == set(rows[1])
    assert list(rows[0]) != list(rows[1])
    mod, _, record = _capture(tmp_path, body=_body(rows))
    vintage = mod.CfbdScheduleStore(tmp_path).load_vintage(record.vintage_id)
    assert vintage["games"] == rows
    assert vintage["schema"] == _expected_schema(rows)


def test_g1_empty_array_is_refused(tmp_path):
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=b"[]"), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "raw_empty"
    _assert_empty(tmp_path)


@pytest.mark.parametrize("raw", [b"not json", b'{"id": 1}', b"[NaN]", b"[1]"])
def test_g2_unparseable_or_wrong_root_json_is_refused_and_quarantined(raw, tmp_path):
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=raw), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "raw_unparseable"
    assert (tmp_path / "quarantine" / f"{hashlib.sha256(raw).hexdigest()}.json").read_bytes() == raw
    _assert_empty(tmp_path)


@pytest.mark.parametrize("depth", ["game", "playoff"])
def test_g2b_duplicate_json_member_names_at_any_object_depth_are_refused(
    depth, tmp_path
):
    raw = _body()
    if depth == "game":
        needle = b'"id":401752001'
        replacement = b'"id":999,"id":401752001'
    else:
        needle = b'"competition":"cfp"'
        replacement = b'"competition":"other","competition":"cfp"'
    assert raw.count(needle) == 1
    raw = raw.replace(needle, replacement, 1)
    # Default json.loads silently keeps the second valid value. The contract
    # therefore needs duplicate-aware parsing rather than downstream checks.
    decoded = json.loads(raw)
    if depth == "game":
        assert decoded[0]["id"] == 401752001
    else:
        assert decoded[1]["playoff"]["competition"] == "cfp"

    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=raw, request_count=2),
            api_key=SECRET,
            year=YEAR,
        )

    assert exc.value.code == "duplicate_json_member"
    sha = hashlib.sha256(raw).hexdigest()
    assert (tmp_path / "quarantine" / f"{sha}.json").read_bytes() == raw
    _assert_empty(tmp_path)
    ledger = [json.loads(line) for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert len(ledger) == 1
    assert ledger[0]["status"] == "failed"
    assert ledger[0]["reason"] == "duplicate_json_member"
    assert ledger[0]["raw_sha256"] == sha
    assert ledger[0]["request_count"] == 2
    assert SECRET not in json.dumps(ledger[0])


@pytest.mark.parametrize("conflicting", [False, True])
def test_g3_any_duplicate_game_id_is_refused(conflicting, tmp_path):
    rows = _games()
    duplicate = deepcopy(rows[0])
    if conflicting:
        duplicate["homePoints"] = 99
    rows.append(duplicate)
    assert rows[-1]["id"] == rows[0]["id"]
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=_body(rows)), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "duplicate_game_id"


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("id", None),
        ("id", True),
        ("id", 401752001.0),
        ("season", "2026"),
        ("season", 2026.0),
        ("week", "1"),
        ("week", None),
        ("seasonType", ""),
        ("startDate", None),
        ("startTimeTBD", 0),
        ("completed", 1),
        ("neutralSite", 0),
        ("conferenceGame", 0),
        ("attendance", "unknown"),
        ("venueId", "4013"),
        ("venue", 7),
        ("homeId", True),
        ("homeId", 61.0),
        ("homeTeam", ""),
        ("homeConference", 7),
        ("awayId", None),
        ("awayTeam", ""),
        ("awayConference", 7),
        ("homeClassification", 7),
        ("awayClassification", []),
        ("homePoints", "0"),
        ("awayPoints", "0"),
        ("homeLineScores", {}),
        ("awayLineScores", {}),
        ("homePostgameWinProbability", "0.5"),
        ("awayPostgameWinProbability", "0.5"),
        ("homePregameElo", "1800"),
        ("awayPregameElo", "1750"),
        ("homePostgameElo", "1800"),
        ("awayPostgameElo", "1750"),
        ("excitementIndex", "1.0"),
        ("highlights", []),
        ("notes", []),
        ("playoff", []),
    ],
)
def test_g4_required_identity_scope_and_time_types_fail_closed(field, bad, tmp_path):
    rows = _games()
    rows[0][field] = bad
    original = _games()[0][field]
    assert original != bad or type(original) is not type(bad)
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=_body(rows)), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "required_field_type_invalid"


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("seasonType", "invalid-season-type"),
        ("homeClassification", "naia"),
        ("awayClassification", "naia"),
    ],
)
def test_g4a_response_enums_are_the_provider_game_domain(field, bad, tmp_path):
    rows = _games()
    rows[0][field] = bad
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=_body(rows)), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "enum_invalid"


@pytest.mark.parametrize(
    "season_type",
    ["regular", "postseason"],
)
def test_g4aa_both_normal_season_response_types_are_accepted(season_type, tmp_path):
    rows = [_game(401752010, season_type=season_type)]
    mod, _, record = _capture(tmp_path, body=_body(rows))
    stored = mod.CfbdScheduleStore(tmp_path).load_vintage(record.vintage_id)["games"]
    assert stored[0]["seasonType"] == season_type


@pytest.mark.parametrize(
    "season_type", ["both", "allstar", "spring_regular", "spring_postseason"]
)
def test_g4aaa_other_openapi_season_types_are_outside_this_offering(
    season_type, tmp_path
):
    rows = [_game(401752013, season_type=season_type)]
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=_body(rows)), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "season_type_scope_mismatch"


@pytest.mark.parametrize("away_classification", ["fbs", "fcs", "ii", "iii", None])
def test_g4ab_every_openapi_classification_enum_or_null_is_accepted(
    away_classification, tmp_path
):
    rows = [_game(401752011, away_classification=away_classification)]
    mod, _, record = _capture(tmp_path, body=_body(rows))
    stored = mod.CfbdScheduleStore(tmp_path).load_vintage(record.vintage_id)["games"]
    assert stored[0]["awayClassification"] == away_classification


@pytest.mark.parametrize("round_name", ["first_round", "quarterfinal", "semifinal", "championship"])
def test_g4ac_every_openapi_playoff_round_enum_is_accepted(round_name, tmp_path):
    rows = [_game(401752012, season_type="postseason")]
    rows[0]["playoff"]["round"] = round_name
    mod, _, record = _capture(tmp_path, body=_body(rows))
    stored = mod.CfbdScheduleStore(tmp_path).load_vintage(record.vintage_id)["games"]
    assert stored[0]["playoff"]["round"] == round_name


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("homeLineScores", [7.0, "touchdown"]),
        ("awayLineScores", [0.0, None]),
    ],
)
def test_g4b_line_score_arrays_require_finite_numbers(field, bad, tmp_path):
    rows = _games()
    rows[1][field] = bad
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=_body(rows)), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "nested_field_type_invalid"


def test_g4c_nested_nonfinite_json_is_refused(tmp_path):
    rows = _games()
    rows[1]["homeLineScores"] = [7.0, float("nan")]
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=_body(rows)), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "raw_unparseable"


@pytest.mark.parametrize(
    ("mutation", "bad"),
    [
        ("missing_roundName", None),
        ("extra", None),
        ("competition", "other"),
        ("round", "bowl"),
        ("homeSeed", 1.0),
        ("bowlName", []),
    ],
)
def test_g4d_nonnull_game_playoff_obeys_its_full_nested_schema(
    mutation, bad, tmp_path
):
    rows = _games()
    playoff = rows[1]["playoff"]
    assert isinstance(playoff, dict), "fixture must positively control GamePlayoff"
    if mutation == "missing_roundName":
        del playoff["roundName"]
    elif mutation == "extra":
        playoff["newProviderField"] = "drift"
    else:
        playoff[mutation] = bad
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=_body(rows)), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "nested_schema_invalid"


def test_g5_missing_required_field_is_refused_even_when_other_rows_have_it(tmp_path):
    rows = _games()
    del rows[1]["completed"]
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=_body(rows)), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "schema_missing_field"


@pytest.mark.parametrize("season", [2025, 2027])
def test_g6_every_row_must_match_the_requested_season(season, tmp_path):
    rows = _games()
    rows[1]["season"] = season
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=_body(rows)), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "season_scope_mismatch"


def test_g7_an_fbs_vs_fcs_game_is_valid_but_an_all_non_fbs_game_is_refused(tmp_path):
    mod, _, record = _capture(tmp_path)
    vintage = mod.CfbdScheduleStore(tmp_path).load_vintage(record.vintage_id)
    assert vintage["games"][1]["awayClassification"] == "fcs"

    nullable = [_game(401752004, home_classification="fbs", away_classification=None)]
    nullable_root = tmp_path / "nullable_opponent"
    nullable_record = mod.CfbdScheduleStore(nullable_root).capture(
        fetcher=_fetcher(mod, body=_body(nullable)), api_key=SECRET, year=YEAR
    )
    nullable_stored = mod.CfbdScheduleStore(nullable_root).load_vintage(
        nullable_record.vintage_id
    )
    assert nullable_stored["games"][0]["awayClassification"] is None

    rows = [_game(401752003, home_classification="fcs", away_classification="ii")]
    other = tmp_path / "all_non_fbs"
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(other).capture(
            fetcher=_fetcher(mod, body=_body(rows)), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "competition_scope_mismatch"


@pytest.mark.parametrize(
    "start_date",
    [
        "not-a-date",
        "2026-13-45T25:00:00",
        "2026-09-05",
        "2026-09-05T19",
        "2026-09-05T19:30",
        "2026-09-05 19:30:00",
    ],
)
def test_g8_invalid_or_date_only_start_time_is_refused(start_date, tmp_path):
    rows = _games()
    rows[0]["startDate"] = start_date
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=_body(rows)), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "source_time_invalid"


def test_g9_provider_naive_and_aware_start_times_are_both_retained_verbatim(tmp_path):
    rows = _games()
    assert rows[0]["startDate"].endswith("Z")
    assert rows[1]["startDate"] == "2026-08-29T18:00:00"
    mod, _, record = _capture(tmp_path, body=_body(rows))
    stored = mod.CfbdScheduleStore(tmp_path).load_vintage(record.vintage_id)["games"]
    assert [row["startDate"] for row in stored] == [row["startDate"] for row in rows]


@pytest.mark.parametrize(
    "start_date",
    [
        "2026-09-05T19:30:00",
        "2026-09-05T19:30:00.123Z",
        "2026-09-05T19:30:00-04:00",
    ],
)
def test_g9b_complete_naive_fractional_and_offset_times_are_retained(
    start_date, tmp_path
):
    rows = [_game(401752020, start_date=start_date)]
    mod, _, record = _capture(tmp_path, body=_body(rows))
    stored = mod.CfbdScheduleStore(tmp_path).load_vintage(record.vintage_id)["games"]
    assert stored[0]["startDate"] == start_date


def test_g10_completed_and_scores_are_retained_without_derived_status(tmp_path):
    rows = _games()
    mod, _, record = _capture(tmp_path, body=_body(rows))
    stored = mod.CfbdScheduleStore(tmp_path).load_vintage(record.vintage_id)["games"]
    assert stored[0]["completed"] is False
    assert stored[0]["homePoints"] is None
    assert stored[1]["completed"] is True
    assert stored[1]["homePoints"] == 42
    assert stored[1]["awayPoints"] == 7
    assert stored[1]["homeLineScores"] == [7.0, 14.0, 7.0, 14.0]
    assert stored[1]["playoff"]["competition"] == "cfp"
    assert stored[1]["playoff"]["round"] == "first_round"
    assert all("status" not in row and "finality" not in row for row in stored)


@pytest.mark.parametrize("retrieved_at", ["not-time", "2026-08-09T12:00:00"])
def test_g11_retrieved_at_must_be_timezone_aware(retrieved_at, tmp_path):
    mod = _mod()
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, retrieved_at=retrieved_at), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "retrieved_at_invalid"


@pytest.mark.parametrize("year", ["2026", True, 1800, 10000])
def test_g12_invalid_year_is_api_misuse_and_no_request_is_made(year, tmp_path):
    mod = _mod()
    fetcher = _fetcher(mod)
    with pytest.raises(ValueError):
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=fetcher, api_key=SECRET, year=year
        )
    assert fetcher.calls == []


@pytest.mark.parametrize("api_key", ["", "   ", None])
def test_g13_missing_api_key_is_refused_before_any_request(api_key, tmp_path):
    mod = _mod()
    fetcher = _fetcher(mod)
    with pytest.raises(ValueError):
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=fetcher, api_key=api_key, year=YEAR
        )
    assert fetcher.calls == []


def test_a1_identical_paid_reacquisition_mints_no_duplicate_vintage(tmp_path):
    mod = _mod()
    store = mod.CfbdScheduleStore(tmp_path)
    first = store.capture(fetcher=_fetcher(mod, retrieved_at=T0), api_key=SECRET, year=YEAR)
    second = store.capture(fetcher=_fetcher(mod, retrieved_at=T1), api_key=SECRET, year=YEAR)
    index = json.loads((tmp_path / "index.json").read_text())
    assert second.vintage_id == first.vintage_id
    assert len(index["vintages"]) == 1
    assert len(index["checks"]) == 2
    assert index["total_request_count"] == 2


def test_a2_identical_paid_reacquisition_advances_check_not_change(tmp_path):
    mod = _mod()
    store = mod.CfbdScheduleStore(tmp_path)
    first = store.capture(fetcher=_fetcher(mod, retrieved_at=T0), api_key=SECRET, year=YEAR)
    marker0 = json.loads((tmp_path / "status_latest.json").read_text())
    store.capture(fetcher=_fetcher(mod, retrieved_at=T1), api_key=SECRET, year=YEAR)
    marker1 = json.loads((tmp_path / "status_latest.json").read_text())
    assert marker0["last_changed"] == T0
    assert marker1["last_changed"] == T0
    assert marker1["last_checked"] == T1
    assert marker1["vintage_id"] == first.vintage_id


def test_a2b_local_replay_by_check_id_is_zero_call_and_creates_nothing(
    tmp_path, monkeypatch
):
    mod = _mod()
    store = mod.CfbdScheduleStore(tmp_path)
    first = store.capture(
        fetcher=_fetcher(mod, retrieved_at=T0), api_key=SECRET, year=YEAR
    )
    before = _canonical_census(tmp_path)
    before_ledger = (tmp_path / "ledger.jsonl").read_bytes()
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: pytest.fail("local replay attempted network access"),
    )

    replayed = store.replay(first.check_id)

    assert replayed["games"] == _games()
    assert replayed["raw_sha256"] == first.raw_sha256
    assert _canonical_census(tmp_path) == before
    assert (tmp_path / "ledger.jsonl").read_bytes() == before_ledger
    index = json.loads((tmp_path / "index.json").read_text())
    assert len(index["vintages"]) == 1
    assert len(index["checks"]) == 1
    assert index["total_request_count"] == 1


@pytest.mark.parametrize(
    "target", ["check", "content", "vintage_identity", "vintage_payload"]
)
def test_a2c_local_replay_verifies_every_retained_identity_before_parse(
    target, tmp_path
):
    mod = _mod()
    store = mod.CfbdScheduleStore(tmp_path)
    first = store.capture(fetcher=_fetcher(mod), api_key=SECRET, year=YEAR)
    if target == "check":
        path = tmp_path / "raw" / "checks" / f"{first.check_id}.json"
        path.write_bytes(_body([_game(999)]))
    elif target == "content":
        path = tmp_path / "raw" / "content" / f"{first.raw_sha256}.json"
        path.write_bytes(_body([_game(999)]))
    elif target == "vintage_identity":
        path = tmp_path / "vintages" / f"{first.vintage_id}.json"
        vintage = json.loads(path.read_text())
        vintage["raw_sha256"] = "0" * 64
        path.write_text(json.dumps(vintage))
    else:
        path = tmp_path / "vintages" / f"{first.vintage_id}.json"
        vintage = json.loads(path.read_text())
        vintage["games"][0]["id"] = 999
        path.write_text(json.dumps(vintage))
    before = _canonical_census(tmp_path)
    before_ledger = (tmp_path / "ledger.jsonl").read_bytes()

    with pytest.raises(mod.CaptureError) as exc:
        store.replay(first.check_id)

    assert exc.value.code == "content_integrity_mismatch"
    assert _canonical_census(tmp_path) == before
    assert (tmp_path / "ledger.jsonl").read_bytes() == before_ledger


def test_a3_changed_content_creates_a_second_vintage_and_keeps_first(tmp_path):
    mod = _mod()
    store = mod.CfbdScheduleStore(tmp_path)
    first = store.capture(fetcher=_fetcher(mod), api_key=SECRET, year=YEAR)
    changed = _games()
    changed[0]["startTimeTBD"] = True
    second = store.capture(
        fetcher=_fetcher(mod, body=_body(changed), retrieved_at=T1),
        api_key=SECRET,
        year=YEAR,
    )
    assert second.vintage_id != first.vintage_id
    assert (tmp_path / "vintages" / f"{first.vintage_id}.json").is_file()
    assert (tmp_path / "vintages" / f"{second.vintage_id}.json").is_file()


def test_e1_failed_transport_after_a_good_capture_preserves_last_good_marker(tmp_path):
    mod = _mod()
    store = mod.CfbdScheduleStore(tmp_path)
    store.capture(fetcher=_fetcher(mod), api_key=SECRET, year=YEAR)
    prior = (tmp_path / "status_latest.json").read_bytes()
    with pytest.raises(mod.CaptureError):
        store.capture(
            fetcher=_fetcher(mod, error=f"network failed with {SECRET}"),
            api_key=SECRET,
            year=YEAR,
        )
    assert (tmp_path / "status_latest.json").read_bytes() == prior
    ledger = [json.loads(line) for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert [row["status"] for row in ledger] == ["success", "failed"]
    assert ledger[-1]["request_count"] == 1


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("empty", "raw_empty"),
        ("unparseable", "raw_unparseable"),
        ("duplicate", "duplicate_game_id"),
        ("extra", "schema_drift"),
        ("missing", "schema_missing_field"),
        ("type", "required_field_type_invalid"),
        ("enum", "enum_invalid"),
        ("season_type_scope", "season_type_scope_mismatch"),
        ("season", "season_scope_mismatch"),
        ("competition", "competition_scope_mismatch"),
        ("source_time", "source_time_invalid"),
        ("nested_type", "nested_field_type_invalid"),
        ("nested_schema", "nested_schema_invalid"),
        ("content_type", "content_type_unexpected"),
        ("delivery", "source_identity_unexpected"),
        ("retrieved_at", "retrieved_at_invalid"),
    ],
)
def test_e1b_every_retrieved_validation_failure_is_audited_and_quarantined(
    case, reason, tmp_path
):
    mod = _mod()
    rows = _games()
    kwargs: dict[str, object] = {}
    if case == "empty":
        raw = b"[]"
    elif case == "unparseable":
        raw = b"not-json"
    else:
        if case == "duplicate":
            rows.append(deepcopy(rows[0]))
        elif case == "extra":
            for row in rows:
                row["newProviderField"] = "drift"
        elif case == "missing":
            del rows[0]["completed"]
        elif case == "type":
            rows[0]["season"] = "2026"
        elif case == "enum":
            rows[0]["seasonType"] = "invalid-season-type"
        elif case == "season_type_scope":
            rows[0]["seasonType"] = "both"
        elif case == "season":
            rows[0]["season"] = 2025
        elif case == "competition":
            rows[0]["homeClassification"] = "fcs"
            rows[0]["awayClassification"] = "ii"
        elif case == "source_time":
            rows[0]["startDate"] = "not-a-date"
        elif case == "nested_type":
            rows[1]["homeLineScores"] = [7.0, "bad"]
        elif case == "nested_schema":
            del rows[1]["playoff"]["roundName"]
        elif case == "content_type":
            kwargs["content_type"] = "text/html"
        elif case == "delivery":
            kwargs["final_url"] = "https://evil.example/games"
        elif case == "retrieved_at":
            kwargs["retrieved_at"] = "not-time"
        raw = _body(rows)

    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=raw, request_count=2, **kwargs),
            api_key=SECRET,
            year=YEAR,
        )

    assert exc.value.code == reason
    sha = hashlib.sha256(raw).hexdigest()
    assert (tmp_path / "quarantine" / f"{sha}.json").read_bytes() == raw
    _assert_empty(tmp_path)
    ledger = [json.loads(line) for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert len(ledger) == 1
    assert ledger[0]["status"] == "failed"
    assert ledger[0]["reason"] == reason
    assert ledger[0]["request_count"] == 2
    assert ledger[0]["raw_sha256"] == sha
    assert SECRET not in json.dumps(ledger[0])


@pytest.mark.parametrize("boundary", ["raw", "store", "index", "marker", "audit"])
@pytest.mark.parametrize("fault", ["route_error", "os_error", "mid_write"])
def test_e2_failure_at_any_publish_boundary_rolls_back_and_audits(
    boundary, fault, tmp_path
):
    mod = _mod()
    store = mod.CfbdScheduleStore(tmp_path)
    store.capture(fetcher=_fetcher(mod), api_key=SECRET, year=YEAR)
    prior_marker = (tmp_path / "status_latest.json").read_bytes()
    prior_census = _canonical_census(tmp_path)
    changed = _games()
    changed[0]["notes"] = "changed content"
    storage = mod.FailingAt(mod.FilesystemStorage(tmp_path), boundary, fault=fault)
    with pytest.raises(mod.PublishError) as exc:
        store.capture(
            fetcher=_fetcher(mod, body=_body(changed), retrieved_at=T1),
            api_key=SECRET,
            year=YEAR,
            storage=storage,
        )
    assert exc.value.boundary == boundary
    assert (tmp_path / "status_latest.json").read_bytes() == prior_marker
    assert _canonical_census(tmp_path) == prior_census
    index = json.loads((tmp_path / "index.json").read_text())
    assert len(index["vintages"]) == 1
    assert store.partial_artifacts() == []
    ledger = [json.loads(line) for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert ledger[-1]["status"] == "failed"
    assert ledger[-1]["boundary"] == boundary


@pytest.mark.parametrize("corrupt", ["index", "marker"])
def test_e2b_malformed_prior_state_rolls_back_and_audits_paid_attempt(
    corrupt, tmp_path
):
    mod = _mod()
    store = mod.CfbdScheduleStore(tmp_path)
    store.capture(fetcher=_fetcher(mod), api_key=SECRET, year=YEAR)
    target = tmp_path / ("index.json" if corrupt == "index" else "status_latest.json")
    target.write_bytes(b"{malformed prior state")
    prior = _canonical_census(tmp_path)
    changed = _games()
    changed[0]["notes"] = "new paid response"

    with pytest.raises(mod.CaptureError) as exc:
        store.capture(
            fetcher=_fetcher(mod, body=_body(changed), retrieved_at=T1),
            api_key=SECRET,
            year=YEAR,
        )

    assert exc.value.code == "state_integrity_invalid"
    assert _canonical_census(tmp_path) == prior
    assert target.read_bytes() == b"{malformed prior state"
    ledger = [json.loads(line) for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert [row["status"] for row in ledger] == ["success", "failed"]
    assert ledger[-1]["reason"] == "state_integrity_invalid"
    assert ledger[-1]["request_count"] == 1


def test_e3_preexisting_content_object_with_wrong_bytes_is_refused(tmp_path):
    mod = _mod()
    raw = _body()
    sha = hashlib.sha256(raw).hexdigest()
    target = tmp_path / "raw" / "content" / f"{sha}.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"wrong bytes")
    with pytest.raises(mod.CaptureError) as exc:
        mod.CfbdScheduleStore(tmp_path).capture(
            fetcher=_fetcher(mod, body=raw), api_key=SECRET, year=YEAR
        )
    assert exc.value.code == "content_integrity_mismatch"
    assert target.read_bytes() == b"wrong bytes"
    assert not (tmp_path / "status_latest.json").exists()


def test_e3b_preexisting_check_object_with_wrong_bytes_is_refused(tmp_path):
    mod = _mod()
    store = mod.CfbdScheduleStore(tmp_path)
    first = store.capture(
        fetcher=_fetcher(mod, retrieved_at=T0), api_key=SECRET, year=YEAR
    )
    check = tmp_path / "raw" / "checks" / f"{first.check_id}.json"
    check.write_bytes(b"wrong check bytes")
    prior_marker = (tmp_path / "status_latest.json").read_bytes()
    prior_index = (tmp_path / "index.json").read_bytes()

    with pytest.raises(mod.CaptureError) as exc:
        store.capture(
            fetcher=_fetcher(mod, retrieved_at=T0), api_key=SECRET, year=YEAR
        )

    assert exc.value.code == "content_integrity_mismatch"
    assert check.read_bytes() == b"wrong check bytes"
    assert (tmp_path / "status_latest.json").read_bytes() == prior_marker
    assert (tmp_path / "index.json").read_bytes() == prior_index
    assert len(list((tmp_path / "vintages").glob("*.json"))) == 1


def test_d1_marker_and_vintage_carry_complete_nonsecret_provenance(tmp_path):
    mod, _, record = _capture(tmp_path)
    marker = json.loads((tmp_path / "status_latest.json").read_text())
    vintage = mod.CfbdScheduleStore(tmp_path).load_vintage(record.vintage_id)
    for payload in (marker, vintage):
        assert payload["source"] == "cfbd"
        assert payload["provider"] == "College Football Data API"
        assert payload["report_family"] == "games"
        assert payload["competition"] == "fbs"
        assert payload["endpoint"] == ENDPOINT
        assert payload["query"] == QUERY
        assert payload["year"] == YEAR
        assert payload["raw_sha256"] == record.raw_sha256
        assert payload["raw_bytes"] == record.raw_bytes
        assert payload["row_count"] == 2
        assert payload["schema_hash"] == record.schema_hash
        assert payload["parser_version"]
        assert payload["openapi_version"] == "5.21.0"
        assert payload["openapi_sha256"] == OPENAPI_SHA256
    assert marker["status"] == "ok"
    assert marker["last_good_vintage_id"] == record.vintage_id
    assert SECRET not in json.dumps(marker)


def test_d2_cli_refuses_a_missing_key_before_constructing_a_transport(
    tmp_path, monkeypatch, capsys
):
    try:
        cli = importlib.import_module(CLI_MODULE)
    except ModuleNotFoundError as exc:  # pragma: no cover - RED
        pytest.fail(f"{CLI_MODULE} does not exist yet (RED): {exc}")
    monkeypatch.delenv("CFBD_API_KEY", raising=False)
    loaded = []
    monkeypatch.setattr(cli, "load_dotenv", lambda path: loaded.append(Path(path)))
    called = []
    monkeypatch.setattr(cli, "default_fetcher", lambda *_: called.append(True))
    rc = cli.main(["--root", str(tmp_path), "--year", str(YEAR)])
    output = capsys.readouterr()
    assert loaded == [REPO_ROOT / ".env"]
    assert rc != 0
    assert called == []
    assert "CFBD_API_KEY" in output.err
    _assert_empty(tmp_path)


def test_d3_cli_runs_one_injected_fetch_to_publish_without_real_network(
    tmp_path, monkeypatch
):
    mod = _mod()
    try:
        cli = importlib.import_module(CLI_MODULE)
    except ModuleNotFoundError as exc:  # pragma: no cover - RED
        pytest.fail(f"{CLI_MODULE} does not exist yet (RED): {exc}")
    fetcher = _fetcher(mod)
    loaded = []
    monkeypatch.setattr(cli, "load_dotenv", lambda path: loaded.append(Path(path)))
    monkeypatch.setenv("CFBD_API_KEY", SECRET)
    monkeypatch.setattr(cli, "default_fetcher", lambda: fetcher)
    rc = cli.main(["--root", str(tmp_path), "--year", str(YEAR)])
    assert rc == 0
    assert loaded == [REPO_ROOT / ".env"]
    assert len(fetcher.calls) == 1
    assert (tmp_path / "status_latest.json").is_file()


def test_d4_cli_transport_failure_is_named_nonzero_and_credential_safe(
    tmp_path, monkeypatch, capsys
):
    mod = _mod()
    try:
        cli = importlib.import_module(CLI_MODULE)
    except ModuleNotFoundError as exc:  # pragma: no cover - RED
        pytest.fail(f"{CLI_MODULE} does not exist yet (RED): {exc}")
    poison = (
        f"failed {SECRET} at https://user:password@api.collegefootballdata.com/"
        "games?sig=QUERY_SECRET#jwt"
    )
    monkeypatch.setattr(cli, "load_dotenv", lambda _path: None)
    monkeypatch.setenv("CFBD_API_KEY", SECRET)
    monkeypatch.setattr(
        cli, "default_fetcher", lambda: _fetcher(mod, error=poison, request_count=3)
    )

    rc = cli.main(["--root", str(tmp_path), "--year", str(YEAR)])

    output = capsys.readouterr()
    combined = output.out + output.err + _all_text(tmp_path)
    assert rc != 0
    assert "cfbd_fbs_schedules capture failed" in output.err
    assert "Traceback" not in combined
    for marker in (SECRET, "user:password", "QUERY_SECRET", "#jwt"):
        assert marker not in combined


@pytest.mark.parametrize("fault", ["publish_error", "os_error"])
def test_d5_cli_storage_failures_are_named_nonzero_and_credential_safe(
    fault, tmp_path, monkeypatch, capsys
):
    mod = _mod()
    try:
        cli = importlib.import_module(CLI_MODULE)
    except ModuleNotFoundError as exc:  # pragma: no cover - RED
        pytest.fail(f"{CLI_MODULE} does not exist yet (RED): {exc}")
    poison = (
        f"disk failed {SECRET} https://user:password@example.test/x?sig=QUERY_SECRET#jwt"
    )
    failure = (
        mod.PublishError("index", poison)
        if fault == "publish_error"
        else OSError(28, poison)
    )

    class FailingStore:
        def __init__(self, _root):
            pass

        def capture(self, **_kwargs):
            raise failure

    monkeypatch.setattr(cli, "load_dotenv", lambda _path: None)
    monkeypatch.setenv("CFBD_API_KEY", SECRET)
    monkeypatch.setattr(cli, "CfbdScheduleStore", FailingStore)
    monkeypatch.setattr(cli, "default_fetcher", lambda: object())

    rc = cli.main(["--root", str(tmp_path), "--year", str(YEAR)])

    output = capsys.readouterr()
    combined = output.out + output.err
    assert rc != 0
    assert "cfbd_fbs_schedules capture failed" in output.err
    assert "Traceback" not in combined
    for marker in (SECRET, "user:password", "QUERY_SECRET", "#jwt"):
        assert marker not in combined


def test_d6_default_root_is_covered_as_a_required_backup_directory():
    mod = _mod()
    manifest = json.loads(
        (REPO_ROOT / "app" / "config" / "backup_manifest.json").read_text()
    )
    expected = mod.DEFAULT_ROOT.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    matches = [entry for entry in manifest["required"] if entry["path"] == expected]
    assert matches == [{"path": expected, "required": True, "kind": "directory"}]


def test_p1_canonical_paths_are_contained_under_the_store(tmp_path):
    _, _, record = _capture(tmp_path)
    root = tmp_path.resolve()
    for relative in (
        record.raw_path,
        f"raw/content/{record.raw_sha256}.json",
        f"vintages/{record.vintage_id}.json",
        "index.json",
        "status_latest.json",
        "ledger.jsonl",
    ):
        candidate = (tmp_path / relative).resolve()
        assert candidate.is_relative_to(root)
        assert candidate.is_file()


def test_p2_no_api_key_value_appears_in_module_or_cli_source():
    # A regression guard against a developer making the fixture's key or a live
    # key the implementation default. Environment lookup is the only contract.
    module_path = REPO_ROOT / "src" / "dynasty_genius" / "sources" / "cfbd_schedules_capture.py"
    cli_path = REPO_ROOT / "scripts" / "run_cfbd_schedules_capture.py"
    assert SECRET not in module_path.read_text(encoding="utf-8")
    assert SECRET not in cli_path.read_text(encoding="utf-8")
