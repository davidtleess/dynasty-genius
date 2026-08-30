// @vitest-environment jsdom
//
// DG-109 review panel, two BLOCKING findings on this one component. Both are
// about the boundary between "we cannot say this yet" and "there is nothing to
// say", and both were invisible to the enforcement test by construction.
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { auditRenderedCopy } from "../lib/renderRule";
import { EVIDENCE_ABSENT_SENTENCE, EvidenceSection } from "./EvidenceSection";

// biome-ignore lint/suspicious/noExplicitAny: the component's own Zod parse is the contract check; these are hand-built wire shapes.
type Wire = any;

function evidence(overrides: Record<string, unknown> = {}) {
  return {
    caveats: { caveats: [], items: [] },
    counter_argument: { caveats: [], status: "unavailable", text: null },
    risk_flags: { caveats: [], items: [] },
    top_drivers: { caveats: [], items: [] },
    ...overrides,
  } as Wire;
}

describe("EvidenceSection", () => {
  // FINDING 1. The unmapped fallback stamped `data-receipt` onto the risk bullet
  // itself, so the audit skipped exactly the node it exists to catch — and the
  // token it was hiding is the most common one in the live universe:
  // `age_past_position_cliff` is 14 of 17 driver/risk occurrences in a
  // 179-player sample, and it is on Christian McCaffrey's card today
  // (/api/players/4034 -> risk_flags.items = ["age_past_position_cliff"]).
  it("says the commonest live risk flag in body copy, not behind a receipt attribute", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});

    const { container } = render(
      <EvidenceSection
        evidence={evidence({
          risk_flags: { caveats: [], items: ["age_past_position_cliff"] },
        })}
      />,
    );

    expect(auditRenderedCopy(container)).toEqual([]);
    const bullet = screen.getByText(
      /past the age where production usually starts falling/i,
    );
    // A real risk bullet, carrying the constitutional amber treatment — which
    // still keys off the RAW token, so the sentence is free to say "decline".
    expect(bullet.className).toContain("dg-evidence__risk--age-cliff-amber");
    expect(bullet.closest("[data-receipt]")).toBeNull();
    // Nothing fell through to the raw-token receipt, and the dictionary did not
    // warn — the sentence exists rather than being humanized on the fly.
    expect(
      container.querySelector('[data-testid="untranslated-risk-flags"]'),
    ).toBeNull();
    expect(
      warn.mock.calls.filter((call) => String(call[0]).startsWith("Copy dictionary:")),
    ).toEqual([]);

    vi.restoreAllMocks();
  });

  it("routes a genuinely unmapped risk flag to the receipt line, never onto a bullet", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});

    const { container } = render(
      <EvidenceSection
        evidence={evidence({
          risk_flags: { caveats: [], items: ["some_future_flag_nobody_wrote_yet"] },
        })}
      />,
    );

    // The fact is never dropped...
    const receipt = screen.getByTestId("untranslated-risk-flags");
    expect(receipt.textContent).toContain("some_future_flag_nobody_wrote_yet");
    // ...it just lives where the raw key is allowed, and no bullet claims it.
    expect(receipt.closest("[data-receipt]")).toBeTruthy();
    expect(container.querySelector(".dg-evidence__risk")).toBeNull();
    expect(warn).toHaveBeenCalled();

    vi.restoreAllMocks();
  });

  // FINDING 2. WITHHELD IS NOT ABSENT. players.py:220-236 blanks a
  // counter-argument containing banned language and records the fact in the
  // FIELD's own caveats. Nothing read those arrays, so a fully suppressed card
  // rendered as silence — identical to a player with no evidence at all.
  it("speaks when evidence was withheld, instead of rendering silence", () => {
    const { container } = render(
      <EvidenceSection
        evidence={evidence({
          counter_argument: {
            caveats: ["evidence_suppressed_banned_term"],
            status: "experimental",
            text: null,
          },
        })}
      />,
    );

    expect(container.querySelector(".dg-evidence")).toBeTruthy();
    expect(
      screen.getByText("Some producer notes were withheld from this card."),
    ).toBeTruthy();
    expect(auditRenderedCopy(container)).toEqual([]);
  });

  // The other half of the same boundary. DG-109's rule stands — no per-field "No
  // X available" row is rendered, because absence of content is not content —
  // but DG-111 keeps the ONE sentence that stops the whole-block silence being
  // read as a clean bill of health. A card that shows a projection and no
  // evidence at all looks vetted, and it is not: an empty risk list means "we
  // have no risk notes on him", never "he has no risks". The distinction
  // DG-109 drew is intact — `counter_argument_unavailable` means none was
  // WRITTEN (absence, and the sentence says so is OURS), while
  // `evidence_suppressed_banned_term` means one was REMOVED (and speaks in its
  // own words, asserted in the test above).
  it("says an all-empty block is our gap, and never reads as a clean bill of health", () => {
    const { container } = render(
      <EvidenceSection
        evidence={evidence({
          counter_argument: {
            caveats: ["counter_argument_unavailable"],
            status: "experimental",
            text: null,
          },
        })}
      />,
    );

    // No "No counter-argument available" / "No risk flags available" rows.
    expect(screen.queryByText(/^No .* available$/i)).toBeNull();
    expect(container.querySelectorAll("li")).toHaveLength(0);
    // One sentence, and it locates the absence in OUR notes, not in the player.
    expect(screen.getByText(EVIDENCE_ABSENT_SENTENCE)).toBeTruthy();
    expect(EVIDENCE_ABSENT_SENTENCE).toMatch(/not that there is nothing to say/i);
    expect(auditRenderedCopy(container)).toEqual([]);
  });
});
