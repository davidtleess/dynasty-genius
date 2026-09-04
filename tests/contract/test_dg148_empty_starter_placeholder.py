"""DG-148 — Sleeper's empty-starter placeholder is not a player.

Sleeper fills an EMPTY starter slot with the string ``"0"``. The roster-context
builder filtered ids with ``if pid``, which ``"0"`` passes, so the placeholder
was written into the league snapshot and the universe artifact as a rostered
player — ``UNRESOLVED_IDENTITY``, no name, no position — owned by whichever
roster with an empty slot was processed last. Since DG-145 it also answered
``GET /api/players/0`` with a league-ownership claim naming a real manager.

Measured on the 2026-09-04 13:00 capture: the placeholder appears 8 times across
starter slots, in NO roster's ``players`` list, and it is the ONLY id in
starters/taxi/reserve missing from ``players``. Rostered ids 274 -> 273.

Authorized by David, 2026-09-04 19:34:46Z: "Yes, you have permission to touch a
data capture."
"""
from __future__ import annotations

from src.dynasty_genius.sleeper_universe import _build_roster_context

PLACEHOLDER = "0"


def _roster(roster_id: int, owner: str, **lists: list[str]) -> dict:
    return {"roster_id": roster_id, "owner_id": owner, **lists}


def test_an_empty_starter_slot_creates_no_player():
    """The bug, exactly: seven empty slots on David's own roster."""
    context = _build_roster_context(
        [
            _roster(
                1,
                "david",
                players=["4034", "6794"],
                starters=[PLACEHOLDER, "4034", PLACEHOLDER, PLACEHOLDER],
                taxi=[],
                reserve=[],
            )
        ]
    )
    assert PLACEHOLDER not in context
    assert set(context) == {"4034", "6794"}


def test_the_placeholder_never_becomes_someone_elses_roster():
    """It was attributed to whichever roster was processed LAST, so the phantom
    changed owner as the league's roster order changed."""
    context = _build_roster_context(
        [
            _roster(1, "david", players=["4034"], starters=[PLACEHOLDER, "4034"]),
            _roster(9, "someone_else", players=["6794"], starters=[PLACEHOLDER]),
        ]
    )
    assert PLACEHOLDER not in context
    assert context["4034"]["owner_user_id"] == "david"
    assert context["6794"]["owner_user_id"] == "someone_else"


def test_the_placeholder_is_ignored_in_every_list_it_can_appear_in():
    context = _build_roster_context(
        [
            _roster(
                3,
                "m",
                players=["100"],
                starters=[PLACEHOLDER],
                taxi=[PLACEHOLDER],
                reserve=[PLACEHOLDER],
            )
        ]
    )
    assert set(context) == {"100"}


def test_a_real_starter_keeps_his_flag_and_his_roster():
    context = _build_roster_context(
        [
            _roster(
                5,
                "m",
                players=["100", "200", "300"],
                starters=["100", PLACEHOLDER],
                taxi=["300"],
                reserve=["200"],
            )
        ]
    )
    assert context["100"]["in_starters"] is True
    assert context["100"]["rostered"] is True
    assert context["200"]["on_ir"] is True
    assert context["300"]["on_taxi"] is True
    assert context["200"]["in_starters"] is False


def test_a_real_player_listed_only_as_a_starter_is_still_rostered():
    """Membership keeps the union. Today no non-placeholder id is starters-only
    (measured across all 12 rosters on the 09-04 capture), but dropping a real
    player from David's roster would be a far worse failure than the visible
    junk row this ticket removes, so the union stays and only the placeholder
    goes."""
    context = _build_roster_context(
        [_roster(7, "m", players=["100"], starters=["100", "999"])]
    )
    assert context["999"]["rostered"] is True
    assert context["999"]["in_starters"] is True


def test_falsy_ids_are_still_ignored():
    context = _build_roster_context(
        [_roster(2, "m", players=["100", "", None], starters=[None, ""])]
    )
    assert set(context) == {"100"}
