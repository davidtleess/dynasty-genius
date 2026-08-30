/**
 * DG-113 — ENTAILMENT SPECS.
 *
 * The verdict and the recommendation cards are assembled sentences, and a
 * sentence reads as a conclusion whether or not one was computed. These specs
 * are the mechanical half of the honesty law: each one pins a clause to the
 * field that entails it, and — more importantly — pins the clauses that must
 * NOT appear when the field is absent.
 *
 * Several of them exist because the spec's own example copy was wrong when read
 * against the payload. Those are marked; they are the reason "read the producer,
 * never a plausible reading" is a rule and not a slogan.
 */
import { describe, expect, it } from "vitest";

import type {
  WhatChangedMarketDelta,
  WhatChangedMarketSection,
  WhatChangedResponse,
  WhatChangedStructuralSection,
} from "../lib/api/types.gen";
import {
  cutPressure,
  leagueMovers,
  movement,
  staleInputClause,
  staleInputs,
  verdict,
  whereYouStand,
  windowPhrase,
  worthALook,
} from "./morningRead";

function row(overrides: Partial<WhatChangedMarketDelta> = {}): WhatChangedMarketDelta {
  return {
    sleeper_id: "1",
    player_key: "sleeper:1",
    player_name: "A Player",
    position: "QB",
    value_delta: 0,
    value_delta_direction: "flat",
    overall_rank_delta: 0,
    overall_rank_delta_direction: "unchanged",
    position_rank_delta: 0,
    position_rank_delta_direction: "unchanged",
    ...overrides,
  } as WhatChangedMarketDelta;
}

function market(
  overrides: Partial<WhatChangedMarketSection> = {},
): WhatChangedMarketSection {
  return {
    status: "ok",
    decision_supported: false,
    market_source: "fantasycalc_overlay",
    comparison_window: { from_date: "2026-08-28", to_date: "2026-08-29" },
    roster_deltas: [],
    top_movers: [],
    total_movers_count: 0,
    entered: [],
    exited: [],
    ...overrides,
  } as WhatChangedMarketSection;
}

function section(
  overrides: Partial<WhatChangedStructuralSection> = {},
): WhatChangedStructuralSection {
  return {
    status: "ok",
    decision_supported: false,
    current_not_delta: true,
    ...overrides,
  } as WhatChangedStructuralSection;
}

const CROWDED = section({
  summary: { roster_id: 1, total_players: 27, total_capacity: 26, cuts_required: 1 },
  top_candidates: [
    {
      sleeper_player_id: "11570",
      player_name: "Rasheen Ali",
      position: "RB",
      cut_priority: 1,
      dvs: 20.7,
      xvar_pct: 36.8,
    },
  ],
});

describe("windowPhrase — 'overnight' is a claim about elapsed time", () => {
  it("says overnight only when the two compared captures are adjacent days", () => {
    expect(windowPhrase({ from_date: "2026-08-28", to_date: "2026-08-29" })).toBe(
      "overnight",
    );
  });

  it("names the two days when a capture was missed and the window is wider", () => {
    // The market window is dates[-2] vs dates[-1] (daily_diff.py:119). A missed
    // capture makes those two days apart, and "overnight" would then be a small
    // lie repeated on every sentence of the page.
    expect(windowPhrase({ from_date: "2026-08-26", to_date: "2026-08-29" })).toBe(
      "between Wednesday and Saturday",
    );
  });

  it("falls back to a neutral phrase rather than guessing at an unreadable window", () => {
    expect(windowPhrase(null)).toBe("since the last capture");
    expect(windowPhrase({ from_date: "not-a-date", to_date: "2026-08-29" })).toBe(
      "since the last capture",
    );
  });
});

describe("movement — an empty list is not a verdict", () => {
  it("says the comparison never ran, and never that nothing moved", () => {
    // daily_diff.py:111-117 returns `insufficient_history` with NO
    // aborted_reason at all. Reading the list length alone would print
    // "nothing moved" over a comparison that was never made.
    const moved = movement(
      market({ status: "insufficient_history", roster_deltas: [] }),
      27,
    );
    expect(moved.kind).toBe("not-compared");
    expect(moved.sentence).toMatch(/couldn't compare your prices/i);
    expect(moved.sentence).not.toMatch(/held steady|nothing moved|no movement/i);
  });

  it("distinguishes 'we priced none of yours' from 'yours did not move'", () => {
    const none = movement(market({ roster_deltas: [] }), 27);
    expect(none.kind).toBe("none-priced");
    expect(none.sentence).toMatch(/didn't price any of your players/i);

    const flat = movement(market({ roster_deltas: [row(), row()] }), 27);
    expect(flat.kind).toBe("flat");
    expect(flat.sentence).toMatch(/not one of them moved overnight/i);
  });

  it("states the coverage rather than rounding a priced subset up to the roster", () => {
    // roster_deltas holds only the roster players the market priced in BOTH
    // captures (daily_diff.py:143-147). Saying "26 of your players moved"
    // without the coverage clause quietly promotes a subset to the whole team.
    const moved = movement(
      market({
        roster_deltas: [
          row({
            sleeper_id: "a",
            player_name: "Big Mover",
            value_delta: 306,
            current_value: 5082,
          }),
          row({ sleeper_id: "b", value_delta: 0 }),
        ],
      }),
      27,
    );
    expect(moved.sentence).toMatch(/The market priced 2 of your 27 players/);
    expect(moved.sentence).toMatch(/1 of them moved overnight/);
    expect(moved.sentence).toMatch(/Big Mover most of all, up 306 to 5,082\./);
  });

  it("says 'all' only when coverage is complete, and 'every one' only when all moved", () => {
    const complete = movement(
      market({ roster_deltas: [row({ value_delta: 5, current_value: 100 })] }),
      1,
    );
    expect(complete.sentence).toMatch(/The market priced all 1 of your players/);
    expect(complete.sentence).toMatch(/every one of them moved/);
  });

  it("omits the level when the producer carried none, rather than inventing one", () => {
    const moved = movement(
      market({ roster_deltas: [row({ value_delta: 40, current_value: null })] }),
      null,
    );
    expect(moved.sentence).toMatch(/up 40\./);
    expect(moved.sentence).not.toMatch(/ to /);
  });
});

describe("cutPressure — rank 1 and rank 0 are different things", () => {
  it("names the producer's value-ranked first candidate", () => {
    const pressure = cutPressure(CROWDED);
    expect(pressure.kind).toBe("cut");
    if (pressure.kind !== "cut") throw new Error("unreachable");
    expect(pressure.ranked?.player_name).toBe("Rasheen Ali");
  });

  it("refuses to treat a FORCED review candidate as the most expendable player", () => {
    // cut_priority 0 is an injury-list compliance failure unshifted onto the
    // front of the list (roster_cut_engine.py:286-297). It is not ranked by
    // value at all, so reading position 0 as "lowest value over replacement"
    // would attach a value ordering to a roster-rules problem.
    const forced = cutPressure(
      section({
        summary: {
          roster_id: 1,
          total_players: 27,
          total_capacity: 26,
          cuts_required: 1,
        },
        top_candidates: [
          {
            sleeper_player_id: "x",
            player_name: "Forced Review",
            position: "WR",
            cut_priority: 0,
            dvs: null,
            xvar_pct: null,
          },
        ],
      }),
    );
    expect(forced.kind).toBe("cut");
    if (forced.kind !== "cut") throw new Error("unreachable");
    expect(forced.ranked).toBeNull();

    const cards = worthALook({
      pressure: forced,
      moved: movement(market({ roster_deltas: [] }), 27),
      window: null,
    }).cards;
    expect(cards[0]?.headline).toBe("One cut is due.");
    expect(cards[0]?.reasons.join(" ")).toMatch(/don't have a value-ranked list/i);
    expect(cards[0]?.reasons.join(" ")).not.toMatch(/Forced Review/);
  });

  it("reports the check as unrun rather than clear when its section failed", () => {
    const unknown = cutPressure(
      section({ status: "unavailable", aborted_reason: "missing_structural_artifact" }),
    );
    expect(unknown.kind).toBe("unknown");
  });
});

describe("verdict — the all-clear says how far it reaches", () => {
  const quiet = movement(market({ roster_deltas: [] }), 27);

  it("names the one action when the roster is over its limit", () => {
    const v = verdict({
      pressure: cutPressure(CROWDED),
      moved: quiet,
      stalenessClause: null,
    });
    expect(v.tone).toBe("action");
    expect(v.headline).toBe(
      "One thing needs doing: you're carrying 27 players in 26 spots, so one has to go.",
    );
  });

  it("scopes the all-clear to the check that produced it", () => {
    // "Nothing needs doing today" unqualified is the exact fabrication the
    // phase-2A panel caught — a rollup "ok" rendered as a claim the backend
    // declines to make. The clause after the dash says what was checked.
    const clear = cutPressure(
      section({
        summary: {
          roster_id: 1,
          total_players: 25,
          total_capacity: 26,
          cuts_required: 0,
        },
      }),
    );
    const v = verdict({ pressure: clear, moved: quiet, stalenessClause: null });
    expect(v.tone).toBe("clear");
    expect(v.headline).toBe(
      "Nothing needs doing today — your 25 players fit inside your 26 spots.",
    );
  });

  it("says it cannot tell, and which input is missing, rather than saying all is well", () => {
    const unknown = cutPressure(
      section({ status: "unavailable", aborted_reason: "missing_structural_artifact" }),
    );
    const v = verdict({ pressure: unknown, moved: quiet, stalenessClause: null });
    expect(v.tone).toBe("unknown");
    expect(v.headline).toMatch(/can't tell you whether anything needs doing/i);
    expect(v.headline).not.toMatch(/nothing needs doing/i);
    expect(v.detail).toMatch(/file this section is built from was not there/i);
    expect(v.detail).toMatch(/back on the next run/i);
  });

  it("carries the staleness clause into the detail when the report is old", () => {
    const v = verdict({
      pressure: cutPressure(CROWDED),
      moved: quiet,
      stalenessClause:
        "Everything below is the last verified snapshot, not this morning's.",
    });
    expect(v.detail).toMatch(/last verified snapshot, not this morning's\.$/);
  });
});

describe("worthALook — the spade is called, and only from fields on the page", () => {
  const bigMove = movement(
    market({
      roster_deltas: [
        row({
          player_name: "Jaxson Dart",
          position: "QB",
          value_delta: 306,
          current_value: 5082,
          overall_rank_delta: -3,
          position_rank_delta: -1,
        }),
      ],
    }),
    27,
  );

  it("names the cut and the ordering that put him first", () => {
    const { cards } = worthALook({
      pressure: cutPressure(CROWDED),
      moved: bigMove,
      window: { from_date: "2026-08-28", to_date: "2026-08-29" },
    });
    const cut = cards.find((c) => c.id === "required-cut");
    expect(cut?.headline).toBe("Your required cut: start with Rasheen Ali.");
    expect(cut?.reasons[0]).toBe(
      "You're carrying 27 players in 26 spots, so one has to go.",
    );
    expect(cut?.reasons[1]).toMatch(
      /ranks the players you're allowed to drop and puts him first/i,
    );
    expect(cut?.reasons[1]).toMatch(/36\.8 percentile/);
    // `cut_priority` 1 is the HEAD of the list (roster_cut_engine.py:359-375),
    // so "the bottom of it" read as the opposite of where he is.
    expect(cut?.reasons[1]).not.toMatch(/bottom of it/i);
    // And it no longer asserts the total ordering the frontend cannot verify:
    // `_scoring_tier` returns "D" for engine_path PRE_MODEL BEFORE it looks at
    // xvar_pct (roster_cut_engine.py:161-168), and neither `scoring_tier` nor
    // `engine_path` is serialised to this payload (report.py:425-427).
    expect(cut?.reasons[1]).not.toMatch(/lowest-value first/i);
  });

  it("prices a market move as a share of the player's price, and states its size", () => {
    const { cards } = worthALook({
      pressure: cutPressure(CROWDED),
      moved: bigMove,
      window: { from_date: "2026-08-28", to_date: "2026-08-29" },
    });
    const move = cards.find((c) => c.id === "market-move");
    expect(move?.headline).toBe("Jaxson Dart's price jumped overnight.");
    expect(move?.reasons[0]).toMatch(/up 306 to 5,082 — a 6\.0% move/);
    // Signs: *_rank_delta = latest - prior, so NEGATIVE is toward rank #1.
    expect(move?.reasons[1]).toMatch(
      /3 places up the market's overall board and 1 spot up among quarterbacks/,
    );
  });

  it("NEVER claims a sell-high window, a model comparison, or a period high", () => {
    // All three are in the spec's example copy for this exact player and all
    // three are unsupported here. A market delta row carries no model value at
    // all; the payload has rank DELTAS and no absolute rank; and the sparkline
    // beside it disproves the "strongest market he's had" reading outright —
    // Dart's 5,082 sits below his 5,381 of four weeks earlier.
    const { cards } = worthALook({
      pressure: cutPressure(CROWDED),
      moved: bigMove,
      window: { from_date: "2026-08-28", to_date: "2026-08-29" },
    });
    const text = cards.map((c) => `${c.headline} ${c.reasons.join(" ")}`).join(" ");
    expect(text).not.toMatch(/sell.?high|buy.?low/i);
    expect(text).not.toMatch(/our model prices him|higher than our|lower than our/i);
    expect(text).not.toMatch(/this month|strongest|highest|best price/i);
    expect(text).not.toMatch(/30th overall|11th among/i);
  });

  it("leaves the block empty when the move is too small to be worth a look", () => {
    // 122 on a 5,204 price is 2.3% — under the stated bar. The block does not
    // pad itself with the biggest thing it happens to have.
    const small = movement(
      market({
        roster_deltas: [
          row({ player_name: "Jaxson Dart", value_delta: 122, current_value: 5204 }),
        ],
      }),
      27,
    );
    const clear = cutPressure(
      section({
        summary: {
          roster_id: 1,
          total_players: 25,
          total_capacity: 26,
          cuts_required: 0,
        },
      }),
    );
    const { cards, missing } = worthALook({
      pressure: clear,
      moved: small,
      window: null,
    });
    expect(cards).toEqual([]);
    expect(missing).toEqual([]);
  });

  it("says which input is missing instead of quietly showing one fewer card", () => {
    const unknown = cutPressure(
      section({ status: "unavailable", aborted_reason: "missing_structural_artifact" }),
    );
    const { cards, missing } = worthALook({
      pressure: unknown,
      moved: movement(market({ roster_deltas: [] }), 27),
      window: null,
    });
    expect(cards).toEqual([]);
    expect(missing[0]).toMatch(/normally check your roster limit/i);
    expect(missing[0]).toMatch(/back on the next run/i);
  });

  it("never shows more than two cards", () => {
    const { cards } = worthALook({
      pressure: cutPressure(CROWDED),
      moved: bigMove,
      window: { from_date: "2026-08-28", to_date: "2026-08-29" },
    });
    expect(cards.length).toBe(2);
  });
});

describe("whereYouStand — one posture, and it says what produced it", () => {
  function response(posture: string | null): WhatChangedResponse {
    return {
      structural_context: {
        sections: {
          team_posture: section({
            david_posture: posture,
            david_team_name: "Woodbury Riders",
          }),
        },
      },
    } as unknown as WhatChangedResponse;
  }

  it("says the posture is a formula, not a plan somebody made", () => {
    const stand = whereYouStand(response("REBUILDING"), cutPressure(CROWDED));
    expect(stand.teamName).toBe("Woodbury Riders");
    expect(stand.posture).toMatch(/You're rebuilding/);
    expect(stand.posture).toMatch(
      /formula over your roster's starters, ages and picks/,
    );
    expect(stand.roster).toBe("You're carrying 27 players in 26 spots.");
  });

  it("does not dress an unclassified team up as a posture", () => {
    const stand = whereYouStand(response("UNCLASSIFIED"), cutPressure(CROWDED));
    expect(stand.posture).toBe(
      "We don't have enough signal to put a label on your team yet.",
    );
  });

  it("stays silent when the producer has no posture at all", () => {
    expect(whereYouStand(response(null), cutPressure(CROWDED)).posture).toBeNull();
  });
});

describe("leagueMovers — his own players belong to exactly one list", () => {
  it("removes roster players from the league list and counts what it removed", () => {
    const shared = row({
      sleeper_id: "12508",
      player_name: "Jaxson Dart",
      value_delta: 306,
    });
    const result = leagueMovers(
      market({
        roster_deltas: [shared, row({ sleeper_id: "b" })],
        top_movers: [shared, row({ sleeper_id: "c", player_name: "Someone Else" })],
      }),
    );
    expect(result.rows.map((r) => r.player_name)).toEqual(["Someone Else"]);
    expect(result.excluded).toBe(1);
  });

  it("keeps a league row whose identity we cannot match rather than dropping it", () => {
    // A null sleeper id cannot be proven to be his, and silently deleting a
    // real mover is a worse failure than showing one that might also be his.
    const result = leagueMovers(
      market({
        roster_deltas: [row({ sleeper_id: "a" })],
        top_movers: [
          // The generated type says `sleeper_id: string`, but the producer
          // builds this row from `latest.get("sleeper_id")` on a raw table read
          // (daily_diff.py:200-212) — a nullable column with no guard. The cast
          // is the honest way to test the shape the wire can actually carry.
          {
            ...row({ player_name: "Unmatched" }),
            sleeper_id: null as unknown as string,
          },
        ],
      }),
    );
    expect(result.rows).toHaveLength(1);
    expect(result.excluded).toBe(0);
  });
});

// ── PANEL FIXES ──────────────────────────────────────────────────────────────
//
// Every spec below pins a defect a refuter found by reading the producer, on a
// morning the live payload does not happen to produce. They are here so the
// fix cannot be undone by someone restoring the more confident sentence.

describe("a section's OWN clock is not the report's", () => {
  const STALE_CUT = section({
    summary: { roster_id: 1, total_players: 27, total_capacity: 26, cuts_required: 1 },
    top_candidates: [
      {
        sleeper_player_id: "11570",
        player_name: "Rasheen Ali",
        position: "RB",
        cut_priority: 1,
        dvs: 20.7,
        xvar_pct: 36.8,
      },
    ],
    staleness_caveat: {
      basis: "captured_at_vs_report_generated_at",
      report_generated_at: "2026-08-30T13:00:00+00:00",
      age_hours: 30.2,
      is_stale: true,
    },
  });

  it("finds a stale section inside a fresh report", () => {
    // The two clocks provably diverge on live data: league_opportunity carries
    // age_hours 119.4 inside a report whose own age is 0.0h. `_section_envelope`
    // (report.py:450-486) stamps is_stale from the SECTION's captured_at.
    const found = staleInputs([
      { label: "roster-limit check", section: STALE_CUT },
      { label: "roster read", section: section() },
    ]);
    expect(found).toEqual([{ label: "roster-limit check", hours: 30.2 }]);
    expect(staleInputClause(found)).toMatch(
      /roster-limit check behind this is 30\.2 hours old/i,
    );
    expect(staleInputClause([])).toBeNull();
  });

  it("names both inputs when both are stale", () => {
    const clause = staleInputClause([
      { label: "roster-limit check", hours: 30 },
      { label: "roster read", hours: 40 },
    ]);
    expect(clause).toMatch(/the roster-limit check and the roster read/i);
    expect(clause).toMatch(/last verified reads rather than this morning's/i);
  });

  it("puts the staleness clause under the headline it qualifies, not at the page foot", () => {
    // THE BLOCKER. drop_pressure comes back status "ok" — complete, well-formed
    // and a day old — when yesterday's artifact is reused. The verdict was
    // reading only staleHours(generated_at), the REPORT's clock, so it printed
    // an unqualified directive under a header saying the numbers were current.
    const pressure = cutPressure(STALE_CUT);
    const clause = staleInputClause(
      staleInputs([{ label: "roster-limit check", section: STALE_CUT }]),
    );
    const v = verdict({
      pressure,
      moved: movement(market({ roster_deltas: [] }), 27),
      stalenessClause: null,
      inputStaleClause: clause,
    });
    expect(v.headline).toMatch(/one has to go/);
    expect(v.detail).toMatch(/roster-limit check behind this is 30\.2 hours old/i);
    // It LEADS the detail, so it sits directly beneath the headline.
    expect(v.detail.indexOf("Heads up")).toBe(0);
  });

  it("carries the same clause onto the card that names a real player", () => {
    const clause = staleInputClause(
      staleInputs([{ label: "roster-limit check", section: STALE_CUT }]),
    );
    const { cards } = worthALook({
      pressure: cutPressure(STALE_CUT),
      moved: movement(market({ roster_deltas: [] }), 27),
      window: null,
      inputStaleClause: clause,
    });
    const cut = cards.find((c) => c.id === "required-cut");
    expect(cut?.headline).toMatch(/start with Rasheen Ali/);
    expect(cut?.reasons.some((r) => /30\.2 hours old/.test(r))).toBe(true);
  });

  it("says nothing about staleness when neither section is stale", () => {
    const v = verdict({
      pressure: cutPressure(CROWDED),
      moved: movement(market({ roster_deltas: [] }), 27),
      stalenessClause: null,
      inputStaleClause: staleInputClause(
        staleInputs([{ label: "roster-limit check", section: CROWDED }]),
      ),
    });
    expect(v.detail).not.toMatch(/Heads up/i);
  });
});

describe("rank 1 without a figure is not a value ranking", () => {
  const NO_FIGURES = section({
    summary: { roster_id: 1, total_players: 27, total_capacity: 26, cuts_required: 1 },
    top_candidates: [
      {
        sleeper_player_id: "999",
        player_name: "Somebody",
        position: "WR",
        cut_priority: 1,
        dvs: null,
        xvar_pct: null,
      },
    ],
  });

  it("refuses to name him, because the sort that ranked him was degenerate", () => {
    // THE BLOCKER. `_tier_sort_key` (roster_cut_engine.py:171-181) scores tier C
    // and tier D at float("inf"), and those tiers are exactly the entries with
    // neither xvar_pct nor dvs (:161-168). Tier A sorts before B before C before
    // D, so a rank-1 candidate can only be C/D when the WHOLE droppable pool
    // lacks both numbers — every key identical, the sort stable, and
    // cut_priority 1 is just roster["players"][0].
    const pressure = cutPressure(NO_FIGURES);
    expect(pressure.kind).toBe("cut");
    if (pressure.kind !== "cut") throw new Error("unreachable");
    expect(pressure.ranked).toBeNull();

    const { cards } = worthALook({
      pressure,
      moved: movement(market({ roster_deltas: [] }), 27),
      window: null,
    });
    const card = cards[0];
    expect(card?.id).toBe("required-cut-unranked");
    expect(card?.headline).toBe("One cut is due.");
    expect(card?.headline).not.toMatch(/Somebody/);
    expect(card?.reasons.join(" ")).toMatch(/don't have a value-ranked list/i);
    // And no card anywhere on the block may name him.
    expect(cards.map((c) => c.headline).join(" ")).not.toMatch(/Somebody/);
  });

  it("still names him when the producer carried a figure for him", () => {
    const pressure = cutPressure(CROWDED);
    if (pressure.kind !== "cut") throw new Error("unreachable");
    expect(pressure.ranked?.player_name).toBe("Rasheen Ali");
  });

  it("names him on dynasty value alone when that is the only figure", () => {
    const dvsOnly = section({
      summary: {
        roster_id: 1,
        total_players: 27,
        total_capacity: 26,
        cuts_required: 1,
      },
      top_candidates: [
        {
          sleeper_player_id: "7",
          player_name: "Only DVS",
          position: "TE",
          cut_priority: 1,
          dvs: 12.5,
          xvar_pct: null,
        },
      ],
    });
    const { cards } = worthALook({
      pressure: cutPressure(dvsOnly),
      moved: movement(market({ roster_deltas: [] }), 27),
      window: null,
    });
    expect(cards[0]?.headline).toMatch(/start with Only DVS/);
    expect(cards[0]?.reasons[1]).toMatch(/his dynasty value is 12\.5/i);
  });
});

describe("'worth a look' scopes its all-clear to the checks that ran", () => {
  it("says the price check did not run rather than falling through to quiet", () => {
    // Two inputs, and only one could report its own absence. With the roster
    // limit clear and the market comparison never run, the block rendered
    // "Nothing worth acting on today." on one input — directly above a method
    // line explaining a rule that never got to execute.
    const clear = section({
      summary: {
        roster_id: 1,
        total_players: 25,
        total_capacity: 26,
        cuts_required: 0,
      },
    });
    const notCompared = movement(
      market({ status: "unavailable", aborted_reason: "missing_sleeper_snapshot" }),
      27,
    );
    expect(notCompared.kind).toBe("not-compared");
    const { cards, missing } = worthALook({
      pressure: cutPressure(clear),
      moved: notCompared,
      window: null,
    });
    expect(cards).toHaveLength(0);
    expect(missing.join(" ")).toMatch(/biggest price move/i);
    expect(missing.join(" ")).toMatch(/didn't run this morning/i);
  });
});

describe("the coverage clause carries its own scope", () => {
  it("says 'on both of the last two days', because that is what the list is", () => {
    // roster_deltas keeps only roster players present in BOTH captures
    // (daily_diff.py:143-147). A bare "priced 26 of your 27" asserts pricing
    // coverage; a player who ENTERED the priced pool this morning is priced and
    // still absent from this list.
    const moved = movement(
      market({ roster_deltas: [row({ value_delta: 10, current_value: 100 })] }),
      27,
    );
    expect(moved.sentence).toMatch(
      /priced 1 of your 27 players on both of the last two days/i,
    );
  });

  it("declines the confident wording when the roster size is unknown", () => {
    const moved = movement(
      market({ roster_deltas: [row({ value_delta: 10, current_value: 100 })] }),
      null,
    );
    expect(moved.sentence).not.toMatch(/all 1 of your players/i);
    expect(moved.sentence).toMatch(
      /priced 1 of your players on both of the last two days/i,
    );
  });
});

describe("league rank numerals survive the roster exclusion", () => {
  it("keeps each row's position in the producer's unfiltered list", () => {
    // Renumbering the survivors 1..N shifts every rank below an excluded
    // player: today's displayed #10 is the league's 11th biggest mover.
    const result = leagueMovers(
      market({
        roster_deltas: [row({ sleeper_id: "mine" })],
        top_movers: [
          row({ sleeper_id: "a", player_name: "First" }),
          row({ sleeper_id: "mine", player_name: "His" }),
          row({ sleeper_id: "c", player_name: "Third" }),
        ],
      }),
    );
    expect(result.rows.map((r) => r.player_name)).toEqual(["First", "Third"]);
    expect(result.ranks).toEqual([1, 3]);
    expect(result.excluded).toBe(1);
  });
});
