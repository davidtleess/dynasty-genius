#!/usr/bin/env python3
"""DG-207 — grade one enrolled track-record claim. Explicit inputs only.

This runner cannot go looking for data. Every input is named on the command line, and the
outcome manifest must name the exact files it stands for. **Declared hashes are not trusted:
the runner reads the bytes, hashes them itself, and refuses when the manifest disagrees.** A
hash copied into a manifest proves nothing about the payload beside it.

It also stores the original policy bytes next to the grade, so the ``policy_sha256`` on the
document can be re-checked later by someone who does not trust this run.

    python scripts/grade_workspace_track_record.py \
        --evaluation-root DIR --enrollment-id ID --claim production \
        --outcome-manifest FILE --output-root DIR

Market additionally requires ``--horizon-days`` restricted to 30 or 90.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.dynasty_genius.eval.workspace_track_record import (  # noqa: E402
    PREPARED_ROLE,
    TrackRecordError,
    canonical_grade_bytes,
    grade_market,
    grade_production,
    select_endpoint,
)

CLAIMS = ("production", "market")
HORIZONS = (30, 90)
PRODUCTION_POLICY = "app/config/workspace_evaluation_plan.json"
MARKET_POLICY = "app/config/workspace_market_movement_90d_v1.json"


class CliRefusal(Exception):
    """A refusal with an exit code. Printed to stderr; never a partial grade."""


def _as_datetime(value: str) -> Any:
    """The store requires a timezone-aware datetime; the CLI still never reads a clock."""
    from datetime import datetime, timezone

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise CliRefusal(f"--evaluated-at is not an ISO-8601 instant: {value}") from error
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path, what: str) -> Any:
    if not path.is_file():
        raise CliRefusal(f"{what} is not a file: {path}")
    try:
        return json.loads(path.read_bytes())
    except json.JSONDecodeError as error:
        raise CliRefusal(f"{what} is not valid JSON: {path}") from error


def _verify_source_bytes(manifest: dict, manifest_path: Path) -> tuple[dict[str, str], dict[str, bytes]]:
    """Read every named file ONCE, hash the real bytes, and keep them.

    Declared hashes are not evidence: a hash beside a payload is a claim about it. Names must be
    unique (a collision would silently replace one payload's hash with another's) and any
    declared byte length must match, so a truncated capture cannot pass as a whole one.
    """
    verified: dict[str, str] = {}
    buffers: dict[str, bytes] = {}
    for entry in manifest.get("sources") or []:
        name = entry.get("name")
        declared = entry.get("sha256")
        relative = entry.get("path")
        if not isinstance(name, str) or not isinstance(declared, str):
            raise CliRefusal("every source entry needs a name and a declared sha256")
        if name in verified:
            raise CliRefusal(f"duplicate source name {name!r}; no last-write-wins hash replacement")
        if not isinstance(relative, str) or not relative:
            raise CliRefusal(f"source {name} does not name the bytes it stands for")
        target = (manifest_path.parent / relative).resolve()
        if not target.is_file():
            raise CliRefusal(f"source {name} names a missing file: {target}")
        payload = target.read_bytes()
        computed = _sha256(payload)
        if computed != declared:
            raise CliRefusal(
                f"source {name} bytes do not match the declared hash "
                f"(declared {declared[:12]}…, actual {computed[:12]}…)"
            )
        declared_len = entry.get("bytes_len")
        if declared_len is not None and int(declared_len) != len(payload):
            raise CliRefusal(
                f"source {name} is {len(payload)} bytes, not the declared {declared_len}"
            )
        verified[name] = computed
        buffers[name] = payload
    if not verified:
        raise CliRefusal("the outcome manifest names no verified source bytes")
    return verified, buffers


def _validated_preparation(manifest: dict, verified: dict[str, str]) -> dict:
    """The recipe that connects raw capture bytes to the scored numbers.

    Without this the runner would hash one file and grade a completely unrelated numeric table
    supplied beside it — the hash check would be decoration. This does not re-derive the numbers,
    and the handoff says so; it requires the preparation to be declared, to name only sources
    that were actually verified, and to be stored with the grade so a later reader can replay it.
    """
    preparation = manifest.get("preparation")
    if not isinstance(preparation, dict):
        raise CliRefusal(
            "the manifest declares no preparation recipe, so the scored numbers are not bound to "
            "the verified bytes; a prepared outcome must disclose how it was derived"
        )
    recipe = preparation.get("recipe")
    digest = preparation.get("recipe_sha256")
    inputs = preparation.get("inputs")
    if not isinstance(recipe, str) or not recipe:
        raise CliRefusal("the preparation recipe must be named")
    if not isinstance(digest, str) or len(digest) != 64:
        raise CliRefusal("the preparation recipe needs its own sha256")
    if not isinstance(inputs, list) or not inputs:
        raise CliRefusal("the preparation must name the source inputs it consumed")
    unknown = [name for name in inputs if name not in verified]
    if unknown:
        raise CliRefusal(
            f"the preparation claims inputs that were not verified: {unknown}"
        )
    return preparation


def _code_identity() -> dict[str, Any]:
    """Honest about a dirty tree: a commit alone would not describe what actually ran."""
    def git(*args: str) -> Optional[str]:
        try:
            return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:
            return None

    head = git("rev-parse", "HEAD")
    dirty = git("status", "--porcelain")
    module = REPO_ROOT / "src/dynasty_genius/eval/workspace_track_record.py"
    return {
        "commit": head,
        "dirty": bool(dirty) if dirty is not None else None,
        "scorer_sha256": _sha256(module.read_bytes()) if module.is_file() else None,
        "runner_sha256": _sha256(Path(__file__).resolve().read_bytes()),
    }


PRODUCTION_PLAN_ARTIFACT = "evaluation-plan.json"


def _record_directory(store_root: Path, record_id: str) -> Path:
    """The store sharding, mirrored read-only so the bytes can be re-hashed independently."""
    return store_root / record_id[:2] / record_id


def _policy_bytes(claim: str, enrollment: dict, store_root: Path) -> tuple[bytes, str]:
    """Market hashes the canonical policy JSON; production hashes the ORIGINAL archived bytes.

    The production plan is read from the enrollment record's immutable
    ``evaluation-plan.json`` artifact **on disk** and re-hashed here. ``read_record`` returns
    artifact hashes but not bytes, and a declared hash is a claim about a payload, not the
    payload — so a hash alone is never accepted as proof that the plan exists or matches.
    """
    if claim == "market":
        path = REPO_ROOT / MARKET_POLICY
        if not path.is_file():
            raise CliRefusal(f"market policy is missing: {path}")
        document = json.loads(path.read_bytes())
        canonical = json.dumps(document, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=True, allow_nan=False).encode("utf-8")
        return canonical, _sha256(canonical)

    record_id = enrollment.get("record_id")
    if not isinstance(record_id, str) or len(record_id) != 64:
        raise CliRefusal("the enrollment record carries no usable record id")
    artifact = _record_directory(store_root, record_id) / "artifacts" / PRODUCTION_PLAN_ARTIFACT
    if not artifact.is_file():
        raise CliRefusal(
            f"the enrollment record holds no {PRODUCTION_PLAN_ARTIFACT} artifact at {artifact}; "
            "a production grade cannot stand on a declared hash alone"
        )
    payload = artifact.read_bytes()
    computed = _sha256(payload)
    declared = (enrollment.get("artifact_hashes") or {}).get(PRODUCTION_PLAN_ARTIFACT)
    if declared != computed:
        raise CliRefusal(
            f"{PRODUCTION_PLAN_ARTIFACT} bytes do not match the record's own hash "
            f"(receipt {str(declared)[:12]}…, actual {computed[:12]}…)"
        )
    return payload, computed


def main(argv: Optional[list[str]] = None, *, store: Any = None) -> int:
    parser = argparse.ArgumentParser(description="Grade one enrolled track-record claim.")
    parser.add_argument("--evaluation-root", required=True)
    parser.add_argument("--enrollment-id", required=True)
    parser.add_argument("--claim", required=True, choices=CLAIMS)
    parser.add_argument("--outcome-manifest", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--horizon-days", type=int, default=None)
    parser.add_argument("--capture-inventory", default=None,
                        help="market only: the COMPLETE capture inventory to select from")
    parser.add_argument("--evaluated-at", required=True,
                        help="explicit ISO-8601 instant; the runner never reads a clock")
    args = parser.parse_args(argv)

    try:
        if args.claim == "market":
            if args.horizon_days not in HORIZONS:
                raise CliRefusal(f"--horizon-days must be one of {HORIZONS} for a market claim")
            if not args.capture_inventory:
                raise CliRefusal(
                    "--capture-inventory is required for a market claim; the endpoint is selected "
                    "deterministically from a complete inventory, never supplied on its own"
                )
        elif args.horizon_days is not None:
            raise CliRefusal("--horizon-days does not apply to a production claim")

        if store is None:                                  # DG206 owns the store; bind lazily
            try:
                from src.dynasty_genius.capture import (
                    track_record_store as store,  # type: ignore
                )
            except ImportError as error:
                raise CliRefusal(
                    "the DG206 record store is not available yet; this runner is complete but "
                    "unbound. Re-run once src/dynasty_genius/capture/track_record_store.py exists."
                ) from error

        evaluation_root = Path(args.evaluation_root)
        record = store.read_record(evaluation_root, args.enrollment_id)
        if not isinstance(record, dict) or record.get("kind") != "enrollment":
            raise CliRefusal(f"{args.enrollment_id} is not an enrollment record")

        output_root = Path(args.output_root)
        diagnostics_path = output_root / "grade-diagnostics.json"
        if diagnostics_path.exists():
            raise CliRefusal(
                f"{diagnostics_path} already exists; run evidence is immutable, so choose a fresh "
                "--output-root rather than overwriting a previous run's code identity"
            )

        manifest_path = Path(args.outcome_manifest)
        manifest = _read_json(manifest_path, "outcome manifest")
        verified, buffers = _verify_source_bytes(manifest, manifest_path)
        preparation = _validated_preparation(manifest, verified)

        envelope = dict(manifest.get("envelope") or {})
        if not envelope:
            raise CliRefusal("the outcome manifest carries no envelope")
        # The envelope's own source list is rebuilt from what was actually hashed, so a grade can
        # never inherit a hash the runner did not compute.
        envelope["sources"] = [
            {**entry, "sha256": verified[entry["name"]]}
            for entry in (manifest.get("sources") or [])
        ]
        # The prepared numeric payload is itself hashed and stored, so the grade names the exact
        # table it scored rather than pointing only at raw bytes it did not derive.
        prepared_bytes = json.dumps(envelope, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False).encode("utf-8")
        # Tagged as a serialization and given NO capture time. It is a restatement of the numbers
        # this run prepared, not an observation of the world, so it must never witness for the
        # completeness or chronology of the raw captures. Inventing a preparation time from the
        # target end let a source captured mid-season grade a finished season.
        envelope["sources"] = envelope["sources"] + [{
            "name": "prepared_outcome.json", "sha256": _sha256(prepared_bytes),
            "role": PREPARED_ROLE,
            "url": f"preparation:{preparation['recipe']}", "bytes_len": len(prepared_bytes),
        }]

        inventory_bytes = None
        selection_record = None
        if args.claim == "market":
            inventory_path = Path(args.capture_inventory)
            inventory_bytes = inventory_path.read_bytes()
            inventory = json.loads(inventory_bytes.decode("utf-8"))
            captures = inventory.get("captures")
            if not isinstance(captures, list):
                raise CliRefusal("the capture inventory carries no captures list")
            market_stream = ((record.get("document") or {}).get("market") or {})
            selection = select_endpoint(
                inventory=captures,
                t0=market_stream.get("t0"),
                horizon_days=args.horizon_days,
                configuration=market_stream.get("configuration"),
                evaluated_at=args.evaluated_at,
            )
            chosen = selection["chosen"]
            if chosen is None:
                envelope = None                       # a declared state, not a refusal
            else:
                # The endpoint that is GRADED must be the capture the inventory selected -- the
                # same bytes, the same instant, the same league settings. Accepting any verified
                # source digest let an unrelated supporting file witness for the endpoint: a
                # day-90 selection graded a day-92 envelope and exited 0.
                declared = envelope.get("endpoint_source_name")
                if not isinstance(declared, str) or declared not in verified:
                    raise CliRefusal(
                        "the envelope must name endpoint_source_name, and it must be one of the "
                        f"verified raw captures ({sorted(verified)})"
                    )
                if verified[declared] != chosen.get("sha256"):
                    raise CliRefusal(
                        "the graded endpoint is not the capture the inventory selects "
                        f"(selected as_of {chosen.get('as_of')} sha "
                        f"{str(chosen.get('sha256'))[:12]}…; graded source {declared} sha "
                        f"{verified[declared][:12]}…); the first compatible capture is chosen "
                        "before any result is seen"
                    )
                if envelope.get("as_of") != chosen.get("as_of"):
                    raise CliRefusal(
                        f"the graded endpoint is stamped {envelope.get('as_of')} but the selected "
                        f"capture is stamped {chosen.get('as_of')}"
                    )
                if chosen.get("configuration") != market_stream.get("configuration") or \
                        envelope.get("configuration") != market_stream.get("configuration"):
                    raise CliRefusal(
                        "the selected capture and the graded endpoint must both carry the "
                        "enrolled league configuration"
                    )
                selection_record = {
                    "chosen_as_of": chosen.get("as_of"),
                    "chosen_sha256": chosen.get("sha256"),
                    "endpoint_source_name": declared,
                    "considered": selection.get("considered"),
                    "rejected": selection.get("rejected"),
                }

        policy_payload, policy_hash = _policy_bytes(args.claim, record, evaluation_root)

        if args.claim in ("production", "football_production"):
            grade = grade_production(enrollment=record, outcome_source=envelope,
                                     evaluated_at=args.evaluated_at)
        else:
            grade = grade_market(enrollment=record, endpoint_source=envelope,
                                 evaluated_at=args.evaluated_at,
                                 horizon_days=args.horizon_days)

        if grade.get("policy_sha256") != policy_hash:
            raise CliRefusal(
                "policy identity disagreement between the enrollment and the policy on disk "
                f"(enrolled {str(grade.get('policy_sha256'))[:12]}…, on disk {policy_hash[:12]}…)"
            )

        artifacts = {"policy.json": policy_payload} if policy_payload else {}
        artifacts["outcome_manifest.json"] = manifest_path.read_bytes()
        artifacts["prepared_outcome.json"] = prepared_bytes
        # Every verified raw file travels INTO the immutable record. Otherwise a later replay
        # depends on a mutable external path surviving, which is not evidence.
        for name, payload in buffers.items():
            artifacts[f"source__{name}"] = payload
        artifacts["code_identity.json"] = json.dumps(
            _code_identity(), sort_keys=True, indent=2).encode("utf-8")
        # The inventory the endpoint was chosen from, and the choice itself, are frozen with the
        # grade. A selection nobody can re-derive later is an assertion, not a procedure.
        if inventory_bytes is not None:
            artifacts["capture_inventory.json"] = inventory_bytes
        if selection_record is not None:
            artifacts["endpoint_selection.json"] = json.dumps(
                selection_record, sort_keys=True, indent=2).encode("utf-8")
        # The store verifies that a grade references an enrollment IN THE SAME ROOT, so the grade
        # is appended beside its enrollment. --output-root holds the run-scoped diagnostics; it is
        # not a second record store, and writing the grade there would be refused.
        saved = store.save_record(evaluation_root, kind="grade", document=grade,
                                  artifacts=artifacts, recorded_at=_as_datetime(args.evaluated_at))

        diagnostics = {
            "claim": args.claim,
            "enrollment_id": args.enrollment_id,
            "horizon_days": args.horizon_days,
            "state": grade.get("state"),
            "counts": grade.get("counts"),
            "verified_source_hashes": verified,
            "prepared_outcome_sha256": _sha256(prepared_bytes),
            "preparation_recipe": preparation.get("recipe"),
            "endpoint_selection": (selection if args.claim == "market" else None),
            "policy_sha256": policy_hash,
            "policy_bytes_stored": bool(policy_payload),
            "policy_source": (MARKET_POLICY if args.claim == "market"
                              else f"enrollment artifact {PRODUCTION_PLAN_ARTIFACT}"),
            "grade_record_root": str(evaluation_root),
            "code_identity": _code_identity(),
            "grade_sha256": _sha256(canonical_grade_bytes(grade)),
        }
        output_root.mkdir(parents=True, exist_ok=True)
        diagnostics_path.write_bytes(
            json.dumps(diagnostics, indent=2, sort_keys=True).encode("utf-8")
        )
        print(json.dumps({"state": grade.get("state"),
                          "record_id": (saved.get("record") or {}).get("record_id"),
                          "created": saved.get("created")}, sort_keys=True))
        return 0
    except (CliRefusal, TrackRecordError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
