"""R4-G2 cap-state repair (Codex round-4 instruction, David's 'continue' word).

Injects the archived TW14-QB1-1 rounds (framing/1 + green-review/1-3, VERBATIM
from run.claude-qb1-BLOCKED-after-r3.json.bak) into the continuation run's
cap-bearing current state, and renumbers the open green-review round to index
4 — so the installed loop-control (a pure function of the current run object)
counts the ratified 5-round phase cap from where the law says we are: the next
round after this one is the cap round, index 5.

Run once; idempotence guard refuses a second application.
"""
import json
from pathlib import Path

BASE = Path(
    "/Users/davidleess/dynasty-genius/.git/worktrees/dynasty-genius-product/dg-autonomy"
)


def main() -> None:
    archive = json.loads(
        (BASE / "run.claude-qb1-BLOCKED-after-r3.json.bak").read_text()
    )
    run_path = BASE / "run.json"
    current = json.loads(run_path.read_text())

    current_rounds = current.get("reviewRounds", [])
    if len(current_rounds) != 1 or current_rounds[0].get("phase") != "green-review":
        raise SystemExit(
            f"refusing: unexpected current rounds {[(r.get('phase'), r.get('index')) for r in current_rounds]}"
        )
    open_round = current_rounds[0]
    if open_round.get("closedAt") is not None:
        raise SystemExit("refusing: the open round is already closed")

    archived_rounds = archive.get("reviewRounds", [])
    open_round["index"] = 4
    current["reviewRounds"] = archived_rounds + [open_round]

    run_path.write_text(json.dumps(current, indent=2) + "\n")
    check = json.loads(run_path.read_text())
    print(
        "rounds now:",
        [
            (r["phase"], r["index"], "closed" if r.get("closedAt") else "OPEN")
            for r in check["reviewRounds"]
        ],
    )


if __name__ == "__main__":
    main()
