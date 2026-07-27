"""WIRE-CHIP-1 follow-on: a TERMINAL transaction must not hold a pane claim.

David-authorised via Tower TW26O, after Tower reversed its own "logged, not actioned"
ruling on the evidence: `_submit_with_retry` releases the pane on `delivered_verified`
but NOT on the terminal `delivery_unconfirmed` resolution, so an unconfirmed send held
`%183` forever and every later send was refused `pane_claim_lost`. Three blocked
deliveries this session traced to it.

Scope, absolute: release the claim correctly. Do not redesign the wire or its state
store, and do not touch the mail carrier.
"""

import importlib.util
import sys
from pathlib import Path

# Aliased deliberately: a bare import rebinds this module's SEND_ID and silently breaks
# the owner-bound tests by making the expected owner disagree with the seeded one.
from tests.contract.test_wire_health_hardening_red import READY as _READY
from tests.contract.test_wire_health_hardening_red import SEND_ID as _CONTRACT_SEND_ID
from tests.contract.test_wire_health_hardening_red import WIRE_BODY as _WIRE_BODY
from tests.contract.test_wire_health_hardening_red import FakeCapturer as _FakeCapturer
from tests.contract.test_wire_health_hardening_red import FakeClock as _FakeClock
from tests.contract.test_wire_health_hardening_red import FakeRunner as _FakeRunner
from tests.contract.test_wire_health_hardening_red import FakeStore as _FakeStore
from tests.contract.test_wire_health_hardening_red import PaneFrame as _PaneFrame

_SPEC = importlib.util.spec_from_file_location(
    "dgd_cr", Path(__file__).resolve().parents[1] / "scripts" / "dg_delivery.py")
dgd = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = dgd
_SPEC.loader.exec_module(dgd)

SEND_ID = "w#claim01x-1"
PANE = "%7"


class _Store:
    def __init__(self, owner=SEND_ID):
        self.rows = {SEND_ID: {"send_id": SEND_ID, "pane_id": PANE, "state": "submitted",
                               "terminal": False, "attempts": 1, "profile": "codex",
                               "updated_at": 0.0}}
        self.panes = {PANE: {"pane_id": PANE, "owner_send_id": owner, "epoch": 1}}

    def cas_pane_claim(self, pane_id, expected_epoch, owner, *, expected_owner=None):
        pane = self.panes.get(pane_id)
        if pane is None or int(pane["epoch"]) != int(expected_epoch):
            return False, pane
        if expected_owner is not None and pane.get("owner_send_id") != expected_owner:
            return False, pane
        pane = {"pane_id": pane_id, "owner_send_id": owner, "epoch": int(pane["epoch"]) + 1}
        self.panes[pane_id] = pane
        return True, pane


class _Machine:
    """Carries only what `_release_pane` needs; the release path is the unit under test."""

    def __init__(self, store):
        self.store = store


def test_release_pane_frees_an_owned_claim():
    store = _Store()
    dgd.DeliveryMachine._release_pane(_Machine(store), PANE, expected_owner=SEND_ID)
    assert store.panes[PANE]["owner_send_id"] is None


def test_release_pane_never_clears_a_foreign_claim():
    """The owner-bound guard is the safety property; this fix must not weaken it."""
    store = _Store(owner="w#someoneelse-1")
    dgd.DeliveryMachine._release_pane(_Machine(store), PANE, expected_owner=SEND_ID)
    assert store.panes[PANE]["owner_send_id"] == "w#someoneelse-1"


def test_terminal_unconfirmed_resolution_releases_the_claim():
    """THE DEFECT: `delivered_verified` releases, terminal `delivery_unconfirmed` did not.

    Asserted against the real source so the fix cannot regress into a comment: the
    terminal unconfirmed return must be preceded by an owner-bound release."""
    src = Path(__file__).resolve().parents[1].joinpath("scripts/dg_delivery.py").read_text()
    marker = 'self._transition(send_id, "delivery_unconfirmed")'
    assert marker in src
    tail = src.split(marker, 1)[1].split("return _result(", 1)[0]
    assert "_release_pane" in tail, (
        "terminal delivery_unconfirmed must release the pane claim before returning; "
        "otherwise the claim is held forever and every later send is refused "
        "pane_claim_lost")
    assert "expected_owner=send_id" in tail, "release must stay owner-bound"


def test_carrier_module_is_untouched_by_this_fix():
    """David's standing constraint, reaffirmed TW26F/TW26I/TW26O."""
    carrier = Path(__file__).resolve().parents[1] / "scripts" / "dg_mail_carrier.py"
    text = carrier.read_text(encoding="utf-8")
    assert "enable" in text.lower(), "carrier must retain its explicit enable-marker guard"


# ---------------------------------------------------------------- BEHAVIOURAL tests
#
# Codex r5 defect 4: the source-substring test above passes even with the release call
# COMMENTED OUT, because the comment still contains the string. It asserted on text, not
# behaviour — the "test passes by asserting nothing" failure mode. These drive the real
# code paths and assert the claim is actually released.


def _live_machine(*frames, store=None):
    store = store or _FakeStore()
    machine = dgd.DeliveryMachine(
        runner=_FakeRunner(), capturer=_FakeCapturer(*frames), clock=_FakeClock(),
        store=store, profile=dgd.PaneProfile.for_cli("codex"),
    )
    return machine, store


def test_unconfirmed_branch_actually_releases_the_claim():
    """Drives `_submit_with_retry` to its terminal unconfirmed resolution and asserts the
    pane is free afterwards. Commenting out the release makes THIS test fail."""
    store = _FakeStore()
    row = store.seed_row(state="composed_verified", pane_id="%7")
    store.seed_pane(owner_send_id=_CONTRACT_SEND_ID)
    # READY with the exact body: passes the pre-key guard, keys, then never confirms.
    frames = [_PaneFrame(_READY, input_region=_WIRE_BODY) for _ in range(12)]
    machine, store = _live_machine(*frames, store=store)
    result = machine._submit_with_retry(row, _WIRE_BODY)
    assert result.reason == "delivery_unconfirmed"
    assert store.panes["%7"]["owner_send_id"] is None, (
        "terminal delivery_unconfirmed must release the pane claim")


def test_attempts_exhausted_also_releases_and_marks_terminal():
    """Codex r5 defect 3: `retry_submit` returned terminal `submit_attempts_exhausted`
    while RETAINING the claim and leaving the row non-terminal, so the same
    `pane_claim_lost` jam stayed reachable by another route."""
    store = _FakeStore()
    row = store.seed_row(state="submitted", pane_id="%7", attempts=2)
    store.seed_pane(owner_send_id=_CONTRACT_SEND_ID)
    machine, store = _live_machine(_PaneFrame(_READY), store=store)
    result = machine.retry_submit(_CONTRACT_SEND_ID)
    assert result.reason == "submit_attempts_exhausted"
    assert store.panes["%7"]["owner_send_id"] is None, (
        "a terminal resolution must not retain the pane claim")
    assert row["terminal"] is True, "a terminal result must mark the row terminal"


def test_retry_submit_terminal_environment_routes_also_release():
    """Codex r6 HIGH: a THIRD family of terminal returns in `retry_submit` —
    `pane_not_ready`, `pane_unreadable`, `wire_body_mismatch` — returned terminal=True
    while retaining the claim and leaving the row non-terminal, so the transaction looked
    resumable and the pane stayed jammed."""
    store = _FakeStore()
    row = store.seed_row(state="submit_attempt(1)", pane_id="%7", attempts=1)
    store.seed_pane(owner_send_id=_CONTRACT_SEND_ID)
    dialog = _PaneFrame("Allow this action?\n❯ 1. Yes\n  2. No")
    machine, store = _live_machine(dialog, store=store)
    result = machine.retry_submit(_CONTRACT_SEND_ID)
    assert result.reason == "pane_not_ready"
    assert store.panes["%7"]["owner_send_id"] is None, "terminal route must release"
    assert row["terminal"] is True, "terminal result must mark the row terminal"
