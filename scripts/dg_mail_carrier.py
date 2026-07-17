"""dg_mail_carrier — dialog-aware carrier driver over the D0 delivery machine.

Replaces the retired blind Enter-presser (~/dg-cockpit/mail_carrier.sh). This
module holds NO delivery state of its own: every decision and key emission is a
transition of scripts.dg_delivery.DeliveryMachine, which structurally cannot
answer a dialog, steal a live sender transaction, double-press an exhausted
strand, or auto-submit an untracked/unattributed strand.

Default-paused guard (spec D9): the module exits inert unless the explicit
enable marker exists, so a stray plist load can never resurrect delivery.
Enabling the marker and repointing the plist are separate David words.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    from scripts.dg_delivery import DeliveryMachine, PaneProfile, SendResult, _result
except ModuleNotFoundError:  # direct invocation: sys.path roots at scripts/
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.dg_delivery import DeliveryMachine, PaneProfile, SendResult, _result

ENABLE_MARKER = Path.home() / "dg-cockpit" / "carrier.enabled"
LOG_PATH = Path.home() / "dg-cockpit" / "carrier.log"
SESSION = "dynasty"
PANE_PROFILES = {"%claude": "claude", "%codex": "codex", "%gemini": "gemini"}


class _RealClock:
    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


def _real_capturer(pane_id: str) -> Any:
    raise RuntimeError(
        "live capture requires the production Capturer; the carrier only runs "
        "with explicitly wired dependencies"
    )


def run_once(
    *,
    enable_marker: Path = ENABLE_MARKER,
    runner: Any = subprocess.run,
    capturer: Any = _real_capturer,
    clock: Any = None,
    store: Any = None,
    panes: dict[str, str] | None = None,
) -> SendResult:
    """One carrier fire. Inert without the enable marker (F37)."""

    if not Path(enable_marker).exists():
        return _result("held", "carrier_disabled", terminal=False)
    if store is None:
        return _result("refused", "store_unavailable", terminal=True)
    used_clock = clock or _RealClock()
    outcomes: list[SendResult] = []
    for pane_id, profile_name in (panes or {}).items():
        machine = DeliveryMachine(
            runner=runner,
            capturer=capturer,
            clock=used_clock,
            store=store,
            profile=PaneProfile.for_cli(profile_name),
        )
        outcomes.append(machine.carrier_tick(pane_id))
    if not outcomes:
        return _result("idle", "no_panes_configured", terminal=False)
    return outcomes[-1]


def _discover_panes(runner: Any) -> dict[str, str]:
    """Map live cockpit panes to CLI profiles by title (content beats order)."""

    out = runner(
        ["tmux", "list-panes", "-a", "-F", "#{pane_id}\t#{pane_title}\t#{pane_current_command}"],
        check=True, capture_output=True, text=True,
    ).stdout
    panes: dict[str, str] = {}
    for line in out.splitlines():
        fields = line.split("\t")
        if len(fields) != 3:
            continue
        pane_id, title, command = fields
        lowered = title.lower()
        if "claude" in lowered:
            panes[pane_id] = "claude"
        elif "codex" in lowered:
            panes[pane_id] = "codex"
        elif "gemini" in lowered:
            panes[pane_id] = "gemini"
    return panes


def main() -> int:
    """Production carrier fire [GREEN round-2 B7]: real store, real composite
    capturer, discovered panes. The store must already exist (init-store is a
    separate David-worded deployment step); its absence is a NAMED exit."""

    from scripts.dg_delivery import (
        DEFAULT_STORE_PATH,
        SqliteStoreAdapter,
        StoreError,
        TmuxCapturer,
    )

    if not ENABLE_MARKER.exists():
        print("held: carrier_disabled")
        return 0
    try:
        store = SqliteStoreAdapter(DEFAULT_STORE_PATH)
    except StoreError as error:
        print(f"error: {error}")
        return 5
    try:
        result = run_once(
            runner=subprocess.run,
            capturer=TmuxCapturer(),
            store=store,
            panes=_discover_panes(subprocess.run),
        )
    finally:
        store.close()
    print(f"{result.status}: {result.reason}")
    return 0 if result.reason in ("carrier_disabled", "no_panes_configured") else 1


if __name__ == "__main__":
    raise SystemExit(main())
