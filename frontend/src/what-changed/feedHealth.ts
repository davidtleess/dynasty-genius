/**
 * DG-113 — the health sheet, in words.
 *
 * The front page used to carry a monospace "Partial Market Sync" tape, a FEED
 * DIAGNOSTICS panel and a RECEIPTS panel down the right-hand rail. Spec §2.1
 * replaces all three with ONE freshness sentence and a dot, and puts their
 * content one press down in a health sheet that lists each feed as a plain row.
 *
 * The trap this module exists to avoid is naming the wrong illness. The spec's
 * own example sentence is "two of nine overnight feeds ran a day behind", and
 * on the live payload that would be false three times over: all three feeds ran
 * this morning, none is stale, and what actually makes two of them `degraded`
 * is a missing day earlier in their history. `store_status` is one word over
 * four independent conditions —
 *
 *     status = "ok" if not missing and not stale and not sub_floor
 *                   and not has_class_b_caveat else "degraded"
 *     (app/api/routes/system_capture_health_models.py:576-580)
 *
 * — so the row has to read the four conditions and say which one is true, and
 * fall back to naming its own ignorance rather than picking the likeliest.
 */
import type { CaptureHealthResponse, StoreHealth } from "../lib/api/types.gen";
import { feedName } from "../lib/copy";

const FEED_DATE = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  weekday: "long",
  month: "long",
  day: "numeric",
});

/** A calendar date in words. Noon-anchored (see morningRead.ts `weekday`). */
function dayWords(date: string): string {
  const parsed = Date.parse(`${date}T12:00:00`);
  return Number.isNaN(parsed) ? date : FEED_DATE.format(new Date(parsed));
}

export type FeedRow = {
  id: string;
  name: string;
  ok: boolean;
  /** "Last ran Sunday, August 30." — or the honest absence of a last run. */
  ran: string;
  /** One sentence, only when something is actually wrong. */
  note: string | null;
};

export function feedRow(store: StoreHealth): FeedRow {
  const last = store.staleness.last_capture_date;
  const ran =
    last === null ? "We have no record of it running." : `Last ran ${dayWords(last)}.`;
  return {
    id: store.store_id,
    name: feedName(store.store_id),
    ok: store.store_status === "ok",
    ran,
    note: store.store_status === "ok" ? null : troubleSentence(store),
  };
}

/**
 * WHICH of the four degrading conditions is true, said as a sentence.
 *
 * Order matters: lateness is the one that changes what today's numbers mean, so
 * it leads. Gaps come next because they are what the trend lines are drawn
 * from. The final branch is the important one — a `degraded` store with none of
 * the three visible conditions means a class-B caveat the row cannot see, and
 * the row says exactly that instead of guessing at a cause.
 */
function troubleSentence(store: StoreHealth): string {
  if (store.staleness.stale) {
    return "It hasn't run when it was due, so anything it feeds is the last verified read rather than today's.";
  }
  const missing = store.timeline.missing_dates_count;
  if (missing > 0) {
    const days = missing === 1 ? "one day" : `${missing} days`;
    return `It ran today, but ${days} of its ${store.timeline.expected_days}-day history never landed, so trend lines drawn from it have small gaps.`;
  }
  if (store.density.sub_floor_dates.length > 0) {
    const thin = store.density.sub_floor_dates.length;
    return `It ran every day, but ${thin === 1 ? "one day" : `${thin} days`} came back with far fewer rows than usual, so those days are thin.`;
  }
  if (store.caveats.length > 0) {
    return "It flagged something about the shape of its data — the full health panel in the shell has the detail.";
  }
  return "It reported a problem this sheet can't name from what it was given — the full health panel in the shell has the detail.";
}

export type FeedHealth =
  | { kind: "unread" }
  | { kind: "read"; rows: FeedRow[]; behind: number; allGaps: boolean };

/**
 * The whole feed picture, or an honest admission that we could not read it.
 *
 * `unread` is a real state and it must never collapse into the green one: a
 * capture-health endpoint that did not answer is not evidence that the feeds
 * are fine, and "all feeds ran on time" is the single easiest false sentence
 * this page could print.
 */
export function feedHealth(data: CaptureHealthResponse | null): FeedHealth {
  if (data === null) return { kind: "unread" };
  const rows = data.stores.map(feedRow);
  const troubled = data.stores.filter((store) => store.store_status !== "ok");
  return {
    kind: "read",
    rows,
    behind: troubled.length,
    // Whether every troubled feed is troubled for the SAME reason decides
    // whether the header can name that reason in one clause or has to stay
    // general and let the rows speak.
    allGaps:
      troubled.length > 0 &&
      troubled.every(
        (store) =>
          !store.staleness.stale &&
          store.timeline.missing_dates_count > 0 &&
          store.density.sub_floor_dates.length === 0,
      ),
  };
}

/**
 * The one freshness sentence, and the dot beside it.
 *
 * Two facts on two different clocks, and they are kept apart on purpose: the
 * REPORT's own age (is what I am reading from this morning?) and the FEEDS'
 * health (is the machinery behind it whole?). The report sentence is handed in
 * already built by the surface, which owns the staleness threshold; this adds
 * the feed clause only when there is a feed fact to add, and never claims
 * anything about feeds it could not read.
 */
export function freshnessLine(
  reportSentence: string,
  reportStale: boolean,
  feeds: FeedHealth,
): { sentence: string; status: "ok" | "attention" | "unknown" } {
  if (feeds.kind === "unread") {
    return {
      sentence: `${reportSentence} We couldn't reach the feed check this morning, so we can't tell you how the feeds behind it are doing.`,
      status: reportStale ? "attention" : "unknown",
    };
  }
  const total = feeds.rows.length;
  if (feeds.behind === 0) {
    return {
      sentence: `${reportSentence} All ${total === 1 ? "of our daily feeds is" : `${total} of our daily feeds are`} complete and up to date.`,
      status: reportStale ? "attention" : "ok",
    };
  }
  const clause = feeds.allGaps
    ? `${feeds.behind} of our ${total} daily feeds ran today but have gaps earlier in their history`
    : `${feeds.behind} of our ${total} daily feeds need attention`;
  return { sentence: `${reportSentence} ${clause}.`, status: "attention" };
}
