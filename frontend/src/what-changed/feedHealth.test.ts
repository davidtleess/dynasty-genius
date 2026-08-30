/**
 * DG-113 — HEALTH SHEET ENTAILMENT SPECS.
 *
 * This module had no specs of its own, and it is where the panel found the
 * worst defect on the page: the one always-visible sentence that replaced the
 * entire FEED DIAGNOSTICS rail was asserting "It ran today" from a field that
 * does not entail it.
 *
 * Every fixture below is built to a state the producer demonstrably emits, with
 * the producer line that emits it named. The two that matter most are the
 * pre-deadline morning (which is EVERY morning, before noon ET) and the thin
 * capture, because neither is reachable on the payload the browser pass was
 * driven against — which is exactly why no screenshot could catch them.
 */
import { describe, expect, it } from "vitest";

import type { CaptureHealthResponse, StoreHealth } from "../lib/api/types.gen";
import { feedHealth, feedRow, freshnessLine } from "./feedHealth";

function store(overrides: Partial<StoreHealth> = {}): StoreHealth {
  return {
    store_id: "market_divergence_history",
    store_presence: "present",
    store_status: "ok",
    decision_supported: false,
    caveats: [],
    density: {
      baseline_median_rows: 7400,
      baseline_window: 7,
      floor_pct: 50,
      sub_floor_dates: [],
    },
    flags: {
      warn_basis: "ok",
      warn_missing: false,
      window_risk: false,
      window_risk_basis: "ok",
    },
    schedule_drift: {
      basis: "chain_report",
      chain_step: "run_market_divergence",
      drift_minutes: 0,
      exceeds_grace: false,
      recorded_start: "2026-08-30T09:40:00-04:00",
      target_local: "09:40",
    },
    staleness: {
      expected_by: "2026-08-30T12:40:00-04:00",
      grace_hours: 3,
      last_capture_date: "2026-08-30",
      stale: false,
    },
    timeline: {
      capture_start_date: "2026-07-09",
      consecutive_days_current: 10,
      expected_days: 53,
      first_date: "2026-07-09",
      last_date: "2026-08-30",
      max_contiguous_gap_days: 1,
      missing_dates_count: 0,
      missing_ranges: [],
      missing_ranges_total: 0,
      present_days: 53,
    },
    ...overrides,
  } as StoreHealth;
}

function response(stores: StoreHealth[], checkedAt = "2026-08-30T09:00:00-04:00") {
  return {
    checked_at: checkedAt,
    config_version: 3,
    decision_supported: false,
    overall_status: stores.every((s) => s.store_status === "ok") ? "ok" : "degraded",
    stores,
    backup: {
      decision_supported: false,
      marker: null,
      marker_present: false,
      reasons: [],
      status: "ok",
      threshold_hours: 26,
    },
  } as unknown as CaptureHealthResponse;
}

const TODAY = "2026-08-30";

describe("THE BLOCKER — 'stale === false' does not mean 'it ran today'", () => {
  // system_capture_health_models.py:473
  //     end_date = today if now_local >= deadline else today - timedelta(days=1)
  // system_capture_health_models.py:547
  //     stale = bool(expected_dates) and end_date == today
  //             and today not in effective_present
  //
  // Before a store's deadline, end_date is YESTERDAY, so `stale` is False
  // whether today's capture landed or has simply not come due yet. All three
  // live stores are due between 12:00 and 12:45 ET, so on a 9am read every feed
  // took this branch and was printed as having run today.
  const preDeadline = store({
    store_status: "degraded",
    staleness: {
      expected_by: "2026-08-30T12:40:00-04:00",
      grace_hours: 3,
      last_capture_date: "2026-08-29",
      stale: false,
    },
    timeline: {
      ...store().timeline,
      missing_dates_count: 4,
      last_date: "2026-08-29",
    },
  });

  it("never says a feed ran today when its last capture was yesterday", () => {
    const row = feedRow(preDeadline, TODAY);
    expect(row.ran).toMatch(/Last ran Saturday, August 29\./);
    expect(row.note).not.toMatch(/ran today/i);
    expect(row.ranToday).toBe(false);
  });

  it("says it is not in yet AND not overdue, naming the deadline", () => {
    const row = feedRow(preDeadline, TODAY);
    expect(row.note).toMatch(/Today's capture isn't in yet/i);
    expect(row.note).toMatch(/isn't due until 12:40 PM EDT/);
    // The history problem is still reported — the fix removes a false clause,
    // it does not remove a true one.
    expect(row.note).toMatch(/4 days of its 53-day history never landed/);
    expect(row.trouble).toBe("not-due-yet");
  });

  it("keeps the header from claiming the feeds ran today", () => {
    const feeds = feedHealth(response([preDeadline]));
    if (feeds.kind !== "read") throw new Error("unreachable");
    expect(feeds.allGaps).toBe(false);
    expect(feeds.allRanToday).toBe(false);
    const line = freshnessLine("Report line.", false, feeds);
    expect(line.sentence).not.toMatch(/ran today/i);
    expect(line.sentence).toMatch(/1 of our 1 daily feeds need attention/);
  });

  it("reports only the history problem once today's capture is actually in", () => {
    // With today in hand there is nothing to say ABOUT today, and `ran` has
    // already said which day that was — so the note carries the history alone
    // rather than repeating the date as a claim. The header is where "ran
    // today" is worth saying, because it is summarising several feeds at once.
    const landed = store({
      store_status: "degraded",
      timeline: { ...store().timeline, missing_dates_count: 4 },
    });
    const row = feedRow(landed, TODAY);
    expect(row.ran).toMatch(/Last ran Sunday, August 30\./);
    expect(row.note).toMatch(/^4 days of its 53-day history never landed/);
    expect(row.trouble).toBe("gaps");
    // FOUND IN THE BROWSER, NOT BY A TEST: with nothing to say about today the
    // history clause opens the note, and "one day of its 68-day history…" was
    // rendering with a lowercase first word straight after a full stop.
    const singleGap = feedRow(
      store({
        store_status: "degraded",
        timeline: { ...store().timeline, missing_dates_count: 1 },
      }),
      TODAY,
    );
    expect(singleGap.note).toMatch(/^One day of its 53-day history never landed/);
    const feeds = feedHealth(response([landed]));
    if (feeds.kind !== "read") throw new Error("unreachable");
    expect(feeds.allGaps).toBe(true);
    expect(freshnessLine("Report line.", false, feeds).sentence).toMatch(
      /1 of our 1 daily feeds ran today but have gaps earlier in their history/,
    );
  });

  it("says nothing about today when it cannot tell what day it is", () => {
    const row = feedRow(
      store({ store_status: "degraded", caveats: ["something_odd"] }),
      null,
    );
    expect(row.ranToday).toBeNull();
    expect(row.note).not.toMatch(/today/i);
  });
});

describe("a feed that is LATE is named late, not merely gapped", () => {
  it("leads with lateness and does not bill today twice", () => {
    // stale means today was due and today is not in effective_present, so today
    // is itself one of the missing days. The history clause must not count it
    // again: missing_dates_count 5 with today among them is 4 days of history.
    const late = store({
      store_status: "degraded",
      staleness: {
        expected_by: "2026-08-30T12:40:00-04:00",
        grace_hours: 3,
        last_capture_date: "2026-08-29",
        stale: true,
      },
      timeline: { ...store().timeline, missing_dates_count: 5 },
    });
    const row = feedRow(late, TODAY);
    expect(row.trouble).toBe("late");
    expect(row.note).toMatch(/hasn't run when it was due/i);
    expect(row.note).toMatch(/4 days of its 53-day history never landed/);
    expect(row.note).not.toMatch(/5 days/);
  });
});

describe("THE SECOND BLOCKER — sub-floor days are a SUBSET of missing days", () => {
  // system_capture_health_models.py:536-537
  //     effective_present = set(present_raw) - set(sub_floor)
  //     missing = [d for d in expected_dates if d not in effective_present]
  //
  // So a `missing_dates_count > 0` test fires for thin days too. Ordering the
  // branches missing-first made the "those days are thin" sentence unreachable
  // and reported every thin day as one that never landed.

  it("calls a thin capture today thin, not a feed that failed to run", () => {
    // A capture that lands thin TODAY sets stale=True (today is in present_raw
    // but not in effective_present) while last_capture_date is still today —
    // `observed` is filled at :500-501, BEFORE the density pass. The old code
    // printed "Last ran Sunday, August 30. It hasn't run when it was due."
    const thinToday = store({
      store_status: "degraded",
      staleness: {
        expected_by: "2026-08-30T12:40:00-04:00",
        grace_hours: 3,
        last_capture_date: TODAY,
        stale: true,
      },
      density: { ...store().density, sub_floor_dates: [TODAY] },
      timeline: { ...store().timeline, missing_dates_count: 1 },
    });
    const row = feedRow(thinToday, TODAY);
    expect(row.ran).toMatch(/Last ran Sunday, August 30\./);
    expect(row.trouble).toBe("thin-today");
    expect(row.note).toMatch(/It ran today, but came back with far fewer rows/i);
    expect(row.note).not.toMatch(/hasn't run when it was due/i);
    // Today was the only thin day and the only missing day, so there is no
    // history clause left to print.
    expect(row.note).not.toMatch(/never landed/);
  });

  it("reaches the thin-history branch that used to be dead code", () => {
    const thinPast = store({
      store_status: "degraded",
      density: { ...store().density, sub_floor_dates: ["2026-08-20", "2026-08-21"] },
      timeline: { ...store().timeline, missing_dates_count: 2 },
    });
    const row = feedRow(thinPast, TODAY);
    expect(row.trouble).toBe("thin-history");
    expect(row.note).toMatch(
      /2 days of its 53-day history came back with far fewer rows/i,
    );
    expect(row.note).not.toMatch(/never landed/);
  });

  it("separates the two counts when both are true", () => {
    const both = store({
      store_status: "degraded",
      density: { ...store().density, sub_floor_dates: ["2026-08-20"] },
      timeline: { ...store().timeline, missing_dates_count: 4 },
    });
    const row = feedRow(both, TODAY);
    expect(row.note).toMatch(/3 days of its 53-day history never landed/);
    expect(row.note).toMatch(/one day came back thin/);
  });
});

describe("the row names its own ignorance rather than guessing", () => {
  it("says so when the store could not be read at all", () => {
    const absent = store({ store_status: "degraded", store_presence: "absent" });
    const row = feedRow(absent, TODAY);
    expect(row.trouble).toBe("unreadable");
    expect(row.note).toMatch(/couldn't read this feed's history at all/i);
    expect(row.note).not.toMatch(/ran today/i);
  });

  it("falls back to naming the caveat, then to naming nothing", () => {
    const caveat = store({
      store_status: "degraded",
      caveats: ["density_baseline_insufficient"],
    });
    expect(feedRow(caveat, TODAY).note).toMatch(/flagged something about the shape/i);

    const unnamed = store({ store_status: "degraded" });
    expect(feedRow(unnamed, TODAY).note).toMatch(/can't name from what it was given/i);
  });
});

describe("the header's shared-reason clause is only built over a shared reason", () => {
  it("stays general when the troubled feeds are troubled differently", () => {
    const gapped = store({
      store_id: "fc_forward_capture",
      store_status: "degraded",
      timeline: { ...store().timeline, missing_dates_count: 2 },
    });
    const notDue = store({
      store_status: "degraded",
      staleness: { ...store().staleness, last_capture_date: "2026-08-29" },
      timeline: { ...store().timeline, missing_dates_count: 2 },
    });
    const feeds = feedHealth(response([gapped, notDue]));
    if (feeds.kind !== "read") throw new Error("unreachable");
    expect(feeds.allGaps).toBe(false);
    expect(freshnessLine("Report.", false, feeds).sentence).toMatch(
      /2 of our 2 daily feeds need attention/,
    );
  });

  it("does not collapse a caveat-degraded feed into the gaps clause", () => {
    // has_class_b_caveat is a FOURTH independent input to store_status
    // (system_capture_health_models.py:576-580). A feed degraded by a caveat
    // alone must not be summarised to the reader as gaps.
    const gapped = store({
      store_id: "fc_forward_capture",
      store_status: "degraded",
      timeline: { ...store().timeline, missing_dates_count: 2 },
    });
    const caveated = store({ store_status: "degraded", caveats: ["odd_shape"] });
    const feeds = feedHealth(response([gapped, caveated]));
    if (feeds.kind !== "read") throw new Error("unreachable");
    expect(feeds.allGaps).toBe(false);
  });
});

describe("the all-clear says how far it reaches", () => {
  it("claims today only when every feed's capture for today is in", () => {
    const feeds = feedHealth(response([store()]));
    if (feeds.kind !== "read") throw new Error("unreachable");
    expect(feeds.allRanToday).toBe(true);
    expect(freshnessLine("Report.", false, feeds).sentence).toMatch(
      /Our daily feed is in for today\./,
    );
  });

  it("falls to the weaker claim when an ok feed simply is not due yet", () => {
    // store_status "ok" means nothing missing, nothing stale, nothing thin, no
    // caveat — all of which a store can satisfy while today's capture has not
    // come due. "Up to date" was carrying more than the field can bear.
    const notDueYet = store({
      staleness: { ...store().staleness, last_capture_date: "2026-08-29" },
    });
    const feeds = feedHealth(response([notDueYet]));
    if (feeds.kind !== "read") throw new Error("unreachable");
    expect(feeds.allRanToday).toBe(false);
    const line = freshnessLine("Report.", false, feeds);
    expect(line.sentence).toMatch(/has landed everything it was due for/);
    expect(line.sentence).not.toMatch(/in for today/);
    expect(line.status).toBe("ok");
  });

  it("never turns an unread endpoint into an all-clear", () => {
    const line = freshnessLine("Report.", false, feedHealth(null));
    expect(line.sentence).toMatch(/couldn't reach the feed check/i);
    expect(line.sentence).not.toMatch(/in for today|landed everything/i);
    expect(line.status).toBe("unknown");
  });
});

describe("today is taken from the payload's own clock, not the browser's", () => {
  it("uses checked_at, so a viewer in another timezone reads the same sheet", () => {
    // Every date in this payload was computed against the producer's `now` in
    // America/New_York (system_capture_health_models.py:465). A late-evening
    // Pacific viewer would otherwise disagree about what day it is and call a
    // feed late that ran on time.
    const feeds = feedHealth(response([store()], "2026-08-30T23:30:00-04:00"));
    if (feeds.kind !== "read") throw new Error("unreachable");
    expect(feeds.rows[0]?.ranToday).toBe(true);
  });

  it("declines to judge today at all when checked_at is unreadable", () => {
    const feeds = feedHealth(response([store()], "not-a-timestamp"));
    if (feeds.kind !== "read") throw new Error("unreachable");
    expect(feeds.rows[0]?.ranToday).toBeNull();
    expect(feeds.allRanToday).toBe(false);
    expect(freshnessLine("Report.", false, feeds).sentence).not.toMatch(/in for today/);
  });
});
