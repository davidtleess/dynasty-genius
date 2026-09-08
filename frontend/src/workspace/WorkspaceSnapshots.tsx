// DG-191 — saving what this screen showed, and listing what has been saved.
//
// David said "lets build" to preserving today's forecasts and valuations before decision recording
// is added on top. This is the archive half of that: an explicit, deliberate "save this snapshot",
// and a list of what has been saved.
//
// Three honesty rules shape the whole file:
//   * A snapshot is a record of what THIS screen showed, taken NOW. Archiving September 6 forecasts
//     on September 8 does not mean they were frozen on September 6, and the copy says so.
//   * Saving the same content twice is not a second observation. A duplicate keeps the FIRST saved
//     time and says "already saved", so the archive can never be padded by pressing a button again.
//   * Nothing here has been graded, and nothing here claims an edge.
//
// The mechanism that carries most of the weight: every outcome is tagged with the exact source
// tuple its request was made against, and is only shown while the screen still shows that tuple.
// That is what makes "a success arriving after the sources moved must not describe the new screen
// as saved" true by construction rather than by careful effect ordering.
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { z } from "zod";

import "./WorkspaceSnapshots.css";

export type SnapshotExpected = {
  report_run: string;
  report_sha256: string;
  market_sha256: string;
  league_sha256: string;
  catalog_run: string;
  catalog_content_sha256: string;
};

const SNAPSHOTS_URL = "/api/research/snapshots";

const dated = z.string().refine((s) => Number.isFinite(Date.parse(s)));
const wholeCount = z.number().int().nonnegative();

const expectedSchema = z.object({
  report_run: z.string(),
  report_sha256: z.string(),
  market_sha256: z.string(),
  league_sha256: z.string(),
  catalog_run: z.string(),
  catalog_content_sha256: z.string(),
});

const receiptSchema = z.object({
  snapshot_id: z.string(),
  saved_at: dated,
  forecast_date: z.string(),
  market_as_of: dated,
  ownership_as_of: dated,
  years: z.array(z.number().int()),
  // When the sources were CREATED — a different fact from the nominal forecast date they carry.
  // Absent in a source that never recorded it, and absent is not zero.
  report_generated_at: dated.nullable(),
  catalog_generated_at: dated.nullable(),
  source: expectedSchema,
  counts: z.object({
    model: wholeCount,
    // `market` is market PLAYERS; picks are counted separately and never folded in.
    market: wholeCount,
    market_picks: wholeCount,
    paired: wholeCount,
    roster: wholeCount,
    // `available` is the RELEVANT pool; `available_total` is every catalog row. Conflating the two
    // would overstate what is on offer, so both are kept and both are labelled.
    available: wholeCount,
    available_total: wholeCount,
    available_with_forecasts: wholeCount,
    available_without_forecasts: wholeCount,
    starting_estimates: wholeCount,
  }),
  // The declaration of how a future evaluation will be run, archived with the reading. It is a
  // plan, never a result, so this screen validates it and does not render it.
  evaluation_plan: z.record(z.string(), z.unknown()).optional(),
  capture_code_sha: z.string(),
  // The only status this increment can produce. A payload claiming anything else is not something
  // this screen knows how to describe, so it is refused rather than half-rendered.
  evaluation_status: z.literal("ungraded"),
});
export type SnapshotReceipt = z.infer<typeof receiptSchema>;

const listSchema = z.discriminatedUnion("status", [
  z.object({ status: z.literal("available"), snapshots: z.array(receiptSchema) }),
  z.object({ status: z.literal("not_configured") }),
]);
const saveSchema = z.object({
  status: z.literal("saved"),
  created: z.boolean(),
  snapshot: receiptSchema,
});

type ListState =
  | { mode: "loading" }
  | { mode: "ready"; snapshots: SnapshotReceipt[] }
  | { mode: "not-configured" }
  | { mode: "unavailable" };

type Outcome =
  | { kind: "saved"; created: boolean; receipt: SnapshotReceipt }
  | { kind: "stale" }
  | { kind: "failed" };

type SnapshotState = {
  expected: SnapshotExpected | null;
  list: ListState;
  pending: boolean;
  /** Only ever set for the tuple currently on screen; see the header note. */
  outcome: Outcome | null;
  save: () => void;
};

const INERT: SnapshotState = {
  expected: null,
  list: { mode: "loading" },
  pending: false,
  outcome: null,
  save: () => {},
};

const SnapshotContext = createContext<SnapshotState>(INERT);

const sameSources = (a: SnapshotExpected | null, b: SnapshotExpected | null): boolean =>
  a !== null &&
  b !== null &&
  a.report_run === b.report_run &&
  a.report_sha256 === b.report_sha256 &&
  a.market_sha256 === b.market_sha256 &&
  a.league_sha256 === b.league_sha256 &&
  a.catalog_run === b.catalog_run &&
  a.catalog_content_sha256 === b.catalog_content_sha256;

function dayLabel(value: string): string {
  const parsed = Date.parse(value.length === 10 ? `${value}T12:00:00Z` : value);
  if (Number.isNaN(parsed)) return value;
  return new Date(parsed).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

function momentLabel(value: string): string {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value;
  return `${new Date(parsed).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  })} UTC`;
}

export function WorkspaceSnapshotProvider({
  expected,
  children,
}: {
  expected: SnapshotExpected | null;
  children: ReactNode;
}) {
  const [list, setList] = useState<ListState>({ mode: "loading" });
  const [pending, setPending] = useState(false);
  // The outcome remembers which sources it belongs to. Rendering compares that against the tuple
  // on screen now, so a stale success cannot survive a source change.
  const [outcome, setOutcome] = useState<{
    for: SnapshotExpected;
    value: Outcome;
  } | null>(null);

  const readList = useCallback(async (): Promise<void> => {
    try {
      const response = await fetch(SNAPSHOTS_URL);
      if (!response.ok) throw new Error("archive unavailable");
      const parsed = listSchema.parse(await response.json());
      setList(
        parsed.status === "available"
          ? { mode: "ready", snapshots: parsed.snapshots }
          : { mode: "not-configured" },
      );
    } catch {
      // A list we cannot read is not an empty archive, and must never render as one.
      setList({ mode: "unavailable" });
    }
  }, []);

  useEffect(() => {
    let live = true;
    void (async () => {
      await readList();
      if (!live) return;
    })();
    return () => {
      live = false;
    };
    // Read once. No polling and no refresh on focus: a snapshot is a deliberate act.
  }, [readList]);

  const save = useCallback(() => {
    if (expected === null || pending) return;
    const asked = expected;
    setPending(true);
    void (async () => {
      try {
        const response = await fetch(SNAPSHOTS_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ expected: asked }),
        });
        if (response.status === 409) {
          setOutcome({ for: asked, value: { kind: "stale" } });
          return;
        }
        if (!response.ok) throw new Error("save failed");
        const parsed = saveSchema.parse(await response.json());
        // A receipt for other sources is not evidence about the sources we asked to save. Claiming
        // success on it would put someone else's forecasts behind this screen's confirmation.
        if (!sameSources(parsed.snapshot.source, asked)) {
          throw new Error("receipt is for different sources");
        }
        setOutcome({
          for: asked,
          value: { kind: "saved", created: parsed.created, receipt: parsed.snapshot },
        });
        // The archive really did change, so the list is re-read even when the screen has since
        // moved on and this outcome will not be shown.
        await readList();
      } catch {
        setOutcome({ for: asked, value: { kind: "failed" } });
      } finally {
        setPending(false);
      }
    })();
  }, [expected, pending, readList]);

  const shown =
    outcome !== null && sameSources(outcome.for, expected) ? outcome.value : null;

  return (
    <SnapshotContext.Provider value={{ expected, list, pending, outcome: shown, save }}>
      {children}
    </SnapshotContext.Provider>
  );
}

export function SnapshotSaveControl() {
  const { expected, list, pending, outcome, save } = useContext(SnapshotContext);
  const unconfigured = list.mode === "not-configured";
  const disabled = expected === null || unconfigured || pending;

  // These exact sources may already be archived from an earlier visit. A snapshot id hashes the
  // whole saved READING, so a later rendering of the same sources hashes differently; the source
  // tuple is what says "this forecast is already preserved". Saving again stays possible and is
  // simply not a new observation.
  // The capture tool can archive more than one RENDERING of the same sources; those are not
  // separate forecasts, so the earliest saved time is the one that answers "when were these
  // forecasts first preserved".
  const archived =
    list.mode === "ready"
      ? (list.snapshots
          .filter((s) => sameSources(s.source, expected))
          .reduce<SnapshotReceipt | null>(
            (earliest, s) =>
              earliest === null ||
              Date.parse(s.saved_at) < Date.parse(earliest.saved_at)
                ? s
                : earliest,
            null,
          ) ?? null)
      : null;

  let note: string | null = null;
  if (expected === null) {
    note = "Source details are not available yet, so there is nothing to save.";
  } else if (unconfigured) {
    note = "Saving snapshots is switched off in this setup.";
  } else if (outcome?.kind === "saved") {
    // A duplicate names the FORECASTS and the date they were first saved. Saying only "already
    // saved" would invite the reading that this exact rendering is what sits in the archive; what
    // was locked is the first reading of these sources, not every later wording of them.
    note = outcome.created
      ? "Saved. The forecasts and prices on this screen are archived as they are now."
      : `These forecasts were already saved ${momentLabel(outcome.receipt.saved_at)}.`;
  } else if (outcome?.kind === "stale") {
    note =
      "The underlying data changed before this could be saved, so no new snapshot was saved by this request. Reload to see the current screen, then save again.";
  } else if (outcome?.kind === "failed") {
    // The request failed, which is NOT the same as the save failing: a connection can drop after
    // the server has already written the snapshot. So this says what we know — that we cannot
    // confirm it — and points out that retrying is harmless, because the archive is keyed by
    // content and the same forecasts cannot be stored twice.
    note =
      "We could not confirm this save. Try again; saving the same forecasts twice will not duplicate them.";
  } else if (archived !== null) {
    note = `These forecasts were already saved ${momentLabel(archived.saved_at)}.`;
  }

  return (
    <div className="dg-workspace-snapshots__save">
      <button
        type="button"
        className="dg-workspace-snapshots__button"
        disabled={disabled}
        onClick={save}
      >
        {pending ? "Saving…" : "Save this snapshot"}
      </button>
      {/* One live region carrying one sentence. Pressing the button again is not a new
          observation, so a duplicate reports the date these forecasts were FIRST saved. */}
      <p className="dg-workspace-snapshots__note" role="status">
        {note}
      </p>
    </div>
  );
}

/** The wider populations, kept out of the summary so the relevant pool is never overstated. */
function extraCountLine(counts: SnapshotReceipt["counts"]): string {
  return `${counts.model} players we forecast · ${counts.market} market players and ${counts.market_picks} market picks · ${counts.available_total} catalog rows in total, of which ${counts.available} are the relevant pool.`;
}

/** When the sources were created, said only for the ones that recorded it. */
function createdLine(snapshot: SnapshotReceipt): string | null {
  const parts: string[] = [];
  if (snapshot.report_generated_at !== null)
    parts.push(`Report created ${momentLabel(snapshot.report_generated_at)}`);
  if (snapshot.catalog_generated_at !== null)
    parts.push(`Catalog created ${momentLabel(snapshot.catalog_generated_at)}`);
  return parts.length === 0 ? null : parts.join(" · ");
}

function countLine(counts: SnapshotReceipt["counts"]): string {
  return `${counts.roster} of your players · ${counts.available} relevant available players, ${counts.available_with_forecasts} with forecasts and ${counts.available_without_forecasts} without · ${counts.starting_estimates} starting estimates · ${counts.paired} ranked on both sides`;
}

export function SnapshotHistory({ action }: { action?: ReactNode }) {
  const { list } = useContext(SnapshotContext);

  return (
    <section className="dg-workspace-snapshots" aria-label="Saved snapshots">
      <h2 className="dg-workspace-snapshots__title">Saved snapshots</h2>
      {list.mode === "loading" && <p role="status">Loading saved snapshots…</p>}
      {list.mode === "not-configured" && (
        <p>No snapshots can be saved in this setup, so none are listed.</p>
      )}
      {list.mode === "unavailable" && (
        <p role="status">Saved snapshots could not be read. Reload to try again.</p>
      )}
      {list.mode === "ready" &&
        (list.snapshots.length === 0 ? (
          <>
            <p>No snapshots have been saved yet.</p>
          </>
        ) : (
          <ul className="dg-workspace-snapshots__list">
            {list.snapshots.map((snapshot) => (
              <li key={snapshot.snapshot_id} className="dg-workspace-snapshots__entry">
                {/* When it was archived is a different fact from the dates of the data inside it,
                    and the two are never merged into one date. */}
                <span className="dg-workspace-snapshots__archived">
                  Archived{" "}
                  <time dateTime={snapshot.saved_at}>
                    {momentLabel(snapshot.saved_at)}
                  </time>
                </span>
                <span className="dg-workspace-snapshots__dates">
                  Forecasts dated {dayLabel(snapshot.forecast_date)} · Market prices{" "}
                  {dayLabel(snapshot.market_as_of)}
                </span>
                {createdLine(snapshot) !== null && (
                  <span className="dg-workspace-snapshots__created">
                    {createdLine(snapshot)}
                  </span>
                )}
                <span className="dg-workspace-snapshots__counts">
                  {countLine(snapshot.counts)}
                </span>
                <details className="dg-workspace-snapshots__more">
                  <summary>More counts</summary>
                  <p>{extraCountLine(snapshot.counts)}</p>
                </details>
                <span className="dg-workspace-snapshots__ungraded">
                  Not graded yet.
                </span>
              </li>
            ))}
          </ul>
        ))}
      {list.mode === "ready" && action}
      <p className="dg-workspace-snapshots__standing">
        A snapshot records what this screen showed. It is not a claim that the numbers
        were frozen on the forecast date, and nothing here has been graded.
      </p>
    </section>
  );
}
