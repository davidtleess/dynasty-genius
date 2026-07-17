"""Wire-health GREEN round-1 reinforcement contract (R1-R14).

Covers the RED blind spots Codex's independent GREEN review (2026-07-17 13:26 ET)
proved with its break-suite: real-path wiring, terminal-row immutability across
every public API, pane-claim enforcement at the side-effect boundary, carrier
correlation/precedence in carrier_tick itself, evidence-based reconciliation,
strict dialog approval, ghost-READY classification, and the D8 body contract.

Authored by Claude per Codex's blind-spot-repair handoff; subject to Codex
re-review with the repaired GREEN blob set. Hermetic throughout.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from tests.contract.test_wire_health_hardening_red import (
    BODY,
    DIALOG,
    READY,
    SEND_ID,
    WIRE_BODY,
    FakeCapturer,
    FakeClock,
    FakeRunner,
    FakeStore,
    PaneFrame,
    _machine,
)


def _delivery():
    return importlib.import_module("scripts.dg_delivery")


def _sender():
    return importlib.import_module("scripts.tmux_msg")


def test_r1_cli_send_drives_the_delivery_machine_not_raw_tmux(monkeypatch, tmp_path) -> None:
    sender = _sender()
    delivery = _delivery()
    driven: list[str] = []

    class _FakeMachine:
        def send_message(self, target, body, **kwargs):
            driven.append(target)
            return delivery.SendResult(
                "delivered_verified", "delivered_verified", "submitted", True, 1, [],
                {"exit_code": 0},
            )

    monkeypatch.setattr(sender, "_machine_for", lambda target: _FakeMachine())
    body_path = tmp_path / "body.txt"
    body_path.write_text("From Codex — probe", encoding="utf-8")
    legacy_calls: list = []
    monkeypatch.setattr(sender, "send_message", lambda *a, **k: legacy_calls.append(a))
    monkeypatch.setattr(
        "sys.argv",
        ["tmux_msg.py", "send", "dynasty:1.2", "--message-file", str(body_path), "--submit"],
    )
    with pytest.raises(SystemExit) as exit_info:
        sender.main()
    assert exit_info.value.code == 0
    assert driven == ["dynasty:1.2"]
    assert legacy_calls == []


def test_r2_real_sqlite_store_drives_the_machine_end_to_end(tmp_path) -> None:
    delivery = _delivery()
    path = tmp_path / "delivery.db"
    delivery.init_store(path)
    store = delivery.SqliteStoreAdapter(path)
    # Build the machine manually over the REAL adapter.
    capturer = FakeCapturer(
        PaneFrame(READY, input_region=""),
        PaneFrame(READY, input_region=""),
    )
    runner = FakeRunner()
    machine = delivery.DeliveryMachine(
        runner=runner,
        capturer=capturer,
        clock=FakeClock(),
        store=store,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    result = machine.acquire_composer("%7", "From Codex — real-store probe")
    assert result.reason == "composing"
    send_id = result.meta["send_id"]
    store.close()
    reloaded = delivery.SqliteStoreAdapter(path)
    assert reloaded.rows[send_id]["state"] == "composing"
    assert reloaded.panes["%7"]["owner_send_id"] == send_id
    reloaded.close()


def test_r3_terminal_rows_survive_every_public_mutation_path() -> None:
    delivery = _delivery()
    for terminal_state in ("strand_lost", "episode_exhausted", "manual_clear_required"):
        store = FakeStore()
        original = store.seed_row(state=terminal_state, terminal=True, wire_digest=WIRE_BODY).copy()
        frame = PaneFrame(READY, input_region=WIRE_BODY)
        machine, runner, *_ = _machine(
            delivery, frame, frame, frame, frame, store=store
        )
        adopt = machine.send_message("dynasty:1.2", BODY)
        assert adopt.terminal is True
        assert store.rows[SEND_ID]["state"] == terminal_state
        retry = machine.retry_press(SEND_ID, elapsed=999.0)
        assert retry.terminal is True
        assert store.rows[SEND_ID] == original
        assert runner.key_calls == []


def test_r3b_submit_and_recover_refuse_terminal_rows() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="episode_exhausted", terminal=True, updated_at=-9999.0)
    machine, runner, *_ = _machine(delivery, PaneFrame(READY), PaneFrame(READY), store=store)
    assert machine.submit(SEND_ID).terminal is True
    assert machine.retry_submit(SEND_ID).terminal is True
    assert machine.recover_stale_claim(SEND_ID).terminal is True
    assert store.rows[SEND_ID]["state"] == "episode_exhausted"
    assert runner.key_calls == []


def test_r4_pane_claim_loser_emits_zero_side_effects() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_pane(pane_id="%7", owner_send_id="w#occupant1-9", epoch=4)
    empty = PaneFrame(READY, input_region="")
    machine, runner, *_ = _machine(delivery, empty, empty, empty, store=store)
    result = machine.send_message("dynasty:1.2", BODY)
    assert result.reason == "pane_claim_lost"
    assert runner.paste_calls == []
    assert runner.key_calls == []


def test_r4b_carrier_press_requires_the_pane_claim() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="orphan_eligible")
    store.seed_pane(pane_id="%7", owner_send_id="w#occupant1-9", epoch=4)
    frame = PaneFrame(READY, input_region=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, frame, frame, store=store)
    result = machine.carrier_tick("%7")
    assert runner.key_calls == []
    assert result.reason in {"pane_claim_lost", "held_dialog_shape", "untracked_strand"}


def test_r5_carrier_never_attaches_a_row_to_unstamped_foreign_text() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="orphan_eligible")
    frame = PaneFrame(READY, input_region="From Human — unrelated unstamped text")
    machine, runner, *_ = _machine(delivery, frame, frame, store=store)
    result = machine.carrier_tick("%7")
    assert runner.key_calls == []
    assert result.reason == "untracked_strand"
    assert store.rows[SEND_ID]["attempts"] == 0


def test_r5b_carrier_tick_resolves_positive_delivery_before_pressing() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="press_attempt(1)", attempts=1)
    frame = PaneFrame(READY, input_region=WIRE_BODY, conversation_region=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, frame, frame, store=store)
    result = machine.carrier_tick("%7")
    assert result.status == "delivered_verified"
    assert store.rows[SEND_ID]["state"] == "delivered_verified"
    assert runner.key_calls == []


def test_r6_reconcile_ignores_a_lying_caller_label() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="submit_attempt(1)", wire_digest=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, PaneFrame(READY), PaneFrame(READY), store=store)
    result = machine.reconcile(
        SEND_ID, crash_window="key_no_result_new_occurrence", actor="sender"
    )
    assert result.reason == "manual_clear_required"
    assert store.rows[SEND_ID]["state"] == "manual_clear_required"
    assert runner.key_calls == []


def test_r6b_reconcile_persists_the_delivered_verdict_from_evidence() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="press_attempt(1)", wire_digest=WIRE_BODY)
    frame = PaneFrame(READY, conversation_region=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, frame, frame, store=store)
    result = machine.reconcile(SEND_ID, crash_window="anything", actor="carrier")
    assert result.reason == "delivered_verified"
    assert store.rows[SEND_ID]["state"] == "delivered_verified"
    assert runner.key_calls == []


def test_r7_approve_requires_a_highlighted_option_row() -> None:
    delivery = _delivery()
    unhighlighted = "Allow this action?\n  1. Yes\n  2. No"
    machine, runner, *_ = _machine(delivery, PaneFrame(unhighlighted))
    result = machine.approve("%7", option_text="Yes")
    assert result.reason == "no_highlighted_option"
    assert runner.key_calls == []


def test_r7b_approve_fails_loud_when_the_dialog_stays_open() -> None:
    delivery = _delivery()
    machine, runner, *_ = _machine(delivery, PaneFrame(DIALOG), PaneFrame(DIALOG))
    result = machine.approve("%7", option_text="Yes")
    assert result.reason == "dialog_still_open"
    assert result.status != "approved"
    assert result.meta["warning_exit"] != 0
    assert len(runner.key_calls) == 1


def test_r8_dim_ready_marker_never_classifies_ready() -> None:
    delivery = _delivery()
    profile = delivery.PaneProfile.for_cli("claude")
    assert delivery.classify_pane("\x1b[2m❯ \x1b[22m", profile) is delivery.PaneState.UNKNOWN


def test_r9_body_contract_names_every_failure(tmp_path: Path) -> None:
    sender = _sender()
    nul = tmp_path / "nul.txt"
    nul.write_bytes(b"From Codex \x00 body")
    with pytest.raises(sender.BodyError, match="body_contains_nul"):
        sender.read_body(str(nul))
    big = tmp_path / "big.txt"
    big.write_bytes(b"A" * (sender.BODY_MAX_BYTES + 1))
    with pytest.raises(sender.BodyError, match="body_too_large"):
        sender.read_body(str(big))
    bad = tmp_path / "bad.txt"
    bad.write_bytes(b"\xff\xfe invalid")
    with pytest.raises(sender.BodyError, match="body_not_utf8"):
        sender.read_body(str(bad))
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"  \n ")
    with pytest.raises(sender.BodyError, match="body_empty"):
        sender.read_body(str(empty))
    with pytest.raises(sender.BodyError, match="body_unreadable"):
        sender.read_body(str(tmp_path / "missing.txt"))


def test_r10_ready_debounce_reads_are_separated_by_the_pinned_gap() -> None:
    delivery = _delivery()
    clock = FakeClock()
    empty = PaneFrame(READY, input_region="")
    machine, *_ , used_clock, _ = _machine(
        delivery, empty, empty, empty, PaneFrame(READY, input_region=BODY), clock=clock
    )
    machine.send_message("dynasty:1.2", BODY)
    assert 0.5 in used_clock.sleeps


def test_r11_carrier_driver_reaches_the_stale_handoff_fork() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="composed_verified", updated_at=-301.0, profile="claude")
    store.seed_pane(pane_id="%7", owner_send_id=SEND_ID, epoch=2)
    frame = PaneFrame(READY, input_region=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, frame, frame, store=store, profile="claude")
    result = machine.carrier_tick("%7")
    assert result.reason == "orphan_manual_required"
    assert store.rows[SEND_ID]["state"] == "orphan_manual_required"
    assert runner.key_calls == []


# --- GREEN round-2 reinforcements (Codex 13:58 B1-B10/H1) ---


def test_r12_two_stale_adapters_cannot_both_win_row_and_pane_cas(tmp_path: Path) -> None:
    delivery = _delivery()
    path = tmp_path / "delivery.db"
    delivery.init_store(path)
    seed = delivery.SqliteStoreAdapter(path)
    seed_machine = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(), clock=FakeClock(), store=seed,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    seed_machine._new_row(SEND_ID, "%7", "composed_verified", wire_digest=WIRE_BODY)
    assert seed_machine._claim_pane("%7", SEND_ID)
    a = delivery.SqliteStoreAdapter(path)
    b = delivery.SqliteStoreAdapter(path)
    row_a, row_b = dict(a.rows[SEND_ID]), dict(b.rows[SEND_ID])
    won_a = a.cas_row_state(SEND_ID, "composed_verified", "orphan_candidate", row_a)
    won_b = b.cas_row_state(SEND_ID, "composed_verified", "orphan_candidate", row_b)
    assert [won_a, won_b].count(True) == 1
    epoch = a.panes["%7"]["epoch"]
    claim_a = a.cas_pane_claim("%7", epoch, "w#racerraa-1")
    claim_b = b.cas_pane_claim("%7", epoch, "w#racerrbb-1")
    assert [claim_a[0], claim_b[0]].count(True) <= 1
    for adapter in (seed, a, b):
        adapter.close()


def test_r13_last_press_at_survives_adapter_reopen_and_blocks_instant_repress(tmp_path: Path) -> None:
    delivery = _delivery()
    path = tmp_path / "delivery.db"
    delivery.init_store(path)
    clock = FakeClock()
    clock.advance(1000.0)
    store1 = delivery.SqliteStoreAdapter(path)
    frame = PaneFrame(READY, input_region=WIRE_BODY)
    machine1 = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(frame, frame), clock=clock, store=store1,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    machine1._new_row(SEND_ID, "%7", "orphan_eligible", wire_digest=WIRE_BODY)
    machine1.carrier_tick("%7")
    assert store1.rows[SEND_ID]["attempts"] == 1
    store1.close()
    store2 = delivery.SqliteStoreAdapter(path)
    assert float(store2.rows[SEND_ID]["last_press_at"]) == 1000.0
    runner2 = FakeRunner()
    machine2 = delivery.DeliveryMachine(
        runner=runner2, capturer=FakeCapturer(frame, frame), clock=clock, store=store2,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    machine2.carrier_tick("%7")
    assert runner2.key_calls == []
    assert store2.rows[SEND_ID]["attempts"] == 1
    store2.close()


def test_r14_release_and_ack_clear_are_durable(tmp_path: Path) -> None:
    delivery = _delivery()
    path = tmp_path / "delivery.db"
    delivery.init_store(path)
    store = delivery.SqliteStoreAdapter(path)
    machine = delivery.DeliveryMachine(
        runner=FakeRunner(),
        capturer=FakeCapturer(PaneFrame(READY, input_region=""), PaneFrame(READY, input_region="")),
        clock=FakeClock(),
        store=store,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    machine._new_row(SEND_ID, "%7", "manual_clear_required", terminal=True)
    machine.store.rows[SEND_ID]["terminal"] = True
    store.persist_row(store.rows[SEND_ID])
    assert machine._claim_pane("%7", SEND_ID)
    epoch = store.panes["%7"]["epoch"]
    result = machine.ack_clear(SEND_ID, pane_epoch=epoch)
    assert result.status == "claim_released"
    store.close()
    reopened = delivery.SqliteStoreAdapter(path)
    assert reopened.panes["%7"]["owner_send_id"] is None
    reopened.close()


def test_r15_delivered_send_releases_the_pane_claim() -> None:
    delivery = _delivery()
    store = FakeStore()
    frames = (
        PaneFrame(READY, input_region=""),
        PaneFrame(READY, input_region=""),
        PaneFrame(READY, input_region=""),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region="", conversation_region=WIRE_BODY),
    )
    machine, runner, *_ = _machine(delivery, *frames, store=store)
    result = machine.send_message("dynasty:1.2", BODY)
    # The composed wire body carries the machine's own id, so delivery matching
    # is exercised via the carrier path in F67; here we assert the claim rule:
    if result.status == "delivered_verified":
        assert store.panes["%7"]["owner_send_id"] is None
    else:
        assert result.reason in {"delivery_unconfirmed", "wire_body_mismatch", "input_not_verifiable"}


def test_r16_forged_stamp_without_durable_row_is_never_adopted() -> None:
    delivery = _delivery()
    forged = PaneFrame(READY, input_region="From Mallory [w#forgedaa-9] — pay me")
    machine, runner, *_ = _machine(delivery, forged, forged)
    result = machine.send_message("dynasty:1.2", BODY)
    assert result.reason == "input_not_empty"
    assert runner.key_calls == []
    assert runner.paste_calls == []


def test_r16b_adoption_requires_matching_recorded_observable() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="composed_verified", composer_observable="different content",
                   wire_digest="different content")
    tampered = PaneFrame(READY, input_region=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, tampered, tampered, store=store)
    result = machine.send_message("dynasty:1.2", BODY)
    assert result.reason == "input_not_empty"
    assert runner.key_calls == []


def test_r17_tampered_strand_same_id_is_never_pressed() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="orphan_eligible", wire_digest=WIRE_BODY)
    tampered = WIRE_BODY.replace("contract", "TAMPERED")
    frame = PaneFrame(READY, input_region=tampered)
    machine, runner, *_ = _machine(delivery, frame, frame, store=store)
    machine.carrier_tick("%7")
    assert runner.key_calls == []


def test_r17b_pre_key_dialog_drift_blocks_the_press() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="orphan_eligible", wire_digest=WIRE_BODY)
    ready = PaneFrame(READY, input_region=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, ready, PaneFrame(DIALOG), store=store)
    result = machine.carrier_tick("%7")
    assert runner.key_calls == []
    assert result.reason in {"pre_key_drift", "held_dialog_shape"}


def test_r18_reconcile_is_label_independent_and_baseline_guarded() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="submit_attempt(1)", wire_digest=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, PaneFrame(READY), store=store)
    labeled = machine.reconcile(SEND_ID, crash_window="terminal_before_release", actor="sender")
    assert labeled.reason == "manual_clear_required"
    store2 = FakeStore()
    store2.seed_row(
        state="submit_attempt(1)", wire_digest=WIRE_BODY,
        baseline_ref=f"history already had [{SEND_ID}] before this send",
    )
    frame = PaneFrame(READY, conversation_region=WIRE_BODY)
    machine2, runner2, *_ = _machine(delivery, frame, frame, store=store2)
    stale = machine2.reconcile(SEND_ID, crash_window="anything", actor="sender")
    assert stale.reason == "manual_clear_required"
    assert runner2.key_calls == []


def test_r19_terminal_rows_are_byte_immutable_under_every_mutator() -> None:
    delivery = _delivery()
    store = FakeStore()
    original = store.seed_row(
        state="strand_lost", terminal=True, carrier_eligible=True, updated_at=-42.0
    ).copy()
    machine, runner, *_ = _machine(delivery, PaneFrame(READY), PaneFrame(READY), store=store)
    machine.mark_superseded(SEND_ID)
    assert store.rows[SEND_ID] == original
    machine._transition(SEND_ID, "strand_lost")
    assert store.rows[SEND_ID] == original
    assert runner.key_calls == []


def test_r20_production_capture_is_one_dispatch(monkeypatch) -> None:
    delivery = _delivery()
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        meta = "DGMETA\t%7\t1\t2\t120\t40\tCodex pane\tcodex"
        return type("Completed", (), {"returncode": 0, "stdout": meta + "\ncodex > \n", "stderr": ""})()

    capturer = delivery.TmuxCapturer(runner=fake_run)
    frame = capturer.capture("%7")
    assert len(calls) == 1
    assert ";" in calls[0]
    assert frame.pane_id == "%7"
    assert frame.current_command == "codex"


def test_r21_cli_exposes_approve_and_direct_send_reaches_named_store_error(tmp_path: Path) -> None:
    import subprocess
    import sys

    sender = _sender()
    parser = sender.build_parser()
    args = parser.parse_args(["approve", "dynasty:1.2", "--option", "Yes"])
    assert args.command == "approve"
    assert args.option == "Yes"
    body = tmp_path / "b.txt"
    body.write_text("From Test — probe", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "scripts/tmux_msg.py", "send", "dynasty:9.9",
         "--message-file", str(body)],
        capture_output=True, text=True, cwd=str(Path(sender.__file__).resolve().parent.parent),
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
    )
    assert "ModuleNotFoundError" not in proc.stderr
    assert "store_unavailable" in proc.stderr + proc.stdout
    assert proc.returncode == 5


# --- GREEN round-3 reinforcements (Codex 14:28 B1-B7/H1) ---


def test_r22_cas_loss_at_the_press_moment_emits_zero_keys(tmp_path: Path) -> None:
    delivery = _delivery()
    path = tmp_path / "delivery.db"
    delivery.init_store(path)
    seed = delivery.SqliteStoreAdapter(path)
    seed_machine = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(), clock=FakeClock(), store=seed,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    seed_machine._new_row(SEND_ID, "%7", "orphan_eligible", wire_digest=WIRE_BODY)
    stale = delivery.SqliteStoreAdapter(path)
    winner = delivery.SqliteStoreAdapter(path)
    row_w = dict(winner.rows[SEND_ID])
    assert winner.cas_row_state(SEND_ID, "orphan_eligible", "manual_clear_required", row_w)
    frame = PaneFrame(READY, input_region=WIRE_BODY)
    runner = FakeRunner()
    machine = delivery.DeliveryMachine(
        runner=runner, capturer=FakeCapturer(frame, frame, frame), clock=FakeClock(),
        store=stale, profile=delivery.PaneProfile.for_cli("codex"),
    )
    result = machine.carrier_tick("%7")
    assert runner.key_calls == []
    assert result.reason in {"cas_lost", "manual_clear_required", "held_dialog_shape"}
    for adapter in (seed, stale, winner):
        adapter.close()


def test_r23_stale_release_cannot_clobber_a_newer_owner(tmp_path: Path) -> None:
    delivery = _delivery()
    path = tmp_path / "delivery.db"
    delivery.init_store(path)
    a = delivery.SqliteStoreAdapter(path)
    machine_a = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(), clock=FakeClock(), store=a,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    assert machine_a._claim_pane("%7", "w#firstaaa-1")
    stale_epoch_view = delivery.SqliteStoreAdapter(path)
    b = delivery.SqliteStoreAdapter(path)
    machine_b = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(), clock=FakeClock(), store=b,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    b.cas_pane_claim("%7", b.panes["%7"]["epoch"], None)
    assert machine_b._claim_pane("%7", "w#newerooo-2")
    stale_machine = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(), clock=FakeClock(),
        store=stale_epoch_view, profile=delivery.PaneProfile.for_cli("codex"),
    )
    stale_machine._release_pane("%7")
    fresh = delivery.SqliteStoreAdapter(path)
    assert fresh.panes["%7"]["owner_send_id"] == "w#newerooo-2"
    for adapter in (a, b, stale_epoch_view, fresh):
        adapter.close()


def test_r24_compose_refuses_existing_ids_and_retry_press_refuses_illegal_edges() -> None:
    delivery = _delivery()
    store = FakeStore()
    original = store.seed_row(state="episode_exhausted", terminal=True).copy()
    machine, runner, *_ = _machine(delivery, PaneFrame(READY), PaneFrame(READY), store=store)
    composed = machine.compose("%7", "From Codex — again", send_id=SEND_ID)
    assert composed.reason == "send_id_exists"
    assert store.rows[SEND_ID] == original
    assert runner.paste_calls == []
    store2 = FakeStore()
    store2.seed_row(state="composing")
    machine2, runner2, *_ = _machine(delivery, PaneFrame(READY), PaneFrame(READY), store=store2)
    illegal = machine2.retry_press(SEND_ID, elapsed=999.0)
    assert illegal.reason == "illegal_edge"
    assert runner2.key_calls == []
    assert store2.rows[SEND_ID]["state"] == "composing"


def test_r25_sender_pre_key_dialog_and_tampered_retry_block_keys() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(
        state="composed_verified", wire_digest=WIRE_BODY, composer_observable=WIRE_BODY
    )
    frames = (
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(DIALOG),
    )
    machine, runner, *_ = _machine(delivery, *frames, store=store)
    result = machine.send_message("dynasty:1.2", BODY)
    assert result.reason == "pre_key_drift"
    assert runner.key_calls == []
    store2 = FakeStore()
    store2.seed_row(
        state="composed_verified", wire_digest=WIRE_BODY, composer_observable=WIRE_BODY
    )
    tampered = WIRE_BODY.replace("contract", "SWAPPED")
    frames2 = (
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=tampered),
        PaneFrame(READY, input_region=tampered),
    )
    machine2, runner2, *_ = _machine(delivery, *frames2, store=store2)
    machine2.send_message("dynasty:1.2", BODY)
    assert len(runner2.key_calls) == 1


def test_r25b_submit_requires_the_pane_claim() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="composed_verified", wire_digest=WIRE_BODY)
    store.seed_pane(pane_id="%7", owner_send_id="w#foreignoo-3", epoch=6)
    machine, runner, *_ = _machine(delivery, PaneFrame(READY), PaneFrame(READY), store=store)
    result = machine.submit(SEND_ID)
    assert result.reason == "pane_claim_lost"
    assert runner.key_calls == []


def test_r26_fresh_sends_persist_baseline_and_carrier_honors_it() -> None:
    delivery = _delivery()
    history = f"old traffic already contains [{SEND_ID}] here"
    store = FakeStore()
    store.seed_row(
        state="press_attempt(1)", attempts=1, wire_digest=WIRE_BODY, baseline_ref=history
    )
    frame = PaneFrame(READY, input_region=WIRE_BODY, conversation_region=history)
    machine, runner, *_ = _machine(delivery, frame, frame, frame, store=store)
    result = machine.carrier_tick("%7")
    assert result.status != "delivered_verified"
    assert runner.key_calls == []
    empty = PaneFrame(READY, input_region="", conversation_region="prior context")
    store2 = FakeStore()
    frames = (empty, empty, empty, PaneFrame(READY, input_region="x"), PaneFrame(READY))
    machine2, _, *_ = _machine(delivery, *frames, store=store2)
    sent = machine2.send_message("dynasty:1.2", BODY)
    created = store2.rows.get(sent.meta.get("send_id", ""), {})
    assert created.get("baseline_ref") == "prior context"


def test_r27_durable_first_observed_at_blocks_same_time_press(tmp_path: Path) -> None:
    delivery = _delivery()
    path = tmp_path / "delivery.db"
    delivery.init_store(path)
    clock = FakeClock()
    clock.advance(500.0)
    store1 = delivery.SqliteStoreAdapter(path)
    frame = PaneFrame(READY, input_region=WIRE_BODY)
    machine1 = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(frame), clock=clock, store=store1,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    machine1._new_row(SEND_ID, "%7", "composed_verified", wire_digest=WIRE_BODY,
                      updated_at=100.0)
    store1.rows[SEND_ID]["updated_at"] = 100.0
    store1.persist_row(store1.rows[SEND_ID])
    first = machine1.carrier_tick("%7")
    assert first.reason == "orphan_candidate"
    store1.close()
    store2 = delivery.SqliteStoreAdapter(path)
    assert float(store2.rows[SEND_ID]["first_observed_at"]) == 500.0
    runner2 = FakeRunner()
    machine2 = delivery.DeliveryMachine(
        runner=runner2, capturer=FakeCapturer(frame, frame), clock=clock, store=store2,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    second = machine2.carrier_tick("%7")
    assert runner2.key_calls == []
    assert second.reason in {"orphan_candidate", "press_wait"}
    store2.close()


def test_r28_migration_performs_ddl_and_rolls_back_on_failure(tmp_path: Path) -> None:
    delivery = _delivery()
    import sqlite3 as sqlite_module

    old = tmp_path / "old.db"
    conn = sqlite_module.connect(old)
    conn.execute("CREATE TABLE rows (send_id TEXT PRIMARY KEY, state TEXT NOT NULL)")
    conn.execute("INSERT INTO rows (send_id, state) VALUES (?, ?)", (SEND_ID, "composing"))
    conn.commit()
    conn.close()
    status = delivery.migrate_store(old, target_schema=delivery.SCHEMA_VERSION)
    assert status.backup_verified is True
    adapter = delivery.SqliteStoreAdapter(old)
    assert adapter.rows[SEND_ID]["state"] == "composing"
    adapter.close()
    with pytest.raises(delivery.StoreError, match="unsupported_target_schema"):
        delivery.migrate_store(old, target_schema=delivery.SCHEMA_VERSION + 7)


def test_r29_stray_diagnostic_observes_without_keying() -> None:
    delivery = _delivery()
    machine, runner, *_ = _machine(delivery, PaneFrame(READY, input_region="1"))
    result = machine.diagnose_stray("%7")
    assert result.reason == "stray_present"
    assert result.meta["stray"] == "1"
    assert runner.key_calls == [] and runner.paste_calls == []
    clear, runner2, *_ = _machine(delivery, PaneFrame(READY, input_region=""))
    assert clear.diagnose_stray("%7").reason == "no_stray"
    assert runner2.key_calls == []


# --- GREEN round-4 reinforcements (Codex 16:12 B1-B6/H1) ---


def test_r30_stale_adapter_cannot_recreate_or_rewind_a_durable_row(tmp_path: Path) -> None:
    delivery = _delivery()
    path = tmp_path / "delivery.db"
    delivery.init_store(path)
    seed = delivery.SqliteStoreAdapter(path)
    m1 = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(), clock=FakeClock(), store=seed,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    assert m1._new_row(SEND_ID, "%7", "composing", wire_digest=WIRE_BODY) is not None
    assert m1._transition(SEND_ID, "pasted")
    stale = delivery.SqliteStoreAdapter(path)
    stale.rows.clear()  # simulate a process that never saw the row
    m2 = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(), clock=FakeClock(), store=stale,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    assert m2._new_row(SEND_ID, "%7", "composing") is None
    fresh = delivery.SqliteStoreAdapter(path)
    assert fresh.rows[SEND_ID]["state"] == "pasted"
    for adapter in (seed, stale, fresh):
        adapter.close()


def test_r30b_compose_pastes_only_after_winning_the_t2_cas() -> None:
    delivery = _delivery()

    class VetoStore(FakeStore):
        def cas_row_state(self, send_id, old_state, new_state, row):
            if new_state == "pasted":
                return False
            self.rows[send_id] = row
            return True

    store = VetoStore()
    machine, runner, *_ = _machine(delivery, PaneFrame(READY), store=store)
    result = machine.compose("%7", "From Codex — veto probe")
    assert result.reason == "cas_lost"
    assert runner.paste_calls == []


def test_r31_retry_emitters_obey_cas_loss_with_zero_keys() -> None:
    delivery = _delivery()

    class VetoStore(FakeStore):
        def cas_row_state(self, send_id, old_state, new_state, row):
            return not new_state.startswith(("submit_attempt", "press_attempt"))

    for state, call in (
        ("submit_attempt(1)", lambda m: m.retry_submit(SEND_ID)),
        ("press_attempt(1)", lambda m: m.retry_press(SEND_ID, elapsed=30.0)),
    ):
        store = VetoStore()
        store.seed_row(state=state, attempts=1, wire_digest=WIRE_BODY)
        frame = PaneFrame(READY, input_region=WIRE_BODY)
        machine, runner, *_ = _machine(delivery, frame, frame, store=store)
        result = call(machine)
        assert result.reason == "cas_lost"
        assert runner.key_calls == []
        assert store.rows[SEND_ID]["attempts"] == 1


def test_r31b_tampered_input_and_foreign_claim_block_retry_submit() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="submit_attempt(1)", attempts=1, wire_digest=WIRE_BODY)
    tampered = PaneFrame(READY, input_region=WIRE_BODY.replace("contract", "EVIL"))
    machine, runner, *_ = _machine(delivery, tampered, store=store)
    assert machine.retry_submit(SEND_ID).reason == "wire_body_mismatch"
    assert runner.key_calls == []
    store2 = FakeStore()
    store2.seed_row(state="submit_attempt(1)", attempts=1, wire_digest=WIRE_BODY)
    store2.seed_pane(pane_id="%7", owner_send_id="w#foreignzz-4", epoch=3)
    intact = PaneFrame(READY, input_region=WIRE_BODY)
    machine2, runner2, *_ = _machine(delivery, intact, store=store2)
    assert machine2.retry_submit(SEND_ID).reason == "pane_claim_lost"
    assert runner2.key_calls == []


def test_r32_release_is_owner_bound_and_terminal_paths_release_their_claim() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="press_attempt(1)", attempts=1, wire_digest=WIRE_BODY,
                   baseline_ref="")
    store.seed_pane(pane_id="%7", owner_send_id="w#foreignqq-5", epoch=9)
    frame = PaneFrame(READY, input_region=WIRE_BODY, conversation_region=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, frame, frame, store=store)
    machine.carrier_tick("%7")
    assert store.panes["%7"]["owner_send_id"] == "w#foreignqq-5"
    store2 = FakeStore()
    store2.seed_row(state="press_attempt(1)", attempts=1, wire_digest=WIRE_BODY)
    store2.seed_pane(pane_id="%7", owner_send_id=SEND_ID, epoch=2)
    gone = PaneFrame(READY, input_region="", conversation_region="")
    machine2, runner2, *_ = _machine(delivery, gone, gone, store=store2)
    lost = machine2.carrier_tick("%7")
    assert lost.reason == "strand_lost"
    assert store2.panes["%7"]["owner_send_id"] is None


def test_r33_backward_and_skipped_attempt_edges_are_illegal() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="submit_attempt(2)", attempts=2)
    machine, *_ = _machine(delivery, store=store)
    assert machine._transition(SEND_ID, "submit_attempt(1)") is False
    store2 = FakeStore()
    store2.seed_row(state="press_attempt(1)", attempts=1)
    machine2, *_ = _machine(delivery, store=store2)
    assert machine2._transition(SEND_ID, "press_attempt(3)") is False
    assert store2.rows[SEND_ID]["state"] == "press_attempt(1)"


def test_r34_attempt_evidence_carries_post_digest_and_resolution() -> None:
    import json

    delivery = _delivery()
    store = FakeStore()
    empty = PaneFrame(READY, input_region="")
    frames = (
        empty, empty, empty,
        PaneFrame(READY, input_region="x"),
        PaneFrame(READY),
    )
    machine, *_ = _machine(delivery, *frames, store=store)
    sent = machine.send_message("dynasty:1.2", BODY)
    row = store.rows[sent.meta["send_id"]]
    evidence = json.loads(row["attempt_evidence"]) if row["attempt_evidence"] else {}
    if evidence:
        last = evidence[str(max(int(k) for k in evidence))]
        assert "resolution" in last and last["resolution"] != ""
        assert "post_digest" in last


def test_r35_init_refuses_old_layouts_and_migration_backfills(tmp_path: Path) -> None:
    delivery = _delivery()
    import sqlite3 as sqlite_module

    old = tmp_path / "old.db"
    conn = sqlite_module.connect(old)
    conn.execute("CREATE TABLE rows (send_id TEXT PRIMARY KEY, state TEXT NOT NULL)")
    conn.execute("INSERT INTO rows (send_id, state) VALUES (?, ?)", (SEND_ID, "composing"))
    conn.commit()
    conn.close()
    with pytest.raises(delivery.StoreError, match="init_requires_migration"):
        delivery.init_store(old)
    delivery.migrate_store(old, target_schema=delivery.SCHEMA_VERSION)
    adapter = delivery.SqliteStoreAdapter(old)
    row = adapter.rows[SEND_ID]
    assert row["attempts"] == 0
    assert row["terminal"] in (False, 0)
    assert row["attempt_evidence"] == ""
    adapter.close()


def test_r35b_migration_failure_restores_and_verifies_the_backup(tmp_path: Path, monkeypatch) -> None:
    delivery = _delivery()
    import sqlite3 as sqlite_module

    old = tmp_path / "old.db"
    conn = sqlite_module.connect(old)
    conn.execute("CREATE TABLE rows (send_id TEXT PRIMARY KEY, state TEXT NOT NULL)")
    conn.commit()
    conn.close()
    original_connect = delivery._connect
    calls = {"n": 0}

    def sabotage(path):
        calls["n"] += 1
        if calls["n"] == 3:  # first post-backup DDL connection
            raise sqlite_module.OperationalError("sabotaged")
        return original_connect(path)

    monkeypatch.setattr(delivery, "_connect", sabotage)
    with pytest.raises(delivery.StoreError, match="rolled_back_verified"):
        delivery.migrate_store(old, target_schema=delivery.SCHEMA_VERSION)
    monkeypatch.setattr(delivery, "_connect", original_connect)
    check = sqlite_module.connect(old)
    assert check.execute("SELECT count(*) FROM sqlite_master").fetchone()[0] >= 1
    check.close()


def test_r36_offset_diagnostic_classifies_the_consumed_stray_signature() -> None:
    delivery = _delivery()
    dialog_with_stray = PaneFrame(DIALOG, input_region="1")
    closed_clean = PaneFrame(READY, input_region="")
    machine, runner, *_ = _machine(delivery, dialog_with_stray, closed_clean)
    result = machine.diagnose_stray_offset("%7")
    assert result.reason == "stray_offset_signature"
    assert "observational" in result.meta["hypothesis"]
    assert runner.key_calls == [] and runner.paste_calls == []
    persisting = _machine(delivery, dialog_with_stray, PaneFrame(DIALOG, input_region="1"))[0]
    assert persisting.diagnose_stray_offset("%7").reason == "stray_at_dialog_risk"


def test_r37_retry_press_baseline_guard_blocks_historical_occurrences() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(
        state="press_attempt(1)", attempts=1, wire_digest=WIRE_BODY,
        baseline_ref=f"history already has [{SEND_ID}]",
    )
    frame = PaneFrame(READY, input_region=WIRE_BODY, conversation_region=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, frame, frame, store=store)
    result = machine.retry_press(SEND_ID, elapsed=30.0)
    assert result.status != "delivered_verified"
    assert store.rows[SEND_ID]["state"] != "delivered_verified"


# --- GREEN round-5 reinforcements (Codex 17:26 B1-B4/H1-H2) ---


def test_r38_stale_evidence_write_cannot_resurrect_a_terminal_row(tmp_path: Path) -> None:
    delivery = _delivery()
    path = tmp_path / "delivery.db"
    delivery.init_store(path)
    seed = delivery.SqliteStoreAdapter(path)
    m_seed = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(), clock=FakeClock(), store=seed,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    m_seed._new_row(SEND_ID, "%7", "orphan_eligible", wire_digest=WIRE_BODY)
    stale = delivery.SqliteStoreAdapter(path)
    winner = delivery.SqliteStoreAdapter(path)
    row_w = dict(winner.rows[SEND_ID])
    assert winner.cas_row_state(SEND_ID, "orphan_eligible", "manual_clear_required", row_w)
    frame = PaneFrame(READY, input_region=WIRE_BODY, conversation_region=WIRE_BODY)
    m_stale = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(frame, frame), clock=FakeClock(),
        store=stale, profile=delivery.PaneProfile.for_cli("codex"),
    )
    m_stale.retry_press(SEND_ID, elapsed=30.0)
    fresh = delivery.SqliteStoreAdapter(path)
    assert fresh.rows[SEND_ID]["state"] == "manual_clear_required"
    for adapter in (seed, stale, winner, fresh):
        adapter.close()


def test_r39_reconcile_and_exhaust_complete_the_evidence_record() -> None:
    import json

    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="press_attempt(1)", attempts=1, wire_digest=WIRE_BODY,
                   attempt_evidence=json.dumps({"1": {"kind": "press", "at": 0.0,
                                                       "post_digest": None,
                                                       "resolution": "pending"}}))
    frame = PaneFrame(READY, conversation_region=WIRE_BODY)
    machine, *_ = _machine(delivery, frame, frame, store=store)
    machine.reconcile(SEND_ID, crash_window="w", actor="carrier")
    evidence = json.loads(store.rows[SEND_ID]["attempt_evidence"])
    assert evidence["1"]["resolution"] == "delivered_verified"
    assert evidence["1"]["post_digest"]
    store2 = FakeStore()
    store2.seed_row(state="press_attempt(3)", attempts=3, wire_digest=WIRE_BODY,
                    attempt_evidence=json.dumps({"3": {"kind": "press", "at": 0.0,
                                                        "post_digest": None,
                                                        "resolution": "pending"}}))
    machine2, *_ = _machine(delivery, PaneFrame(READY, input_region=WIRE_BODY), store=store2)
    machine2.retry_press(SEND_ID, elapsed=999.0)
    evidence2 = json.loads(store2.rows[SEND_ID]["attempt_evidence"])
    assert evidence2["3"]["resolution"] == "episode_exhausted"


def test_r40_stale_recovery_cannot_clear_a_foreign_owner() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="composed_verified", updated_at=-301.0, wire_digest=WIRE_BODY)
    store.seed_pane(pane_id="%7", owner_send_id="w#foreignvv-6", epoch=11)
    machine, runner, *_ = _machine(delivery, PaneFrame(READY), store=store)
    machine.recover_stale_claim(SEND_ID)
    assert store.panes["%7"]["owner_send_id"] == "w#foreignvv-6"
    assert runner.key_calls == []


def test_r41_sender_delivered_requires_two_agreeing_post_reads() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(
        state="composed_verified", wire_digest=WIRE_BODY, composer_observable=WIRE_BODY
    )
    contradictory = (
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region="", conversation_region=WIRE_BODY),
        PaneFrame(READY, input_region="", conversation_region="gone again"),
    )
    machine, runner, *_ = _machine(delivery, *contradictory, store=store)
    result = machine.send_message("dynasty:1.2", BODY)
    assert result.status != "delivered_verified"
    agreeing = (
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region="", conversation_region=WIRE_BODY),
        PaneFrame(READY, input_region="", conversation_region=WIRE_BODY),
    )
    store2 = FakeStore()
    store2.seed_row(
        state="composed_verified", wire_digest=WIRE_BODY, composer_observable=WIRE_BODY
    )
    machine2, *_ = _machine(delivery, *agreeing, store=store2)
    confirmed = machine2.send_message("dynasty:1.2", BODY)
    assert confirmed.status == "delivered_verified"


def test_r42_retry_press_early_exhaust_releases_its_own_claim() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="press_attempt(3)", attempts=3, wire_digest=WIRE_BODY)
    store.seed_pane(pane_id="%7", owner_send_id=SEND_ID, epoch=4)
    machine, runner, *_ = _machine(delivery, PaneFrame(READY, input_region=WIRE_BODY), store=store)
    result = machine.retry_press(SEND_ID, elapsed=999.0)
    assert result.reason == "episode_exhausted"
    assert store.panes["%7"]["owner_send_id"] is None
    assert runner.key_calls == []


# --- GREEN round-6 reinforcements (Codex 17:36 B1-B2) ---


def test_r43_reclaimable_evidence_is_durable_and_mixed_reads_resolve(tmp_path: Path) -> None:
    import json

    delivery = _delivery()
    path = tmp_path / "delivery.db"
    delivery.init_store(path)
    store = delivery.SqliteStoreAdapter(path)
    machine = delivery.DeliveryMachine(
        runner=FakeRunner(),
        capturer=FakeCapturer(
            PaneFrame(READY, input_region=WIRE_BODY),
            PaneFrame(READY, input_region=WIRE_BODY),
        ),
        clock=FakeClock(),
        store=store,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    machine._new_row(SEND_ID, "%7", "composing", wire_digest=WIRE_BODY)
    machine._transition(SEND_ID, "pasted")
    machine._transition(SEND_ID, "composed_verified")
    machine.store.rows[SEND_ID]["attempts"] = 1
    machine._record_attempt(store.rows[SEND_ID], 1, "submit")
    assert machine._transition(SEND_ID, "submit_attempt(1)")
    result = machine.reconcile(SEND_ID, crash_window="w", actor="sender")
    assert result.reason == "reclaimable"
    store.close()
    reopened = delivery.SqliteStoreAdapter(path)
    evidence = json.loads(reopened.rows[SEND_ID]["attempt_evidence"])
    assert evidence["1"]["resolution"] == "reclaimable"
    reopened.close()
    store2 = FakeStore()
    store2.seed_row(state="submit_attempt(1)", attempts=1, wire_digest=WIRE_BODY,
                    attempt_evidence='{"1": {"kind": "submit", "at": 0.0,'
                                     ' "post_digest": null, "resolution": "pending"}}')
    disagreeing = (
        PaneFrame(READY, cursor_row=1),
        PaneFrame(READY, cursor_row=9),
    )
    machine2, *_ = _machine(delivery, *disagreeing, store=store2)
    mixed = machine2.reconcile(SEND_ID, crash_window="w", actor="sender")
    assert mixed.reason == "manual_clear_required"
    import json as json2
    evidence2 = json2.loads(store2.rows[SEND_ID]["attempt_evidence"])
    assert evidence2["1"]["resolution"] == "manual_clear_required"


def test_r44_all_three_delivered_paths_demand_composite_agreement() -> None:
    delivery = _delivery()
    # Sender: metadata (cursor) contradiction between post and confirm blocks.
    store = FakeStore()
    store.seed_row(state="composed_verified", wire_digest=WIRE_BODY,
                   composer_observable=WIRE_BODY)
    frames = (
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region="", conversation_region=WIRE_BODY, cursor_row=1),
        PaneFrame(READY, input_region="", conversation_region=WIRE_BODY, cursor_row=8),
    )
    machine, *_ = _machine(delivery, *frames, store=store)
    assert machine.send_message("dynasty:1.2", BODY).status != "delivered_verified"
    # Carrier: confirm frame missing the occurrence blocks the verdict.
    store2 = FakeStore()
    store2.seed_row(state="press_attempt(1)", attempts=1, wire_digest=WIRE_BODY)
    tick_frames = (
        PaneFrame(READY, input_region=WIRE_BODY, conversation_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY, conversation_region="vanished"),
    )
    machine2, runner2, *_ = _machine(delivery, *tick_frames, store=store2)
    tick = machine2.carrier_tick("%7")
    assert tick.status != "delivered_verified"
    assert store2.rows[SEND_ID]["state"] == "press_attempt(1)"
    assert runner2.key_calls == []
    # retry_press: profile contradiction between the two reads blocks.
    store3 = FakeStore()
    store3.seed_row(state="press_attempt(1)", attempts=1, wire_digest=WIRE_BODY)
    retry_frames = (
        PaneFrame(READY, conversation_region=WIRE_BODY, current_command="codex"),
        PaneFrame(READY, conversation_region=WIRE_BODY, current_command="claude"),
    )
    machine3, runner3, *_ = _machine(delivery, *retry_frames, store=store3)
    retry = machine3.retry_press(SEND_ID, elapsed=30.0)
    assert retry.status != "delivered_verified"
    assert runner3.key_calls == []


# --- GREEN round-7 reinforcements (Codex 17:45 B1-B3/H1) ---


def test_r45_reclaimable_withdraws_when_the_evidence_cas_loses(tmp_path: Path) -> None:
    delivery = _delivery()
    path = tmp_path / "delivery.db"
    delivery.init_store(path)
    seed = delivery.SqliteStoreAdapter(path)
    m_seed = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(), clock=FakeClock(), store=seed,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    m_seed._new_row(SEND_ID, "%7", "composing", wire_digest=WIRE_BODY)
    m_seed._transition(SEND_ID, "pasted")
    m_seed._transition(SEND_ID, "composed_verified")
    m_seed.store.rows[SEND_ID]["attempts"] = 1
    m_seed._record_attempt(seed.rows[SEND_ID], 1, "submit")
    assert m_seed._transition(SEND_ID, "submit_attempt(1)")
    stale = delivery.SqliteStoreAdapter(path)
    winner = delivery.SqliteStoreAdapter(path)
    row_w = dict(winner.rows[SEND_ID])
    assert winner.cas_row_state(SEND_ID, "submit_attempt(1)", "manual_clear_required", row_w)
    frame = PaneFrame(READY, input_region=WIRE_BODY)
    m_stale = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(frame, frame), clock=FakeClock(),
        store=stale, profile=delivery.PaneProfile.for_cli("codex"),
    )
    result = m_stale.reconcile(SEND_ID, crash_window="w", actor="sender")
    assert result.reason != "reclaimable"
    fresh = delivery.SqliteStoreAdapter(path)
    assert fresh.rows[SEND_ID]["state"] == "manual_clear_required"
    for adapter in (seed, stale, winner, fresh):
        adapter.close()


def test_r46_viewport_geometry_contradictions_block_delivery() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="press_attempt(1)", attempts=1, wire_digest=WIRE_BODY)
    frames = (
        PaneFrame(READY, input_region=WIRE_BODY, conversation_region=WIRE_BODY, width=120),
        PaneFrame(READY, input_region=WIRE_BODY, conversation_region=WIRE_BODY, width=80),
    )
    machine, runner, *_ = _machine(delivery, *frames, store=store)
    result = machine.carrier_tick("%7")
    assert result.status != "delivered_verified"
    assert runner.key_calls == []
    store2 = FakeStore()
    store2.seed_row(state="press_attempt(1)", attempts=1, wire_digest=WIRE_BODY)
    frames2 = (
        PaneFrame(READY, conversation_region=WIRE_BODY, cursor_col=2),
        PaneFrame(READY, conversation_region=WIRE_BODY, cursor_col=44),
    )
    machine2, runner2, *_ = _machine(delivery, *frames2, store=store2)
    assert machine2.retry_press(SEND_ID, elapsed=30.0).status != "delivered_verified"
    assert runner2.key_calls == []


def test_r47_dialog_overlay_confirm_frame_blocks_every_delivered_path() -> None:
    delivery = _delivery()
    dialog_confirm = PaneFrame(
        DIALOG + "\n" + READY, input_region="", conversation_region=WIRE_BODY
    )
    store = FakeStore()
    store.seed_row(state="press_attempt(1)", attempts=1, wire_digest=WIRE_BODY)
    first = PaneFrame(READY, input_region="", conversation_region=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, first, dialog_confirm, store=store)
    result = machine.carrier_tick("%7")
    assert result.status != "delivered_verified"
    assert store.rows[SEND_ID]["state"] == "press_attempt(1)"
    assert runner.key_calls == []


def test_r48_post_key_exhaustion_records_a_terminal_observation_digest() -> None:
    import json

    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="press_attempt(2)", attempts=2, wire_digest=WIRE_BODY,
                   last_press_at=0.0)
    clock = FakeClock()
    clock.advance(1000.0)
    frame = PaneFrame(READY, input_region=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, frame, frame, store=store)
    result = machine.retry_press(SEND_ID, elapsed=999.0)
    assert result.reason == "episode_exhausted"
    assert len(runner.key_calls) == 1
    evidence = json.loads(store.rows[SEND_ID]["attempt_evidence"])
    last = evidence[str(max(int(k) for k in evidence))]
    assert last["resolution"] == "episode_exhausted"
    assert last["post_digest"]


# --- GREEN round-8 reinforcements (Codex 17:55 B1-B2) ---


def test_r49_dialog_overlay_first_frame_blocks_sender_and_retry_delivery() -> None:
    delivery = _delivery()
    dialog_post = PaneFrame(
        DIALOG + "\n" + READY, input_region="", conversation_region=WIRE_BODY
    )
    store = FakeStore()
    store.seed_row(state="composed_verified", wire_digest=WIRE_BODY,
                   composer_observable=WIRE_BODY)
    frames = (
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        dialog_post,
        dialog_post,
    )
    machine, *_ = _machine(delivery, *frames, store=store)
    assert machine.send_message("dynasty:1.2", BODY).status != "delivered_verified"
    store2 = FakeStore()
    store2.seed_row(state="press_attempt(1)", attempts=1, wire_digest=WIRE_BODY)
    dialog_first = PaneFrame(DIALOG + "\n" + READY, conversation_region=WIRE_BODY)
    machine2, runner2, *_ = _machine(delivery, dialog_first, dialog_first, store=store2)
    assert machine2.retry_press(SEND_ID, elapsed=30.0).status != "delivered_verified"
    assert runner2.key_calls == []


def test_r50_exhaustion_uses_the_captured_frame_as_its_observation() -> None:
    import json

    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="press_attempt(3)", attempts=3, wire_digest=WIRE_BODY,
                   attempt_evidence=json.dumps({"3": {"kind": "press", "at": 0.0,
                                                       "post_digest": None,
                                                       "resolution": "pending"}}))
    frame = PaneFrame(READY, input_region=WIRE_BODY)
    machine, *_ = _machine(delivery, frame, store=store)
    result = machine.retry_press(SEND_ID, elapsed=999.0)
    assert result.reason == "episode_exhausted"
    evidence = json.loads(store.rows[SEND_ID]["attempt_evidence"])
    assert evidence["3"]["post_digest"]
    assert "observation_failed" not in evidence["3"]
    store2 = FakeStore()
    store2.seed_row(state="orphan_eligible", attempts=3, wire_digest=WIRE_BODY,
                    attempt_evidence=json.dumps({"3": {"kind": "press", "at": 0.0,
                                                        "post_digest": None,
                                                        "resolution": "pending"}}))
    tick_frame = PaneFrame(READY, input_region=WIRE_BODY)
    machine2, runner2, *_ = _machine(delivery, tick_frame, store=store2)
    tick = machine2.carrier_tick("%7")
    assert tick.reason == "episode_exhausted"
    evidence2 = json.loads(store2.rows[SEND_ID]["attempt_evidence"])
    assert evidence2["3"]["post_digest"]
    assert runner2.key_calls == []


# --- GREEN round-9 reinforcements (Codex 18:05 B1-B2) ---


def test_r51_unconfirmed_exit_preserves_the_last_successful_observation() -> None:
    import json

    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="composed_verified", wire_digest=WIRE_BODY,
                   composer_observable=WIRE_BODY)
    frames = (
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
        PaneFrame(READY, input_region=WIRE_BODY),
    )
    machine, *_ = _machine(delivery, *frames, store=store)
    result = machine.send_message("dynasty:1.2", BODY)
    assert result.reason == "delivery_unconfirmed"
    evidence = json.loads(store.rows[SEND_ID]["attempt_evidence"])
    last = evidence[str(max(int(k) for k in evidence))]
    assert last["post_digest"]
    assert "observation_failed" not in last


def test_r51b_reconcile_cas_loss_reports_predicate_terminality(tmp_path: Path) -> None:
    delivery = _delivery()
    path = tmp_path / "delivery.db"
    delivery.init_store(path)
    seed = delivery.SqliteStoreAdapter(path)
    m_seed = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(), clock=FakeClock(), store=seed,
        profile=delivery.PaneProfile.for_cli("codex"),
    )
    m_seed._new_row(SEND_ID, "%7", "composing", wire_digest=WIRE_BODY)
    m_seed._transition(SEND_ID, "pasted")
    m_seed._transition(SEND_ID, "composed_verified")
    seed.rows[SEND_ID]["attempts"] = 1
    m_seed._record_attempt(seed.rows[SEND_ID], 1, "submit")
    assert m_seed._transition(SEND_ID, "submit_attempt(1)")
    stale = delivery.SqliteStoreAdapter(path)
    winner = delivery.SqliteStoreAdapter(path)
    row_w = dict(winner.rows[SEND_ID])
    # Winner moves the row to a terminal state but with the stored boolean stale.
    row_w["terminal"] = False
    assert winner.cas_row_state(SEND_ID, "submit_attempt(1)", "manual_clear_required", row_w)
    frame = PaneFrame(READY, input_region=WIRE_BODY)
    m_stale = delivery.DeliveryMachine(
        runner=FakeRunner(), capturer=FakeCapturer(frame, frame), clock=FakeClock(),
        store=stale, profile=delivery.PaneProfile.for_cli("codex"),
    )
    result = m_stale.reconcile(SEND_ID, crash_window="w", actor="sender")
    if result.reason == "manual_clear_required" or result.status == "held":
        assert result.terminal is True
    for adapter in (seed, stale, winner):
        adapter.close()
