"""Send explicit messages to local tmux agent panes."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from typing import Callable

TMUX_PANE_FORMAT = (
    "#{session_name}:#{window_index}.#{pane_index}\t"
    "#{pane_title}\t"
    "#{pane_current_command}\t"
    "#{pane_current_path}\t"
    "#{pane_active}"
)

Runner = Callable[..., subprocess.CompletedProcess]


@dataclass(frozen=True)
class TmuxPane:
    target: str
    title: str
    current_command: str
    current_path: str
    active: bool


def parse_panes(output: str) -> list[TmuxPane]:
    """Parse `tmux list-panes` tab-separated output."""

    panes: list[TmuxPane] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) != 5:
            raise ValueError(f"Unexpected tmux pane row with {len(fields)} fields: {line!r}")
        target, title, current_command, current_path, active = fields
        panes.append(
            TmuxPane(
                target=target,
                title=title,
                current_command=current_command,
                current_path=current_path,
                active=active == "1",
            )
        )
    return panes


def list_panes(
    *,
    session: str | None = None,
    runner: Runner = subprocess.run,
) -> list[TmuxPane]:
    command = ["tmux", "list-panes", "-a", "-F", TMUX_PANE_FORMAT]
    if session:
        command = ["tmux", "list-panes", "-t", session, "-F", TMUX_PANE_FORMAT]

    result = runner(command, check=True, capture_output=True, text=True)
    return parse_panes(result.stdout)


def _send_commands(target: str, message: str, *, submit: bool) -> list[list[str]]:
    if submit:
        # tmux treats ";" as an internal command separator here, keeping paste
        # and Enter in one invocation so the submit key cannot lag behind.
        return [
            ["tmux", "set-buffer", "--", message],
            [
                "tmux",
                "paste-buffer",
                "-p",
                "-t",
                target,
                ";",
                "send-keys",
                "-t",
                target,
                "C-m",
            ],
        ]

    commands = [
        ["tmux", "set-buffer", "--", message],
        ["tmux", "paste-buffer", "-p", "-t", target],
    ]
    return commands


def send_message(
    target: str,
    message: str,
    *,
    submit: bool = False,
    dry_run: bool = False,
    runner: Runner = subprocess.run,
) -> list[list[str]]:
    """Paste or type a message into a tmux pane and optionally submit it."""

    commands = _send_commands(target, message, submit=submit)
    if dry_run:
        return commands

    for command in commands:
        runner(command, check=True, capture_output=True, text=True)
    return commands


def _print_panes(panes: list[TmuxPane]) -> None:
    for pane in panes:
        marker = "*" if pane.active else " "
        print(
            f"{marker} {pane.target} "
            f"command={pane.current_command} "
            f"title={pane.title!r} "
            f"path={pane.current_path}"
        )


def _print_commands(commands: list[list[str]]) -> None:
    for command in commands:
        print(" ".join(command))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List tmux panes or send explicit text to an agent pane."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List tmux panes.")
    list_parser.add_argument("--session", help="Optional tmux session target.")

    send_parser = subparsers.add_parser("send", help="Paste a message into a tmux pane.")
    send_parser.add_argument("target", help="tmux pane target, e.g. dynasty:1.3")
    send_parser.add_argument("message", nargs="+", help="Message text to paste.")
    send_parser.add_argument(
        "--submit",
        action="store_true",
        help="Press Enter after pasting the message.",
    )
    send_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print tmux commands without running them.",
    )

    args = parser.parse_args()
    if args.command == "list":
        _print_panes(list_panes(session=args.session))
        return

    message = " ".join(args.message)
    commands = send_message(
        args.target,
        message,
        submit=args.submit,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        _print_commands(commands)


if __name__ == "__main__":
    main()
