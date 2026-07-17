"""dg_delivery — the D0 cockpit delivery state machine.

Single source of truth for cockpit wire deliveries, per the ratified
wire-health spec (docs/superpowers/specs/2026-07-16-wire-health-hardening-design.md,
blob 715f288c). Owns send-id creation, wire-body stamping, pane classification,
ghost stripping, every lease/claim state transition, attempt/tombstone
persistence, and terminal/retryability classification. `tmux_msg.py` (sender)
and `dg_mail_carrier.py` (carrier) are thin drivers over this module; neither
may emit a key outside a machine-granted transition.

Every external effect is injected (runner/capturer/clock/store) so the
contract suite runs hermetically.
"""

from __future__ import annotations

import enum
import os
import re
import sqlite3
import stat as stat_module
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 1

GHOST_PLACEHOLDER = "�"

# Reason -> pinned CLI exit code (spec D2 exit table).
_EXIT_CODES = {
    "delivered_verified": 0,
    "delivery_unconfirmed": 2,
    "pane_busy": 3,
    "pane_dialog": 3,
    "pane_state_unknown": 3,
    "wait_budget_exhausted": 3,
    "body_missing_sender_header": 4,
    "body_empty": 4,
    "pane_identity_changed": 5,
    "profile_mismatch": 5,
    "pane_unreadable": 5,
    "mixed_frame": 5,
    "delivered_content_unconfirmed": 7,
}

_SENDER_LIVE_STATES = {"composing", "pasted", "composed_verifying", "composed_verified"}
_TERMINAL_STATES = {
    "strand_lost",
    "episode_exhausted",
    "manual_clear_required",
    "input_not_empty",
    "input_not_verifiable",
    "orphan_manual_required",
    "delivered_verified",
    "delivered_content_unconfirmed",
    "delivery_unconfirmed",
}
_NEVER_ORPHAN_STATES = {"input_not_verifiable", "input_not_empty", "manual_clear_required"}

_SEND_ID_RE = re.compile(r"\[(w#[a-z0-9]{1,16}-\d+)\]")
_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")
_CHIP_RE = re.compile(r"\[Pasted text #\d+ \+(\d+) lines?\]")
_OPTION_ROW_RE = re.compile(r"^\s*[❯›>]?\s*(\d+)\.\s+(.*)$")


class PaneState(enum.Enum):
    READY = "ready"
    BUSY = "busy"
    DIALOG = "dialog"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PaneProfile:
    """Per-CLI pane signature table. UNKNOWN is fail-closed by construction."""

    name: str
    ready_markers: tuple[str, ...]
    chip_collapsing: bool = False

    _REGISTRY = {
        "claude": {"ready": ("❯ ",), "chip": True},
        "codex": {"ready": ("codex > ", "❯ ", "› "), "chip": False},
        "gemini": {"ready": ("Type your message", "> ",), "chip": False},
    }

    @classmethod
    def for_cli(cls, name: str) -> "PaneProfile":
        entry = cls._REGISTRY.get(name)
        if entry is None:
            raise ValueError(f"unknown CLI profile: {name!r}")
        return cls(name=name, ready_markers=tuple(entry["ready"]), chip_collapsing=entry["chip"])


@dataclass
class SendResult:
    status: str
    reason: str
    phase: str
    terminal: bool
    attempts: int
    snapshots: list
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedSendId:
    nonce: str
    seq: int


class StoreError(RuntimeError):
    pass


def make_send_id(*, seq: int, random_bytes: bytes | None = None) -> str:
    """Collision-bounded send-id: random process nonce + counter (spec round-6 B3)."""

    raw = random_bytes if random_bytes is not None else os.urandom(5)
    value = int.from_bytes(raw, "big")
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    digits = []
    while value:
        value, rem = divmod(value, 36)
        digits.append(alphabet[rem])
    nonce = ("".join(reversed(digits)) or "0").rjust(8, "0")[:8]
    return f"w#{nonce}-{seq}"


def parse_send_id(send_id: str) -> ParsedSendId:
    match = re.fullmatch(r"w#([a-z0-9]{1,16})-(\d+)", send_id)
    if match is None:
        raise ValueError(f"not a send id: {send_id!r}")
    return ParsedSendId(nonce=match.group(1), seq=int(match.group(2)))


def stamp_wire_body(original: str, *, send_id: str) -> str:
    """Deterministic stamp: insert " [id]" into the first line (the one sanctioned delta)."""

    if not original:
        raise ValueError("body_empty")
    first, sep, rest = original.partition("\n")
    marker = f" [{send_id}]"
    dash = first.find(" —")
    if dash >= 0:
        stamped_first = first[:dash] + marker + first[dash:]
    else:
        stamped_first = first + marker
    return stamped_first + sep + rest


def _strip_stamp(text: str) -> str:
    return _SEND_ID_RE.sub("", text).replace("  ", " ").replace(" [", " [")


def _normalize_for_compare(text: str) -> str:
    return re.sub(r"\s*\[w#[a-z0-9]{1,16}-\d+\]", "", text)


def strip_ghost(raw: str) -> str:
    """Per-line SGR state machine (spec D4): dim spans -> one placeholder, never deleted.

    Sequential left-to-right parameter semantics; empty parameter list = reset;
    an unclosed dim span dims the rest of its line. Non-dim SGR sequences are
    removed; printable escape lookalikes (no real ESC byte) are preserved.
    """

    lines_out = []
    for line in raw.split("\n"):
        out: list[str] = []
        dim = False
        ghost_open = False
        pos = 0
        for match in _SGR_RE.finditer(line):
            segment = line[pos : match.start()]
            if segment:
                if dim:
                    if not ghost_open:
                        out.append(GHOST_PLACEHOLDER)
                        ghost_open = True
                else:
                    out.append(segment)
                    ghost_open = False
            params = match.group(1)
            codes = [int(p) for p in params.split(";") if p != ""] if params else [0]
            if not params:
                codes = [0]
            for code in codes:
                if code == 2:
                    dim = True
                elif code in (0, 22):
                    dim = False
            pos = match.end()
        tail = line[pos:]
        if tail:
            if dim:
                if not ghost_open:
                    out.append(GHOST_PLACEHOLDER)
            else:
                out.append(tail)
        lines_out.append("".join(out))
    return "\n".join(lines_out)


def _visible_empty(text: str) -> bool:
    stripped = strip_ghost(text).replace(GHOST_PLACEHOLDER, "")
    return stripped.strip() == ""


def classify_pane(raw: str, profile: PaneProfile) -> PaneState:
    """Positive classification; absence of markers is UNKNOWN, never READY."""

    stripped = strip_ghost(raw)
    tail_lines = [line for line in stripped.splitlines() if line.strip()][-8:]
    tail = "\n".join(tail_lines)
    if "Working (" in tail or "esc to interrupt" in tail or "esc to cancel" in tail:
        return PaneState.BUSY
    option_rows = [line for line in stripped.splitlines() if _OPTION_ROW_RE.match(line)]
    if option_rows and ("Press enter" in stripped or len(option_rows) >= 2 or "?" in stripped):
        return PaneState.DIALOG
    for marker in profile.ready_markers:
        if marker in stripped:
            return PaneState.READY
    return PaneState.UNKNOWN


def _result(
    status: str,
    reason: str,
    *,
    phase: str = "pre_paste",
    terminal: bool = False,
    attempts: int = 0,
    meta: dict | None = None,
) -> SendResult:
    merged = dict(meta or {})
    merged.setdefault("exit_code", _EXIT_CODES.get(reason, _EXIT_CODES.get(status, 1)))
    return SendResult(status, reason, phase, terminal, attempts, [], merged)


class DeliveryMachine:
    """The one state machine both the sender and carrier drive (spec D0/D0.1)."""

    _STORE_ENTRY_FAULTS = {
        "missing": "store_unavailable",
        "corrupt": "store_unavailable",
        "schema": "store_schema_mismatch",
        "locked": "store_locked",
    }

    STALE_CLAIM_SECONDS = 300.0
    ORPHAN_STABILITY_SECONDS = 30.0
    PRESS_WAITS = (30.0, 60.0)
    GC_ORPHAN_SECONDS = 900.0

    def __init__(
        self,
        *,
        runner: Callable[..., Any],
        capturer: Callable[[str], Any],
        clock: Any,
        store: Any,
        profile: PaneProfile,
    ) -> None:
        self.runner = runner
        self.capturer = capturer
        self.clock = clock
        self.store = store
        self.profile = profile
        self._seq = 0
        self._buffer_seq = 0
        self._machine_nonce = os.urandom(3).hex()

    # ------------------------------------------------------------------ store

    def _store_entry_check(self) -> SendResult | None:
        fault = getattr(self.store, "fault_at", None)
        if fault in self._STORE_ENTRY_FAULTS:
            reason = self._STORE_ENTRY_FAULTS[fault]
            return _result("refused", reason, terminal=True, meta={"exit_code": 5})
        return None

    @staticmethod
    def _frames_agree(a: Any, b: Any) -> bool:
        """D3's two-read law is COMPOSITE [round-6 B2]: identity, profile, and
        geometry must agree along with the ghost-stripped text regions."""

        return (
            a.pane_id == b.pane_id
            and a.current_command == b.current_command
            and a.cursor_row == b.cursor_row
            and a.cursor_col == b.cursor_col
            and a.width == b.width
            and a.height == b.height
            and strip_ghost(a.input_region) == strip_ghost(b.input_region)
            and strip_ghost(a.conversation_region) == strip_ghost(b.conversation_region)
        )

    def _terminal_row(self, row: dict | None) -> bool:
        return bool(row) and (
            row.get("terminal") or row.get("state") in _TERMINAL_STATES
        )

    @staticmethod
    def _edge_allowed(old: str, new: str) -> bool:
        """The D0.1 allowed-edge law [GREEN round-3 B3]: only ratified graph
        edges may execute; everything else loses the CAS by construction."""

        attempt = re.compile(r"^(submit|press)_attempt\((\d+)\)$")
        old_match = attempt.match(old)
        new_match = attempt.match(new)
        if old_match and new_match:
            # T5a/T12a are the ONLY attempt-to-attempt edges: same family,
            # exactly n -> n+1, within the family ceiling [round-4 B4].
            if old_match.group(1) != new_match.group(1):
                return False
            step = int(new_match.group(2)) - int(old_match.group(2))
            ceiling = 2 if new_match.group(1) == "submit" else 3
            return step == 1 and int(new_match.group(2)) <= ceiling
        if new_match:
            family, number = new_match.group(1), int(new_match.group(2))
            if family == "submit":
                return old == "composed_verified" and number == 1
            return old == "orphan_eligible" and number == 1

        def norm(state: str) -> str:
            if state.startswith("submit_attempt"):
                return "submit_attempt"
            if state.startswith("press_attempt"):
                return "press_attempt"
            return state

        edges = {
            "∅": {"composing", "input_not_empty"},
            "composing": {"pasted", "input_not_empty", "input_not_verifiable",
                          "manual_clear_required"},
            "pasted": {"composed_verified", "input_not_verifiable", "manual_clear_required"},
            "composed_verified": {"submit_attempt", "orphan_candidate",
                                  "orphan_manual_required", "manual_clear_required"},
            "submit_attempt": {"submit_attempt", "delivered_verified",
                               "delivered_content_unconfirmed", "delivery_unconfirmed",
                               "manual_clear_required"},
            "orphan_candidate": {"orphan_eligible", "manual_clear_required",
                                 "orphan_manual_required"},
            "orphan_eligible": {"press_attempt", "manual_clear_required",
                                "orphan_manual_required"},
            "press_attempt": {"press_attempt", "delivered_verified", "strand_lost",
                              "episode_exhausted", "manual_clear_required"},
        }
        return norm(new) in edges.get(norm(old), set())

    def _transition(self, send_id: str, new_state: str, *, expect: str | None = None) -> bool:
        """State CAS. Terminal rows are BYTE-IMMUTABLE; only ratified graph
        edges execute [round-3 B3]; `updated_at` is set BEFORE the durable CAS
        so the persisted row carries the new timestamp [round-3 B6]; when the
        store exposes `cas_row_state`, the durable CAS decides [round-2 B1]."""

        row = self.store.rows.get(send_id)
        old = row["state"] if row else "∅"
        if row is not None:
            if self._terminal_row(row):
                return False
            expected = expect if expect is not None else row.get("state")
            if row.get("state") != expected:
                return False
            if not self._edge_allowed(expected, new_state):
                return False
            previous_updated = row.get("updated_at")
            row["updated_at"] = self._now()
            cas = getattr(self.store, "cas_row_state", None)
            if cas is not None:
                if not cas(send_id, expected, new_state, row):
                    row["updated_at"] = previous_updated
                    return False
                row["state"] = new_state
            else:
                row["state"] = new_state
                persist = getattr(self.store, "persist_row", None)
                if persist is not None:
                    persist(row)
        else:
            if not self._edge_allowed("∅", new_state):
                return False
        self.store.transitions.append((send_id, old, new_state))
        return True

    def _now(self) -> float:
        return float(self.clock.monotonic())

    def _record_attempt(self, row: dict, attempt: int, kind: str) -> None:
        """Durable per-attempt evidence [GREEN round-2 B2, round-4 B5]: each
        attempt records kind + timestamp at key time and is completed with the
        post-key snapshot digest and its resolution when observed."""

        import json

        evidence = {}
        raw = row.get("attempt_evidence")
        if raw:
            try:
                evidence = json.loads(raw) if isinstance(raw, str) else dict(raw)
            except ValueError:
                evidence = {}
        evidence[str(attempt)] = {
            "kind": kind, "at": self._now(), "post_digest": None, "resolution": "pending",
        }
        row["attempt_evidence"] = json.dumps(evidence)

    def _resolve_attempt(self, row: dict, resolution: str, frame: Any | None) -> None:
        """Complete the last attempt's pinned evidence [round-4 B5]."""

        import hashlib
        import json

        raw = row.get("attempt_evidence")
        if not raw:
            return
        try:
            evidence = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except ValueError:
            return
        if not evidence:
            return
        last = str(max(int(k) for k in evidence))
        entry = evidence.get(last, {})
        if frame is not None:
            snapshot = strip_ghost(frame.input_region) + "\x1f" + strip_ghost(
                frame.conversation_region
            )
            entry["post_digest"] = hashlib.sha256(snapshot.encode("utf-8")).hexdigest()[:16]
        else:
            # An honest null [round-7 survivor]: the observation was attempted
            # and failed — recorded as such, never fabricated.
            entry["observation_failed"] = True
        entry["resolution"] = resolution
        evidence[last] = entry
        row["attempt_evidence"] = json.dumps(evidence)
        # Deliberately NO standalone persistence [round-5 B1]: the evidence
        # rides the immediately-following _transition CAS, so a stale process
        # that loses the transition also loses the evidence write — it can
        # never resurrect a durably-terminal row through an evidence upsert.

    def _new_row(self, send_id: str, pane_id: str, state: str, **extra: Any) -> dict | None:
        row = {
            "send_id": send_id,
            "state": state,
            "wire_digest": "",
            "pane_id": pane_id,
            "pane_epoch": 0,
            "profile": self.profile.name,
            "attempts": 0,
            "terminal": False,
            "carrier_eligible": False,
            "created_at": self._now(),
            "last_press_at": 0.0,
            "first_observed_at": 0.0,
            "attempt_evidence": "",
            "baseline_ref": "",
            "composer_observable": "",
            "updated_at": self._now(),
        }
        row.update(extra)
        if send_id in self.store.rows:
            return None
        cas = getattr(self.store, "cas_row_state", None)
        if cas is not None:
            # Durable unique create [round-4 B1]: the INSERT OR IGNORE decides;
            # a stale process can never overwrite an existing durable row.
            if not cas(send_id, "∅", state, row):
                return None
            self.store.rows[send_id] = row
        else:
            self.store.rows[send_id] = row
            persist = getattr(self.store, "persist_row", None)
            if persist is not None:
                persist(row)
        self.store.transitions.append((send_id, "∅", state))
        return row

    def _next_send_id(self) -> str:
        self._seq += 1
        return make_send_id(seq=self._seq)

    # ---------------------------------------------------------------- capture

    def _capture(self, pane_id: str) -> Any:
        capture = getattr(self.capturer, "capture", self.capturer)
        return capture(pane_id)

    def _try_capture(self, pane_id: str) -> tuple[Any | None, SendResult | None]:
        try:
            return self._capture(pane_id), None
        except BaseException:
            return None, _result("refused", "pane_unreadable", terminal=False)

    # ------------------------------------------------------------- pane claim

    def _claim_pane(self, pane_id: str, send_id: str) -> bool:
        cas = getattr(self.store, "cas_pane_claim", None)
        pane = self.store.panes.get(pane_id)
        if cas is not None:
            expected_epoch = int(pane.get("epoch", 0)) if pane else 0
            won, new_pane = cas(pane_id, expected_epoch, send_id)
            if not won:
                if new_pane is not None:
                    self.store.panes[pane_id] = new_pane
                return False
            self.store.panes[pane_id] = new_pane
            return True
        if pane is None:
            pane = {"pane_id": pane_id, "owner_send_id": send_id, "epoch": 1}
            self.store.panes[pane_id] = pane
        elif pane.get("owner_send_id") in (None, send_id):
            pane["owner_send_id"] = send_id
            pane["epoch"] = int(pane.get("epoch", 0)) + 1
        else:
            return False
        persist = getattr(self.store, "persist_pane", None)
        if persist is not None:
            persist(pane)
        return True

    def _release_pane(self, pane_id: str, expected_owner: str | None = None) -> None:
        """Owner-bound, epoch-conditional release [round-3 B2, round-4 B3]: a
        releaser that is not the current owner (or is stale) loses and the local
        mirror reloads — it can never clear a foreign claim."""

        pane = self.store.panes.get(pane_id)
        if pane is None:
            return
        if expected_owner is not None and pane.get("owner_send_id") not in (
            expected_owner, None
        ):
            return
        cas = getattr(self.store, "cas_pane_claim", None)
        if cas is not None:
            cas(
                pane_id, int(pane.get("epoch", 0)), None,
                expected_owner=expected_owner,
            )
            return
        pane["owner_send_id"] = None
        pane["epoch"] = int(pane.get("epoch", 0)) + 1
        persist = getattr(self.store, "persist_pane", None)
        if persist is not None:
            persist(pane)

    # --------------------------------------------------------------- sending

    def send_message(
        self,
        target: Any,
        body: Any,
        *,
        wait: bool = False,
        wait_budget: float | None = None,
    ) -> SendResult:
        if not isinstance(target, str) or not isinstance(body, str):
            raise TypeError("target and body must be strings")
        if not target or not body:
            raise ValueError("target and body must be non-empty")
        if not body.split("\n", 1)[0].startswith("From "):
            return _result("refused", "body_missing_sender_header", terminal=True)
        fault = self._store_entry_check()
        if fault is not None:
            return fault

        gate = self._readiness_gate(target, wait=wait, wait_budget=wait_budget)
        if isinstance(gate, SendResult):
            return gate
        frame_a, frame_b = gate

        visible = strip_ghost(frame_b.input_region)
        if not _visible_empty(frame_b.input_region):
            stamp = _SEND_ID_RE.search(frame_b.input_region)
            if stamp and stamp.group(1) in self.store.rows:
                candidate = self.store.rows[stamp.group(1)]
                recorded = _normalize_for_compare(
                    str(candidate.get("composer_observable") or candidate.get("wire_digest") or "")
                ).strip()
                if (
                    not self._terminal_row(candidate)
                    and candidate.get("state") in ("pasted", "composed_verified")
                    and recorded
                    and recorded == _normalize_for_compare(visible).strip()
                ):
                    return self._adopt_and_submit(frame_b, stamp.group(1))
            # Forged/unknown stamps and self-similar bodies without a durable
            # matching row are FOREIGN content [GREEN round-2 B4].
            send_id = self._next_send_id()
            if self._new_row(send_id, frame_b.pane_id, "input_not_empty", terminal=True):
                self._claim_pane(frame_b.pane_id, send_id)
            return _result(
                "refused", "input_not_empty", terminal=True,
                meta={"send_id": send_id, "guard": "T1_empty_proof"},
            )

        # Fresh path: T1 create + claim, then the T2 immediate pre-paste recheck.
        send_id = self._next_send_id()
        if getattr(self.store, "fault_at", None) == "claim_before_paste":
            return _result("refused", "store_unavailable", terminal=True)
        wire_body = stamp_wire_body(body, send_id=send_id)
        row = self._new_row(
            send_id, frame_b.pane_id, "composing", wire_digest=wire_body,
            baseline_ref=strip_ghost(frame_b.conversation_region),
        )
        if row is None:
            return _result("refused", "send_id_exists", terminal=True, meta={"send_id": send_id})
        if not self._claim_pane(frame_b.pane_id, send_id):
            self._transition(send_id, "manual_clear_required")
            row["terminal"] = True
            return _result("refused", "pane_claim_lost", terminal=True, meta={"send_id": send_id})

        recheck, err = self._try_capture(frame_b.pane_id)
        if err is not None:
            return err
        if not _visible_empty(recheck.input_region):
            self._transition(send_id, "input_not_empty")
            row["terminal"] = True
            return _result(
                "refused", "input_not_empty", terminal=True,
                meta={"send_id": send_id, "guard": "T2_pre_paste_recheck"},
            )
        if not self._transition(send_id, "pasted"):
            return _result("held", "cas_lost", terminal=False, meta={"send_id": send_id})
        self._paste(frame_b.pane_id, wire_body)

        verify, err = self._try_capture(frame_b.pane_id)
        if err is not None:
            return _result(
                "refused", "input_not_verifiable", phase="pasted", terminal=True,
                meta={"send_id": send_id},
            )
        composed = self._composed_matches(verify, wire_body)
        if composed is not True:
            self._transition(send_id, "input_not_verifiable")
            row["terminal"] = True
            return _result(
                "refused", composed, phase="pasted", terminal=True, meta={"send_id": send_id}
            )
        row["composer_observable"] = strip_ghost(verify.input_region)
        self._transition(send_id, "composed_verified")
        return self._submit_with_retry(row, wire_body)

    def _adopt_and_submit(self, frame: Any, found_id: str | None, body: str | None = None) -> SendResult:
        send_id = found_id or self._next_send_id()
        wire_body = strip_ghost(frame.input_region)
        row = self.store.rows.get(send_id)
        if row is not None:
            if self._terminal_row(row) or row.get("state") not in ("pasted", "composed_verified"):
                return _result(
                    "held", row.get("state", "adoption_refused"), terminal=True,
                    meta={"send_id": send_id, "guard": "terminal_row_immutable"},
                )
            self._transition(send_id, "composed_verified")
        else:
            row = self._new_row(send_id, frame.pane_id, "composed_verified", wire_digest=wire_body)
        if not self._claim_pane(frame.pane_id, send_id):
            return _result("refused", "pane_claim_lost", terminal=True, meta={"send_id": send_id})
        return self._submit_with_retry(row, wire_body)

    def _submit_with_retry(self, row: dict, wire_body: str) -> SendResult:
        send_id = row["send_id"]
        pane_id = row["pane_id"]
        if getattr(self.store, "fault_at", None) == "claim_before_key":
            return _result("refused", "store_unavailable", phase="pasted", terminal=True,
                           meta={"send_id": send_id})
        # Immediate pre-key snapshot [GREEN round-3 B4]: fresh admissible frame,
        # still READY, composed observable digest-intact — a queued DIALOG or a
        # tampered body blocks the key.
        pre_key, err = self._try_capture(pane_id)
        if err is not None:
            return _result("refused", "pane_unreadable", phase="pasted", terminal=True,
                           meta={"send_id": send_id})
        if classify_pane(pre_key.raw, self.profile) is not PaneState.READY:
            self._transition(send_id, "manual_clear_required")
            row["terminal"] = True
            return _result("refused", "pre_key_drift", phase="pasted", terminal=True,
                           meta={"send_id": send_id})
        if _normalize_for_compare(strip_ghost(pre_key.input_region)).strip() != (
            _normalize_for_compare(wire_body).strip()
        ):
            self._transition(send_id, "manual_clear_required")
            row["terminal"] = True
            return _result("refused", "wire_body_mismatch", phase="pasted", terminal=True,
                           meta={"send_id": send_id})
        row["attempts"] = 1
        row["last_press_at"] = self._now()
        self._record_attempt(row, 1, "submit")
        if not self._transition(send_id, "submit_attempt(1)"):
            row["attempts"] = 0
            return _result("held", "cas_lost", phase="pasted", terminal=False,
                           meta={"send_id": send_id})
        self._key(pane_id)
        last_observation = None
        for attempt in (1, 2):
            post, err = self._try_capture(pane_id)
            if err is not None:
                break
            last_observation = post
            if _visible_empty(post.input_region):
                if classify_pane(
                    post.raw, self.profile
                ) is PaneState.READY and send_id in strip_ghost(
                    post.conversation_region
                ) and send_id not in str(
                    row.get("baseline_ref") or ""
                ):
                    # D3 positive-verdict law [round-5 B4; symmetric
                    # admissibility per round-8 B1]: TWO agreeing composite
                    # reads, BOTH classified READY, never one.
                    confirm, err = self._try_capture(pane_id)
                    if (
                        err is None
                        and classify_pane(confirm.raw, self.profile) is PaneState.READY
                        and self._frames_agree(post, confirm)
                        and _visible_empty(confirm.input_region)
                        and send_id in strip_ghost(confirm.conversation_region)
                    ):
                        self._resolve_attempt(row, "delivered_verified", confirm)
                        self._transition(send_id, "delivered_verified")
                        row["terminal"] = True
                        self._release_pane(pane_id, expected_owner=send_id)
                        return _result(
                            "delivered_verified", "delivered_verified", phase="submitted",
                            terminal=True, attempts=row["attempts"], meta={"send_id": send_id},
                        )
                break
            if attempt == 1:
                recheck, err = self._try_capture(pane_id)
                if err is not None:
                    break
                state = classify_pane(recheck.raw, self.profile)
                intact = _normalize_for_compare(strip_ghost(recheck.input_region)).strip() == (
                    _normalize_for_compare(wire_body).strip()
                )
                if state is not PaneState.READY or not intact:
                    break
                row["attempts"] = 2
                row["last_press_at"] = self._now()
                self._record_attempt(row, 2, "submit")
                if not self._transition(send_id, "submit_attempt(2)"):
                    break
                self._key(pane_id)
        # The last successful post capture IS the observation [round-9 B1]:
        # observation_failed is recorded only when no capture ever succeeded.
        self._resolve_attempt(row, "delivery_unconfirmed", last_observation)
        self._transition(send_id, "delivery_unconfirmed")
        row["terminal"] = True
        return _result(
            "unconfirmed", "delivery_unconfirmed", phase="submitted", terminal=True,
            attempts=row["attempts"], meta={"send_id": send_id},
        )

    def _readiness_gate(
        self, target: str, *, wait: bool, wait_budget: float | None
    ) -> tuple[Any, Any] | SendResult:
        budget = wait_budget if wait_budget is not None else 30.0
        spent = 0.0
        previous = None
        while True:
            frame, err = self._try_capture(target)
            if err is not None:
                return err
            state = classify_pane(frame.raw, self.profile)
            if state is PaneState.DIALOG:
                return _result("refused", "pane_dialog", terminal=False)
            if state is PaneState.UNKNOWN:
                return _result("refused", "pane_state_unknown", terminal=False)
            if state is PaneState.BUSY:
                previous = None
                if not wait:
                    return _result("refused", "pane_busy", terminal=False)
                if spent >= budget:
                    return _result("refused", "wait_budget_exhausted", terminal=False)
                self.clock.sleep(0.5)
                spent += 0.5
                continue
            # READY: debounce needs two agreeing reads separated by the pinned gap.
            if previous is None:
                previous = frame
                if wait and spent >= budget:
                    return _result("refused", "wait_budget_exhausted", terminal=False)
                self.clock.sleep(0.5)
                spent += 0.5
                continue
            if frame.pane_id != previous.pane_id:
                return _result("refused", "pane_identity_changed", terminal=True)
            if frame.current_command != previous.current_command:
                return _result("refused", "profile_mismatch", terminal=True)
            if frame.cursor_row != previous.cursor_row:
                # one retry pair, then fail closed
                retry_a, err = self._try_capture(target)
                if err is not None:
                    return err
                retry_b, err = self._try_capture(target)
                if err is not None:
                    return err
                if (
                    retry_a.cursor_row == retry_b.cursor_row
                    and retry_a.pane_id == retry_b.pane_id
                ):
                    return retry_a, retry_b
                return _result("refused", "mixed_frame", terminal=False)
            return previous, frame

    # ----------------------------------------------------------- side effects

    def _paste(self, pane_id: str, wire_body: str) -> None:
        self._buffer_seq += 1
        name = f"dg-msg-{os.getpid()}-{self._machine_nonce}-{self._buffer_seq}"
        self.runner(["tmux", "set-buffer", "-b", name, "--", wire_body])
        try:
            self.runner(["tmux", "paste-buffer", "-p", "-b", name, "-t", pane_id])
        finally:
            self.runner(["tmux", "delete-buffer", "-b", name])

    def _key(self, pane_id: str) -> None:
        self.runner(["tmux", "send-keys", "-t", pane_id, "C-m"])

    # ------------------------------------------------------------ composition

    def compose(self, pane_id: str, body: str, *, send_id: str | None = None) -> SendResult:
        chosen = send_id or self._next_send_id()
        wire_body = stamp_wire_body(body, send_id=chosen)
        row = self._new_row(chosen, pane_id, "composing", wire_digest=wire_body)
        if row is None:
            return _result("refused", "send_id_exists", terminal=True, meta={"send_id": chosen})
        if not self._claim_pane(pane_id, chosen):
            return _result("refused", "pane_claim_lost", terminal=True, meta={"send_id": chosen})
        if not self._transition(chosen, "pasted"):
            return _result("held", "cas_lost", terminal=False, meta={"send_id": chosen})
        self._paste(pane_id, wire_body)
        return _result("pasted", "pasted", phase="pasted", meta={"send_id": chosen})

    def acquire_composer(self, pane_id: str, body: str) -> SendResult:
        frame_a, err = self._try_capture(pane_id)
        if err is not None:
            return err
        frame_b, err = self._try_capture(pane_id)
        if err is not None:
            return err
        if _visible_empty(frame_b.input_region):
            send_id = self._next_send_id()
            if self._new_row(send_id, frame_b.pane_id, "composing") is None:
                return _result("refused", "send_id_exists", terminal=True,
                               meta={"send_id": send_id})
            if not self._claim_pane(frame_b.pane_id, send_id):
                self._transition(send_id, "manual_clear_required")
                self.store.rows[send_id]["terminal"] = True
                return _result("refused", "pane_claim_lost", terminal=True,
                               meta={"send_id": send_id})
            return _result("composing", "composing", meta={"send_id": send_id})
        for row in self.store.rows.values():
            if row.get("composer_observable") == frame_b.input_region and row["state"] in (
                "pasted",
                "composed_verified",
            ):
                return _result("resume", "resume", meta={"send_id": row["send_id"]})
        send_id = self._next_send_id()
        self._new_row(send_id, frame_b.pane_id, "input_not_empty", terminal=True)
        self._claim_pane(frame_b.pane_id, send_id)
        return _result(
            "refused", "input_not_empty", terminal=True,
            meta={"send_id": send_id, "guard": "T1_empty_proof"},
        )

    def verify_composed(self, wire_body: str, *, expected_lines: int | None = None) -> SendResult:
        frame, err = self._try_capture("verify")
        if err is not None:
            return err
        outcome = self._composed_matches(frame, wire_body, expected_lines=expected_lines)
        if outcome is True:
            return _result("composed_verified", "composed_verified")
        return _result("refused", outcome, terminal=False)

    def _composed_matches(
        self, frame: Any, wire_body: str, *, expected_lines: int | None = None
    ) -> Any:
        visible = strip_ghost(frame.input_region)
        chip = _CHIP_RE.search(visible)
        if self.profile.chip_collapsing and chip:
            advertised = int(chip.group(1)) + 1
            if expected_lines is not None and advertised != expected_lines:
                return "input_not_verifiable"
            return True
        if self.profile.chip_collapsing and expected_lines is not None and not chip:
            return "input_not_verifiable"
        if _visible_empty(frame.input_region):
            return "input_not_verifiable"
        if _normalize_for_compare(visible).strip() == _normalize_for_compare(wire_body).strip():
            return True
        return "wire_body_mismatch"

    # ------------------------------------------------------------ verification

    def verify_delivery(
        self,
        send_id: str,
        wire_body: str,
        *,
        baseline: Any | None = None,
        chip_profile: bool = False,
    ) -> SendResult:
        frame, err = self._try_capture("verify")
        if err is not None:
            return err
        raw_conv = frame.conversation_region
        stripped_conv = strip_ghost(raw_conv)
        if send_id in raw_conv and send_id not in stripped_conv:
            return _result("refused", "ghost_text_not_delivery", terminal=False)
        if send_id not in stripped_conv:
            return _result("unconfirmed", "delivery_unconfirmed", phase="submitted", terminal=True)
        if baseline is not None and send_id in strip_ghost(baseline.conversation_region):
            return _result("unconfirmed", "delivery_unconfirmed", phase="submitted", terminal=True)
        if chip_profile:
            header = wire_body.split("\n", 1)[0].split(" [", 1)[0]
            id_lines = [line for line in stripped_conv.splitlines() if send_id in line]
            re_exposed = any(line.strip().startswith(header) for line in id_lines)
            if not re_exposed:
                return _result(
                    "delivered_content_unconfirmed", "delivered_content_unconfirmed",
                    phase="submitted", terminal=True, meta={"exit_code": 7},
                )
            matched = any(
                _normalize_for_compare(line).strip() == _normalize_for_compare(wire_body).strip()
                for line in id_lines
            )
            if not matched:
                return _result(
                    "unconfirmed", "delivery_unconfirmed", phase="submitted", terminal=True
                )
        if baseline is None:
            return _result(
                "delivered_verified", "delivered_verified", phase="submitted", terminal=True
            )
        return _result(
            "delivered_verified", "delivered_verified", phase="submitted", terminal=True
        )

    # ---------------------------------------------------------------- approve

    def approve(self, target: str, *, option_text: str) -> SendResult:
        frame, err = self._try_capture(target)
        if err is not None:
            return err
        if classify_pane(frame.raw, self.profile) is not PaneState.DIALOG:
            return _result("refused", "no_dialog_present", terminal=False)
        highlighted = None
        digit = None
        for line in strip_ghost(frame.raw).splitlines():
            match = _OPTION_ROW_RE.match(line)
            if match and line.lstrip().startswith(("❯", "›")):
                digit, highlighted = match.group(1), match.group(2).strip()
                break
        if highlighted is None:
            # No highlighted row -> the tool cannot know what Enter/digit selects.
            return _result("refused", "no_highlighted_option", terminal=False)
        if highlighted != option_text.strip():
            return _result("refused", "option_mismatch", terminal=False)
        self.runner(["tmux", "send-keys", "-t", target, digit])
        post, err = self._try_capture(target)
        if err is not None:
            return _result("refused", "post_approve_unreadable", terminal=False,
                           meta={"warning_exit": 8})
        if classify_pane(post.raw, self.profile) is PaneState.DIALOG:
            return _result(
                "refused", "dialog_still_open", terminal=False, meta={"warning_exit": 8}
            )
        if not _visible_empty(post.input_region):
            return _result(
                "refused", "stray_echo_detected", terminal=False, meta={"warning_exit": 8}
            )
        return _result(
            "approved", "approved", terminal=False,
            meta={
                "toctou_warning": (
                    "residual TOCTOU window between capture and keypress —"
                    " verify the dialog outcome by its effect, not this result"
                )
            },
        )

    def diagnose_stray(self, target: str) -> SendResult:
        """D7 buffered-stray / one-keystroke-offset diagnostic [round-3 H1].

        Captures WITHOUT keying: reports whether the input region holds a
        stray keystroke residue (a bare digit/short fragment that matches the
        approval-echo shape). Purely observational — zero pane mutations.
        """

        frame, err = self._try_capture(target)
        if err is not None:
            return err
        visible = strip_ghost(frame.input_region).replace(GHOST_PLACEHOLDER, "").strip()
        if not visible:
            return _result("clear", "no_stray", terminal=False)
        if re.fullmatch(r"[0-9]{1,2}", visible):
            return _result(
                "warning", "stray_present", terminal=False,
                meta={"stray": visible, "warning_exit": 8},
            )
        return _result("held", "input_not_empty", terminal=False)

    def diagnose_stray_offset(self, target: str) -> SendResult:
        """D7's named one-keystroke-offset diagnostic [round-4 H1]: a scripted
        two-phase observation of a dialog + buffered stray, ZERO keys emitted.

        Phase 1 captures the dialog-open frame and looks for buffered stray
        residue; phase 2 captures again and classifies the offset signature:
        a dialog that closed while the stray vanished WITHOUT any tool key is
        the stray-consumed-by-dialog confirmation the spec's probe names.
        """

        first, err = self._try_capture(target)
        if err is not None:
            return err
        first_dialog = classify_pane(first.raw, self.profile) is PaneState.DIALOG
        first_stray = strip_ghost(first.input_region).replace(GHOST_PLACEHOLDER, "").strip()
        second, err = self._try_capture(target)
        if err is not None:
            return err
        second_dialog = classify_pane(second.raw, self.profile) is PaneState.DIALOG
        second_stray = strip_ghost(second.input_region).replace(GHOST_PLACEHOLDER, "").strip()
        stray_shape = bool(re.fullmatch(r"[0-9]{1,2}", first_stray or ""))
        if first_dialog and stray_shape and not second_dialog and not second_stray:
            return _result(
                "warning", "stray_offset_signature", terminal=False,
                meta={"stray": first_stray, "warning_exit": 8,
                      "hypothesis": (
                          "CONSISTENT WITH one-keystroke-offset — observational"
                          " only; causal confirmation requires controlled"
                          " buffer/approval provenance (the David-gated live probe)"
                      )},
            )
        if first_dialog and stray_shape:
            return _result(
                "warning", "stray_at_dialog_risk", terminal=False,
                meta={"stray": first_stray, "warning_exit": 8},
            )
        if stray_shape:
            return _result("warning", "stray_present", terminal=False,
                           meta={"stray": first_stray, "warning_exit": 8})
        return _result("clear", "no_stray", terminal=False)

    # ---------------------------------------------------------------- carrier

    def carrier_tick(self, pane_id: str) -> SendResult:
        frame, err = self._try_capture(pane_id)
        if err is not None:
            return err
        state = classify_pane(frame.raw, self.profile)
        if state is PaneState.DIALOG:
            return _result("held", "held_dialog_shape", terminal=False)
        if state is not PaneState.READY:
            return _result("held", "pane_busy", terminal=False)

        input_stripped = strip_ghost(frame.input_region)
        stamp = _SEND_ID_RE.search(input_stripped)
        row = None
        if stamp:
            row = self.store.rows.get(stamp.group(1))
        if row is None:
            # Pane-scoped lookup ONLY for rows this machine must resolve without a
            # visible stamp: pending press attempts (absence/result processing) and
            # stale composed rows. Never an unconditional attachment [GREEN B5].
            for candidate in self.store.rows.values():
                if candidate.get("pane_id") != pane_id and not self._terminal_row(candidate):
                    continue
                state = candidate.get("state", "")
                if state.startswith("press_attempt") and candidate.get("pane_id") == pane_id:
                    row = candidate
                    break
                if self._terminal_row(candidate) and candidate["send_id"] in input_stripped:
                    row = candidate
                    break
                if state in ("composed_verified", "orphan_candidate", "orphan_eligible") and (
                    candidate["send_id"] in input_stripped
                ):
                    row = candidate
                    break

        if row is not None:
            row_state = row["state"]
            if row_state in _TERMINAL_STATES:
                return _result("held", row_state, terminal=True, attempts=row.get("attempts", 0))
            if row_state.startswith("submit_attempt") or row_state in _SENDER_LIVE_STATES - {
                "composed_verified"
            }:
                return _result("held", "sender_live", terminal=False)
            if row_state in _NEVER_ORPHAN_STATES or row_state.startswith("refused"):
                return _result("held", row_state, terminal=True)
            if row_state.startswith("press_attempt"):
                if row["send_id"] in strip_ghost(frame.conversation_region) and row[
                    "send_id"
                ] not in str(row.get("baseline_ref") or ""):
                    confirm, cerr = self._try_capture(pane_id)
                    if cerr is not None or classify_pane(
                        confirm.raw, self.profile
                    ) is not PaneState.READY or not self._frames_agree(frame, confirm) or row[
                        "send_id"
                    ] not in strip_ghost(confirm.conversation_region):
                        return _result("held", "delivery_unconfirmed_pending",
                                       terminal=False,
                                       attempts=int(row.get("attempts", 0)))
                    self._resolve_attempt(row, "delivered_verified", confirm)
                    self._transition(row["send_id"], "delivered_verified")
                    row["terminal"] = True
                    self._release_pane(pane_id, expected_owner=row["send_id"])
                    return _result(
                        "delivered_verified", "delivered_verified", phase="submitted",
                        terminal=True, attempts=int(row.get("attempts", 0)),
                    )
                if self._strand_absent(frame, row, pane_id):
                    return self._strand_lost(row, frame)
                if row["send_id"] not in input_stripped:
                    return _result("held", "untracked_strand", terminal=False)
                return self._press_timeline(row, pane_id, frame)
            if row_state == "composed_verified":
                pane = self.store.panes.get(row.get("pane_id"))
                claimed = pane is not None and pane.get("owner_send_id") == row["send_id"]
                quiet = self._now() - float(row.get("updated_at", 0.0)) >= self.STALE_CLAIM_SECONDS
                if claimed and quiet:
                    # T16a/T10x stale handoff is reachable from the driver [GREEN H3].
                    return self.recover_stale_claim(row["send_id"])
                if claimed or not quiet:
                    return _result("held", "sender_live", terminal=False)
                if self.profile.chip_collapsing:
                    self._transition(row["send_id"], "orphan_manual_required")
                    row["terminal"] = True
                    return _result("held", "orphan_manual_required", terminal=True)
                if row["send_id"] not in input_stripped:
                    return _result("held", "untracked_strand", terminal=False)
                row["first_observed_at"] = self._now()
                self._transition(row["send_id"], "orphan_candidate")
                return _result("observing", "orphan_candidate", terminal=False)
            if row_state == "orphan_candidate":
                if row["send_id"] not in input_stripped:
                    return _result("held", "untracked_strand", terminal=False)
                first = float(row.get("first_observed_at") or 0.0)
                if first <= 0.0:
                    row["first_observed_at"] = self._now()
                    persist = getattr(self.store, "persist_row", None)
                    if persist is not None:
                        persist(row)
                    return _result("observing", "orphan_candidate", terminal=False)
                if self._now() - first >= self.ORPHAN_STABILITY_SECONDS:
                    self._transition(row["send_id"], "orphan_eligible")
                    return self._press_timeline(row, pane_id, frame)
                return _result("observing", "orphan_candidate", terminal=False)
            if row_state == "orphan_eligible":
                if row["send_id"] not in input_stripped:
                    return _result("held", "untracked_strand", terminal=False)
                return self._press_timeline(row, pane_id, frame)
            return _result("held", row_state, terminal=False)

        # No machine row for what is visible.
        if _visible_empty(frame.input_region):
            return _result("idle", "no_strand", terminal=False)
        if not input_stripped.lstrip().startswith("From "):
            return _result("held", "unattributed_strand", terminal=False)
        if stamp is None:
            return _result("held", "untracked_strand", terminal=False)
        return _result("held", "untracked_strand", terminal=False)

    def _strand_absent(self, frame: Any, row: dict, pane_id: str) -> bool:
        if not _visible_empty(frame.input_region):
            return False
        if row["send_id"] in strip_ghost(frame.conversation_region):
            return False
        second, err = self._try_capture(pane_id)
        if err is not None:
            return False
        if classify_pane(second.raw, self.profile) is not PaneState.READY:
            return False
        return _visible_empty(second.input_region) and row["send_id"] not in strip_ghost(
            second.conversation_region
        )

    def _strand_lost(self, row: dict, frame: Any | None = None) -> SendResult:
        self._resolve_attempt(row, "strand_lost", frame)
        self._transition(row["send_id"], "strand_lost")
        row["terminal"] = True
        row["carrier_eligible"] = False
        self._release_pane(row["pane_id"], expected_owner=row["send_id"])
        return _result("held", "strand_lost", terminal=True, attempts=row.get("attempts", 0))

    def _press_timeline(self, row: dict, pane_id: str, frame: Any | None = None) -> SendResult:
        if self._terminal_row(row):
            return _result("held", row.get("state", "terminal"), terminal=True,
                           attempts=int(row.get("attempts", 0)))
        attempts = int(row.get("attempts", 0))
        if attempts >= 3:
            # The tick's own frame is the observation when available [round-8 B2].
            self._resolve_attempt(row, "episode_exhausted", frame)
            self._transition(row["send_id"], "episode_exhausted")
            row["terminal"] = True
            self._release_pane(pane_id, expected_owner=row["send_id"])
            return _result("held", "episode_exhausted", terminal=True, attempts=attempts)
        if not self._claim_pane(pane_id, row["send_id"]):
            return _result("held", "pane_claim_lost", terminal=False, attempts=attempts)
        now = self._now()
        if attempts >= 1:
            wait_needed = self.PRESS_WAITS[min(attempts - 1, 1)]
            last = float(row.get("last_press_at", 0.0))
            if now - last < wait_needed:
                return _result("waiting", "press_wait", terminal=False, attempts=attempts)
        # Immediate pre-key snapshot [GREEN round-2 B5]: fresh admissible frame,
        # still READY, strand digest-identical to the durable record.
        pre_key, err = self._try_capture(pane_id)
        if err is not None:
            return _result("held", "pane_unreadable", terminal=False, attempts=attempts)
        if classify_pane(pre_key.raw, self.profile) is not PaneState.READY:
            return _result("held", "pre_key_drift", terminal=False, attempts=attempts)
        strand = _normalize_for_compare(strip_ghost(pre_key.input_region)).strip()
        recorded = _normalize_for_compare(str(row.get("wire_digest", ""))).strip()
        if not recorded or strand != recorded:
            return _result("held", "strand_digest_mismatch", terminal=False, attempts=attempts)
        attempts += 1
        row["attempts"] = attempts
        row["last_press_at"] = now
        self._record_attempt(row, attempts, "press")
        if not self._transition(row["send_id"], f"press_attempt({attempts})"):
            row["attempts"] = attempts - 1
            return _result("held", "cas_lost", terminal=False, attempts=attempts - 1)
        self._key(pane_id)
        if attempts >= 3:
            observation, _o_err = self._try_capture(pane_id)
            self._resolve_attempt(row, "episode_exhausted", observation)
            self._transition(row["send_id"], "episode_exhausted")
            row["terminal"] = True
            self._release_pane(pane_id, expected_owner=row["send_id"])
            return _result("held", "episode_exhausted", terminal=True, attempts=attempts)
        return _result("pressed", f"press_attempt({attempts})", terminal=False, attempts=attempts)

    # ------------------------------------------------------------- lifecycle

    def submit(self, send_id: str) -> SendResult:
        row = self.store.rows[send_id]
        if self._terminal_row(row):
            return _result("held", row.get("state", "terminal"), terminal=True)
        first, err = self._try_capture(row["pane_id"])
        if err is not None:
            return _result("refused", "pane_unreadable", terminal=True)
        recheck, err = self._try_capture(row["pane_id"])
        if err is not None:
            return _result("refused", "pane_unreadable", terminal=True)
        state = classify_pane(recheck.raw, self.profile)
        if state is PaneState.DIALOG:
            return _result("refused", "pane_dialog", terminal=True)
        if state is not PaneState.READY:
            return _result("refused", "pane_not_ready", terminal=True)
        if recheck.pane_id != first.pane_id:
            return _result("refused", "pane_identity_changed", terminal=True)
        if recheck.current_command != first.current_command:
            return _result("refused", "profile_mismatch", terminal=True)
        if not self._claim_pane(row["pane_id"], send_id):
            return _result("refused", "pane_claim_lost", terminal=False)
        recorded = _normalize_for_compare(str(row.get("wire_digest", ""))).strip()
        observed = _normalize_for_compare(strip_ghost(recheck.input_region)).strip()
        if not recorded or observed != recorded:
            return _result("refused", "wire_body_mismatch", terminal=True)
        row["attempts"] = int(row.get("attempts", 0)) + 1
        row["last_press_at"] = self._now()
        self._record_attempt(row, row["attempts"], "submit")
        if not self._transition(send_id, "submit_attempt(1)"):
            row["attempts"] -= 1
            return _result("held", "cas_lost", terminal=False)
        self._key(row["pane_id"])
        return _result("submitted", "submitted", phase="submitted", attempts=row["attempts"])

    def retry_submit(self, send_id: str) -> SendResult:
        row = self.store.rows[send_id]
        if self._terminal_row(row):
            return _result("held", row.get("state", "terminal"), terminal=True,
                           attempts=int(row.get("attempts", 0)))
        attempts = int(row.get("attempts", 0))
        if attempts >= 2:
            return _result(
                "refused", "submit_attempts_exhausted", phase="submitted", terminal=True,
                attempts=attempts,
            )
        frame, err = self._try_capture(row["pane_id"])
        if err is not None:
            return _result("refused", "pane_unreadable", terminal=True, attempts=attempts)
        if classify_pane(frame.raw, self.profile) is not PaneState.READY:
            return _result("refused", "pane_not_ready", terminal=True, attempts=attempts)
        recorded = _normalize_for_compare(str(row.get("wire_digest", ""))).strip()
        observed = _normalize_for_compare(strip_ghost(frame.input_region)).strip()
        if not recorded or observed != recorded:
            return _result("refused", "wire_body_mismatch", terminal=True, attempts=attempts)
        if not self._claim_pane(row["pane_id"], send_id):
            return _result("refused", "pane_claim_lost", terminal=False, attempts=attempts)
        attempts += 1
        row["attempts"] = attempts
        row["last_press_at"] = self._now()
        self._record_attempt(row, attempts, "submit")
        if not self._transition(send_id, f"submit_attempt({attempts})"):
            row["attempts"] = attempts - 1
            return _result("held", "cas_lost", terminal=False, attempts=attempts - 1)
        self._key(row["pane_id"])
        return _result("submitted", f"submit_attempt({attempts})", phase="submitted",
                       attempts=attempts)

    def retry_press(self, send_id: str, *, elapsed: float) -> SendResult:
        row = self.store.rows[send_id]
        if self._terminal_row(row):
            return _result("held", row.get("state", "terminal"), terminal=True,
                           attempts=int(row.get("attempts", 0)))
        if not (
            str(row.get("state", "")).startswith("press_attempt")
            or row.get("state") == "orphan_eligible"
        ):
            return _result("refused", "illegal_edge", terminal=False,
                           attempts=int(row.get("attempts", 0)))
        frame, err = self._try_capture(row["pane_id"])
        if err is None:
            conv = strip_ghost(frame.conversation_region)
            baseline = str(row.get("baseline_ref") or "")
            if classify_pane(
                frame.raw, self.profile
            ) is PaneState.READY and send_id in conv and send_id not in baseline:
                # Positive delivery precedence: baseline guard + the composite
                # two-read confirmation [round-4 residual, round-6 B2].
                confirm, cerr = self._try_capture(row["pane_id"])
                if cerr is None and classify_pane(
                    confirm.raw, self.profile
                ) is PaneState.READY and self._frames_agree(frame, confirm) and send_id in (
                    strip_ghost(confirm.conversation_region)
                ):
                    self._resolve_attempt(row, "delivered_verified", confirm)
                    self._transition(send_id, "delivered_verified")
                    row["terminal"] = True
                    self._release_pane(row["pane_id"], expected_owner=send_id)
                    return _result(
                        "delivered_verified", "delivered_verified", phase="submitted",
                        terminal=True, attempts=int(row.get("attempts", 0)),
                    )
                return _result("waiting", "delivery_unconfirmed_pending", terminal=False,
                               attempts=int(row.get("attempts", 0)))
        attempts = int(row.get("attempts", 0))
        if attempts >= 3:
            # The already-captured frame IS the observation [round-8 B2]:
            # never fabricate an observation failure after a successful capture.
            self._resolve_attempt(row, "episode_exhausted", frame if err is None else None)
            self._transition(send_id, "episode_exhausted")
            row["terminal"] = True
            self._release_pane(row["pane_id"], expected_owner=send_id)
            return _result("held", "episode_exhausted", terminal=True, attempts=attempts)
        wait_needed = self.PRESS_WAITS[min(max(attempts - 1, 0), 1)]
        if elapsed < wait_needed:
            return _result("waiting", "press_wait", terminal=False, attempts=attempts)
        recorded = _normalize_for_compare(str(row.get("wire_digest", ""))).strip()
        observed = _normalize_for_compare(strip_ghost(frame.input_region)).strip()
        if not recorded or observed != recorded:
            return _result("held", "strand_digest_mismatch", terminal=False, attempts=attempts)
        if not self._claim_pane(row["pane_id"], send_id):
            return _result("held", "pane_claim_lost", terminal=False, attempts=attempts)
        attempts += 1
        row["attempts"] = attempts
        row["last_press_at"] = self._now()
        self._record_attempt(row, attempts, "press")
        if not self._transition(send_id, f"press_attempt({attempts})"):
            row["attempts"] = attempts - 1
            return _result("held", "cas_lost", terminal=False, attempts=attempts - 1)
        self._key(row["pane_id"])
        if attempts >= 3:
            observation, _o_err = self._try_capture(row["pane_id"])
            self._resolve_attempt(row, "episode_exhausted", observation)
            self._transition(send_id, "episode_exhausted")
            row["terminal"] = True
            self._release_pane(row["pane_id"], expected_owner=send_id)
            return _result("held", "episode_exhausted", terminal=True, attempts=attempts)
        return _result("pressed", f"press_attempt({attempts})", terminal=False, attempts=attempts)

    def reconcile(self, send_id: str, *, crash_window: str, actor: str) -> SendResult:
        """Crash-window reconciliation from EVIDENCE, never the caller's label [GREEN B6].

        The `crash_window`/`actor` arguments are audit context only. The verdict
        comes from a fresh capture plus the durable row: a new conversation
        occurrence of the send-id proves delivery; an unchanged composed
        observable proves the attempt is reclaimable; anything else is
        terminal/manual. The outcome is persisted to the row.
        """

        row = self.store.rows.get(send_id)
        if row is None:
            return _result("refused", "unknown_send_id", terminal=True)
        if self._terminal_row(row):
            return _result("held", row.get("state", "terminal"), terminal=True)
        frame, err = self._try_capture(row.get("pane_id", ""))
        second, err2 = (None, None) if err is not None else self._try_capture(
            row.get("pane_id", "")
        )
        if err is not None or err2 is not None or second is None or not self._frames_agree(
            frame, second
        ) or classify_pane(frame.raw, self.profile) is not PaneState.READY or classify_pane(
            second.raw, self.profile
        ) is not PaneState.READY:
            # The two-read law [round-4 B5, composite per round-6 B2]: no
            # verdict from one frame or from disagreeing frames — and the
            # ambiguous outcome still completes the evidence record [round-6 B1].
            self._resolve_attempt(row, "manual_clear_required", None)
            self._transition(send_id, "manual_clear_required")
            row["terminal"] = True
            return _result("manual", "manual_clear_required", phase="submitted", terminal=True)
        conv = strip_ghost(frame.conversation_region)
        baseline_ref = str(row.get("baseline_ref") or "")
        if send_id in conv and send_id not in baseline_ref:
            self._resolve_attempt(row, "delivered_verified", frame)
            self._transition(send_id, "delivered_verified")
            row["terminal"] = True
            return _result(
                "delivered_verified", "delivered_verified", phase="submitted", terminal=True
            )
        observable = _normalize_for_compare(strip_ghost(frame.input_region)).strip()
        recorded = _normalize_for_compare(str(row.get("wire_digest", ""))).strip()
        if observable and recorded and observable == recorded:
            self._resolve_attempt(row, "reclaimable", frame)
            evidence_cas = getattr(self.store, "cas_update_evidence", None)
            if evidence_cas is not None:
                # Reclaimable has NO following transition, so its evidence gets
                # the dedicated state-conditioned durable write [round-6 B1] —
                # and a LOST write means the row moved durably: the verdict is
                # withdrawn, never reported stale [round-7 B1].
                if not evidence_cas(send_id, row["state"], row["attempt_evidence"]):
                    reload_row = getattr(self.store, "_reload_row", None)
                    if reload_row is not None:
                        reload_row(send_id)
                    fresh = self.store.rows.get(send_id, row)
                    return _result(
                        "held", fresh.get("state", "cas_lost"), phase="submitted",
                        terminal=self._terminal_row(fresh),
                    )
            return _result("reclaimable", "reclaimable", phase="pasted", terminal=False)
        self._resolve_attempt(row, "manual_clear_required", frame)
        self._transition(send_id, "manual_clear_required")
        row["terminal"] = True
        return _result("manual", "manual_clear_required", phase="submitted", terminal=True)

    def recover_stale_claim(self, send_id: str) -> SendResult:
        row = self.store.rows[send_id]
        if self._terminal_row(row):
            return _result("held", row.get("state", "terminal"), terminal=True)
        if self._now() - float(row.get("updated_at", 0.0)) < self.STALE_CLAIM_SECONDS:
            return _result("held", "claim_not_stale", terminal=False)
        if row["state"] == "composed_verified":
            if self.profile.chip_collapsing or row.get("profile") in ("claude",):
                self._transition(send_id, "orphan_manual_required")
                row["terminal"] = True
                return _result("held", "orphan_manual_required", terminal=True)
            row["first_observed_at"] = self._now()
            self._transition(send_id, "orphan_candidate")
            self._release_pane(row["pane_id"], expected_owner=send_id)
            return _result("observing", "orphan_candidate", terminal=False)
        self._transition(send_id, "manual_clear_required")
        row["terminal"] = True
        return _result("held", "manual_clear_required", terminal=True)

    def ack_clear(self, send_id: str, *, pane_epoch: int) -> SendResult:
        row = self.store.rows[send_id]
        pane = self.store.panes.get(row["pane_id"])
        if pane is None or int(pane.get("epoch", -1)) != pane_epoch:
            return _result("refused", "pane_epoch_mismatch", terminal=False)
        for _ in range(2):
            frame, err = self._try_capture(row["pane_id"])
            if err is not None:
                return err
            if not _visible_empty(frame.input_region):
                return _result("refused", "input_not_empty", terminal=False)
        cas = getattr(self.store, "cas_pane_claim", None)
        if cas is not None:
            won, new_pane = cas(row["pane_id"], pane_epoch, None)
            if not won:
                return _result("refused", "pane_epoch_mismatch", terminal=False)
            self.store.panes[row["pane_id"]] = new_pane
        else:
            pane["owner_send_id"] = None
            pane["epoch"] = int(pane.get("epoch", 0)) + 1
            persist = getattr(self.store, "persist_pane", None)
            if persist is not None:
                persist(pane)
        return _result("claim_released", "claim_released", terminal=False)

    def gc_orphaned_composers(self) -> None:
        now = self._now()
        doomed = [
            send_id
            for send_id, row in list(self.store.rows.items())
            if row["state"] == "composing"
            and now - float(row.get("updated_at", 0.0)) >= self.GC_ORPHAN_SECONDS
        ]
        for send_id in doomed:
            row = self.store.rows[send_id]
            delete = getattr(self.store, "delete_row", None)
            if delete is not None:
                delete(send_id)
            else:
                self.store.rows.pop(send_id)
            pane = self.store.panes.get(row["pane_id"])
            if pane is not None and pane.get("owner_send_id") == send_id:
                pane["owner_send_id"] = None
                persist = getattr(self.store, "persist_pane", None)
                if persist is not None:
                    persist(pane)
            self.store.transitions.append((send_id, row["state"], "∅"))

    def mark_superseded(self, send_id: str) -> None:
        row = self.store.rows.get(send_id)
        if row is None:
            return
        if self._terminal_row(row):
            return
        row["carrier_eligible"] = False
        self._transition(send_id, "manual_clear_required")
        row["terminal"] = True

    def race_for_pane(
        self, pane_id: str, *, carrier_send_id: str, sender_send_id: str, first: str
    ) -> list[str]:
        order = ["carrier", "sender"] if first == "carrier" else ["sender", "carrier"]
        winners: list[str] = []
        for actor in order:
            send_id = carrier_send_id if actor == "carrier" else sender_send_id
            if not winners and self._claim_pane(pane_id, send_id):
                winners.append(actor)
        return winners

    def wait_until_ready(self, pane_id: str, *, budget: float) -> SendResult:
        spent = 0.0
        consecutive = 0
        while True:
            frame, err = self._try_capture(pane_id)
            if err is not None:
                return err
            if classify_pane(frame.raw, self.profile) is PaneState.READY:
                consecutive += 1
                if consecutive >= 2:
                    return _result("ready", "ready", terminal=False)
            else:
                consecutive = 0
            if spent >= budget:
                return _result("refused", "wait_budget_exhausted", terminal=False)
            self.clock.sleep(0.5)
            spent += 0.5


# --------------------------------------------------------------------- store


@dataclass
class StoreStatus:
    status: str
    backup_verified: bool = False


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    return conn


def init_store(path: Path) -> StoreStatus:
    """Idempotent, deployment-gated store initializer (spec round-8 B2)."""

    path = Path(path)
    if path.exists():
        if path.stat().st_size:
            header = path.read_bytes()[:16]
            if not header.startswith(b"SQLite format 3"):
                raise StoreError(f"init_target_exists: {path}")
        try:
            with _connect(path) as conn:
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                tables = {
                    name for (name,) in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                if "rows" in tables:
                    present = {
                        info[1] for info in conn.execute(
                            "PRAGMA table_info(rows)"
                        ).fetchall()
                    }
                    if not set(_ROW_COLUMNS).issubset(present):
                        # Old layout: init NEVER migrates [round-4 B6].
                        raise StoreError(f"init_requires_migration: {path}")
        except sqlite3.DatabaseError as error:
            raise StoreError(f"init_target_exists: {path}") from error
        if version not in (0, SCHEMA_VERSION):
            raise StoreError(f"newer_schema: {version}")
    with _connect(path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS rows ("
            " send_id TEXT PRIMARY KEY, state TEXT NOT NULL, wire_digest TEXT,"
            " pane_id TEXT, pane_epoch INTEGER, profile TEXT, attempts INTEGER,"
            " terminal INTEGER, carrier_eligible INTEGER, baseline_ref TEXT,"
            " composer_observable TEXT, created_at REAL, last_press_at REAL,"
            " first_observed_at REAL, attempt_evidence TEXT, updated_at REAL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS panes ("
            " pane_id TEXT PRIMARY KEY, owner_send_id TEXT, epoch INTEGER)"
        )
        conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    os.chmod(path, stat_module.S_IRUSR | stat_module.S_IWUSR)
    with _connect(path) as conn:
        conn.execute("SELECT count(*) FROM rows").fetchone()
    return StoreStatus(status="store_ready")


_COLUMN_DDL = {
    "wire_digest": "TEXT", "pane_id": "TEXT", "pane_epoch": "INTEGER",
    "profile": "TEXT", "attempts": "INTEGER", "terminal": "INTEGER",
    "carrier_eligible": "INTEGER", "baseline_ref": "TEXT",
    "composer_observable": "TEXT", "created_at": "REAL", "last_press_at": "REAL",
    "first_observed_at": "REAL", "attempt_evidence": "TEXT", "updated_at": "REAL",
}


def migrate_store(path: Path, *, target_schema: int) -> StoreStatus:
    """Real DDL migration [GREEN round-3 B7]: transaction-consistent verified
    backup FIRST, then ALTER TABLE for every missing pinned column, panes table
    creation, version stamping, and a read-back verification; any failure
    restores the verified backup."""

    import shutil

    path = Path(path)
    if target_schema != SCHEMA_VERSION:
        raise StoreError(f"unsupported_target_schema: {target_schema}")
    backup = path.with_suffix(".backup.db")
    if backup.exists():
        backup.unlink()
    with _connect(path) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("VACUUM INTO ?", (str(backup),))
    with _connect(backup) as verify:
        verify.execute("SELECT count(*) FROM sqlite_master").fetchone()
    try:
        with _connect(path) as conn:
            existing_tables = {
                name for (name,) in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "rows" not in existing_tables:
                conn.execute(
                    "CREATE TABLE rows (send_id TEXT PRIMARY KEY, state TEXT NOT NULL)"
                )
            present = {
                info[1] for info in conn.execute("PRAGMA table_info(rows)").fetchall()
            }
            for column in _ROW_COLUMNS:
                if column in present:
                    continue
                ddl_type = _COLUMN_DDL.get(column, "TEXT")
                conn.execute(f"ALTER TABLE rows ADD COLUMN {column} {ddl_type}")
            # Backfill lifecycle defaults so migrated rows are USABLE [round-4 B6].
            defaults = {
                "wire_digest": "''", "pane_id": "''", "pane_epoch": "0",
                "profile": "''", "attempts": "0", "terminal": "0",
                "carrier_eligible": "0", "baseline_ref": "''",
                "composer_observable": "''", "created_at": "0", "last_press_at": "0",
                "first_observed_at": "0", "attempt_evidence": "''", "updated_at": "0",
            }
            for column, default in defaults.items():
                conn.execute(
                    f"UPDATE rows SET {column}=COALESCE({column}, {default})"
                )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS panes ("
                " pane_id TEXT PRIMARY KEY, owner_send_id TEXT, epoch INTEGER)"
            )
            conn.execute(f"PRAGMA user_version={target_schema}")
        with _connect(path) as readback:
            readback.execute(
                "SELECT " + ", ".join(_ROW_COLUMNS) + " FROM rows LIMIT 1"
            ).fetchone()
            stamped = readback.execute("PRAGMA user_version").fetchone()[0]
            if stamped != target_schema:
                raise StoreError(f"migration_stamp_failed: {stamped}")
    except Exception as error:
        shutil.copyfile(backup, path)
        for suffix in ("-wal", "-shm"):
            side = Path(str(path) + suffix)
            if side.exists():
                side.unlink()
        # Verify the RESTORE itself [round-4 B6] before reporting rollback.
        with _connect(path) as restored:
            restored.execute("SELECT count(*) FROM sqlite_master").fetchone()
        raise StoreError(f"migration_failed_rolled_back_verified: {error}") from error
    return StoreStatus(status="store_ready", backup_verified=True)


def open_store(path: Path, *, schema_version: int) -> sqlite3.Connection:
    path = Path(path)
    if not path.exists():
        raise StoreError(f"store_unavailable: {path}")
    conn = _connect(path)
    stored = conn.execute("PRAGMA user_version").fetchone()[0]
    if schema_version > stored:
        conn.close()
        raise StoreError(f"newer_schema: requested {schema_version}, stored {stored}")
    if schema_version != stored:
        conn.close()
        raise StoreError(f"store_schema_mismatch: {stored}")
    return conn


# ---------------------------------------------------------------- real store


_ROW_COLUMNS = (
    "send_id", "state", "wire_digest", "pane_id", "pane_epoch", "profile",
    "attempts", "terminal", "carrier_eligible", "baseline_ref",
    "composer_observable", "created_at", "last_press_at", "first_observed_at",
    "attempt_evidence", "updated_at",
)


class _PersistentDict(dict):
    """Row/pane dict that mirrors machine mutations; flushed via persist hooks."""


class SqliteStoreAdapter:
    """The machine-facing adapter over the real store [GREEN round-1 B2].

    Exposes the same `.rows` / `.panes` / `.transitions` surface the machine
    drives, backed by SQLite with write-through persistence: `DeliveryMachine`
    calls `persist_row` / `persist_pane` (via the hooks it already probes for)
    inside every CAS transition and claim, so durable state survives process
    boundaries — the property the carrier's 30s process lifetime requires.
    """

    fault_at: str | None = None

    def __init__(self, path: Path, *, schema_version: int = SCHEMA_VERSION) -> None:
        self._conn = open_store(Path(path), schema_version=schema_version)
        self._conn.execute("PRAGMA busy_timeout=2000")
        self.transitions: list[tuple[str, str, str]] = []
        self.rows: dict[str, dict] = {}
        self.panes: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        cursor = self._conn.execute(
            "SELECT " + ", ".join(_ROW_COLUMNS) + " FROM rows"
        )
        for values in cursor.fetchall():
            row = _PersistentDict(zip(_ROW_COLUMNS, values))
            row["terminal"] = bool(row.get("terminal"))
            row["carrier_eligible"] = bool(row.get("carrier_eligible"))
            self.rows[row["send_id"]] = row
        for pane_id, owner, epoch in self._conn.execute(
            "SELECT pane_id, owner_send_id, epoch FROM panes"
        ).fetchall():
            self.panes[pane_id] = _PersistentDict(
                pane_id=pane_id, owner_send_id=owner, epoch=epoch
            )

    def cas_row_state(self, send_id: str, old_state: str, new_state: str, row: dict) -> bool:
        """Durable state CAS [GREEN round-2 B1]: BEGIN IMMEDIATE + conditional
        UPDATE; the rowcount decides — independent stale processes cannot both
        win the same transition."""

        payload = {column: row.get(column) for column in _ROW_COLUMNS}
        payload["terminal"] = 1 if row.get("terminal") else 0
        payload["carrier_eligible"] = 1 if row.get("carrier_eligible") else 0
        payload["state"] = new_state
        payload["old_state"] = old_state
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            cursor = self._conn.execute(
                "UPDATE rows SET "
                + ", ".join(f"{column}=:{column}" for column in _ROW_COLUMNS[1:])
                + " WHERE send_id=:send_id AND state=:old_state",
                payload,
            )
            won = cursor.rowcount == 1
            if not won and old_state == "∅":
                cursor = self._conn.execute(
                    "INSERT OR IGNORE INTO rows (" + ", ".join(_ROW_COLUMNS) + ") VALUES ("
                    + ", ".join(":" + column for column in _ROW_COLUMNS) + ")",
                    payload,
                )
                won = cursor.rowcount == 1
            self._conn.execute("COMMIT" if won else "ROLLBACK")
        except sqlite3.OperationalError as error:
            try:
                self._conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            raise StoreError("store_locked") from error
        if won:
            self.rows[send_id] = row
        else:
            self._reload_row(send_id)
        return won

    def cas_pane_claim(
        self, pane_id: str, expected_epoch: int, owner: str | None,
        *, expected_owner: str | None = None,
    ) -> tuple[bool, dict | None]:
        """Durable pane-epoch CAS [GREEN round-2 B1/B3; owner-bound release per
        round-4 B3]. `owner=None` releases — and releases only the expected
        owner's claim when one is named."""

        try:
            self._conn.execute("BEGIN IMMEDIATE")
            if expected_epoch == 0:
                cursor = self._conn.execute(
                    "INSERT OR IGNORE INTO panes (pane_id, owner_send_id, epoch)"
                    " VALUES (?, ?, 1)",
                    (pane_id, owner),
                )
                won = cursor.rowcount == 1
            else:
                if owner is None:
                    if expected_owner is not None:
                        cursor = self._conn.execute(
                            "UPDATE panes SET owner_send_id=NULL, epoch=epoch+1"
                            " WHERE pane_id=? AND epoch=?"
                            " AND (owner_send_id=? OR owner_send_id IS NULL)",
                            (pane_id, expected_epoch, expected_owner),
                        )
                    else:
                        cursor = self._conn.execute(
                            "UPDATE panes SET owner_send_id=NULL, epoch=epoch+1"
                            " WHERE pane_id=? AND epoch=?",
                            (pane_id, expected_epoch),
                        )
                else:
                    cursor = self._conn.execute(
                        "UPDATE panes SET owner_send_id=?, epoch=epoch+1"
                        " WHERE pane_id=? AND epoch=?"
                        " AND (owner_send_id IS NULL OR owner_send_id=?)",
                        (owner, pane_id, expected_epoch, owner),
                    )
                won = cursor.rowcount == 1
            self._conn.execute("COMMIT" if won else "ROLLBACK")
        except sqlite3.OperationalError as error:
            try:
                self._conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            raise StoreError("store_locked") from error
        fresh = self._reload_pane(pane_id)
        return won, fresh

    def _reload_row(self, send_id: str) -> None:
        cursor = self._conn.execute(
            "SELECT " + ", ".join(_ROW_COLUMNS) + " FROM rows WHERE send_id=?", (send_id,)
        )
        values = cursor.fetchone()
        if values is not None:
            row = _PersistentDict(zip(_ROW_COLUMNS, values))
            row["terminal"] = bool(row.get("terminal"))
            row["carrier_eligible"] = bool(row.get("carrier_eligible"))
            self.rows[send_id] = row

    def _reload_pane(self, pane_id: str) -> dict | None:
        values = self._conn.execute(
            "SELECT pane_id, owner_send_id, epoch FROM panes WHERE pane_id=?", (pane_id,)
        ).fetchone()
        if values is None:
            self.panes.pop(pane_id, None)
            return None
        pane = _PersistentDict(pane_id=values[0], owner_send_id=values[1], epoch=values[2])
        self.panes[pane_id] = pane
        return pane

    def cas_update_evidence(self, send_id: str, expected_state: str, evidence: str) -> bool:
        """Durable evidence write WITHOUT a state change [round-6 B1]: state-
        conditioned, so a stale process still cannot touch a moved row."""

        try:
            self._conn.execute("BEGIN IMMEDIATE")
            cursor = self._conn.execute(
                "UPDATE rows SET attempt_evidence=? WHERE send_id=? AND state=?",
                (evidence, send_id, expected_state),
            )
            won = cursor.rowcount == 1
            self._conn.execute("COMMIT" if won else "ROLLBACK")
        except sqlite3.OperationalError as error:
            try:
                self._conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            raise StoreError("store_locked") from error
        return won

    def persist_row(self, row: dict) -> None:
        payload = {column: row.get(column) for column in _ROW_COLUMNS}
        payload["terminal"] = 1 if row.get("terminal") else 0
        payload["carrier_eligible"] = 1 if row.get("carrier_eligible") else 0
        with self._conn:
            self._conn.execute(
                "INSERT INTO rows (" + ", ".join(_ROW_COLUMNS) + ") VALUES ("
                + ", ".join(":" + column for column in _ROW_COLUMNS) + ")"
                " ON CONFLICT(send_id) DO UPDATE SET "
                + ", ".join(f"{column}=:{column}" for column in _ROW_COLUMNS[1:]),
                payload,
            )
        self.rows[row["send_id"]] = row

    def persist_pane(self, pane: dict) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO panes (pane_id, owner_send_id, epoch)"
                " VALUES (:pane_id, :owner_send_id, :epoch)"
                " ON CONFLICT(pane_id) DO UPDATE SET"
                " owner_send_id=:owner_send_id, epoch=:epoch",
                {
                    "pane_id": pane["pane_id"],
                    "owner_send_id": pane.get("owner_send_id"),
                    "epoch": int(pane.get("epoch", 0)),
                },
            )
        self.panes[pane["pane_id"]] = pane

    def delete_row(self, send_id: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM rows WHERE send_id=?", (send_id,))
        self.rows.pop(send_id, None)

    def close(self) -> None:
        self._conn.close()


# ---------------------------------------------------------- production capture


@dataclass(frozen=True)
class CapturedFrame:
    raw: str
    pane_id: str
    cursor_row: int
    cursor_col: int
    width: int
    height: int
    title: str
    current_command: str
    input_region: str
    conversation_region: str
    readable: bool = True
    frame_id: str = ""


class TmuxCapturer:
    """Composite live snapshot: escapes + cursor/geometry in one server dispatch."""

    _PROMPT_PREFIXES = ("❯", "›", ">", "codex >")

    def __init__(self, runner: Callable[..., Any] = None) -> None:
        import subprocess

        self.runner = runner or subprocess.run

    _META_FORMAT = (
        "DGMETA\t#{pane_id}\t#{cursor_y}\t#{cursor_x}\t#{pane_width}\t"
        "#{pane_height}\t#{pane_title}\t#{pane_current_command}"
    )

    def capture(self, pane_id: str) -> CapturedFrame:
        # ONE tmux server dispatch [GREEN round-2 B9]: metadata and escaped pane
        # text ride the same chained command, so a frame can never mix metadata
        # from one instant with text from another.
        combined = self.runner(
            [
                "tmux", "display-message", "-p", "-t", pane_id, self._META_FORMAT,
                ";", "capture-pane", "-e", "-p", "-t", pane_id,
            ],
            check=True, capture_output=True, text=True,
        ).stdout
        first_line, _, raw = combined.partition("\n")
        meta = first_line.strip()
        if not meta.startswith("DGMETA\t"):
            raise RuntimeError(f"pane_unreadable: bad composite header {meta[:40]!r}")
        fields = meta[len("DGMETA\t"):].split("\t")
        if len(fields) != 7:
            raise RuntimeError(f"pane_unreadable: bad metadata {meta!r}")
        resolved, cursor_row, cursor_col, width, height, title, command = fields
        input_lines: list[str] = []
        conversation_lines: list[str] = []
        seen_prompt = False
        for line in reversed(raw.splitlines()):
            stripped_line = strip_ghost(line).strip()
            if not seen_prompt and any(
                stripped_line.startswith(prefix) for prefix in self._PROMPT_PREFIXES
            ):
                input_lines.append(line)
                seen_prompt = True
                continue
            if not seen_prompt:
                input_lines.append(line)
            else:
                conversation_lines.append(line)
        return CapturedFrame(
            raw=raw,
            pane_id=resolved,
            cursor_row=int(cursor_row),
            cursor_col=int(cursor_col),
            width=int(width),
            height=int(height),
            title=title,
            current_command=command,
            input_region="\n".join(reversed(input_lines)),
            conversation_region="\n".join(reversed(conversation_lines)),
        )

    __call__ = capture


DEFAULT_STORE_PATH = Path.home() / "dg-cockpit" / "delivery.db"


def main() -> int:
    """Deployment CLI [GREEN round-2 B7]: init-store / migrate are the ONLY
    store-creating entrypoints; drivers never create or migrate."""

    import argparse

    parser = argparse.ArgumentParser(description="dg_delivery store administration")
    commands = parser.add_subparsers(dest="command", required=True)
    init_parser = commands.add_parser("init-store", help="Idempotent store initializer.")
    init_parser.add_argument("path", nargs="?", default=str(DEFAULT_STORE_PATH))
    migrate_parser = commands.add_parser("migrate", help="Verified-backup migration.")
    migrate_parser.add_argument("path", nargs="?", default=str(DEFAULT_STORE_PATH))
    migrate_parser.add_argument("--target-schema", type=int, default=SCHEMA_VERSION)
    args = parser.parse_args()
    try:
        if args.command == "init-store":
            status = init_store(Path(args.path))
        else:
            status = migrate_store(Path(args.path), target_schema=args.target_schema)
    except StoreError as error:
        print(f"error: {error}")
        return 5
    print(f"{status.status} (backup_verified={status.backup_verified})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
