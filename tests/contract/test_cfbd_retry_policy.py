"""Retry-policy contract for CFBD adapters.

Codex review 2026-08-01: the retry loop was added with NO transition tested —
the existing G2 rows only sleep through three persistent failures and assert the
final raise. Nothing asserted call counts, transient-then-success recovery,
classification, or raw_sink behaviour, so the whole policy could regress
silently. These rows close that.

`time.sleep` is patched throughout so backoff costs no wall-clock.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.dynasty_genius.adapters import cfbd_http
from src.dynasty_genius.adapters.cfbd_qb_adapter import (
    CfbdRequestError,
    fetch_qb_college_stats,
)
from src.dynasty_genius.adapters.cfbd_receiving_adapter import (
    CfbdTeamStatRequestError,
    fetch_team_pass_attempts,
)

QB_GET = "src.dynasty_genius.adapters.cfbd_qb_adapter.httpx.get"
RECV_GET = "src.dynasty_genius.adapters.cfbd_receiving_adapter.httpx.get"
NO_SLEEP = "src.dynasty_genius.adapters.cfbd_http.time.sleep"

REQUEST = httpx.Request("GET", "https://api.collegefootballdata.com/x")


def _ok(payload):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload
    return response


def _status_error(code: int) -> httpx.HTTPStatusError:
    return httpx.HTTPStatusError(
        "boom", request=REQUEST, response=httpx.Response(code, request=REQUEST)
    )


TEAM_ROWS = [{"statName": "passAttempts", "statValue": 430}]


# ── Classification ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "code,expected",
    [
        (408, True),   # explicit timeout status
        (429, True),   # rate limited
        (500, True),
        (502, True),
        (503, True),
        (504, True),
        (501, False),  # deterministic refusal — retry cannot change it
        (505, False),  # deterministic refusal
        (400, False),
        (401, False),
        (404, False),
    ],
)
def test_status_classification(code, expected):
    assert cfbd_http.is_retryable(_status_error(code)) is expected


@pytest.mark.parametrize(
    "exc,expected",
    [
        (httpx.ReadError("x"), True),
        (httpx.ConnectError("x"), True),
        (httpx.ConnectTimeout("x"), True),
        (httpx.ReadTimeout("x"), True),
        (httpx.RemoteProtocolError("x"), True),   # server broke protocol
        (httpx.LocalProtocolError("x"), False),   # WE built a bad request
        (httpx.UnsupportedProtocol("x"), False),  # bad URL scheme
        (ValueError("malformed body"), False),    # schema change, not a hiccup
    ],
)
def test_transport_classification(exc, expected):
    assert cfbd_http.is_retryable(exc) is expected


# ── Transitions: receiving adapter ────────────────────────────────────────────


@patch(NO_SLEEP)
def test_transient_readerror_then_success_makes_exactly_two_calls(sleep_):
    calls = [httpx.ReadError("reset by peer"), _ok(TEAM_ROWS)]

    def side_effect(*a, **k):
        item = calls.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    with patch(RECV_GET, side_effect=side_effect) as get:
        result = fetch_team_pass_attempts("Clemson", 2020, api_key="k")

    assert result == pytest.approx(430.0)
    assert get.call_count == 2
    assert sleep_.call_count == 1


@patch(NO_SLEEP)
def test_persistent_readerror_makes_three_calls_then_raises_typed(sleep_):
    with (
        patch(RECV_GET, side_effect=httpx.ReadError("reset")) as get,
        pytest.raises(CfbdTeamStatRequestError),
    ):
        fetch_team_pass_attempts("Clemson", 2020, api_key="k")

    assert get.call_count == cfbd_http.MAX_ATTEMPTS == 3
    assert sleep_.call_count == 2


@patch(NO_SLEEP)
def test_retryable_status_then_success(sleep_):
    responses = [_status_error(503), _ok(TEAM_ROWS)]

    def side_effect(*a, **k):
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    with patch(RECV_GET, side_effect=side_effect) as get:
        result = fetch_team_pass_attempts("Clemson", 2020, api_key="k")

    assert result == pytest.approx(430.0)
    assert get.call_count == 2


@patch(NO_SLEEP)
@pytest.mark.parametrize("code", [401, 404, 501])
def test_definite_status_is_not_retried(sleep_, code):
    with (
        patch(RECV_GET, side_effect=_status_error(code)) as get,
        pytest.raises(CfbdTeamStatRequestError),
    ):
        fetch_team_pass_attempts("Clemson", 2020, api_key="k")

    assert get.call_count == 1, "a definite answer must cost exactly one paid call"
    assert sleep_.call_count == 0


# ── raw_sink behaviour ────────────────────────────────────────────────────────


@patch(NO_SLEEP)
def test_raw_sink_untouched_when_attempts_are_exhausted(sleep_):
    sink: list = []
    with (
        patch(RECV_GET, side_effect=httpx.ReadError("reset")),
        pytest.raises(CfbdTeamStatRequestError),
    ):
        fetch_team_pass_attempts("Clemson", 2020, api_key="k", raw_sink=sink)

    assert sink == [], "a failure must never leave a partial snapshot behind"


@patch(NO_SLEEP)
def test_raw_sink_populated_exactly_once_on_recovery(sleep_):
    calls = [httpx.ReadError("reset"), _ok(TEAM_ROWS)]

    def side_effect(*a, **k):
        item = calls.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    sink: list = []
    with patch(RECV_GET, side_effect=side_effect):
        fetch_team_pass_attempts("Clemson", 2020, api_key="k", raw_sink=sink)

    assert sink == TEAM_ROWS, "recovery must record the response exactly once"


# ── Transitions: QB adapter (proves both adapters share the policy) ───────────


@patch(NO_SLEEP)
def test_qb_adapter_retries_transient_then_succeeds(sleep_):
    state = {"failed": False}

    def side_effect(url, **kwargs):
        if not state["failed"]:
            state["failed"] = True
            raise httpx.ReadError("reset by peer")
        if "/player/search" in url:
            return _ok([{"id": "p1", "name": "Trevor Lawrence", "team": "Clemson"}])
        if "/stats/season" in url:
            return _ok(TEAM_ROWS)
        return _ok([])

    with patch(QB_GET, side_effect=side_effect) as get:
        result = fetch_qb_college_stats(
            "Trevor Lawrence", 2020, api_key="k", college_team="Clemson"
        )

    assert sleep_.call_count == 1, "the transient failure must have been retried"
    assert get.call_count >= 2
    assert result["completion_pct"] is None  # no passing rows in this fixture


@patch(NO_SLEEP)
def test_qb_adapter_does_not_retry_a_definite_status(sleep_):
    with (
        patch(QB_GET, side_effect=_status_error(404)) as get,
        pytest.raises(CfbdRequestError),
    ):
        fetch_qb_college_stats(
            "Trevor Lawrence", 2020, api_key="k", college_team="Clemson"
        )

    assert get.call_count == 1
    assert sleep_.call_count == 0
