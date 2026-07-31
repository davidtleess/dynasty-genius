"""RED contract for the 2026-07-31 wire repair (WIRE-GEMINI-2, WIRE-CLAIM-1/2).

Every row here locks a defect **Codex reproduced against the shared diff** after my first pass
was declared fixed on green tests that never exercised it. The counts were real and the tests
passed; they simply did not lock W1-W4. That is the failure this file exists to prevent.

Origin of the repair: the delivery store held **508 rows in `manual_clear_required` against ONE
`delivered_verified`** — Codex's disposition and Gemini's alignment message had both been written
to the store and never reached a pane.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

import scripts.dg_delivery as d

GEMINI = d.PaneProfile.for_cli("gemini")
CODEX = d.PaneProfile.for_cli("codex")

LIVE_PLACEHOLDER = "> Accept-edits mode: file edits auto-approved (shift+tab to cycle)"
BORDER = "─" * 80


def _idle_gemini_frame() -> str:
    return "\n".join(["  prior conversation output", BORDER, LIVE_PLACEHOLDER, BORDER,
                      "? for shortcuts        accept-edits · Gemini 3.5 Flash · high"])


# --------------------------------------------------------------------------
# W1 — placeholder recognition must be geometry + full match, never a suffix
# --------------------------------------------------------------------------


def test_w1_typed_text_ending_with_the_placeholder_phrase_is_not_empty() -> None:
    """Codex's exact probe. A suffix match called REAL composer text empty, which
    is an overwrite hazard: the sender would paste over someone's unsent strand."""
    probe = "> From Claude — literal note (shift+tab to cycle)"
    assert d._visible_empty(probe, GEMINI) is False


def test_w1_history_mention_without_a_composer_is_not_ready() -> None:
    """Codex's exact probe. As a loose ready marker the phrase classified a pane
    READY with no composer present at all."""
    pane = "completed prose mentions (shift+tab to cycle)\nno composer"
    assert d.classify_pane(pane, GEMINI) is d.PaneState.UNKNOWN


def test_w1_the_real_live_placeholder_still_reads_empty_and_ready() -> None:
    """The fix must not over-correct: the actual chrome must still work, or the
    Gemini edge goes dark again."""
    assert d._visible_empty(LIVE_PLACEHOLDER, GEMINI) is True
    assert d.classify_pane(_idle_gemini_frame(), GEMINI) is d.PaneState.READY


def test_w1_the_other_live_mode_variant_also_reads_empty() -> None:
    """The agy chrome renders more than one mode word; the pattern is anchored on
    the placeholder's shape, not on one mode's literal text."""
    other = "> request-review mode: file edits shown for approval (shift+tab to cycle)"
    assert d._visible_empty(other, GEMINI) is True


def test_w1_placeholder_off_the_prompt_line_supplies_nothing() -> None:
    """Geometry guard: a conversation line cannot donate emptiness to a composer."""
    region = "\n".join(["Accept-edits mode: file edits auto-approved (shift+tab to cycle)",
                        "> a real strand"])
    assert d._visible_empty(region, GEMINI) is False


def test_w1_other_profiles_register_no_placeholder() -> None:
    assert CODEX.placeholder_patterns == ()
    assert d.PaneProfile.for_cli("claude").placeholder_patterns == ()


# --------------------------------------------------------------------------
# W2 / W3 — a terminal transaction must never keep a pane claim,
#           and result and row must agree about terminality
# --------------------------------------------------------------------------


def _Frame(pane_id: str, input_region: str, conversation_region: str = "") -> d.CapturedFrame:
    """The REAL frame dataclass, not a hand-rolled double — a double that omits a
    field the machine reads is how a green suite misses a live defect."""
    raw = "\n".join([conversation_region, BORDER, input_region, BORDER,
                     "? for shortcuts   accept-edits · Gemini 3.5 Flash · high"])
    return d.CapturedFrame(
        raw=raw, pane_id=pane_id, cursor_row=2, cursor_col=2, width=100, height=10,
        title="pane", current_command="agy", input_region=input_region,
        conversation_region=conversation_region,
    )


@pytest.fixture()
def store(tmp_path):
    """The REAL durable store, not a hand-rolled double.

    A double is what let the first pass go green while W2-W4 were live: it
    answered whatever the machine happened to ask and drifted from the durable
    claim semantics that actually matter. These rows run against the same SQLite
    adapter production uses.
    """
    path = tmp_path / "delivery.db"
    d.init_store(path)
    return d.SqliteStoreAdapter(str(path))


def _machine(store, capture_frames, profile=GEMINI):
    frames = list(capture_frames)

    def capturer(target):
        return frames.pop(0) if len(frames) > 1 else frames[0]

    class _Clock:
        def sleep(self, _s):
            return None

        def now(self):
            return 0.0

        def monotonic(self):
            return 0.0

    return d.DeliveryMachine(
        runner=lambda *a, **k: None, capturer=capturer, clock=_Clock(),
        store=store, profile=profile,
    )


def test_w3_foreign_composer_refusal_does_not_claim_the_pane(store) -> None:
    """A refusal that never pasted anything held the pane forever.

    Uses the CODEX profile deliberately: its prompt marker survives typed text, so
    the pane classifies READY while the composer is occupied — which is the only
    way to reach the T1 foreign-composer branch at all. On the gemini chrome a
    typed-in pane classifies UNKNOWN and is refused earlier, by design."""
    frame = _Frame("%900", "\u203a somebody else's unsent strand")
    machine = _machine(store, [frame, frame], profile=CODEX)
    result = machine.send_message("dynasty:9.9", "From Test — body\n\nhello")

    assert result.status == "refused" and result.reason == "input_not_empty"
    assert result.terminal is True
    owner = store.panes.get("%900", {}).get("owner_send_id")
    assert owner is None, f"a terminal refusal kept the claim: owner={owner!r}"


def test_w2_and_w3_terminal_rows_never_retain_a_claim_and_agree_with_the_result(store) -> None:
    """Sweeps the terminal paths: every terminal RESULT must leave a terminal ROW
    and a released pane. W2 was the ordinary post-paste mismatch; W3 was a
    terminal result sitting on a `pasted`/non-terminal row."""
    empty = _Frame("%901", "\u203a ")
    # after the paste the composer shows something that is NOT the wire body
    mismatched = _Frame("%901", "\u203a totally different content")
    machine = _machine(store, [empty, empty, mismatched], profile=CODEX)
    result = machine.send_message("dynasty:9.9", "From Test — body\n\nhello")

    assert result.terminal is True, result
    send_id = result.meta["send_id"]
    row = store.rows[send_id]
    assert machine._terminal_row(row), f"terminal result on a non-terminal row: {row['state']}"
    owner = store.panes.get("%901", {}).get("owner_send_id")
    assert owner is None, f"terminal transaction still owns the pane: {owner!r}"


# --------------------------------------------------------------------------
# W4 — the terminal-owner reap must be CAS-bound against a real store race
# --------------------------------------------------------------------------


def test_w4_a_stale_reaper_cannot_clear_a_newer_owner() -> None:
    """Two adapters over one REAL SQLite store — Codex's required race proof. A
    reaper that read a TERMINAL owner must lose to a live sender that claimed in
    between; the first version used an unconditional upsert and silently
    clobbered the newer claim while its own comment promised it could not."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "delivery.db"
        d.init_store(path)
        stale_reaper = d.SqliteStoreAdapter(str(path))
        live_sender = d.SqliteStoreAdapter(str(path))

        # Seed: the pane is owned by a TERMINAL send that will never release it.
        won, pane = stale_reaper.cas_pane_claim("%950", 0, "w#dead-1")
        assert won
        stale_epoch = int(pane["epoch"])

        # A live sender reaps the terminal owner and takes the pane legitimately.
        reaped, after = live_sender.cas_pane_claim(
            "%950", stale_epoch, None, expected_owner="w#dead-1"
        )
        assert reaped, "setup: a reaper must be able to release a terminal owner"
        acquired, _ = live_sender.cas_pane_claim("%950", int(after["epoch"]), "w#live-1")
        assert acquired, "setup: the live sender must then acquire the freed pane"

        # THE RACE: the first reaper still holds the OLD epoch and now tries to
        # release. Under the unconditional upsert this clobbered the live claim.
        lost, _ = stale_reaper.cas_pane_claim(
            "%950", stale_epoch, None, expected_owner="w#dead-1"
        )
        assert lost is False, "a stale reaper won the CAS and clobbered a live claim"

        with sqlite3.connect(path) as conn:
            owner = conn.execute(
                "SELECT owner_send_id FROM panes WHERE pane_id=?", ("%950",)
            ).fetchone()[0]
        assert owner == "w#live-1", f"live sender was displaced: owner={owner!r}"


# --------------------------------------------------------------------------
# Codex round-2 counter-probes (W1.2, W4.2, W3.2)
# --------------------------------------------------------------------------


def test_w1r2_quoted_history_line_is_not_composer_geometry() -> None:
    """Codex's round-2 probe, verbatim. ASCII '>' is a registered prompt prefix,
    so a MARKDOWN-QUOTED history line reading like the placeholder masqueraded as
    a composer. Readiness must come from the bordered composer box, which
    conversation content cannot draw."""
    probe = ("> Accept-edits mode: file edits auto-approved (shift+tab to cycle)\n"
             "no composer")
    assert d.classify_pane(probe, GEMINI) is d.PaneState.UNKNOWN


def test_w1r2_a_quote_above_a_real_composer_still_reads_ready() -> None:
    """The fix must not over-correct: a real box below quoted history is READY."""
    frame = "\n".join([
        "> Accept-edits mode: file edits auto-approved (shift+tab to cycle)",
        "chatter", BORDER, LIVE_PLACEHOLDER, BORDER,
        "? for shortcuts   accept-edits · Gemini 3.5 Flash · high",
    ])
    assert d.classify_pane(frame, GEMINI) is d.PaneState.READY


def test_w1r2_a_bordered_box_without_the_placeholder_is_not_ready() -> None:
    frame = "\n".join(["hi", BORDER, "> a real typed strand", BORDER, "? for shortcuts"])
    assert d.classify_pane(frame, GEMINI) is d.PaneState.UNKNOWN


def test_w4r2_claim_pane_itself_refuses_to_clobber_a_newer_owner(store) -> None:
    """Codex's round-2 gap: my first W4 row called `cas_pane_claim` directly, so it
    passed even if `_claim_pane` kept the unconditional `persist_pane` upsert.
    This drives `_claim_pane` and injects a competing acquisition BETWEEN its stale
    read and its reap CAS."""
    frame = _Frame("%960", "› ")
    machine = _machine(store, [frame, frame], profile=CODEX)

    # A TERMINAL owner holds the pane — the reap's precondition.
    store.rows["w#dead-1"] = {"send_id": "w#dead-1", "state": "input_not_empty",
                              "terminal": True, "pane_id": "%960"}
    won, pane = store.cas_pane_claim("%960", 0, "w#dead-1")
    assert won
    stale_epoch = int(pane["epoch"])

    # Freeze the machine's view at the stale epoch, then let a competitor take it.
    machine.store.panes["%960"] = dict(pane)
    competitor = d.SqliteStoreAdapter(str(store._conn.execute(
        "PRAGMA database_list").fetchall()[0][2]))
    freed, after = competitor.cas_pane_claim("%960", stale_epoch, None,
                                            expected_owner="w#dead-1")
    assert freed
    taken, _ = competitor.cas_pane_claim("%960", int(after["epoch"]), "w#live-1")
    assert taken, "setup: a live sender must hold the pane before the stale reap"

    # The machine now reaps from its stale view. It must NOT clear the live owner.
    machine._claim_pane("%960", "w#mine-1")

    with sqlite3.connect(store._conn.execute("PRAGMA database_list").fetchall()[0][2]) as conn:
        owner = conn.execute(
            "SELECT owner_send_id FROM panes WHERE pane_id=?", ("%960",)
        ).fetchone()[0]
    assert owner == "w#live-1", f"_claim_pane clobbered a live claim: owner={owner!r}"


def test_w3r2_post_paste_capture_exception_is_terminal_and_releases(store) -> None:
    """Codex's round-2 gap: no row drove the capture-EXCEPTION branch after the
    paste. It must leave a TERMINAL durable row (not `pasted`) and a freed pane."""
    empty = _Frame("%961", "› ")
    pasted = {"yes": False}

    def runner(*_a, **_k):
        # The paste goes through the runner, so binding the failure to this flag
        # targets the POST-PASTE read specifically — a call count would drift the
        # moment the readiness debounce changes and silently stop testing this.
        pasted["yes"] = True

    def capturer(_target):
        if pasted["yes"]:
            raise OSError("capture failed after paste")
        return empty

    class _Clock:
        def sleep(self, _s):
            return None

        def now(self):
            return 0.0

        def monotonic(self):
            return 0.0

    machine = d.DeliveryMachine(
        runner=runner, capturer=capturer, clock=_Clock(),
        store=store, profile=CODEX,
    )
    result = machine.send_message("dynasty:9.9", "From Test — body\n\nhello")

    assert pasted["yes"], "the probe never reached the paste"
    assert result.terminal is True, result
    send_id = result.meta["send_id"]
    row = store.rows[send_id]
    assert machine._terminal_row(row), (
        f"terminal result left a non-terminal row: state={row['state']!r}"
    )
    owner = store.panes.get("%961", {}).get("owner_send_id")
    assert owner is None, f"capture-exception path kept the claim: {owner!r}"
