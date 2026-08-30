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
 *
 * PANEL FIX — THE BLOCKER, AND IT WAS THE WHOLE POINT OF THE MODULE.
 * The first cut of this file inferred "It ran today" from `stale === false`.
 * The producer does not entail that, and the gap is widest at exactly the hour
 * this page is named for:
 *
 *     end_date = today if now_local >= deadline else today - timedelta(days=1)
 *     stale    = bool(expected_dates) and end_date == today
 *                and today not in effective_present
 *     (system_capture_health_models.py:473, :547)
 *
 * Before a store's deadline `end_date` is YESTERDAY, so `stale` is False
 * whether today's capture landed or has simply not come due yet. All three
 * live stores are due between 12:00 and 12:45 ET (`expected_by`, grace_hours
 * 3), so on David's 7am read every feed took the `!stale` branch and was
 * printed as having "ran today" — one clause after the same row said it last
 * ran yesterday. The row now reads `last_capture_date`, which is the actual
 * answer to "did it run today", and says "isn't in yet, and isn't due until
 * 12:45 PM EDT" when that is what is true.
 *
 * SECOND PRODUCER FACT, same class: sub-floor days are a SUBSET of missing
 * days, not a separate bucket —
 *
 *     effective_present = set(present_raw) - set(sub_floor)
 *     missing = [d for d in expected_dates if d not in effective_present]
 *     (system_capture_health_models.py:536-537)
 *
 * — so a `missing_dates_count > 0` test fires for thin days too, and the old
 * branch order made the "those days are thin" sentence unreachable while
 * reporting every thin day as one that "never landed". They landed; they came
 * back under the density floor. The two counts are separated here by
 * subtraction over the producer's own numbers, and a capture that lands thin
 * TODAY (which sets `stale`, because today is not in `effective_present`, while
 * `last_capture_date` is still today — `observed` is filled at :500-501, before
 * the density pass) is named as thin rather than as a feed that did not run.
 */
import type { CaptureHealthResponse, StoreHealth } from "../lib/api/types.gen";
import { feedName } from "../lib/copy";

const FEED_DATE = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  weekday: "long",
  month: "long",
  day: "numeric",
});

/**
 * The calendar day a timestamp falls on, as the producer's own `YYYY-MM-DD`.
 *
 * America/New_York because that is the zone every date in this payload is
 * computed in (`tz = ZoneInfo(timezone)`, system_capture_health_models.py:465),
 * and `en-CA` because it is the locale that formats a date as `2026-08-30`.
 */
const DAY_KEY = new Intl.DateTimeFormat("en-CA", {
  timeZone: "America/New_York",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

const DUE_TIME = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  hour: "numeric",
  minute: "2-digit",
  timeZoneName: "short",
});

/** A calendar date in words. Noon-anchored (see morningRead.ts `weekday`). */
function dayWords(date: string): string {
  const parsed = Date.parse(`${date}T12:00:00`);
  return Number.isNaN(parsed) ? date : FEED_DATE.format(new Date(parsed));
}

/**
 * Which day "today" is, taken from the SERVER's own observation time.
 *
 * Not the browser clock: every date in this payload was computed against the
 * producer's `now`, and a viewer in Los Angeles at 10pm would otherwise
 * disagree with the payload about what day it is and call a feed late that ran
 * on time. Unparseable input returns null, and null makes every branch below
 * decline to say anything about today rather than guess.
 */
export function captureDay(checkedAt: string | null | undefined): string | null {
  if (typeof checkedAt !== "string") return null;
  const ms = Date.parse(checkedAt);
  return Number.isNaN(ms) ? null : DAY_KEY.format(new Date(ms));
}

function dueWords(expectedBy: string | null | undefined): string | null {
  if (typeof expectedBy !== "string") return null;
  const ms = Date.parse(expectedBy);
  return Number.isNaN(ms) ? null : DUE_TIME.format(new Date(ms));
}

function daysWord(count: number): string {
  return count === 1 ? "one day" : `${count} days`;
}

/**
 * The history clause can either follow a today-clause or open the note on its
 * own, and it reads as a sentence either way. Found in the browser, not by a
 * test: with today's capture in, there is nothing to say about today, so the
 * note began "one day of its 68-day history never landed" — a lowercase word
 * opening a sentence, directly after "Last ran Sunday, August 30."
 */
function openSentence(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/**
 * WHICH condition the row is naming — the header reads this to decide whether
 * every troubled feed is troubled for the same reason, so a shared-reason
 * sentence can never be built over feeds that do not actually share one.
 */
export type FeedTrouble =
  | "none"
  | "unreadable"
  | "late"
  | "not-due-yet"
  | "day-unknown"
  | "thin-today"
  | "gaps"
  | "thin-history"
  | "caveat"
  | "unnamed";

export type FeedRow = {
  id: string;
  name: string;
  ok: boolean;
  /** "Last ran Sunday, August 30." — or the honest absence of a last run. */
  ran: string;
  /** Whether today's capture is in. `null` when we cannot tell what day it is. */
  ranToday: boolean | null;
  /** One sentence, only when something is actually wrong. */
  note: string | null;
  trouble: FeedTrouble;
};

export function feedRow(store: StoreHealth, today: string | null): FeedRow {
  const last = store.staleness.last_capture_date;
  const ran =
    last === null ? "We have no record of it running." : `Last ran ${dayWords(last)}.`;
  // A store with no capture on record has definitively not run today; only an
  // unreadable clock leaves the question genuinely open.
  const ranToday = today === null ? null : last !== null && last === today;
  const ok = store.store_status === "ok";
  const trouble = ok ? "none" : classify(store, today, ranToday);
  return {
    id: store.store_id,
    name: feedName(store.store_id),
    ok,
    ran,
    ranToday,
    note: ok ? null : troubleSentence(store, today, trouble),
    trouble,
  };
}

/**
 * The four degrading conditions, resolved to the ONE this row is naming.
 *
 * Order is by what changes the meaning of today's numbers: whether today's
 * capture is in at all leads, then what its history looks like, then a caveat
 * the row cannot see, then an admission that the row cannot name the cause.
 */
function classify(
  store: StoreHealth,
  today: string | null,
  ranToday: boolean | null,
): FeedTrouble {
  if (store.store_presence === "absent") return "unreadable";
  const thinToday = today !== null && store.density.sub_floor_dates.includes(today);
  if (thinToday) return "thin-today";
  if (ranToday === false) {
    return store.staleness.stale ? "late" : "not-due-yet";
  }
  if (ranToday === null) return "day-unknown";
  const { neverLanded, thinPast } = historyCounts(store, today, false);
  if (neverLanded > 0) return "gaps";
  if (thinPast > 0) return "thin-history";
  return store.caveats.length > 0 ? "caveat" : "unnamed";
}

/**
 * How many days never landed, and how many landed thin — kept apart.
 *
 * `missing_dates_count` counts BOTH (sub_floor ⊆ missing, :536-537), so the
 * never-landed count is the difference. Today is subtracted out when the
 * today-clause has already accounted for it, so a feed that has not run yet is
 * not also billed a history gap for the same day.
 */
function historyCounts(
  store: StoreHealth,
  today: string | null,
  todayCounted: boolean,
): { neverLanded: number; thinPast: number } {
  const thinDates = store.density.sub_floor_dates;
  const thinToday = today !== null && thinDates.includes(today);
  return {
    neverLanded: Math.max(
      0,
      store.timeline.missing_dates_count - thinDates.length - (todayCounted ? 1 : 0),
    ),
    thinPast: thinDates.length - (thinToday ? 1 : 0),
  };
}

function troubleSentence(
  store: StoreHealth,
  today: string | null,
  trouble: FeedTrouble,
): string {
  if (trouble === "unreadable") {
    return "We couldn't read this feed's history at all, so nothing on this page is measured from it.";
  }

  // `stale` means today was due and today is not in `effective_present`, so
  // today itself is one of the missing days. The today-clause says that; the
  // history clause must not bill it a second time.
  const todayCounted = trouble === "late";
  const { neverLanded, thinPast } = historyCounts(store, today, todayCounted);
  const days = store.timeline.expected_days;

  let todayClause: string | null = null;
  if (trouble === "thin-today") {
    todayClause =
      "It ran today, but came back with far fewer rows than usual, so today's read is thin.";
  } else if (trouble === "late") {
    todayClause =
      "It hasn't run when it was due, so anything it feeds is the last verified read rather than today's.";
  } else if (trouble === "not-due-yet") {
    const due = dueWords(store.staleness.expected_by);
    todayClause =
      due === null
        ? "Today's capture isn't in yet, though it isn't overdue either."
        : `Today's capture isn't in yet — it isn't due until ${due}.`;
  }

  let historyClause: string | null = null;
  if (neverLanded > 0 && thinPast > 0) {
    historyClause = `${daysWord(neverLanded)} of its ${days}-day history never landed and ${daysWord(thinPast)} came back thin, so trend lines drawn from it have gaps.`;
  } else if (neverLanded > 0) {
    historyClause = `${daysWord(neverLanded)} of its ${days}-day history never landed, so trend lines drawn from it have small gaps.`;
  } else if (thinPast > 0) {
    historyClause = `${daysWord(thinPast)} of its ${days}-day history came back with far fewer rows than usual, so those days are thin.`;
  }

  const said = [
    todayClause,
    historyClause === null
      ? null
      : todayClause === null
        ? openSentence(historyClause)
        : historyClause,
  ]
    .filter((part) => part !== null)
    .join(" ");
  if (said !== "") return said;
  if (store.caveats.length > 0) {
    return "It flagged something about the shape of its data — the full health panel in the shell has the detail.";
  }
  return "It reported a problem this sheet can't name from what it was given — the full health panel in the shell has the detail.";
}

export type FeedHealth =
  | { kind: "unread" }
  | {
      kind: "read";
      rows: FeedRow[];
      behind: number;
      /** Every troubled feed ran today and is troubled only by history gaps. */
      allGaps: boolean;
      /** Every feed's capture for today is in. `false` when any is not, or unknown. */
      allRanToday: boolean;
    };

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
  const today = captureDay(data.checked_at);
  const rows = data.stores.map((store) => feedRow(store, today));
  const troubled = rows.filter((row) => !row.ok);
  return {
    kind: "read",
    rows,
    behind: troubled.length,
    // Whether every troubled feed is troubled for the SAME reason decides
    // whether the header can name that reason in one clause or has to stay
    // general and let the rows speak. "gaps" is only ever assigned to a feed
    // whose capture for today is in, so the header's "ran today" is entailed.
    allGaps: troubled.length > 0 && troubled.every((row) => row.trouble === "gaps"),
    allRanToday: rows.length > 0 && rows.every((row) => row.ranToday === true),
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
 *
 * The all-clear is two branches, not one, for the same reason the rows are:
 * a store can be `ok` — nothing missing, nothing stale, nothing thin — while
 * today's capture is simply not due yet, and "up to date" would then be
 * carrying more weight than `store_status` can bear.
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
    const clause =
      total === 1
        ? feeds.allRanToday
          ? "Our daily feed is in for today."
          : "Our daily feed has landed everything it was due for."
        : feeds.allRanToday
          ? `All ${total} of our daily feeds are in for today.`
          : `All ${total} of our daily feeds have landed everything they were due for.`;
    return {
      sentence: `${reportSentence} ${clause}`,
      status: reportStale ? "attention" : "ok",
    };
  }
  const clause = feeds.allGaps
    ? `${feeds.behind} of our ${total} daily feeds ran today but have gaps earlier in their history`
    : `${feeds.behind} of our ${total} daily feeds need attention`;
  return { sentence: `${reportSentence} ${clause}.`, status: "attention" };
}
