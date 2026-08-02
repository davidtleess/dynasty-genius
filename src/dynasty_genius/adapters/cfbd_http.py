"""Shared CFBD HTTP retry policy.

One classifier, one retry loop, used by every CFBD adapter. Two copies of a
policy drift; this module exists so the qb and receiving adapters cannot
disagree about what "transient" means.

Policy (Codex review, 2026-08-01). Retry only what a second attempt could
plausibly change:

- `TimeoutException` — connect/read/write/pool timeouts.
- `NetworkError` — connect/read/write/close errors, including the
  `Connection reset by peer` that aborted a paid ~800-call refresh.
- `RemoteProtocolError` — the *server* violated the protocol, often a
  connection dropped mid-response.
- Statuses 408, 429, 500, 502, 503, 504.

Deliberately NOT retried, because a second attempt cannot change the answer and
would only multiply a paid call:

- 4xx other than 408/429 — the request itself is wrong.
- 501 Not Implemented, 505 HTTP Version Not Supported — deterministic refusals.
- `LocalProtocolError` — *we* built a malformed request.
- `UnsupportedProtocol` — a bad URL scheme.
- A malformed or wrong-rooted body — a schema change, not a hiccup.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

#: Statuses worth a second attempt. 408 is the explicit timeout status and 429
#: is rate limiting; both are transient by definition. 501 and 505 are absent
#: on purpose — they are deterministic refusals.
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 0.4


def is_retryable(exc: Exception) -> bool:
    """True when a second attempt could plausibly succeed."""
    if isinstance(
        exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)
    ):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS_CODES
    return False


def with_retry(
    operation: Callable[[], Any],
    *,
    max_attempts: int = MAX_ATTEMPTS,
    backoff_seconds: float = BACKOFF_SECONDS,
) -> Any:
    """Run `operation`, retrying transient failures with exponential backoff.

    This module shares the *policy*, not the transport call. Each adapter still
    issues its own `httpx.get`, so `patch("<adapter>.httpx.get")` keeps working —
    moving the call in here would have silently broken every existing patch
    target and let contract tests reach the real network.

    Raises the originating exception once attempts are exhausted, so callers can
    wrap it in their own typed error. Exhaustion always raises — retry never
    converts a failure into "no data" (G2).
    """
    for attempt in range(max_attempts):
        try:
            return operation()
        except Exception as exc:
            if attempt + 1 < max_attempts and is_retryable(exc):
                time.sleep(backoff_seconds * (2**attempt))
                continue
            raise
    raise AssertionError("unreachable: loop returns or raises")  # pragma: no cover
