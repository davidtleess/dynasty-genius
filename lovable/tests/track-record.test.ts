// DG-208 — the track record client. Written before the module it tests.
//
// Every test names the thing it prevents. The screen this feeds exists because David's reviewer said
// the decision edge is unverified, so its failure mode is not a crash: it is quietly implying a record
// that does not exist, or turning an absence into a number.
import { test } from "node:test";
import assert from "node:assert/strict";

import { views, captureResults } from "./fixtures/track-record-views.ts";
import {
  readTrackRecordView,
  readCaptureResult,
  saveEnablement,
  boardSourceFromBundle,
  SOURCE_FIELDS,
  TrackRecordError,
} from "../src/lib/dg/track-record.ts";

const clone = (value: unknown) => JSON.parse(JSON.stringify(value));

// --- the view parses, and refuses rather than coercing -------------------------------------------

test("a well formed view parses", () => {
  const view = readTrackRecordView(clone(views.enrolledPending));
  assert.equal(view.status, "available");
  assert.equal(view.snapshots.length, 1);
  assert.equal(view.production.state, "awaiting_horizon");
});

test("a malformed required field is refused, never turned into null", () => {
  const broken = clone(views.enrolledPending);
  broken.production.counts.eligible = "three";
  assert.throws(() => readTrackRecordView(broken), TrackRecordError);
});

test("an unknown stream state is refused rather than displayed as a word", () => {
  const broken = clone(views.enrolledPending);
  broken.production.state = "looks_good";
  assert.throws(() => readTrackRecordView(broken), TrackRecordError);
});

test("a wrong schema version is refused", () => {
  const broken = clone(views.enrolledPending);
  broken.schema_version = "track_record.view.v2";
  assert.throws(() => readTrackRecordView(broken), TrackRecordError);
});

// --- the distinctions the screen exists to keep ---------------------------------------------------

test("a transport failure is not an empty archive", () => {
  const view = readTrackRecordView(clone(views.unavailable));
  assert.equal(view.status, "unavailable");
  assert.ok(view.reason && view.reason.length > 0);
  // An empty snapshot list here means "we could not look", never "there is nothing".
  assert.equal(view.snapshots.length, 0);
  assert.equal(readTrackRecordView(clone(views.empty)).status, "available");
});

test("observations are always present, so a pending reading can show what was frozen", () => {
  for (const name of Object.keys(views) as (keyof typeof views)[]) {
    const view = readTrackRecordView(clone(views[name]));
    assert.ok(Array.isArray(view.production.observations), `${name} production`);
    assert.ok(Array.isArray(view.market.observations), `${name} market`);
  }
  const pending = readTrackRecordView(clone(views.enrolledPending));
  assert.ok(pending.production.observations.length > 0);
  assert.equal(pending.production.result, null, "a pending stream carries no result");
});

test("a pending observation carries a forecast but no outcome and no error", () => {
  const [row] = readTrackRecordView(clone(views.enrolledPending)).production.observations;
  assert.equal(typeof row.forecast, "number");
  assert.equal(row.outcome, null);
  assert.equal(row.error, null);
});

test("an absent value stays null and is never read as zero", () => {
  const rows = readTrackRecordView(clone(views.enrolledPending)).production.observations;
  const unforecast = rows.find((r) => r.provenance === "unforecast");
  assert.ok(unforecast);
  assert.equal(unforecast.forecast, null);
  assert.equal(unforecast.baseline, null);
  assert.notEqual(unforecast.forecast, 0);
  assert.ok(unforecast.reason, "an absence has to say why");
});

test("both production baselines survive on one row", () => {
  const [row] = readTrackRecordView(clone(views.enrolledPending)).production.observations;
  assert.equal(typeof row.baseline, "number");
  assert.equal(typeof row.baseline_position_median, "number");
});

// --- saving ----------------------------------------------------------------------------------------

test("the three capture outcomes stay distinguishable", () => {
  assert.equal(readCaptureResult(clone(captureResults.saved)).enrollment_status, "saved");
  assert.equal(
    readCaptureResult(clone(captureResults.alreadySaved)).snapshot_status,
    "already_saved",
  );
  const partial = readCaptureResult(clone(captureResults.partial));
  assert.equal(partial.snapshot_status, "saved");
  assert.equal(partial.enrollment_status, "input_unavailable");
  assert.ok(partial.reason, "a partial success has to say what did not happen");
});

// --- when the save button may be offered -------------------------------------------------------------

const expected = views.empty.save_capability.expected;

test("save is offered when the board reading matches what the server expects", () => {
  const decision = saveEnablement({ ...expected }, { enabled: true, reason: null, expected });
  assert.equal(decision.enabled, true);
});

test("save is refused, with a reason, when the board carries a different reading", () => {
  const decision = saveEnablement(
    { ...expected, report_run: "20260907T000000Z" },
    { enabled: true, reason: null, expected },
  );
  assert.equal(decision.enabled, false);
  assert.match(decision.reason, /different reading|does not match/i);
});

test("an incomplete board reading is refused in the manager's language, never by field name", () => {
  // A silently disabled button is indistinguishable from a broken one, so it must give a reason.
  // But the missing field is a pipeline identifier, and naming it on screen is the habit this
  // product ruled out. Both halves are asserted.
  for (const field of SOURCE_FIELDS) {
    const partial = { ...expected } as Record<string, unknown>;
    delete partial[field];
    const decision = saveEnablement(partial, { enabled: true, reason: null, expected });
    assert.equal(decision.enabled, false, `${field} missing should refuse`);
    assert.match(decision.reason, /missing source details/i);
    assert.doesNotMatch(
      decision.reason,
      /sha256|catalog|hash|report_run|_/i,
      `${field}: no pipeline identifier may reach the screen`,
    );
  }
});

test("the board's six fields are narrowed at runtime, and a partial tuple is not a mismatch", () => {
  assert.deepEqual(boardSourceFromBundle({ ...expected, extra: 1 }), { ...expected });
  assert.equal(boardSourceFromBundle({ ...expected, catalog_run: "" }), null);
  assert.equal(boardSourceFromBundle(null), null);
});

test("save stays refused when the server says so, and repeats the server's reason", () => {
  const decision = saveEnablement(
    { ...expected },
    { enabled: false, reason: "No archive root is configured.", expected: null },
  );
  assert.equal(decision.enabled, false);
  assert.equal(decision.reason, "No archive root is configured.");
});

test("a stream with no observations list is refused, not silently emptied", () => {
  // Caught by mutation: every fixture carries observations, so asserting they are an array proved
  // nothing. The contract says the list is ALWAYS present, so its absence is a breach to report, not
  // an empty list to invent — the difference decides whether a pending reading shows its forecasts.
  const broken = JSON.parse(JSON.stringify(views.enrolledPending));
  delete broken.production.observations;
  assert.throws(() => readTrackRecordView(broken), TrackRecordError);
});

test("a response for a different saved reading cannot appear under the requested URL", async () => {
  const { trackRecordQuery } = await import("../src/lib/dg/track-record.ts");
  const previous = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify(views.enrolledPending), {
      headers: { "content-type": "application/json" },
    });
  try {
    const query = trackRecordQuery("b".repeat(64));
    await assert.rejects(() => query.queryFn!({} as never), /different saved reading/);
  } finally {
    globalThis.fetch = previous;
  }
});

test("an invalid saved link is refused before fetching a replacement", async () => {
  const { trackRecordQuery } = await import("../src/lib/dg/track-record.ts");
  const previous = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return new Response(JSON.stringify(views.enrolledPending));
  };
  try {
    const query = trackRecordQuery("invalid");
    await assert.rejects(() => query.queryFn!({} as never), /saved-reading link is invalid/);
    assert.equal(calls, 0);
  } finally {
    globalThis.fetch = previous;
  }
});
