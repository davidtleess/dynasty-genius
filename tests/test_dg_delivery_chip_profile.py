"""WIRE-CHIP-1 — Codex pane chip recognition (David-authorised 2026-07-26, TW26F).

The codex profile declared `chip: False` while the live Codex build collapses a long
paste into `[Pasted Content <N> chars]`. The composed-body check therefore compared a
chip against the full wire body, refused `wire_body_mismatch`, and left the pane in the
terminal `manual_clear_required` state — jamming every later send with `pane_claim_lost`.
Observed live twice on 2026-07-26.

This is NOT the one-line flag it was first reported as: `_CHIP_RE` only matches Claude's
`[Pasted text #N +M lines]` (a LINE count). Codex advertises CHARACTERS, so recognition
needs its own pattern and its own verification predicate.

SCOPE, deliberate: `chip_chars` governs BODY VERIFICATION only. `chip_collapsing` is left
False for codex so the carrier's orphan-adoption semantics do not move under an
authorisation scoped to a delivery defect — enabling it flipped two ratified carrier
contract rows. Named residual, disclosed not fixed: if the mail carrier is ever ARMED,
codex strand adoption must be revisited, because a collapsed strand cannot be read and
therefore cannot be proven to belong to its sender. The carrier remains paused/unarmed
and this change arms nothing.
"""

import importlib.util
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "dgd", Path(__file__).resolve().parents[1] / "scripts" / "dg_delivery.py")
dgd = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = dgd
_SPEC.loader.exec_module(dgd)


class _Frame:
    def __init__(self, input_region):
        self.input_region = input_region


class _Matcher:
    """Minimal carrier for the unbound `_composed_matches` under a chosen profile."""

    def __init__(self, profile):
        self.profile = profile

    def match(self, visible, wire_body, expected_lines=None):
        return dgd.DeliveryMachine._composed_matches(
            self, _Frame(visible), wire_body, expected_lines=expected_lines)


CODEX = dgd.PaneProfile.for_cli("codex")
CLAUDE = dgd.PaneProfile.for_cli("claude")


def test_codex_profile_recognises_a_chars_chip_without_moving_carrier_semantics():
    assert CODEX.chip_collapsing is False  # carrier orphan semantics deliberately untouched
    assert CODEX.chip_chars is True


def test_claude_profile_is_untouched():
    """Regression guard: the Claude path must not shift under this fix."""
    assert CLAUDE.chip_collapsing is True
    assert CLAUDE.chip_chars is False


def test_chars_chip_pattern_matches_the_live_codex_chrome():
    m = dgd._CHIP_CHARS_RE.search("› [Pasted Content 7265 chars]")
    assert m and m.group(1) == "7265"
    assert dgd._CHIP_CHARS_RE.search("[Pasted Content 1 char]")


def test_chars_chip_pattern_does_not_match_the_claude_chip():
    assert dgd._CHIP_CHARS_RE.search("[Pasted text #3 +42 lines]") is None
    assert dgd._CHIP_RE.search("[Pasted Content 7265 chars]") is None


def test_codex_chip_verifies_against_the_stamped_body_length():
    """The real 2026-07-26 failure, reproduced exactly.

    The pane advertised 7265 chars; the raw file was 7250 chars; the 15-char
    ` [send_id]` stamp accounts for the difference. Verification must compare against
    the STAMPED wire body, which is what was actually pasted."""
    raw = "From Claude Code — review request\nbody line\n"
    wire = dgd.stamp_wire_body(raw, send_id="w#7bt0fwg2-1")
    assert len(wire) == len(raw) + len(" [w#7bt0fwg2-1]")
    visible = f"› [Pasted Content {len(wire)} chars]"
    assert _Matcher(CODEX).match(visible, wire) is True


def test_codex_chip_with_a_wrong_count_fails_closed():
    """A length that does not match must NOT be accepted. Fail closed, never guess."""
    wire = dgd.stamp_wire_body("subject\nbody\n", send_id="w#7bt0fwg2-1")
    visible = f"› [Pasted Content {len(wire) + 1} chars]"
    assert _Matcher(CODEX).match(visible, wire) == "input_not_verifiable"


def test_codex_uncollapsed_body_still_compares_literally():
    """A short paste is not collapsed; the literal comparison path must still work."""
    wire = dgd.stamp_wire_body("subject\nbody\n", send_id="w#7bt0fwg2-1")
    assert _Matcher(CODEX).match(wire, wire) is True
    assert _Matcher(CODEX).match("something else entirely", wire) == "wire_body_mismatch"


def test_codex_empty_input_is_not_verifiable():
    wire = dgd.stamp_wire_body("subject\nbody\n", send_id="w#7bt0fwg2-1")
    assert _Matcher(CODEX).match("", wire) == "input_not_verifiable"


def test_claude_line_chip_semantics_preserved():
    """Claude's line-count branch keeps its exact prior behaviour."""
    wire = dgd.stamp_wire_body("subject\nbody\n", send_id="w#7bt0fwg2-1")
    assert _Matcher(CLAUDE).match("[Pasted text #1 +2 lines]", wire, expected_lines=3) is True
    assert _Matcher(CLAUDE).match(
        "[Pasted text #1 +2 lines]", wire, expected_lines=9) == "input_not_verifiable"


def test_a_chars_chip_on_a_lines_profile_is_not_silently_accepted():
    """Cross-unit safety: Claude must not accept a chars chip as verification."""
    wire = dgd.stamp_wire_body("subject\nbody\n", send_id="w#7bt0fwg2-1")
    out = _Matcher(CLAUDE).match(f"[Pasted Content {len(wire)} chars]", wire,
                                 expected_lines=3)
    assert out == "input_not_verifiable"


# --------------------------------------------------------------- the SECOND comparison
#
# Live proof that patching `_composed_matches` alone was incomplete: with a correct chip
# (2142-char body + 15-char stamp = the advertised 2157) the send STILL refused
# `wire_body_mismatch`, because `_submit_with_retry`'s pre-key guard — and two retry
# paths — compare the input region to the wire body LITERALLY and never consult the chip.


class _Cap:
    def __init__(self, *frames):
        self.frames = list(frames)

    def capture(self, pane_id):
        return self.frames.pop(0) if len(self.frames) > 1 else self.frames[0]

    __call__ = capture


class _Runner:
    def __init__(self):
        self.calls = []

    def __call__(self, command, *, input=None, **_):
        self.calls.append(list(command))
        return type("C", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    @property
    def key_calls(self):
        return [c for c in self.calls if "send-keys" in c]


def test_observed_body_predicate_accepts_a_correct_chars_chip():
    machine = _Matcher(CODEX)
    wire = dgd.stamp_wire_body("subject\nbody\n", send_id="w#7bt0fwg2-1")
    assert dgd.DeliveryMachine._observed_matches_body(
        machine, f"› [Pasted Content {len(wire)} chars]", wire) is True
    assert dgd.DeliveryMachine._observed_matches_body(
        machine, f"› [Pasted Content {len(wire) + 1} chars]", wire) is False
    assert dgd.DeliveryMachine._observed_matches_body(machine, wire, wire) is True


def test_observed_body_predicate_is_literal_for_a_non_chars_profile():
    machine = _Matcher(CLAUDE)
    wire = dgd.stamp_wire_body("subject\nbody\n", send_id="w#7bt0fwg2-1")
    assert dgd.DeliveryMachine._observed_matches_body(machine, wire, wire) is True
    assert dgd.DeliveryMachine._observed_matches_body(
        machine, f"[Pasted Content {len(wire)} chars]", wire) is False


def test_chip_recognition_is_anchored_to_the_whole_composer():
    """Codex r3 Thread B: `_CHIP_CHARS_RE.search` accepted a chip-shaped SUBSTRING inside
    arbitrary prose, so a composer holding the wrong text plus a matching-count chip
    fragment verified True. Count equality is bounded evidence only when the entire
    normalized composer IS the chip."""
    machine = _Matcher(CODEX)
    wire = dgd.stamp_wire_body("subject\nbody\n", send_id="w#7bt0fwg2-1")
    n = len(wire)
    for bad in (f"totally different text [Pasted Content {n} chars] more junk",
                f"human typing [Pasted Content {n} chars]",
                f"[Pasted Content {n} chars] trailing prose"):
        assert dgd.DeliveryMachine._observed_matches_body(machine, bad, wire) is False, bad
    # The real live shapes must still verify.
    for good in (f"[Pasted Content {n} chars]",
                 f"› [Pasted Content {n} chars]",
                 f"  › [Pasted Content {n} chars]  \n"):
        assert dgd.DeliveryMachine._observed_matches_body(machine, good, wire) is True, good


def test_anchored_chip_also_governs_the_composed_check():
    machine = _Matcher(CODEX)
    wire = dgd.stamp_wire_body("subject\nbody\n", send_id="w#7bt0fwg2-1")
    n = len(wire)
    assert machine.match(f"junk [Pasted Content {n} chars] junk", wire) != True  # noqa: E712
    assert machine.match(f"› [Pasted Content {n} chars]", wire) is True


def test_r4_recognizer_admits_only_evidenced_codex_chrome():
    """Codex r4 HIGH (`dg_delivery.py:76`): the prefix class allowed arbitrary `>`, `|`
    and `\\s` INCLUDING newline, so chip-shaped Markdown/table prose satisfied the
    pre-key and retry body checks.

    ASCII `>` is explicitly rejected as a selection glyph elsewhere in this same profile
    registry because it collides with Markdown quoting, and `|` is not a registered Codex
    prompt glyph — so admitting them here reintroduced a hazard the registry had already
    removed. The only evidenced live shapes are an empty prefix and `›`."""
    machine = _Matcher(CODEX)
    wire = "subject\nbody\n [w#7bt0fwg2-1]"
    assert len(wire) == 28
    for prose in ("> |\n[Pasted Content 28 chars]",
                  "|[Pasted Content 28 chars]",
                  ">[Pasted Content 28 chars]",
                  "> quoted markdown\n[Pasted Content 28 chars]",
                  "[Pasted Content 28 chars]\nsecond line of prose"):
        assert dgd.DeliveryMachine._observed_matches_body(machine, prose, wire) is False, prose
    for live in ("[Pasted Content 28 chars]", "› [Pasted Content 28 chars]",
                 "  › [Pasted Content 28 chars]  "):
        assert dgd.DeliveryMachine._observed_matches_body(machine, live, wire) is True, live
