from __future__ import annotations

import subprocess

from scripts import tmux_msg


def test_parse_panes_from_tmux_output() -> None:
    output = (
        "dynasty:1.1\tClaude pane\tclaude\t/Users/david/project\t0\n"
        "dynasty:1.3\tPM pane\tagy\t/Users/david/project\t1\n"
    )

    panes = tmux_msg.parse_panes(output)

    assert [pane.target for pane in panes] == ["dynasty:1.1", "dynasty:1.3"]
    assert panes[0].title == "Claude pane"
    assert panes[0].current_command == "claude"
    assert panes[1].active is True


def test_send_message_pastes_without_submit_by_default() -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    tmux_msg.send_message("dynasty:1.3", "hello PM", runner=runner)

    assert calls == [
        ["tmux", "set-buffer", "--", "hello PM"],
        ["tmux", "paste-buffer", "-p", "-t", "dynasty:1.3"],
    ]


def test_send_message_separates_option_like_message_from_set_buffer_flags() -> None:
    commands = tmux_msg.send_message(
        "dynasty:1.3",
        "-n no flag please",
        dry_run=True,
    )

    assert commands[0] == ["tmux", "set-buffer", "--", "-n no flag please"]


def test_send_message_submits_with_carriage_return() -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    tmux_msg.send_message("dynasty:1.1", "status?", submit=True, runner=runner)

    assert calls == [
        ["tmux", "set-buffer", "--", "status?"],
        [
            "tmux",
            "paste-buffer",
            "-p",
            "-t",
            "dynasty:1.1",
            ";",
            "send-keys",
            "-t",
            "dynasty:1.1",
            "C-m",
        ],
    ]


def test_dry_run_does_not_call_runner() -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    commands = tmux_msg.send_message(
        "dynasty:1.3",
        "dry run only",
        submit=True,
        dry_run=True,
        runner=runner,
    )

    assert calls == []
    assert commands == [
        ["tmux", "set-buffer", "--", "dry run only"],
        [
            "tmux",
            "paste-buffer",
            "-p",
            "-t",
            "dynasty:1.3",
            ";",
            "send-keys",
            "-t",
            "dynasty:1.3",
            "C-m",
        ],
    ]
