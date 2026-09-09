/**
 * DG-208 — the track record client. Mine alone; not part of the shared queries module.
 *
 * This reads a private archive through root's same-origin bridge. It parses strictly and refuses a
 * malformed required field rather than coercing it to null, because every failure this screen can have
 * is the same failure: implying a record that does not exist, or turning an absence into a number.
 *
 * Three distinctions it exists to keep:
 *   · a transport failure is not an empty archive;
 *   · an enrolled but ungraded reading has observations and no result, which is not a grade;
 *   · a saved reading and an enrolled evaluation are separate outcomes of one deliberate save.
 */
import { queryOptions } from "@tanstack/react-query";

export class TrackRecordError extends Error {}

const STREAM_STATES = [
  "not_registered",
  "awaiting_horizon",
  "awaiting_capture",
  "input_unavailable",
  "cutoff_ineligible",
  "insufficient_evidence",
  "graded",
] as const;
export type StreamState = (typeof STREAM_STATES)[number];

export const SOURCE_FIELDS = [
  "report_run",
  "report_sha256",
  "market_sha256",
  "league_sha256",
  "catalog_run",
  "catalog_content_sha256",
] as const;
export type SixSourceFields = Record<(typeof SOURCE_FIELDS)[number], string>;

export type ResultRow = {
  sleeper_id: string;
  name: string;
  position: string;
  producer: string | null;
  provenance: string;
  forecast: number | null;
  baseline: number | null;
  baseline_position_median: number | null;
  outcome: number | null;
  error: number | null;
  reason: string | null;
};
export type Comparison = {
  id: string;
  label: string;
  units: string;
  estimate: number | null;
  interval95: [number, number] | null;
  state: "favorable" | "unfavorable" | "inconclusive" | "insufficient";
  note: string;
  eligible: number;
  scored: number;
};
export type Result = {
  summary: string;
  comparisons: Comparison[];
  rows: ResultRow[];
  details: { label: string; value: string }[];
};
export type Stream = {
  state: StreamState;
  reason: string | null;
  window: { label: string; start_at: string | null; end_at: string | null };
  provenance_class: string;
  counts: { eligible: number; scored: number; missing: number };
  observations: ResultRow[];
  result: Result | null;
};
export type SafeReceipt = {
  snapshot_id: string;
  saved_at: string;
  forecast_date: string;
  market_as_of: string;
  ownership_as_of: string;
  report_generated_at: string | null;
  catalog_generated_at: string | null;
  years: number[];
  counts: Record<string, number>;
  source: SixSourceFields;
  evaluation_status: "ungraded";
  evaluation_plan: Record<string, unknown>;
};
export type SaveCapability = {
  enabled: boolean;
  reason: string | null;
  expected: SixSourceFields | null;
};
export type TrackRecordView = {
  status: "available" | "not_configured" | "unavailable";
  reason: string | null;
  snapshots: SafeReceipt[];
  selected: SafeReceipt | null;
  production: Stream;
  market: Stream;
  save_capability: SaveCapability;
};
export type CaptureResult = {
  snapshot_status: "saved" | "already_saved";
  snapshot: SafeReceipt;
  enrollment_status: "saved" | "already_saved" | "input_unavailable";
  reason: string | null;
};

// --- strict readers. Each names the field, so a refusal is actionable rather than "invalid". --------

const object = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
function need(condition: unknown, what: string): asserts condition {
  if (!condition) throw new TrackRecordError(`track record view: ${what}`);
}
const str = (v: unknown, what: string): string => {
  need(typeof v === "string" && v.length > 0, `${what} is missing`);
  return v as string;
};
const strOrNull = (v: unknown, what: string): string | null => {
  need(v === null || typeof v === "string", `${what} is neither text nor absent`);
  return (v as string) ?? null;
};
const int = (v: unknown, what: string): number => {
  need(Number.isInteger(v), `${what} is not a whole number`);
  return v as number;
};
/** Absent stays absent. A number that is not finite is a refusal, never a zero. */
const numOrNull = (v: unknown, what: string): number | null => {
  if (v === null || v === undefined) return null;
  need(typeof v === "number" && Number.isFinite(v), `${what} is not a finite number`);
  return v as number;
};

function readRow(value: unknown, what: string): ResultRow {
  need(object(value), `${what} is not a row`);
  const v = value as Record<string, unknown>;
  return {
    sleeper_id: str(v["sleeper_id"], `${what} sleeper_id`),
    name: str(v["name"], `${what} name`),
    position: str(v["position"], `${what} position`),
    producer: strOrNull(v["producer"] ?? null, `${what} producer`),
    provenance: str(v["provenance"], `${what} provenance`),
    forecast: numOrNull(v["forecast"], `${what} forecast`),
    baseline: numOrNull(v["baseline"], `${what} baseline`),
    baseline_position_median: numOrNull(v["baseline_position_median"], `${what} position median`),
    outcome: numOrNull(v["outcome"], `${what} outcome`),
    error: numOrNull(v["error"], `${what} error`),
    reason: strOrNull(v["reason"] ?? null, `${what} reason`),
  };
}

function readResult(value: unknown): Result | null {
  if (value === null || value === undefined) return null;
  need(object(value), "a result is not an object");
  const v = value as Record<string, unknown>;
  need(
    Array.isArray(v["comparisons"]) && Array.isArray(v["rows"]) && Array.isArray(v["details"]),
    "a result is missing its comparisons, rows or details",
  );
  return {
    summary: str(v["summary"], "result summary"),
    comparisons: (v["comparisons"] as unknown[]).map((c, i) => {
      need(object(c), `comparison ${i} is not an object`);
      const x = c as Record<string, unknown>;
      const interval = x["interval95"];
      need(
        interval === null ||
          interval === undefined ||
          (Array.isArray(interval) && interval.length === 2 && interval.every(Number.isFinite)),
        `comparison ${i} interval is neither absent nor two finite bounds`,
      );
      const state = x["state"];
      need(
        ["favorable", "unfavorable", "inconclusive", "insufficient"].includes(state as string),
        `comparison ${i} state ${String(state)} is not one this screen can render`,
      );
      return {
        id: str(x["id"], `comparison ${i} id`),
        label: str(x["label"], `comparison ${i} label`),
        units: str(x["units"], `comparison ${i} units`),
        estimate: numOrNull(x["estimate"], `comparison ${i} estimate`),
        interval95: (interval as [number, number] | null) ?? null,
        state: state as Comparison["state"],
        note: str(x["note"], `comparison ${i} note`),
        eligible: int(x["eligible"], `comparison ${i} eligible`),
        scored: int(x["scored"], `comparison ${i} scored`),
      };
    }),
    rows: (v["rows"] as unknown[]).map((r, i) => readRow(r, `result row ${i}`)),
    details: (v["details"] as unknown[]).map((d, i) => {
      need(object(d), `detail ${i} is not an object`);
      const x = d as Record<string, unknown>;
      return {
        label: str(x["label"], `detail ${i} label`),
        value: str(x["value"], `detail ${i} value`),
      };
    }),
  };
}

function readStream(value: unknown, what: string): Stream {
  need(object(value), `${what} is missing`);
  const v = value as Record<string, unknown>;
  need(
    STREAM_STATES.includes(v["state"] as StreamState),
    `${what} state ${String(v["state"])} is not one this screen can render`,
  );
  need(object(v["window"]), `${what} window is missing`);
  need(object(v["counts"]), `${what} counts are missing`);
  // Always an array, even when nothing can be shown. A missing observations list is a contract breach,
  // not an empty one, because the difference decides whether a pending reading can show its forecasts.
  need(
    Array.isArray(v["observations"]),
    `${what} observations must be a list, empty if there are none`,
  );
  const w = v["window"] as Record<string, unknown>;
  const c = v["counts"] as Record<string, unknown>;
  return {
    state: v["state"] as StreamState,
    reason: strOrNull(v["reason"] ?? null, `${what} reason`),
    window: {
      label: str(w["label"], `${what} window label`),
      start_at: strOrNull(w["start_at"] ?? null, `${what} window start`),
      end_at: strOrNull(w["end_at"] ?? null, `${what} window end`),
    },
    provenance_class: str(v["provenance_class"], `${what} provenance class`),
    counts: {
      eligible: int(c["eligible"], `${what} eligible count`),
      scored: int(c["scored"], `${what} scored count`),
      missing: int(c["missing"], `${what} missing count`),
    },
    observations: (v["observations"] as unknown[]).map((r, i) =>
      readRow(r, `${what} observation ${i}`),
    ),
    result: readResult(v["result"] ?? null),
  };
}

function readSource(value: unknown, what: string): SixSourceFields {
  need(object(value), `${what} is missing`);
  const v = value as Record<string, unknown>;
  const out = {} as SixSourceFields;
  for (const key of SOURCE_FIELDS) out[key] = str(v[key], `${what} ${key}`);
  return out;
}

function readReceipt(value: unknown, what: string): SafeReceipt {
  need(object(value), `${what} is not a saved reading`);
  const v = value as Record<string, unknown>;
  need(
    Array.isArray(v["years"]) && (v["years"] as unknown[]).every(Number.isInteger),
    `${what} years are not whole years`,
  );
  need(object(v["counts"]), `${what} counts are missing`);
  need(
    v["evaluation_status"] === "ungraded",
    `${what} evaluation_status is ${String(v["evaluation_status"])}; the archive never grades itself`,
  );
  const counts: Record<string, number> = {};
  for (const [key, n] of Object.entries(v["counts"] as Record<string, unknown>))
    counts[key] = int(n, `${what} count ${key}`);
  return {
    snapshot_id: str(v["snapshot_id"], `${what} snapshot_id`),
    saved_at: str(v["saved_at"], `${what} saved_at`),
    forecast_date: str(v["forecast_date"], `${what} forecast_date`),
    market_as_of: str(v["market_as_of"], `${what} market_as_of`),
    ownership_as_of: str(v["ownership_as_of"], `${what} ownership_as_of`),
    report_generated_at: strOrNull(v["report_generated_at"] ?? null, `${what} report_generated_at`),
    catalog_generated_at: strOrNull(
      v["catalog_generated_at"] ?? null,
      `${what} catalog_generated_at`,
    ),
    years: v["years"] as number[],
    counts,
    source: readSource(v["source"], `${what} source`),
    evaluation_status: "ungraded",
    evaluation_plan: object(v["evaluation_plan"])
      ? (v["evaluation_plan"] as Record<string, unknown>)
      : {},
  };
}

export function readTrackRecordView(value: unknown): TrackRecordView {
  need(object(value), "the response is not an object");
  const v = value as Record<string, unknown>;
  need(
    v["schema_version"] === "track_record.view.v1",
    `schema ${String(v["schema_version"])} is not the one this screen reads`,
  );
  const status = v["status"];
  need(
    ["available", "not_configured", "unavailable"].includes(status as string),
    `status ${String(status)} is not one this screen can render`,
  );
  need(Array.isArray(v["snapshots"]), "the saved readings are missing");
  need(object(v["save_capability"]), "the save capability is missing");
  const cap = v["save_capability"] as Record<string, unknown>;
  need(
    typeof cap["enabled"] === "boolean",
    "the save capability does not say whether saving is enabled",
  );
  return {
    status: status as TrackRecordView["status"],
    reason: strOrNull(v["reason"] ?? null, "reason"),
    snapshots: (v["snapshots"] as unknown[]).map((s, i) => readReceipt(s, `saved reading ${i}`)),
    selected:
      v["selected"] === null || v["selected"] === undefined
        ? null
        : readReceipt(v["selected"], "the selected reading"),
    production: readStream(v["production"], "the production stream"),
    market: readStream(v["market"], "the market stream"),
    save_capability: {
      enabled: cap["enabled"] as boolean,
      reason: strOrNull(cap["reason"] ?? null, "save capability reason"),
      expected:
        cap["expected"] === null || cap["expected"] === undefined
          ? null
          : readSource(cap["expected"], "the expected source"),
    },
  };
}

export function readCaptureResult(value: unknown): CaptureResult {
  need(object(value), "the save response is not an object");
  const v = value as Record<string, unknown>;
  need(
    ["saved", "already_saved"].includes(v["snapshot_status"] as string),
    `snapshot_status ${String(v["snapshot_status"])} is not one this screen can render`,
  );
  need(
    ["saved", "already_saved", "input_unavailable"].includes(v["enrollment_status"] as string),
    `enrollment_status ${String(v["enrollment_status"])} is not one this screen can render`,
  );
  return {
    snapshot_status: v["snapshot_status"] as CaptureResult["snapshot_status"],
    snapshot: readReceipt(v["snapshot"], "the saved reading"),
    enrollment_status: v["enrollment_status"] as CaptureResult["enrollment_status"],
    reason: strOrNull(v["reason"] ?? null, "save reason"),
  };
}

/**
 * The six source fields of the board currently on screen, read at runtime.
 *
 * The bundle's snapshot is typed loosely and two of these six are optional in its validator, so this
 * narrows rather than casting. It returns null the moment any field is missing, because a partial
 * tuple can only ever produce a mismatch, and a mismatch would read as "different reading" when the
 * truth is "incomplete reading".
 */
export function boardSourceFromBundle(snapshot: unknown): SixSourceFields | null {
  if (!object(snapshot)) return null;
  const source = {} as SixSourceFields;
  for (const key of SOURCE_FIELDS) {
    const value = (snapshot as Record<string, unknown>)[key];
    if (typeof value !== "string" || value.length === 0) return null;
    source[key] = value;
  }
  return source;
}

/**
 * Whether the board reading on screen may be saved, and if not, why in words.
 *
 * The server decides first. After that the reading itself has to match, field by field: saving a
 * reading whose source differs from the one the server expects would archive something other than
 * what the manager is looking at. A field the board does not carry is named, because a silently
 * disabled button is indistinguishable from a broken one.
 */
export function saveEnablement(
  boardSource: Record<string, unknown> | null | undefined,
  capability: SaveCapability,
): { enabled: boolean; reason: string } {
  if (!capability.enabled)
    return {
      enabled: false,
      reason: capability.reason ?? "Saving is not available in this session.",
    };
  if (!capability.expected)
    return { enabled: false, reason: "The archive did not say which reading it expects." };
  if (!boardSource) return { enabled: false, reason: "The board reading has not loaded yet." };

  // Named in the manager's language on purpose. The missing field is a pipeline identifier, and
  // putting one on screen is the backend-language-in-the-frontend habit this product ruled out.
  const missing = SOURCE_FIELDS.some((key) => typeof boardSource[key] !== "string");
  if (missing)
    return {
      enabled: false,
      reason: "This board reading is missing source details needed to save it. Reload the board.",
    };
  const differing = SOURCE_FIELDS.filter((key) => boardSource[key] !== capability.expected![key]);
  if (differing.length > 0)
    return {
      enabled: false,
      reason:
        "The board is showing a different reading from the one the archive expects, so saving is held.",
    };
  return { enabled: true, reason: "" };
}

// --- queries --------------------------------------------------------------------------------------

async function get(path: string): Promise<unknown> {
  const response = await fetch(path, { headers: { accept: "application/json" } });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new TrackRecordError(
      (detail as { detail?: string } | null)?.detail ?? `the archive answered ${response.status}`,
    );
  }
  return response.json();
}

export function trackRecordQuery(snapshotId: string | null) {
  const path = snapshotId
    ? `/api/private/track-record?snapshot_id=${encodeURIComponent(snapshotId)}`
    : "/api/private/track-record";
  return queryOptions({
    queryKey: ["dg", "track-record", snapshotId],
    queryFn: async () => {
      if (snapshotId !== null && !/^[a-f0-9]{64}$/.test(snapshotId))
        throw new TrackRecordError(
          "This saved-reading link is invalid. Choose a saved reading from Track record.",
        );
      const view = readTrackRecordView(await get(path));
      if (snapshotId !== null && view.selected?.snapshot_id !== snapshotId)
        throw new TrackRecordError(
          "The archive returned a different saved reading. It has not been substituted for your selection.",
        );
      return view;
    },
    retry: false,
    staleTime: 30_000,
  });
}

export async function saveBoardReading(expected: SixSourceFields): Promise<CaptureResult> {
  const response = await fetch("/api/private/track-record/capture", {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify({ expected }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new TrackRecordError(
      (detail as { detail?: string } | null)?.detail ??
        `the save was refused with ${response.status}`,
    );
  }
  return readCaptureResult(await response.json());
}
