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


class _RejectPositionalBody(argparse.Action):
    """A positional body is a usage error (spec D8: file/stdin only), exit 6."""

    def __call__(self, parser, namespace, values, option_string=None):  # noqa: ANN001
        if values is not None:
            parser.exit(6, "error: body_requires_file — use --message-file <path> (or '-')\n")
        setattr(namespace, self.dest, None)


def build_parser() -> argparse.ArgumentParser:
    """Wire-health CLI grammar: message bodies arrive via --message-file only."""

    parser = argparse.ArgumentParser(
        description="List tmux panes or send a verified message to an agent pane."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List tmux panes.")
    list_parser.add_argument("--session", help="Optional tmux session target.")

    send_parser = subparsers.add_parser("send", help="Send a message body from a file/stdin.")
    send_parser.add_argument("target", help="tmux pane target, e.g. dynasty:1.3")
    send_parser.add_argument(
        "body",
        nargs="?",
        action=_RejectPositionalBody,
        help=argparse.SUPPRESS,
    )
    send_parser.add_argument(
        "--message-file",
        required=False,
        help="Path to the message body; '-' reads stdin (the only stdin form).",
    )
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

    approve_parser = subparsers.add_parser(
        "approve",
        help="HUMAN-ONLY dialog approval executor (D7, David-adopted): verifies an"
             " open dialog and the highlighted option text before keying.",
    )
    approve_parser.add_argument("target", help="tmux pane target with the open dialog")
    approve_parser.add_argument(
        "--option", required=True, help="Exact text of the highlighted option to approve."
    )
    return parser


def send_and_confirm(send_once) -> "object":  # noqa: ANN001
    """Reference caller (spec F44/F51): terminal results are NEVER auto-resent."""

    result = send_once()
    if getattr(result, "terminal", False):
        return result
    return result


BODY_MAX_BYTES = 65536


class BodyError(ValueError):
    """Named body failure per spec D8: reason is the first argument."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def read_body(message_file: str) -> str:
    """D8 body loader with the named failure contract [GREEN round-1 H2]."""

    import sys

    try:
        if message_file == "-":
            data = sys.stdin.buffer.read()
        else:
            with open(message_file, "rb") as handle:
                data = handle.read()
    except OSError as error:
        raise BodyError("body_unreadable") from error
    if len(data) > BODY_MAX_BYTES:
        raise BodyError("body_too_large")
    if b"\x00" in data:
        raise BodyError("body_contains_nul")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise BodyError("body_not_utf8") from error
    if not text.strip():
        raise BodyError("body_empty")
    return text


def _import_dg_delivery():
    """Direct-invocation import boundary [GREEN round-2 B10]: `scripts/tmux_msg.py`
    runs with sys.path rooted at scripts/, so the package import needs the repo
    root bootstrapped."""

    import sys
    from pathlib import Path

    try:
        from scripts import dg_delivery
    except ModuleNotFoundError:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from scripts import dg_delivery
    return dg_delivery


def _machine_for(target: str):
    """Production D0 wiring: the CLI is a thin driver, never a raw tmux caller."""

    dg_delivery = _import_dg_delivery()

    profile_name = "codex"
    try:
        for pane in list_panes():
            if pane.target == target:
                title = pane.title.lower()
                if "claude" in title or pane.current_command.startswith("2."):
                    profile_name = "claude"
                elif "gemini" in title or pane.current_command == "agy":
                    profile_name = "gemini"
                break
    except Exception:  # noqa: BLE001 - profile fallback is fail-closed downstream
        pass
    import time

    class _Clock:
        def monotonic(self) -> float:
            return time.monotonic()

        def sleep(self, seconds: float) -> None:
            time.sleep(seconds)

    store = dg_delivery.SqliteStoreAdapter(dg_delivery.DEFAULT_STORE_PATH)
    return dg_delivery.DeliveryMachine(
        runner=subprocess.run,
        capturer=dg_delivery.TmuxCapturer(),
        clock=_Clock(),
        store=store,
        profile=dg_delivery.PaneProfile.for_cli(profile_name),
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "list":
        _print_panes(list_panes(session=args.session))
        return
    if args.command == "approve":
        dg_delivery = _import_dg_delivery()
        try:
            machine = _machine_for(args.target)
        except dg_delivery.StoreError as error:
            parser.exit(5, f"error: {error} (init-store is a separate deployment step)\n")
        result = machine.approve(args.target, option_text=args.option)
        print(f"{result.status}: {result.reason}")
        if result.status == "approved":
            print(f"WARNING: {result.meta['toctou_warning']}")
        raise SystemExit(int(result.meta.get("warning_exit", result.meta.get("exit_code", 1))))
    if not args.message_file:
        parser.exit(6, "error: body_requires_file — use --message-file <path> (or '-')\n")
    try:
        message = read_body(args.message_file)
    except BodyError as error:
        parser.exit(4, f"error: {error.reason}\n")
    if args.dry_run:
        _print_commands(_send_commands(args.target, message, submit=args.submit))
        return
    dg_delivery = _import_dg_delivery()
    try:
        machine = _machine_for(args.target)
    except dg_delivery.StoreError as error:
        parser.exit(5, f"error: {error} (init-store is a separate deployment step)\n")
    result = machine.send_message(args.target, message, wait=args.submit)
    print(f"{result.status}: {result.reason}")
    if result.meta.get("toctou_warning"):
        print(f"WARNING: {result.meta['toctou_warning']}")
    raise SystemExit(int(result.meta.get("exit_code", 1)))


if __name__ == "__main__":
    main()
