"""Wire-health F1-F68 RED contract for ratified spec v15.

The frozen source of record is blob 715f288c7dc0824815b4c7afcfa8fd0313bfb392.
These tests are intentionally RED against main: the shared delivery machine and
carrier driver do not exist yet.  Every dependency is injected; this module
never invokes live tmux, reads a cockpit artifact, or sleeps in wall-clock time.

Matrix accounting: 70 collected items.  F36 and F39 are split into a/b rows,
and retired F48 remains as one explicit skip for numbering stability.  David's
D7 ADOPT word makes F16, F17, and F31 binding rows.
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

READY = "❯ "
BUSY = "Working (12s)\n❯ "
DIALOG = "Allow this action?\n❯ 1. Yes\n  2. No"
UNKNOWN = "rendered by a future profile"
BODY = "From Codex — contract probe"
SEND_ID = "w#abc123xy-1"
WIRE_BODY = f"From Codex [{SEND_ID}] — contract probe"


@dataclass(frozen=True)
class PaneFrame:
    """Synthetic result returned by the injected Capturer."""

    raw: str
    pane_id: str = "%7"
    cursor_row: int = 1
    cursor_col: int = 2
    width: int = 120
    height: int = 40
    title: str = "Codex pane"
    current_command: str = "codex"
    input_region: str = ""
    conversation_region: str = ""
    readable: bool = True
    frame_id: str = "frame-1"


@dataclass
class FakeClock:
    """Monotonic fake clock; sleep advances instantly."""

    value: float = 0.0
    sleeps: list[float] = field(default_factory=list)

    def monotonic(self) -> float:
        return self.value

    def time(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds

    def advance(self, seconds: float) -> None:
        self.value += seconds


@dataclass
class RunnerCall:
    command: list[str]
    input: str | bytes | None = None


class FakeRunner:
    """Records subprocess-shaped calls without touching tmux."""

    def __init__(self) -> None:
        self.calls: list[RunnerCall] = []

    def __call__(
        self,
        command: list[str],
        *,
        input: str | bytes | None = None,
        **_: Any,
    ) -> Any:
        self.calls.append(RunnerCall(list(command), input))
        return type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    @property
    def key_calls(self) -> list[RunnerCall]:
        return [call for call in self.calls if "send-keys" in call.command]

    @property
    def paste_calls(self) -> list[RunnerCall]:
        return [call for call in self.calls if "paste-buffer" in call.command]

    @property
    def buffer_calls(self) -> list[RunnerCall]:
        return [call for call in self.calls if "set-buffer" in call.command]


class FakeCapturer:
    """Returns a deterministic sequence of composite snapshots or exceptions."""

    def __init__(self, *items: PaneFrame | BaseException) -> None:
        self.items = list(items)
        self.calls: list[str] = []

    def capture(self, pane_id: str) -> PaneFrame:
        self.calls.append(pane_id)
        if not self.items:
            raise AssertionError("unexpected capture")
        item = self.items.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    __call__ = capture


class FakeStore:
    """Minimal injected store probe with durable-looking row/pane dictionaries."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self.panes: dict[str, dict[str, Any]] = {}
        self.fault_at: str | None = None
        self.transitions: list[tuple[str, str, str]] = []

    def seed_row(self, send_id: str = SEND_ID, **values: Any) -> dict[str, Any]:
        row = {
            "send_id": send_id,
            "state": "composed_verified",
            "wire_digest": "digest",
            "pane_id": "%7",
            "pane_epoch": 1,
            "profile": "codex",
            "attempts": 0,
            "terminal": False,
            "carrier_eligible": False,
            "updated_at": 0.0,
        }
        row.update(values)
        self.rows[send_id] = row
        return row

    def seed_pane(self, pane_id: str = "%7", **values: Any) -> dict[str, Any]:
        pane = {"pane_id": pane_id, "owner_send_id": SEND_ID, "epoch": 1}
        pane.update(values)
        self.panes[pane_id] = pane
        return pane


def _delivery():
    return importlib.import_module("scripts.dg_delivery")


def _carrier():
    return importlib.import_module("scripts.dg_mail_carrier")


def _sender():
    return importlib.import_module("scripts.tmux_msg")


def _profile(module: Any, name: str = "codex") -> Any:
    return module.PaneProfile.for_cli(name)


def _machine(
    module: Any,
    *frames: PaneFrame | BaseException,
    runner: FakeRunner | None = None,
    clock: FakeClock | None = None,
    store: FakeStore | None = None,
    profile: str = "codex",
) -> tuple[Any, FakeRunner, FakeCapturer, FakeClock, FakeStore]:
    used_runner = runner or FakeRunner()
    capturer = FakeCapturer(*frames)
    used_clock = clock or FakeClock()
    used_store = store or FakeStore()
    machine = module.DeliveryMachine(
        runner=used_runner,
        capturer=capturer,
        clock=used_clock,
        store=used_store,
        profile=_profile(module, profile),
    )
    return machine, used_runner, capturer, used_clock, used_store


def _assert_reason(result: Any, reason: str) -> None:
    assert result.reason == reason
    assert result.status != "delivered_verified"


def _assert_zero_pane_mutations(runner: FakeRunner) -> None:
    assert runner.key_calls == []
    assert runner.paste_calls == []
    assert runner.buffer_calls == []


def test_f1_ready_capture_fixtures_classify_ready_for_every_profile() -> None:
    delivery = _delivery()
    fixtures = {
        "claude": "────────────────────────────────────────\n❯ ",
        "codex": "codex > ",
        "gemini": "Type your message or @path/to/file",
    }
    for name, raw in fixtures.items():
        assert delivery.classify_pane(raw, _profile(delivery, name)) is delivery.PaneState.READY


def test_f2_dialog_refuses_before_any_buffer_command() -> None:
    delivery = _delivery()
    machine, runner, *_ = _machine(delivery, PaneFrame(DIALOG), PaneFrame(DIALOG))
    result = machine.send_message("dynasty:1.2", BODY)
    _assert_reason(result, "pane_dialog")
    _assert_zero_pane_mutations(runner)


def test_f3_busy_refusal_and_wait_are_bounded() -> None:
    delivery = _delivery()
    clock = FakeClock()
    frames = tuple(PaneFrame(BUSY) for _ in range(64))
    machine, runner, _, used_clock, _ = _machine(delivery, *frames, clock=clock)
    result = machine.send_message("dynasty:1.2", BODY, wait=True, wait_budget=30.0)
    _assert_reason(result, "wait_budget_exhausted")
    assert used_clock.monotonic() <= 30.5
    _assert_zero_pane_mutations(runner)


def test_f4_dim_only_history_is_not_positive_delivery_evidence() -> None:
    delivery = _delivery()
    ghost = f"\x1b[2m{WIRE_BODY}\x1b[22m"
    machine, runner, *_ = _machine(delivery, PaneFrame(ghost, conversation_region=ghost))
    result = machine.verify_delivery(SEND_ID, WIRE_BODY)
    _assert_reason(result, "ghost_text_not_delivery")
    assert runner.key_calls == []


def test_f5_strip_ghost_replaces_dim_spans_without_fragment_joining() -> None:
    delivery = _delivery()
    raw = "real-A\x1b[2;38;5;245mghost\x1b[22mreal-B"
    stripped = delivery.strip_ghost(raw)
    assert stripped == "real-A�real-B"
    assert "ghost" not in stripped
    assert "real-Areal-B" not in stripped


def test_f6_sender_retry_is_exactly_one_claimed_fresh_attempt() -> None:
    # GREEN round-2 B4 repair: nonempty entry is legal ONLY as exact machine
    # resume — a durable pasted/composed_verified row whose recorded observable
    # matches the visible strand. The fixture now seeds that row.
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(
        state="composed_verified",
        wire_digest=WIRE_BODY,
        composer_observable=WIRE_BODY,
    )
    composed = PaneFrame(READY, input_region=WIRE_BODY)
    machine, runner, _, _, store = _machine(
        delivery, composed, composed, composed, composed, composed, composed, store=store
    )
    result = machine.send_message("dynasty:1.2", BODY)
    _assert_reason(result, "delivery_unconfirmed")
    assert len(runner.key_calls) == 2
    assert store.rows[result.meta["send_id"]]["attempts"] == 2
    assert result.meta["send_id"] == SEND_ID


def test_f7_empty_input_without_new_send_id_occurrence_is_not_success() -> None:
    delivery = _delivery()
    empty = PaneFrame(READY, input_region="", conversation_region="old history")
    machine, *_ = _machine(delivery, empty, empty)
    result = machine.verify_delivery(SEND_ID, WIRE_BODY)
    _assert_reason(result, "delivery_unconfirmed")


def test_f8_multiline_visible_body_is_one_paste_and_full_compare() -> None:
    delivery = _delivery()
    body = "From Codex — first\nsecond\nmiddle\nlast"
    machine, runner, *_ = _machine(
        delivery,
        PaneFrame(READY, input_region=""),
        PaneFrame(READY, input_region=""),
        PaneFrame(READY, input_region=""),
        PaneFrame(READY, input_region=body),
        PaneFrame(READY, input_region=body),
    )
    machine.send_message("dynasty:1.2", body)
    assert len(runner.paste_calls) == 1
    assert len(runner.key_calls) <= 2


def test_f9_capture_failure_or_unknown_target_fails_closed() -> None:
    delivery = _delivery()
    machine, runner, *_ = _machine(delivery, RuntimeError("capture failed"))
    result = machine.send_message("missing:9.9", BODY)
    _assert_reason(result, "pane_unreadable")
    _assert_zero_pane_mutations(runner)


def test_f10_printable_escape_lookalikes_are_preserved() -> None:
    delivery = _delivery()
    raw = "real ESC[2m text, not an SGR byte"
    assert delivery.strip_ghost(raw) == raw


def test_f11_readiness_gate_precedes_set_buffer_on_refusal() -> None:
    delivery = _delivery()
    machine, runner, *_ = _machine(delivery, PaneFrame(BUSY))
    machine.send_message("dynasty:1.2", BODY)
    assert runner.buffer_calls == []


def test_f12_none_non_string_and_empty_inputs_fail_loud() -> None:
    delivery = _delivery()
    machine, *_ = _machine(delivery)
    for target, message in [(None, BODY), (7, BODY), ("dynasty:1.2", None), ("dynasty:1.2", 7), ("dynasty:1.2", "")]:
        with pytest.raises((TypeError, ValueError)):
            machine.send_message(target, message)


def test_f13_profile_rot_is_unknown_and_refused() -> None:
    delivery = _delivery()
    assert delivery.classify_pane(UNKNOWN, _profile(delivery)) is delivery.PaneState.UNKNOWN
    machine, runner, *_ = _machine(delivery, PaneFrame(UNKNOWN))
    result = machine.send_message("dynasty:1.2", BODY)
    _assert_reason(result, "pane_state_unknown")
    _assert_zero_pane_mutations(runner)


def test_f14_force_bypass_is_absent_from_cli_and_api() -> None:
    sender = _sender()
    parser = sender.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["send", "dynasty:1.2", "--message-file", "body.txt", "--force"])
    assert "force" not in inspect.signature(sender.send_message).parameters


def test_f15_single_ready_flicker_between_busy_frames_never_opens_gate() -> None:
    delivery = _delivery()
    clock = FakeClock()
    machine, runner, *_ = _machine(
        delivery,
        PaneFrame(BUSY),
        PaneFrame(READY),
        PaneFrame(BUSY),
        clock=clock,
    )
    result = machine.send_message("dynasty:1.2", BODY, wait=True, wait_budget=1.0)
    assert result.status != "delivered_verified"
    _assert_zero_pane_mutations(runner)


def test_f16_adopted_approve_refuses_when_no_dialog_is_present() -> None:
    delivery = _delivery()
    machine, runner, *_ = _machine(delivery, PaneFrame(READY))
    result = machine.approve("dynasty:1.2", option_text="Yes")
    _assert_reason(result, "no_dialog_present")
    assert runner.key_calls == []


def test_f17_adopted_approve_reports_stray_echo_after_key() -> None:
    delivery = _delivery()
    after = PaneFrame(READY, input_region="1")
    machine, runner, *_ = _machine(delivery, PaneFrame(DIALOG), after)
    result = machine.approve("dynasty:1.2", option_text="Yes")
    _assert_reason(result, "stray_echo_detected")
    assert len(runner.key_calls) == 1
    assert result.meta["warning_exit"] != 0


def test_f18_file_and_stdin_preserve_shell_risk_bytes_inside_wire_body(tmp_path: Path) -> None:
    delivery = _delivery()
    original = "From Codex — `tick` $(touch nope) 'quote' \"double\" !\nline two"
    body_path = tmp_path / "body.txt"
    body_path.write_text(original, encoding="utf-8")
    stamped = delivery.stamp_wire_body(original, send_id=SEND_ID)
    assert stamped.replace(f" [{SEND_ID}]", "", 1) == original
    assert "$(touch nope)" in stamped


def test_f19_wait_timeout_is_named_and_never_claims_queued_delivery() -> None:
    delivery = _delivery()
    machine, _, _, _, _ = _machine(delivery, *(PaneFrame(BUSY) for _ in range(64)))
    result = machine.send_message("dynasty:1.2", BODY, wait=True, wait_budget=30.0)
    _assert_reason(result, "wait_budget_exhausted")
    assert result.meta.get("queued") is not True
    assert result.meta["exit_code"] == 3


def test_f20_carrier_holds_numbered_option_shaped_strand() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="composed_verified", updated_at=-301.0)
    machine, runner, *_ = _machine(delivery, PaneFrame(DIALOG), store=store)
    result = machine.carrier_tick("%7")
    _assert_reason(result, "held_dialog_shape")
    assert runner.key_calls == []


def test_f21_carrier_busy_flicker_never_emits_enter() -> None:
    delivery = _delivery()
    machine, runner, *_ = _machine(
        delivery,
        PaneFrame(BUSY),
        PaneFrame(READY),
        PaneFrame(BUSY),
    )
    machine.carrier_tick("%7")
    assert runner.key_calls == []


def test_f22_carrier_press_timeline_is_t0_plus_30_plus_60_then_exhausted() -> None:
    delivery = _delivery()
    clock = FakeClock()
    store = FakeStore()
    store.seed_row(state="orphan_eligible", wire_digest=WIRE_BODY)
    visible = PaneFrame(READY, input_region=WIRE_BODY)
    machine, runner, _, used_clock, used_store = _machine(
        delivery,
        *(visible for _ in range(20)),
        clock=clock,
        store=store,
    )
    machine.carrier_tick("%7")
    clock.advance(29.9)
    machine.carrier_tick("%7")
    assert len(runner.key_calls) == 1
    clock.advance(0.1)
    machine.carrier_tick("%7")
    clock.advance(59.9)
    machine.carrier_tick("%7")
    assert len(runner.key_calls) == 2
    clock.advance(0.1)
    result = machine.carrier_tick("%7")
    assert len(runner.key_calls) == 3
    assert result.reason == "episode_exhausted"
    assert used_store.rows[SEND_ID]["state"] == "episode_exhausted"
    assert used_clock.monotonic() == pytest.approx(90.0)


def test_f23_carrier_holds_unattributed_strand() -> None:
    delivery = _delivery()
    frame = PaneFrame(READY, input_region=f"[{SEND_ID}] no sender header")
    machine, runner, *_ = _machine(delivery, frame, frame)
    result = machine.carrier_tick("%7")
    assert result.reason in {"unattributed_strand", "held_unattributed"}
    assert runner.key_calls == []


def test_f24_identical_history_before_baseline_cannot_satisfy_delivery() -> None:
    delivery = _delivery()
    baseline = PaneFrame(READY, conversation_region=WIRE_BODY)
    post = PaneFrame(READY, conversation_region=WIRE_BODY)
    machine, *_ = _machine(delivery, baseline, post)
    result = machine.verify_delivery(SEND_ID, WIRE_BODY, baseline=baseline)
    _assert_reason(result, "delivery_unconfirmed")


def test_f25_middle_corruption_fails_full_body_paste_verification() -> None:
    delivery = _delivery()
    corrupt = WIRE_BODY.replace("contract", "CORRUPT")
    frame = PaneFrame(READY, input_region=corrupt)
    machine, *_ = _machine(delivery, frame, frame)
    result = machine.verify_composed(WIRE_BODY)
    assert result.reason in {"input_not_verifiable", "wire_body_mismatch"}


def test_f26_interleaved_senders_use_isolated_named_buffers_and_cleanup() -> None:
    delivery = _delivery()
    runner = FakeRunner()
    machine_a, _, *_ = _machine(delivery, PaneFrame(READY), PaneFrame(READY), runner=runner)
    machine_b, _, *_ = _machine(delivery, PaneFrame(READY), PaneFrame(READY), runner=runner)
    machine_a.compose("%7", "From Codex — A", send_id="w#a1111111-1")
    machine_b.compose("%8", "From Claude — B", send_id="w#b2222222-1")
    buffer_names = [call.command[call.command.index("-b") + 1] for call in runner.calls if "-b" in call.command]
    assert len(set(buffer_names)) == 2
    assert all(name.startswith("dg-msg-") for name in buffer_names)
    assert any("delete-buffer" in call.command for call in runner.calls)


def test_f27_strip_ghost_handles_unclosed_clear_and_compound_sequences() -> None:
    delivery = _delivery()
    assert delivery.strip_ghost("A\x1b[2mghost") == "A�"
    assert delivery.strip_ghost("A\x1b[2;22mreal") == "Areal"
    assert delivery.strip_ghost("A\x1b[0;2mghost\nB") == "A�\nB"


def test_f28_fake_clock_reproduces_wait_budget_failure_and_final_ready() -> None:
    delivery = _delivery()
    clock = FakeClock()
    frames = [PaneFrame(BUSY) for _ in range(59)] + [PaneFrame(READY), PaneFrame(READY)]
    machine, _, _, used_clock, _ = _machine(delivery, *frames, clock=clock)
    result = machine.wait_until_ready("%7", budget=30.0)
    assert result.status == "ready"
    assert used_clock.sleeps and all(value == 0.5 for value in used_clock.sleeps)
    broken, *_ = _machine(delivery, PaneFrame(BUSY), RuntimeError("capture"), clock=FakeClock())
    assert broken.wait_until_ready("%7", budget=30.0).reason == "pane_unreadable"


def test_f29_pane_respawn_or_profile_drift_emits_no_keys() -> None:
    delivery = _delivery()
    resolved = PaneFrame(READY, pane_id="%7", current_command="codex")
    respawned = PaneFrame(READY, pane_id="%8", current_command="claude")
    machine, runner, *_ = _machine(delivery, resolved, respawned)
    result = machine.send_message("dynasty:1.2", BODY)
    assert result.reason in {"pane_identity_changed", "profile_mismatch"}
    assert runner.key_calls == []


def test_f30_positional_body_is_usage_error_while_file_form_is_byte_safe(tmp_path: Path) -> None:
    sender = _sender()
    parser = sender.build_parser()
    with pytest.raises(SystemExit) as error:
        parser.parse_args(["send", "dynasty:1.2", BODY])
    assert error.value.code == 6
    body_path = tmp_path / "message.txt"
    body_path.write_text("From Codex — `x` $(x)\nnext", encoding="utf-8")
    args = parser.parse_args(["send", "dynasty:1.2", "--message-file", str(body_path)])
    assert args.message_file == str(body_path)


def test_f31_adopted_approve_hash_mismatch_emits_zero_keys() -> None:
    delivery = _delivery()
    machine, runner, *_ = _machine(delivery, PaneFrame(DIALOG))
    result = machine.approve("%7", option_text="A different option")
    _assert_reason(result, "option_mismatch")
    assert runner.key_calls == []


def test_f32_collapsed_chip_uses_chip_and_buffer_proof_not_full_pane_body() -> None:
    delivery = _delivery()
    chip = "[Pasted text #1 +42 lines]"
    machine, *_ = _machine(delivery, PaneFrame(READY, input_region=chip), profile="claude")
    verified = machine.verify_composed(WIRE_BODY, expected_lines=43)
    assert verified.status == "composed_verified"
    missing, *_ = _machine(delivery, PaneFrame(READY, input_region=""), profile="claude")
    assert missing.verify_composed(WIRE_BODY, expected_lines=43).reason == "input_not_verifiable"


def test_f33_identical_twins_require_their_own_new_send_id() -> None:
    delivery = _delivery()
    twin = "From Codex [w#other123-1] — contract probe"
    frame = PaneFrame(READY, conversation_region=twin)
    machine, *_ = _machine(delivery, frame, frame)
    result = machine.verify_delivery(SEND_ID, WIRE_BODY, baseline=frame)
    _assert_reason(result, "delivery_unconfirmed")


def test_f34_mixed_composite_frames_never_produce_a_one_frame_verdict() -> None:
    delivery = _delivery()
    a = PaneFrame(READY, cursor_row=1, frame_id="a")
    b = PaneFrame(READY, cursor_row=9, frame_id="b")
    machine, runner, *_ = _machine(delivery, a, b, a, b)
    result = machine.send_message("dynasty:1.2", BODY)
    assert result.reason in {"pane_unreadable", "mixed_frame"}
    _assert_zero_pane_mutations(runner)


def test_f35_vanished_post_press_strand_is_terminal_strand_lost() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="press_attempt(1)", attempts=1)
    gone = PaneFrame(READY, input_region="", conversation_region="")
    machine, runner, *_ = _machine(delivery, gone, gone, store=store)
    result = machine.carrier_tick("%7")
    _assert_reason(result, "strand_lost")
    assert result.terminal is True
    assert runner.key_calls == []


def test_f36a_attempt_budget_survives_three_consecutive_carrier_process_fires() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="orphan_eligible", wire_digest=WIRE_BODY)
    clock = FakeClock()
    presses = 0
    for advance in (0.0, 30.0, 60.0):
        clock.advance(advance)
        frame = PaneFrame(READY, input_region=WIRE_BODY)
        machine, runner, *_ = _machine(delivery, frame, frame, frame, clock=clock, store=store)
        machine.carrier_tick("%7")
        presses += len(runner.key_calls)
    assert presses == 3
    assert store.rows[SEND_ID]["attempts"] == 3
    assert store.rows[SEND_ID]["state"] == "episode_exhausted"


def test_f36b_same_send_id_keeps_tombstone_across_absence_and_respawn() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="episode_exhausted", attempts=3, terminal=True, pane_id="%7")
    frame = PaneFrame(READY, pane_id="%8", input_region=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, frame, frame, store=store)
    result = machine.carrier_tick("%8")
    assert result.reason == "episode_exhausted"
    assert runner.key_calls == []


def test_f37_carrier_is_inert_without_enable_marker(tmp_path: Path) -> None:
    carrier = _carrier()
    runner = FakeRunner()
    result = carrier.run_once(
        enable_marker=tmp_path / "not-enabled",
        runner=runner,
        capturer=FakeCapturer(),
        clock=FakeClock(),
        store=FakeStore(),
    )
    assert result.reason == "carrier_disabled"
    _assert_zero_pane_mutations(runner)


def test_f38_sgr_parameters_apply_left_to_right_and_empty_means_reset() -> None:
    delivery = _delivery()
    assert delivery.strip_ghost("A\x1b[0;2mghost") == "A�"
    assert delivery.strip_ghost("A\x1b[2;0mreal") == "Areal"
    assert delivery.strip_ghost("A\x1b[2mghost\x1b[mreal") == "A�real"


def test_f39a_reexposed_corrupted_chip_body_is_delivery_unconfirmed() -> None:
    delivery = _delivery()
    corrupted = WIRE_BODY.replace("contract", "mangled")
    frame = PaneFrame(READY, conversation_region=corrupted)
    machine, *_ = _machine(delivery, frame, frame, profile="claude")
    result = machine.verify_delivery(SEND_ID, WIRE_BODY, chip_profile=True)
    _assert_reason(result, "delivery_unconfirmed")


def test_f39b_non_reexposed_chip_body_is_terminal_content_unconfirmed_exit_7() -> None:
    delivery = _delivery()
    frame = PaneFrame(READY, conversation_region=f"received [{SEND_ID}] without body")
    machine, *_ = _machine(delivery, frame, frame, profile="claude")
    result = machine.verify_delivery(SEND_ID, WIRE_BODY, chip_profile=True)
    assert result.status == "delivered_content_unconfirmed"
    assert result.meta["exit_code"] == 7
    assert result.terminal is True


def test_f40_two_process_nonces_make_equal_counters_unique() -> None:
    delivery = _delivery()
    first = delivery.make_send_id(seq=1, random_bytes=b"\x01\x02\x03\x04\x05")
    second = delivery.make_send_id(seq=1, random_bytes=b"\x06\x07\x08\x09\x0a")
    assert first != second
    assert first.startswith("w#") and first.endswith("-1")
    assert second.startswith("w#") and second.endswith("-1")


def test_f41_idless_attributed_strand_is_untracked_and_never_pressed() -> None:
    delivery = _delivery()
    frame = PaneFrame(READY, input_region="From Codex — same body")
    machine, runner, *_ = _machine(delivery, frame, frame)
    result = machine.carrier_tick("%7")
    _assert_reason(result, "untracked_strand")
    assert runner.key_calls == []


def test_f42_body_missing_sender_header_is_refused() -> None:
    delivery = _delivery()
    machine, runner, *_ = _machine(delivery)
    result = machine.send_message("dynasty:1.2", "not a sender header\nbody")
    _assert_reason(result, "body_missing_sender_header")
    _assert_zero_pane_mutations(runner)


def test_f43_hidden_exhausted_strand_never_refreshes_budget() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="episode_exhausted", attempts=3, terminal=True)
    frames = (
        RuntimeError("capture"),
        PaneFrame(BUSY),
        PaneFrame(READY, cursor_row=1, frame_id="a"),
        PaneFrame(READY, cursor_row=2, frame_id="b"),
        PaneFrame(READY, input_region=WIRE_BODY),
    )
    machine, runner, *_ = _machine(delivery, *frames, store=store)
    for _ in frames:
        machine.carrier_tick("%7")
    assert store.rows[SEND_ID]["attempts"] == 3
    assert store.rows[SEND_ID]["state"] == "episode_exhausted"
    assert runner.key_calls == []


def test_f44_reference_caller_never_resends_terminal_results() -> None:
    sender = _sender()
    calls: list[str] = []

    def send_once() -> Any:
        calls.append("send")
        return type(
            "Result",
            (),
            {"status": "delivered_content_unconfirmed", "terminal": True, "meta": {"exit_code": 7}},
        )()

    result = sender.send_and_confirm(send_once)
    assert result.terminal is True
    assert calls == ["send"]


def test_f45_carrier_during_any_sender_live_state_emits_zero_keys() -> None:
    delivery = _delivery()
    for state in ("composing", "pasted", "composed_verifying"):
        store = FakeStore()
        store.seed_row(state=state, updated_at=-1000.0)
        machine, runner, *_ = _machine(delivery, PaneFrame(READY, input_region=WIRE_BODY), store=store)
        machine.carrier_tick("%7")
        assert runner.key_calls == []


def test_f46_exhausted_identity_stays_exhausted_in_a_different_pane() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="episode_exhausted", attempts=3, terminal=True, pane_id="%7")
    machine, runner, *_ = _machine(
        delivery,
        PaneFrame(READY, pane_id="%99", input_region=WIRE_BODY),
        store=store,
    )
    machine.carrier_tick("%99")
    assert runner.key_calls == []
    assert store.rows[SEND_ID]["state"] == "episode_exhausted"


def test_f47_superseded_paste_and_all_later_fires_emit_zero_cancel_keys() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="manual_clear_required", terminal=True, updated_at=-10000.0)
    machine, runner, *_ = _machine(delivery, PaneFrame(READY, input_region=WIRE_BODY), store=store)
    machine.mark_superseded(SEND_ID)
    machine.carrier_tick("%7")
    assert runner.key_calls == []
    assert store.rows[SEND_ID]["carrier_eligible"] is False


@pytest.mark.skip(reason="F48 retired by ratified D0.1; F52 owns same-pane contention")
def test_f48_retired_numbering_row() -> None:
    pass


def test_f49_unverified_refused_or_unproven_rows_never_become_orphans() -> None:
    delivery = _delivery()
    for state in ("input_not_verifiable", "refused_busy", "composing"):
        store = FakeStore()
        store.seed_row(state=state, updated_at=-10000.0)
        machine, runner, *_ = _machine(delivery, PaneFrame(READY, input_region=WIRE_BODY), store=store)
        machine.carrier_tick("%7")
        assert runner.key_calls == []
        assert store.rows[SEND_ID]["state"] != "orphan_eligible"


def test_f50_pid_reuse_cannot_collide_with_old_tombstone() -> None:
    delivery = _delivery()
    old = delivery.make_send_id(seq=1, random_bytes=b"\x00\x00\x00\x00\x01")
    new = delivery.make_send_id(seq=1, random_bytes=b"\x00\x00\x00\x00\x02")
    assert old != new
    assert delivery.parse_send_id(old).seq == delivery.parse_send_id(new).seq == 1


def test_f51_post_paste_and_post_key_results_are_terminal_to_reference_caller() -> None:
    delivery = _delivery()
    sender = _sender()
    for result in (
        delivery.SendResult("refused", "input_not_verifiable", "pasted", True, 0, [], {}),
        delivery.SendResult("unconfirmed", "delivery_unconfirmed", "submitted", True, 2, [], {}),
    ):
        calls: list[int] = []
        returned = sender.send_and_confirm(lambda: calls.append(1) or result)
        assert returned.terminal is True
        assert calls == [1]


def test_f52_same_pane_contention_has_exactly_one_epoch_cas_winner() -> None:
    delivery = _delivery()
    for first_actor in ("carrier", "sender"):
        store = FakeStore()
        store.seed_row(state="orphan_eligible")
        store.seed_pane(owner_send_id=None, epoch=4)
        runner = FakeRunner()
        machine, _, *_ = _machine(delivery, PaneFrame(READY), runner=runner, store=store)
        winners = machine.race_for_pane("%7", carrier_send_id=SEND_ID, sender_send_id="w#newnew12-1", first=first_actor)
        assert len(winners) == 1
        assert len(runner.key_calls) + len(runner.paste_calls) <= 1


def test_f53_sender_and_carrier_crash_windows_reconcile_without_blind_replay() -> None:
    # GREEN round-1 blind-spot repair [Codex 13:26 B6]: the verdict must come from
    # capture EVIDENCE plus the durable row, never the caller's window label —
    # each scenario now supplies the evidence frame that justifies its outcome,
    # and a lying label cannot upgrade an ambiguous frame to delivered.
    delivery = _delivery()
    clock = FakeClock()
    scenarios = {
        "claim_no_key_unchanged": (
            PaneFrame(READY, input_region=WIRE_BODY), "reclaimable"
        ),
        "key_no_result_new_occurrence": (
            PaneFrame(READY, conversation_region=WIRE_BODY), "delivered_verified"
        ),
        "key_no_result_ambiguous": (
            PaneFrame(READY), "manual_clear_required"
        ),
    }
    for actor in ("sender", "carrier"):
        for window, (frame, expected) in scenarios.items():
            store = FakeStore()
            store.seed_row(
                state="submit_attempt(1)" if actor == "sender" else "press_attempt(1)",
                wire_digest=WIRE_BODY,
            )
            machine, runner, *_ = _machine(delivery, frame, frame, clock=clock, store=store)
            result = machine.reconcile(SEND_ID, crash_window=window, actor=actor)
            assert result.reason == expected
            assert runner.key_calls == []
    # The lying-label probe: an ambiguous frame with a "delivered" label stays manual.
    store = FakeStore()
    store.seed_row(state="submit_attempt(1)", wire_digest=WIRE_BODY)
    machine, runner, *_ = _machine(
        delivery, PaneFrame(READY), PaneFrame(READY), clock=clock, store=store
    )
    lied = machine.reconcile(SEND_ID, crash_window="key_no_result_new_occurrence", actor="sender")
    assert lied.reason == "manual_clear_required"
    assert runner.key_calls == []


def test_f54_sender_pre_key_drift_is_terminal_and_emits_zero_keys() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="composed_verified")
    machine, runner, *_ = _machine(delivery, PaneFrame(READY), PaneFrame(DIALOG), store=store)
    result = machine.submit(SEND_ID)
    assert result.terminal is True
    assert result.reason in {"pane_dialog", "profile_mismatch", "pane_identity_changed"}
    assert runner.key_calls == []


def test_f55_collapsed_stale_row_takes_t10x_and_retains_blocking_claim() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="composed_verified", profile="claude", updated_at=-301.0)
    store.seed_pane(owner_send_id=SEND_ID)
    machine, runner, *_ = _machine(delivery, PaneFrame(READY), store=store, profile="claude")
    result = machine.recover_stale_claim(SEND_ID)
    assert result.reason == "orphan_manual_required"
    assert store.rows[SEND_ID]["state"] == "orphan_manual_required"
    assert store.panes["%7"]["owner_send_id"] == SEND_ID
    assert runner.key_calls == []


def test_f56_every_store_entry_fault_is_named_and_has_zero_pane_mutations() -> None:
    delivery = _delivery()
    for fault, reason in (
        ("missing", "store_unavailable"),
        ("corrupt", "store_unavailable"),
        ("schema", "store_schema_mismatch"),
        ("locked", "store_locked"),
    ):
        store = FakeStore()
        store.fault_at = fault
        machine, runner, *_ = _machine(delivery, PaneFrame(READY), store=store)
        result = machine.send_message("dynasty:1.2", BODY)
        _assert_reason(result, reason)
        _assert_zero_pane_mutations(runner)


def test_f57_pane_claim_release_retention_ack_stale_and_epoch_mismatch() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="manual_clear_required", terminal=True)
    store.seed_pane(owner_send_id=SEND_ID, epoch=3)
    machine, runner, *_ = _machine(
        delivery,
        PaneFrame(READY, input_region=""),
        PaneFrame(READY, input_region=""),
        store=store,
    )
    assert machine.ack_clear(SEND_ID, pane_epoch=3).status == "claim_released"
    assert store.rows[SEND_ID]["state"] == "manual_clear_required"
    lost = machine.ack_clear(SEND_ID, pane_epoch=2)
    assert lost.reason == "pane_epoch_mismatch"
    assert runner.key_calls == []


def test_f58_init_store_is_idempotent_safe_and_transactionally_migrated(tmp_path: Path) -> None:
    delivery = _delivery()
    path = tmp_path / "delivery.db"
    first = delivery.init_store(path)
    repeat = delivery.init_store(path)
    assert first.status == repeat.status == "store_ready"
    assert path.stat().st_mode & 0o777 == 0o600
    non_db = tmp_path / "occupied"
    non_db.write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(Exception, match="init_target_exists"):
        delivery.init_store(non_db)
    assert non_db.read_text(encoding="utf-8") == "do not overwrite"
    assert delivery.migrate_store(path, target_schema=delivery.SCHEMA_VERSION).backup_verified is True
    with pytest.raises(Exception, match="newer_schema"):
        delivery.open_store(path, schema_version=delivery.SCHEMA_VERSION + 1)


def test_f59_first_paste_requires_empty_composer_except_exact_resume() -> None:
    delivery = _delivery()
    cases = (
        ("manual text", None, "input_not_empty"),
        (WIRE_BODY, None, "input_not_empty"),
        ("\x1b[2mghost\x1b[22m", None, "composing"),
        (WIRE_BODY, {"state": "pasted", "composer_observable": WIRE_BODY}, "resume"),
    )
    for visible, row, expected in cases:
        store = FakeStore()
        if row:
            store.seed_row(**row)
        frame = PaneFrame(READY, input_region=visible)
        machine, runner, *_ = _machine(delivery, frame, frame, store=store)
        result = machine.acquire_composer("%7", BODY)
        assert result.reason == expected
        if expected == "input_not_empty":
            _assert_zero_pane_mutations(runner)


def test_f60_store_fault_boundaries_obey_pre_and_post_mutation_rules() -> None:
    delivery = _delivery()
    for point in ("claim_before_paste", "claim_before_key"):
        store = FakeStore()
        store.fault_at = point
        machine, runner, *_ = _machine(delivery, PaneFrame(READY), store=store)
        machine.send_message("dynasty:1.2", BODY)
        assert runner.paste_calls == [] and runner.key_calls == []
    for point in ("key_before_result", "terminal_before_release"):
        store = FakeStore()
        store.fault_at = point
        store.seed_row(state="composed_verified")
        machine, _, *_ = _machine(delivery, PaneFrame(READY), store=store)
        result = machine.reconcile(SEND_ID, crash_window=point, actor="sender")
        assert result.terminal is True
        assert result.reason in {"manual_clear_required", "delivery_unconfirmed"}


def test_f61_retry_edges_execute_with_two_submit_and_three_press_ceilings() -> None:
    delivery = _delivery()
    store = FakeStore()
    machine, runner, *_ = _machine(delivery, *(PaneFrame(READY, input_region=WIRE_BODY) for _ in range(20)), store=store)
    store.seed_row(state="submit_attempt(1)", attempts=1, wire_digest=WIRE_BODY)
    assert machine.retry_submit(SEND_ID).attempts == 2
    assert machine.retry_submit(SEND_ID).reason == "submit_attempts_exhausted"
    store.seed_row(state="press_attempt(1)", attempts=1, wire_digest=WIRE_BODY)
    assert machine.retry_press(SEND_ID, elapsed=30.0).attempts == 2
    assert machine.retry_press(SEND_ID, elapsed=60.0).attempts == 3
    assert machine.retry_press(SEND_ID, elapsed=60.0).reason == "episode_exhausted"
    assert len(runner.key_calls) <= 4


def test_f62_unified_300s_stale_fork_hands_off_only_composed_verified() -> None:
    delivery = _delivery()
    for state, expected in (("composed_verified", "orphan_candidate"), ("pasted", "manual_clear_required")):
        store = FakeStore()
        store.seed_row(state=state, updated_at=-300.001)
        store.seed_pane(owner_send_id=SEND_ID)
        machine, runner, *_ = _machine(delivery, PaneFrame(READY), store=store)
        result = machine.recover_stale_claim(SEND_ID)
        assert result.reason == expected
        assert runner.key_calls == []


def test_f63_in_claim_pre_paste_recheck_blocks_human_keystroke_race() -> None:
    delivery = _delivery()
    empty = PaneFrame(READY, input_region="")
    human_text = PaneFrame(READY, input_region="human typed here")
    machine, runner, *_ = _machine(delivery, empty, empty, human_text)
    result = machine.send_message("dynasty:1.2", BODY)
    assert result.reason == "input_not_empty"
    assert runner.paste_calls == []
    assert result.meta["guard"] == "T2_pre_paste_recheck"


def test_f64_t1_gc_releases_claim_atomically_and_ack_keeps_tombstone() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="composing", updated_at=-10000.0)
    store.seed_pane(owner_send_id=SEND_ID)
    machine, runner, *_ = _machine(delivery, PaneFrame(READY), PaneFrame(READY), store=store)
    machine.gc_orphaned_composers()
    assert SEND_ID not in store.rows
    assert store.panes["%7"]["owner_send_id"] is None
    tombstone = store.seed_row(state="episode_exhausted", terminal=True)
    store.seed_pane(owner_send_id=SEND_ID, epoch=9)
    machine.ack_clear(SEND_ID, pane_epoch=9)
    assert store.rows[SEND_ID] is tombstone
    assert store.panes["%7"]["owner_send_id"] is None
    assert runner.key_calls == []


def test_f65_t1x_and_t10x_negative_states_are_reachable_and_blocking() -> None:
    delivery = _delivery()
    manual = PaneFrame(READY, input_region="human text")
    store = FakeStore()
    machine, runner, *_ = _machine(delivery, manual, manual, store=store)
    first = machine.acquire_composer("%7", BODY)
    assert first.reason == "input_not_empty"
    assert store.rows[first.meta["send_id"]]["state"] == "input_not_empty"
    store.seed_row(state="composed_verified", profile="claude", updated_at=-301.0)
    second = machine.recover_stale_claim(SEND_ID)
    assert second.reason == "orphan_manual_required"
    assert runner.key_calls == []


def test_f66_collapsed_profile_fork_is_atomic_and_never_transits_candidacy() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="composed_verified", profile="claude", updated_at=-301.0)
    store.seed_pane(owner_send_id=SEND_ID, epoch=5)
    machine, runner, *_ = _machine(delivery, PaneFrame(READY), store=store, profile="claude")
    machine.recover_stale_claim(SEND_ID)
    states = [new for _, _, new in store.transitions]
    assert "orphan_candidate" not in states
    assert store.rows[SEND_ID]["state"] == "orphan_manual_required"
    assert store.panes["%7"]["owner_send_id"] == SEND_ID
    assert runner.key_calls == []


def test_f67_positive_occurrence_resolves_before_retry_and_forbids_press() -> None:
    delivery = _delivery()
    store = FakeStore()
    store.seed_row(state="press_attempt(1)", attempts=1)
    frame = PaneFrame(READY, input_region=WIRE_BODY, conversation_region=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, frame, frame, store=store)
    result = machine.retry_press(SEND_ID, elapsed=30.0)
    assert result.status == "delivered_verified"
    assert store.rows[SEND_ID]["state"].startswith("delivered_")
    assert runner.key_calls == []


def test_f68_strand_lost_is_immutable_when_identical_send_id_reappears() -> None:
    delivery = _delivery()
    store = FakeStore()
    original = store.seed_row(
        state="strand_lost",
        attempts=1,
        terminal=True,
        carrier_eligible=False,
    ).copy()
    frame = PaneFrame(READY, input_region=WIRE_BODY)
    machine, runner, *_ = _machine(delivery, frame, frame, store=store)
    result = machine.carrier_tick("%7")
    assert result.reason == "strand_lost"
    assert store.rows[SEND_ID] == original
    assert store.rows[SEND_ID]["carrier_eligible"] is False
    assert runner.key_calls == []
