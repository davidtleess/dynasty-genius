// @vitest-environment jsdom
//
// DG-119 — the trade partners view has to answer WHO TO CALL AND WHY.
//
// Measured on the live product at 1440 before this ticket: 6,401px of page for
// eleven partners, each a flat ~90px stack of label-over-value pairs with no
// card frame, a raw three-decimal `2.091` with no scale, five naked 0-1
// decimals, and THE SAME CAVEAT SENTENCE ON ALL ELEVEN CARDS.
//
// THE HONESTY LAW THIS FILE ENFORCES. Removing ten repetitions of one sentence
// removes furniture; removing the FACT would be a defect. So the caveat is
// asserted to render exactly once — not zero times — and every number the old
// stack printed is asserted to survive in the receipt layer.
//
// AND THE ZERO THAT IS NOT A MEASUREMENT. `activity_recency_score` is the
// literal `0.0` on league_opportunity_map.py:185. It is never computed from
// anything: there is no trade-activity input in this pipeline. Rendering it as
// "How recently they've traded — 0.00" tells a manager these teams have not
// traded recently, which is a claim about the league that nobody measured. The
// last test in this file is the graduation RED that couples the copy to that
// producer line, the same way PostureBasis mirrors POSTURE_SIGNAL_WEIGHTS:
// wire the component up and this test fails until the sentence is rewritten.
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PartnerRankings } from "./PartnerRankings";

// Producer-realistic rows, copied from the shape the live API returned on
// 2026-08-30 (GET /api/league/pulse). Every value here is one the producer can
// actually emit: activity is the hardcoded zero, posture alignment comes out of
// the {0, 0.05, 0.10, 0.15, 0.25} table, and both other parts are clamped 0-1.
function partner(overrides) {
  return {
    counterparty_roster_id: 7,
    counterparty_team_name: "YippeKiYay MarshalFaulker",
    caveats: ["partner_score_market_influenced"],
    decision_supported: false,
    market_influenced: true,
    matched_positions: ["RB", "WR"],
    partner_score: 2.091,
    score_components: {
      activity_recency_score: 0.0,
      complementarity_score: 0.841,
      divergence_density_score: 1.0,
      posture_alignment_score: 0.25,
    },
    evidence: {
      counterparty_posture: "CONTENDER",
      divergence_row_count: 5,
      perspective_posture: "REBUILDING",
      position_scores: { RB: 0.554, WR: 0.841 },
    },
    ...overrides,
  };
}

/** The eleven rows the live league actually returned, in producer order. */
const LIVE_ELEVEN = [
  partner({}),
  partner({
    counterparty_roster_id: 4,
    counterparty_team_name: "Free Kelly",
    matched_positions: ["QB", "WR"],
    partner_score: 1.936,
    score_components: {
      activity_recency_score: 0.0,
      complementarity_score: 0.686,
      divergence_density_score: 1.0,
      posture_alignment_score: 0.25,
    },
    evidence: {
      counterparty_posture: "CONTENDER",
      divergence_row_count: 11,
      perspective_posture: "REBUILDING",
      position_scores: { QB: 0.686, WR: 0.55 },
    },
  }),
  partner({
    counterparty_roster_id: 3,
    counterparty_team_name: "MDEF",
    matched_positions: ["QB", "RB"],
    partner_score: 1.895,
    score_components: {
      activity_recency_score: 0.0,
      complementarity_score: 0.645,
      divergence_density_score: 1.0,
      posture_alignment_score: 0.25,
    },
    evidence: {
      counterparty_posture: "CONTENDER",
      divergence_row_count: 11,
      perspective_posture: "REBUILDING",
      position_scores: { QB: 0.645, RB: 0.506 },
    },
  }),
  partner({
    counterparty_roster_id: 8,
    counterparty_team_name: "jspringe88",
    matched_positions: ["WR"],
    partner_score: 1.661,
    score_components: {
      activity_recency_score: 0.0,
      complementarity_score: 0.661,
      divergence_density_score: 1.0,
      posture_alignment_score: 0.0,
    },
    evidence: {
      counterparty_posture: "ASCENDING",
      divergence_row_count: 11,
      perspective_posture: "REBUILDING",
      position_scores: { WR: 0.661 },
    },
  }),
  partner({
    counterparty_roster_id: 2,
    counterparty_team_name: "jgil96",
    matched_positions: ["RB"],
    partner_score: 1.572,
    score_components: {
      activity_recency_score: 0.0,
      complementarity_score: 0.572,
      divergence_density_score: 1.0,
      posture_alignment_score: 0.0,
    },
    evidence: {
      counterparty_posture: "ASCENDING",
      divergence_row_count: 8,
      perspective_posture: "REBUILDING",
      position_scores: { RB: 0.572 },
    },
  }),
  // The six tail rows: no matched position at all, so complementarity is a
  // MEASURED zero — the loop ran over all four positions and none qualified.
  partner({
    counterparty_roster_id: 6,
    counterparty_team_name: "Drew P. Bauls",
    matched_positions: [],
    partner_score: 1.1,
    score_components: {
      activity_recency_score: 0.0,
      complementarity_score: 0.0,
      divergence_density_score: 1.0,
      posture_alignment_score: 0.1,
    },
    evidence: {
      counterparty_posture: "BALANCED",
      divergence_row_count: 13,
      perspective_posture: "REBUILDING",
      position_scores: {},
    },
  }),
  partner({
    counterparty_roster_id: 10,
    counterparty_team_name: "Kissane’s Team",
    matched_positions: [],
    partner_score: 1.1,
    score_components: {
      activity_recency_score: 0.0,
      complementarity_score: 0.0,
      divergence_density_score: 1.0,
      posture_alignment_score: 0.1,
    },
    evidence: {
      counterparty_posture: "BALANCED",
      divergence_row_count: 8,
      perspective_posture: "REBUILDING",
      position_scores: {},
    },
  }),
  partner({
    counterparty_roster_id: 5,
    counterparty_team_name: "rzalika",
    matched_positions: [],
    partner_score: 1.05,
    score_components: {
      activity_recency_score: 0.0,
      complementarity_score: 0.0,
      divergence_density_score: 1.0,
      posture_alignment_score: 0.05,
    },
    evidence: {
      counterparty_posture: "REBUILDING",
      divergence_row_count: 5,
      perspective_posture: "REBUILDING",
      position_scores: {},
    },
  }),
  partner({
    counterparty_roster_id: 9,
    counterparty_team_name: "Seidmans Sasquatches",
    matched_positions: [],
    partner_score: 1.05,
    score_components: {
      activity_recency_score: 0.0,
      complementarity_score: 0.0,
      divergence_density_score: 1.0,
      posture_alignment_score: 0.05,
    },
    evidence: {
      counterparty_posture: "REBUILDING",
      divergence_row_count: 10,
      perspective_posture: "REBUILDING",
      position_scores: {},
    },
  }),
  partner({
    counterparty_roster_id: 11,
    counterparty_team_name: "jkazzz",
    matched_positions: [],
    partner_score: 1.0,
    score_components: {
      activity_recency_score: 0.0,
      complementarity_score: 0.0,
      divergence_density_score: 1.0,
      posture_alignment_score: 0.0,
    },
    evidence: {
      counterparty_posture: "ASCENDING",
      divergence_row_count: 9,
      perspective_posture: "REBUILDING",
      position_scores: {},
    },
  }),
  partner({
    counterparty_roster_id: 12,
    counterparty_team_name: "Florida Man",
    matched_positions: [],
    partner_score: 1.0,
    score_components: {
      activity_recency_score: 0.0,
      complementarity_score: 0.0,
      divergence_density_score: 1.0,
      posture_alignment_score: 0.0,
    },
    evidence: {
      counterparty_posture: "ASCENDING",
      divergence_row_count: 6,
      perspective_posture: "REBUILDING",
      position_scores: {},
    },
  }),
];

const CAVEAT = /partly market-derived, so it is context rather than a proven edge/;

function cardFor(name) {
  return within(screen.getByText(name).closest("article"));
}

describe("DG-119 · the caveat is a section fact, said once", () => {
  it("prints the market-derived caveat exactly once across eleven partners", () => {
    render(<PartnerRankings rankings={LIVE_ELEVEN} />);

    // ONCE, not zero times. The fact that the score is partly market-derived is
    // a property of how the score is built, so it belongs to the section — but
    // it is still a fact, and deleting it would be the defect this whole
    // program exists to prevent.
    expect(screen.getAllByText(CAVEAT)).toHaveLength(1);
  });

  it("keeps the caveat above the cards it qualifies", () => {
    render(<PartnerRankings rankings={LIVE_ELEVEN} />);

    const caveat = screen.getByText(CAVEAT);
    const firstCard = screen.getByText("YippeKiYay MarshalFaulker").closest("article");
    expect(
      caveat.compareDocumentPosition(firstCard) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("retires the eleven stamped 'Market-influenced' badges", () => {
    render(<PartnerRankings rankings={LIVE_ELEVEN} />);

    // `market_influenced` is `Literal[True]` on every ranking by construction
    // (league_pulse_models.py:135-146), and the whole content of that flag is
    // "this score is partly market-derived" — which the caveat above now says
    // once, in a sentence. A badge repeating it eleven times is furniture, and
    // the fact does not live in it.
    expect(screen.queryAllByText("Market-influenced")).toHaveLength(0);
    expect(screen.getAllByText(CAVEAT)).toHaveLength(1);
  });
});

describe("DG-119 · each card says who to call and why, in a sentence", () => {
  it("leads with the manager's own name, never renamed", () => {
    render(<PartnerRankings rankings={LIVE_ELEVEN} />);

    const name = screen.getByText("YippeKiYay MarshalFaulker");
    expect(name.tagName).toBe("H3");
    // League-authored text. The copy dictionary must never rewrite it, and the
    // render rule's exemption is a DECLARATION the markup makes.
    expect(name.hasAttribute("data-user-text")).toBe(true);
  });

  it("states the fit in words instead of a bare three-decimal score", () => {
    render(<PartnerRankings rankings={LIVE_ELEVEN} />);

    expect(cardFor("YippeKiYay MarshalFaulker").getByText("Best fit")).toBeTruthy();
    expect(cardFor("Free Kelly").getByText("2nd best fit")).toBeTruthy();
    // 1.1 and 1.1 are the SAME score. An ordinal that ranked one above the
    // other would invent a difference the producer did not emit.
    expect(cardFor("Drew P. Bauls").getByText("Tied 6th best fit")).toBeTruthy();
    expect(cardFor("Kissane’s Team").getByText("Tied 6th best fit")).toBeTruthy();
    // The raw score is not deleted — it moves to the receipt layer.
    expect(screen.queryByText("2.091")).toBeNull();
  });

  it("says why in one line: the postures, the positions, the price gaps", () => {
    render(<PartnerRankings rankings={LIVE_ELEVEN} />);

    // Entailed by league_opportunity_map.py:171-175 — a position is MATCHED
    // only where your z <= -0.75 and theirs >= +0.75, which is exactly "thin on
    // your side, deep on theirs".
    expect(
      cardFor("YippeKiYay MarshalFaulker").getByText(
        "You're rebuilding and they're contending. They're deep at RB and WR — exactly where you're thin. We and the market price 5 of their players differently.",
      ),
    ).toBeTruthy();
  });

  it("does not claim a positional fit where the producer matched none", () => {
    render(<PartnerRankings rankings={LIVE_ELEVEN} />);

    expect(
      cardFor("Drew P. Bauls").getByText(
        /You're rebuilding and they're middle of the pack\. There's no position where you're thin and they're deep\./,
      ),
    ).toBeTruthy();
  });

  it("counts the players we and the market price differently", () => {
    render(<PartnerRankings rankings={LIVE_ELEVEN} />);

    expect(
      cardFor("Kissane’s Team").getByText(
        /We and the market price 8 of their players differently\./,
      ),
    ).toBeTruthy();
  });
});

describe("DG-119 · the numbers survive, in the receipt", () => {
  it("keeps the trade-fit score, the four parts and the roster number", () => {
    render(<PartnerRankings rankings={LIVE_ELEVEN} />);

    const card = cardFor("YippeKiYay MarshalFaulker");
    expect(card.getByText("How this fit was scored")).toBeTruthy();
    expect(card.getByText(/Trade-fit score — 2\.091/)).toBeTruthy();
    // The four parts. Each `<dt>` above these already names the field, so the
    // receipt carries the value and the producer key and does not repeat the
    // label — printing the full form gave "How well the rosters fit" twice
    // within eight lines on the first browser pass.
    expect(card.getByText("0.841 (from complementarity_score)")).toBeTruthy();
    expect(card.getByText("1 (from divergence_density_score)")).toBeTruthy();
    expect(card.getByText("0.25 (from posture_alignment_score)")).toBeTruthy();
    expect(card.getByText("How well the rosters fit")).toBeTruthy();
    expect(card.getByText("Whether you're pointed opposite ways")).toBeTruthy();
    expect(card.getByText(/Their roster number — 7/)).toBeTruthy();
    // Per-position scores, still on screen, still labelled.
    expect(card.getByText(/RB 0\.554/)).toBeTruthy();
    expect(card.getByText(/WR 0\.841/)).toBeTruthy();
  });

  it("puts every raw producer key inside a declared receipt subtree", () => {
    render(<PartnerRankings rankings={LIVE_ELEVEN} />);

    const card = cardFor("YippeKiYay MarshalFaulker");
    expect(card.getByText(/from partner_score/).closest("[data-receipt]")).toBeTruthy();
  });
});

describe("DG-119 · a zero that was never measured does not read as a measurement", () => {
  it("says the trade-activity part is not measured, rather than printing 0.00", () => {
    render(<PartnerRankings rankings={LIVE_ELEVEN} />);

    const card = cardFor("YippeKiYay MarshalFaulker");
    expect(
      card.getByText(
        "We don't track trade activity, so this part scores nothing for anybody and moves no one up or down the list.",
      ),
    ).toBeTruthy();
  });

  it("separates a posture pairing that scores nothing from a posture we could not place", () => {
    render(<PartnerRankings rankings={LIVE_ELEVEN} />);

    // Both teams ARE placed (rebuilding / rising), so a 0.0 here is the pairing
    // itself scoring nothing — not a missing signal.
    expect(
      cardFor("jkazzz").getByText(
        "Both postures were placed, so this pairing simply scores nothing.",
      ),
    ).toBeTruthy();

    render(
      <PartnerRankings
        rankings={[
          partner({
            counterparty_team_name: "No Posture FC",
            matched_positions: [],
            partner_score: 1.0,
            score_components: {
              activity_recency_score: 0.0,
              complementarity_score: 0.0,
              divergence_density_score: 1.0,
              posture_alignment_score: 0.0,
            },
            evidence: {
              counterparty_posture: "UNCLASSIFIED",
              divergence_row_count: 5,
              perspective_posture: "REBUILDING",
              position_scores: {},
            },
          }),
        ]}
      />,
    );

    expect(
      cardFor("No Posture FC").getByText(
        "One of these teams does not have enough signal for a posture, so this part could not score.",
      ),
    ).toBeTruthy();
  });

  it("does not fold an unplaced posture into a sentence that says we placed it", () => {
    render(
      <PartnerRankings
        rankings={[
          partner({
            counterparty_team_name: "No Posture FC",
            evidence: {
              counterparty_posture: "UNCLASSIFIED",
              divergence_row_count: 5,
              perspective_posture: "REBUILDING",
              position_scores: { RB: 0.554, WR: 0.841 },
            },
          }),
        ]}
      />,
    );

    const card = cardFor("No Posture FC");
    // "You're rebuilding and they're contending" is unavailable here: one side
    // has no posture. The clause that says so replaces it — it never quietly
    // becomes a claim that we placed them.
    expect(
      card.getByText(
        /You're rebuilding, and we don't have enough signal to say which way they're pointed\. They're deep at RB and WR — exactly where you're thin\./,
      ),
    ).toBeTruthy();
    expect(card.queryByText(/they're not enough signal/i)).toBeNull();
  });
});

describe("DG-119 · the producer coupling behind the not-measured sentence", () => {
  it("fails the moment activity_recency_score stops being a hardcoded zero", () => {
    // THE GRADUATION RED. The copy above tells David we do not track trade
    // activity. That is true only while this line is a literal. Wire the
    // component up to a real signal and this test fails, which is the point:
    // the sentence has to be rewritten in the same commit, not discovered wrong
    // on screen six months later.
    const producer = resolve(
      dirname(fileURLToPath(import.meta.url)),
      "../../../src/dynasty_genius/league_opportunity_map.py",
    );
    const source = readFileSync(producer, "utf8");

    expect(
      source.includes("activity_recency_score = 0.0"),
      "league_opportunity_map.py no longer hardcodes activity_recency_score to 0.0. " +
        "PartnerRankings.tsx tells David we do not track trade activity at all — " +
        "rewrite that sentence before this component reports a measured value as if " +
        "it were an absence of measurement.",
    ).toBe(true);
  });
});
