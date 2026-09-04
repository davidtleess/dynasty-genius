// @vitest-environment jsdom

// DG-158 — the morning the denominators change, every compared score moves by
// exactly its position's factor and no player has changed. The producer refuses
// the per-player list; these pin what the page then says, and — more importantly
// — what it must NOT say.
import { describe, expect, it } from "vitest";

import { describeToken, SCALE_CHANGED_MASTHEAD } from "../lib/copy";

const SECTION = describeToken("model_uniform_factor_per_position");

describe("DG-158 a change of units is announced, not disguised", () => {
  it("says out loud that it is NOT comparing", () => {
    // A suppressed section that does not say it is suppressed is how a refusal
    // reads as a quiet morning — the failure family this whole day catalogued.
    expect(SECTION).toMatch(/not comparing/i);
  });

  it("never claims nobody moved, on the page or in the section", () => {
    // The claim we cannot support: real movement may have happened that morning
    // and this SUPPRESSES it rather than observing its absence. A player who
    // genuinely fell is not covered by anything here, and saying otherwise would
    // be false in the exact direction that costs David a decision.
    for (const text of [SECTION, SCALE_CHANGED_MASTHEAD]) {
      expect(text).not.toMatch(/nobody moved|no player moved|no one moved/i);
      expect(text).not.toMatch(/held steady|nothing moved|quiet/i);
      expect(text).not.toMatch(/\bup or down\b/i);
    }
  });

  it("names no cause the payload cannot carry", () => {
    for (const text of [SECTION, SCALE_CHANGED_MASTHEAD]) {
      expect(text).not.toMatch(/rebuilt|model run|retrain|rescale/i);
    }
  });

  it("tells the reader from the masthead that comparison is paused", () => {
    // So a suppressed section cannot be read as a quiet morning from the top of
    // the page, without opening anything.
    expect(SCALE_CHANGED_MASTHEAD).toMatch(/new scale/i);
    expect(SCALE_CHANGED_MASTHEAD).toMatch(/paused/i);
  });

  it("keeps the masthead line short enough to sit beside the freshness sentence", () => {
    expect(SCALE_CHANGED_MASTHEAD.length).toBeLessThanOrEqual(100);
  });
});
