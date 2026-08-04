#!/usr/bin/env python3
"""CFBD DATA promotion CLI — dry-run by default, offline by construction.

Moves bytes. Runs no bakeoff, writes no model, performs no CFBD refresh or any
network call, and makes no claim about predictive value. ``--confirm`` is the only
mutating path; without it this reports what *would* happen and touches nothing.

    scripts/promote_cfbd_data.py              # dry run (default)
    scripts/promote_cfbd_data.py --confirm    # perform the pinned promotion
    scripts/promote_cfbd_data.py --recover    # classify an interrupted promotion
    scripts/promote_cfbd_data.py --rollback   # CAS-guarded restore of the preimage
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # standalone/launchd invocation from outside the repo
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.capture.cfbd_data_promotion import (  # noqa: E402
    CfbdPromotionError,
    default_promotion_spec,
    promote_cfbd_data,
    recover_cfbd_promotion,
    rollback_cfbd_promotion,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # --confirm is a MODIFIER on whichever action is chosen, not an action itself.
    # Making it mutually exclusive with --recover/--rollback would have meant those
    # two could only ever run in their mutating form, which contradicts the promise
    # that nothing mutates without --confirm.
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="actually mutate; without this every action is read-only",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--recover", action="store_true", help="classify (or with --confirm, repair) a split state"
    )
    action.add_argument(
        "--rollback", action="store_true", help="restore the preimage, CAS-guarded"
    )
    args = parser.parse_args(argv)

    spec = default_promotion_spec()
    try:
        if args.recover:
            report = recover_cfbd_promotion(spec, confirm=args.confirm)
        elif args.rollback:
            report = rollback_cfbd_promotion(spec, confirm=args.confirm)
        else:
            report = promote_cfbd_data(spec, confirm=args.confirm)
    except CfbdPromotionError as exc:
        print(json.dumps({"status": "refused", "reason": exc.reason, "detail": str(exc)}, indent=2))
        return 1

    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
