"""Wire-health profile-registry refresh — regression rows (David-worded 2026-07-19).

Pins the three repairs that restore stamped-crew auto-delivery on the current
CLI chrome, with fixtures taken from LIVE pane captures (ledger 2026-07-19):

1. ``strip_ghost`` extended-color law: truecolor/palette SGR introducer
   arguments (``38;2;R;G;B`` / ``48;2;...`` / ``38;5;N``) are consumed, never
   interpreted — the embedded ``2`` is a color mode, not SGR-dim. The naive
   per-code read placeheld every glyph after a truecolor background and
   swallowed the new Codex chrome's ``› `` ready marker.
2. ``classify_pane`` dialog detection is tail-scoped with the bare-"?"
   alternate removed: numbered lists in conversation history and Gemini's
   permanent ``? for shortcuts`` footer held every send as dialog forever.
   Real dialogs (bottom-rendered option rows) still classify DIALOG.
3. The Gemini (agy) registry entry gains the line-anchored bare-composer
   marker (``\\n>\\n``) evidenced by the live bordered-composer chrome.

The rails are unchanged and re-pinned here: UNKNOWN remains fail-closed and
dialogs are never READY.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import dg_delivery as d  # noqa: E402

GHOST = d.GHOST_PLACEHOLDER

# Live-captured new-Codex composer line (ledger 2026-07-19): bold prompt,
# truecolor background, DIM suggestion text.
CODEX_COMPOSER = (
    "\x1b[1m›\x1b[0m\x1b[48;2;55;55;55m "
    "\x1b[2mRun /review on my current changes\x1b[0m\x1b[48;2;55;55;55m"
)
CODEX_FOOTER = (
    "\x1b[49m  \x1b[38;2;241;189;69mgpt-5.6-sol high\x1b[2m\x1b[39m · "
    "\x1b[0m\x1b[38;2;182;184;58m~/dynasty-genius-product\x1b[39m"
)
CODEX_READY_PANE = "\n".join(
    ["  Verdict ledgered. No CLEAR issued.", "", CODEX_COMPOSER, "", CODEX_FOOTER]
)

GEMINI_READY_PANE = "\n".join(
    [
        "  Standing by for telemetry requests.",
        "\x1b[38;5;23m" + "─" * 40,
        "\x1b[38;5;32m>\x1b[39m",
        "\x1b[38;5;23m" + "─" * 40,
        "\x1b[38;5;246m? for shortcuts\x1b[39m    \x1b[38;5;246mGemini 3.5 Flash (High)",
    ]
)


def _codex():
    return d.PaneProfile.for_cli("codex")


def _gemini():
    return d.PaneProfile.for_cli("gemini")


# --- 1. strip_ghost extended-color law ---------------------------------------
def test_truecolor_background_is_not_dim():
    stripped = d.strip_ghost(CODEX_COMPOSER)
    # The non-dim prompt+space survive; ONLY the dim suggestion placeholds.
    assert stripped.startswith("› ")
    assert GHOST in stripped
    assert "Run /review" not in stripped
def test_truecolor_foreground_is_not_dim():
    stripped = d.strip_ghost(CODEX_FOOTER)
    assert "gpt-5.6-sol high" in stripped
def test_palette_index_two_is_not_dim():
    # 38;5;2 = palette green — the trailing 2 is an index, never dim.
    assert d.strip_ghost("\x1b[38;5;2mgreen\x1b[39m ok") == "green ok"
def test_real_dim_still_placeholds():
    assert d.strip_ghost("a \x1b[2mghost\x1b[0m b") == f"a {GHOST} b"
def test_dim_inside_and_after_truecolor_still_placeholds():
    line = "\x1b[48;2;9;9;9mplain \x1b[2mdim\x1b[22m tail"
    assert d.strip_ghost(line) == f"plain {GHOST} tail"
# --- 2. tail-scoped dialog detection -----------------------------------------
def test_numbered_conversation_list_plus_footer_is_not_dialog():
    pane = "\n".join(
        [
            "  1. first finding",
            "  2. second finding",
            "  discussion of the findings continues here",
            "  more conversation",
            "  and more context lines",
            "  final prose line",
            "  closing remark",
            "  one more remark",
            "  yet another remark",
            "─" * 40,
            ">",
            "─" * 40,
            "? for shortcuts    Gemini 3.5 Flash (High)",
        ]
    )
    assert d.classify_pane(pane, _gemini()) is d.PaneState.READY
def test_bottom_rendered_option_rows_still_classify_dialog():
    # Lawfully narrowed by round-4 B4 (ledgered): selection glyphs are
    # per-profile live evidence — codex classifies DIALOG; gemini (no live
    # dialog capture yet) holds fail-closed, pinned in the r4_b4 row.
    pane = "\n".join(
        [
            "  Allow this command?",
            "❯ 1. Yes, allow once",
            "  2. No, deny",
        ]
    )
    assert d.classify_pane(pane, _codex()) is d.PaneState.DIALOG
def test_single_option_with_press_enter_still_classifies_dialog():
    pane = "\n".join(["  1. Continue", "  Press enter to confirm"])
    assert d.classify_pane(pane, _codex()) is d.PaneState.DIALOG
def test_unmatched_chrome_remains_fail_closed_unknown():
    assert (
        d.classify_pane("some totally novel chrome", _codex())
        is d.PaneState.UNKNOWN
    )
# --- 3. live-chrome READY fixtures --------------------------------------------
def test_new_codex_chrome_classifies_ready():
    assert d.classify_pane(CODEX_READY_PANE, _codex()) is d.PaneState.READY
def test_new_gemini_chrome_classifies_ready():
    assert d.classify_pane(GEMINI_READY_PANE, _gemini()) is d.PaneState.READY
def test_bare_gt_in_prose_does_not_ready_gemini():
    pane = "  the operator wrote a > b in the reply\n  still working on it"
    assert d.classify_pane(pane, _gemini()) is d.PaneState.UNKNOWN
# --- 4. chrome-aware emptiness (the input_not_empty live finding) ------------
CODEX_EMPTY_INPUT_REGION = "\n".join([CODEX_COMPOSER, "", CODEX_FOOTER])


def test_real_text_on_the_prompt_line_reads_non_empty():
    region = "\n".join(["› From Claude (implementing agent) — request", CODEX_FOOTER])
    assert not d._visible_empty(region, _codex())
def test_multi_line_pasted_body_reads_non_empty():
    region = "\n".join(["› From Claude — request", "second body line", CODEX_FOOTER])
    assert not d._visible_empty(region, _codex())
def test_footer_without_any_prompt_line_stays_fail_closed():
    # No prompt line anywhere: the footer skip may not apply — unrecognized
    # trailing text counts as input and the send refuses.
    region = "\n".join(["─" * 40, "? for shortcuts    Gemini 3.5 Flash (High)"])
    assert not d._visible_empty(region, _gemini())
def test_gemini_typed_text_on_prompt_line_reads_non_empty():
    region = "\n".join(["─" * 40, "> real typed text", "─" * 40,
                        "? for shortcuts    Gemini 3.5 Flash (High)"])
    assert not d._visible_empty(region, _gemini())
# --- 5. round-1 findings (Codex wire review) ---------------------------------
def test_b1_arbitrary_final_line_is_input_not_footer():
    # Codex round-1 B1 schedules: manual continuation under an empty prompt
    # is INPUT; only a positively recognized footer skips.
    assert not d._visible_empty("› \nmanual continuation", _codex())
    assert not d._visible_empty(">\nmanual continuation", _gemini())
def test_b1_no_profile_means_no_footer_skip():
    assert not d._visible_empty(
        "› \n  gpt-5.6-sol high · ~/dynasty-genius-product")
def test_b2_selected_option_with_dim_sibling_is_dialog_never_ready():
    # Codex round-1 B2 fixture: selected row visible, unselected sibling dim.
    pane = "\n".join(
        [
            "  Allow this action?",
            "\x1b[1m› 1. Yes, allow once\x1b[0m",
            "\x1b[2m  2. No, deny\x1b[0m",
        ]
    )
    assert d.classify_pane(pane, _codex()) is d.PaneState.DIALOG
def test_b2_option_rows_never_supply_ready_markers():
    pane = "❯ 1. Yes, allow once"
    assert d.classify_pane(pane, _claude()) is not d.PaneState.READY
    assert d.classify_pane(pane, _codex()) is not d.PaneState.READY
def test_h1_empty_sgr_parameters_are_reset():
    # ESC[;m = double reset; ESC[2;m = dim then reset — nothing ghosts.
    assert d.strip_ghost("\x1b[;mplain") == "plain"
    assert d.strip_ghost("\x1b[2;mplain") == "plain"
def test_h1_colon_form_extended_color_is_consumed():
    assert d.strip_ghost("\x1b[38:2::1:2:3mcolored\x1b[0m text") == "colored text"
    # ...and a REAL dim after a colon-form color still ghosts.
    out = d.strip_ghost("\x1b[38:2::1:2:3mplain \x1b[2mdim\x1b[0m tail")
    assert out == f"plain {d.GHOST_PLACEHOLDER} tail"
def test_claude_nbsp_prompt_classifies_ready():
    pane = "─" * 30 + "\n\x1b[38;5;246m❯ \x1b[39m\n" + "─" * 30
    assert d.classify_pane(pane, _claude()) is d.PaneState.READY
def _claude():
    return d.PaneProfile.for_cli("claude")


# --- 6. round-2 findings (Codex wire review) ---------------------------------
def test_r2_b1_numbered_history_in_tail_with_normal_composer_is_ready():
    # Codex's exact round-2 schedule: one recent numbered conversation row
    # inside the 8-line tail + the normal dim-suggestion composer must be
    # READY — the composer ghost is NOT adjacent to the option row.
    pane = "\n".join(
        [
            "  1. First completed check",
            "  prose line between",
            CODEX_COMPOSER,
            "",
            CODEX_FOOTER,
        ]
    )
    assert d.classify_pane(pane, _codex()) is d.PaneState.READY
def test_r2_b1_ghost_adjacent_to_option_row_is_still_dialog():
    pane = "\n".join(
        [
            "  Allow this action?",
            "\x1b[1m› 1. Yes, allow once\x1b[0m",
            "\x1b[2m  2. No, deny\x1b[0m",
        ]
    )
    assert d.classify_pane(pane, _codex()) is d.PaneState.DIALOG


@pytest.mark.parametrize(
    "profile_name,region",
    [
        ("codex", "› \nrelease high /tmp/manual-note"),
        ("claude", "❯ \n⏵ manual input"),
        ("gemini", "─────\n>\n─────\n? for shortcuts please"),
    ],
)
def test_r2_b2_footer_like_manual_text_reads_non_empty(profile_name, region):
    profile = d.PaneProfile.for_cli(profile_name)
    assert not d._visible_empty(region, profile)
def test_r2_b3_border_prefixed_option_rows_classify_dialog_never_ready():
    pane = "\n".join(
        [
            "╭──────────────────────────╮",
            "│  Allow this command?     │",
            "│ › 1. Yes, allow once     │",
            "│   2. No, deny            │",
            "╰──────────────────────────╯",
        ]
    )
    assert d.classify_pane(pane, _codex()) is d.PaneState.DIALOG
def test_r2_b3_bordered_single_selected_row_never_supplies_ready():
    pane = "│ › 1. Yes, allow once"
    assert d.classify_pane(pane, _codex()) is not d.PaneState.READY
# --- 7. round-4 STRUCTURAL contract (David-worded) ----------------------------
def test_footer_text_is_input_at_the_emptiness_layer():
    # Text-pattern footer recognition is RETIRED from _visible_empty: any
    # line reaching it counts as input — exclusion happens structurally
    # upstream (split_regions), and only there.
    region = "\n".join(["› ", "  gpt-5.6-sol high · ~/dynasty-genius-product"])
    assert not d._visible_empty(region, _codex())
# --- 8. round-4 findings (Codex wire review; David's structural word) --------
def test_r4_b4_markdown_quote_is_never_a_selection_glyph():
    # Codex's exact schedule: "> 1. First completed item" beside the normal
    # composer is conversation, not a dialog.
    pane = "\n".join(["> 1. First completed item", CODEX_COMPOSER, "",
                     CODEX_FOOTER])
    assert d.classify_pane(pane, _codex()) is d.PaneState.READY
def test_r4_b4_press_enter_must_bind_to_the_option_group():
    # Codex's exact schedule: prose mentioning Press enter far from the
    # numbered row is not dialog structure.
    pane = "\n".join(["  1. First completed item", "  prose line", "  more",
                     "  Press enter in your terminal when ready",
                     CODEX_COMPOSER, "", CODEX_FOOTER])
    assert d.classify_pane(pane, _codex()) is d.PaneState.READY
    bound = "\n".join(["  1. Continue", "  Press enter to confirm"])
    assert d.classify_pane(bound, _codex()) is d.PaneState.DIALOG
def test_r4_b4_gemini_selection_awaits_live_evidence():
    # No live Gemini dialog capture exists: no glyphs registered — the
    # highlighted-shape pane holds fail-closed (UNKNOWN) for gemini while
    # codex (live-evidenced glyphs) classifies DIALOG.
    pane = "\n".join(["  Allow this command?", "❯ 1. Yes, allow once",
                     "  2. No, deny"])
    assert d.classify_pane(pane, _codex()) is d.PaneState.DIALOG
    assert d.classify_pane(pane, _gemini()) is d.PaneState.UNKNOWN
def test_r4_b1_seven_field_metadata_refuses_pane_unreadable():
    def fake_run(command, **kwargs):
        meta = "DGMETA\t%7\t1\t2\t120\t40\tCodex pane\tcodex"
        return type("Completed", (), {"returncode": 0,
                                      "stdout": meta + "\ncodex > \n",
                                      "stderr": ""})()
    capturer = d.TmuxCapturer(runner=fake_run)
    try:
        capturer.capture("%7")
    except RuntimeError as err:
        assert "pane_unreadable" in str(err)
    else:
        raise AssertionError("short metadata must refuse")
def test_r4_h1_prebound_mismatched_carrier_capturer_is_refused():
    import dg_mail_carrier as carrier

    class _Store:
        rows = {}
        panes = {}

    prebound = d.TmuxCapturer(runner=lambda *a, **k: None,
                              profile=d.PaneProfile.for_cli("codex"))
    result = carrier.run_once(
        runner=lambda *a, **k: None,
        capturer=prebound,
        store=_Store(),
        panes={"%1": "claude"},
        enable_marker=__file__,  # exists -> carrier not disabled
    )
    assert result.reason == "capturer_profile_mismatch"
# --- 9. round-5 findings (Codex; David's rounds-until-CLEAR) -----------------
def test_r5_b3_gemini_unhighlighted_group_plus_composer_never_ready():
    # Codex's exact schedule: an ambiguous bottom option group co-rendered
    # with the ordinary composer must NOT classify READY for a profile with
    # no live dialog evidence.
    pane = "\n".join(["  Allow this action?", "  1. Yes", "  2. No",
                     "─" * 40, ">", "─" * 40, "? for shortcuts    Gemini"])
    assert d.classify_pane(pane, _gemini()) is not d.PaneState.READY
def test_r5_h1_press_enter_beside_lone_numbered_reply_is_ready():
    # Codex's minimal collision: "1. Save the file" then "Press enter in
    # your terminal" beside a normal composer is conversation, not dialog.
    pane = "\n".join(["  1. Save the file",
                     "  Press enter in your terminal when ready",
                     CODEX_COMPOSER, "", CODEX_FOOTER])
    assert d.classify_pane(pane, _codex()) is d.PaneState.READY
def test_r5_h2_lone_numbered_history_refuses_no_dialog_present():
    import types
    # Drive approve directly with a minimal machine over a READY history pane.
    raw = "\n".join(["  1. First completed check", CODEX_COMPOSER, "",
                    CODEX_FOOTER])

    class _Store:
        rows: dict = {}
        panes: dict = {}

    class _Cap:
        profile = d.PaneProfile.for_cli("codex")
        runner = staticmethod(lambda *a, **k: None)

        def capture(self, pane_id):
            return types.SimpleNamespace(
                raw=raw, pane_id=pane_id, input_region="", conversation_region=raw,
                current_command="codex", current_path="/tmp")

    machine = d.DeliveryMachine(
        runner=lambda *a, **k: None, capturer=_Cap(),
        clock=None, store=_Store(), profile=d.PaneProfile.for_cli("codex"))
    result = machine.approve("%1", option_text="First completed check")
    assert result.reason == "no_dialog_present"
def test_r5_h3_runnerless_profile_bearing_capturer_is_guarded():
    import dg_mail_carrier as carrier

    class _Store:
        rows: dict = {}
        panes: dict = {}

    class _RunnerlessCap:
        # profile-bearing, NO public runner attribute
        profile = d.PaneProfile.for_cli("codex")

        def capture(self, pane_id):
            raise AssertionError("must be refused before capture")

    result = carrier.run_once(
        runner=lambda *a, **k: None,
        capturer=_RunnerlessCap(),
        store=_Store(),
        panes={"%1": "claude"},
        enable_marker=__file__,
    )
    assert result.reason == "capturer_profile_mismatch"


# --- 10. round-6 CURSOR-GEOMETRY region contract (David-decided pivot) --------
# Region extraction is now by cursor row: input = prompt-anchor..cursor row;
# every line strictly BELOW the cursor is chrome, regardless of profile. This
# is evidence ordinary input cannot forge and closes the recurring B1/B2 class.

def test_cursor_geometry_codex_footer_below_cursor_is_chrome():
    # Live-shaped Codex frame: composer at the cursor row, footer 2 below.
    raw = "\n".join(["  history line", "› ", "", "  gpt-5.6-sol high · ~/repo", ""])
    inp, conv = d.split_regions(raw, _codex(), 1)  # cursor on the "› " line
    assert "gpt-5.6-sol" not in inp
    assert d._visible_empty(inp, _codex())
    assert "history line" in conv


def test_cursor_geometry_footer_shaped_input_at_cursor_survives():
    # The recurring B1 killer: footer-shaped text the USER typed sits ON the
    # composer line (at the cursor), so it is input — never dropped.
    for typed in ("release high /work/repo", "notes medium · /work/repo",
                  "cd /work/repo", "/work/repo"):
        raw = "\n".join(["› " + typed, "", "  gpt-5.6-sol high · /work/repo"])
        inp, _ = d.split_regions(raw, _codex(), 0)  # cursor on the typed line
        assert typed.split("/")[-1] in inp
        assert not d._visible_empty(inp, _codex())


def test_cursor_geometry_bordered_box_below_cursor_is_chrome():
    # Gemini/Claude: bottom border + footer render below the cursor.
    raw = "\n".join(["  conversation", "─" * 40, ">", "─" * 40,
                     "? for shortcuts    Gemini"])
    inp, conv = d.split_regions(raw, _gemini(), 2)  # cursor on the ">" line
    assert "shortcuts" not in inp
    assert d._visible_empty(inp, _gemini())
    assert "conversation" in conv


def test_cursor_geometry_multiline_input_above_cursor_survives():
    # Multiline paste: cursor at end of input; all input lines at/above it
    # survive, chrome below drops.
    raw = "\n".join(["─" * 40, "> first line", "second line", "third line",
                     "─" * 40, "? for shortcuts    Gemini"])
    inp, _ = d.split_regions(raw, _gemini(), 3)  # cursor on "third line"
    assert "second line" in inp and "third line" in inp
    assert not d._visible_empty(inp, _gemini())


def test_cursor_geometry_no_metadata_is_held_fail_closed():
    # Without cursor metadata, NOTHING is excluded — the footer counts as
    # input and the send holds (never a swallow).
    raw = "\n".join(["› ", "", "  gpt-5.6-sol high · /work/repo"])
    inp, _ = d.split_regions(raw, _codex(), None)
    assert "gpt-5.6-sol" in inp
    assert not d._visible_empty(inp, _codex())


def test_cursor_geometry_interior_rule_never_swallows_below_cursor():
    # Round-6 B2 killer: an interior rule can't act as a closing border,
    # because the boundary is the cursor, not a guessed border line.
    raw = "\n".join(["─" * 40, "> ", "─" * 32, "manual continuation"])
    # cursor on the "> " prompt line (row 1); the continuation is BELOW the
    # cursor here -> it would be chrome. But a user typing "manual
    # continuation" would have the cursor ON that line:
    inp_typed, _ = d.split_regions(raw, _gemini(), 3)  # cursor on continuation
    assert "manual continuation" in inp_typed
    assert not d._visible_empty(inp_typed, _gemini())
