/**
 * DG-208 — the track record screen.
 *
 * It is a list of saved readings and what each is waiting to be graded against, not a scoreboard.
 * David's independent reviewer said the decision edge is unverified, so the failure this screen has to
 * avoid is not a crash: it is implying a record before one exists.
 *
 * Four rules it holds:
 *   · football production and market movement are separate claims, rendered as separate blocks, and
 *     there is no combined figure anywhere;
 *   · an enrolled but ungraded reading shows the forecast and both baselines that were frozen, with no
 *     outcome and no error. Those columns are the milestone's immediate value, and they are not a grade;
 *   · a transport failure is never drawn as an empty archive;
 *   · an absence is stated, never rendered as a number. A player with no forecast says why.
 *
 * Ids and hashes travel in the URL and never appear as copy. A reading is named by when it was saved
 * and what it was reading.
 */
import { useState } from "react";

const dash = "—";

import type { ResultRow, SafeReceipt, Stream, TrackRecordView } from "@/lib/dg/track-record";

import {
  readingDay as day,
  resultNumber as num,
  producerLabel,
  readingText,
  missingInputText,
  type Unit,
} from "@/lib/dg/track-record-format";

function whenSaved(receipt: SafeReceipt, all: SafeReceipt[]): string {
  const at = new Date(receipt.saved_at);
  const sameMinute =
    all.filter((other) => other.saved_at.slice(0, 16) === receipt.saved_at.slice(0, 16)).length > 1;
  return at.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: sameMinute ? "medium" : "short",
  });
}

const words = (value: string) => value.replace(/_/g, " ");

const STATE_COPY: Record<Stream["state"], string> = {
  not_registered: "This reading was never enrolled for evaluation.",
  awaiting_horizon: "Enrolled. The window has not finished, so nothing can be scored yet.",
  awaiting_capture: "Enrolled. The later capture this needs has not been recorded yet.",
  input_unavailable: "Enrolled, but a required input is missing, so it cannot be scored.",
  cutoff_ineligible: "This reading was saved after the declared cutoff, so it is out of scope.",
  insufficient_evidence: "Scored, but too little evidence to say anything.",
  graded: "Scored.",
};

export function TrackRecordScreen({
  view,
  onSelect,
  onSave,
  saving,
  saveDecision,
  boardDate,
  saveOutcome,
}: {
  view: TrackRecordView;
  onSelect: (snapshotId: string) => void;
  onSave: () => void;
  saving: boolean;
  saveDecision: { enabled: boolean; reason: string };
  boardDate: string | null;
  saveOutcome: string | null;
}) {
  if (view.status !== "available") {
    return (
      <section
        className="mt-4 rounded-md border p-4"
        style={{ borderColor: "var(--hairline)" }}
        role="status"
        data-dg-screen="track-record"
      >
        <p className="text-sm" style={{ color: "var(--foreground)" }}>
          {view.status === "unavailable"
            ? "The saved-reading archive is not reachable from this session."
            : "No archive is configured for this session."}
        </p>
        {view.reason ? <p className="mt-2 text-sm text-[var(--ink-dim)]">{view.reason}</p> : null}
        <p className="mt-2 text-sm text-[var(--ink-dim)]">
          This says nothing about what has been saved. It is a connection fact, not a record.
        </p>
      </section>
    );
  }

  return (
    <div className="mt-4 space-y-5" data-dg-screen="track-record">
      <SaveBar
        onSave={onSave}
        saving={saving}
        decision={saveDecision}
        boardDate={boardDate}
        outcome={saveOutcome}
      />

      {view.snapshots.length === 0 ? (
        <section
          className="rounded-md border p-4"
          style={{ borderColor: "var(--hairline)" }}
          role="status"
        >
          <p className="text-sm" style={{ color: "var(--foreground)" }}>
            No reading has been saved yet.
          </p>
          <p className="mt-2 text-sm text-[var(--ink-dim)]">
            Saving one freezes the board you are looking at, with its dates and populations, so a
            later evaluation has something fixed to grade.
          </p>
        </section>
      ) : (
        <>
          <Readings receipts={view.snapshots} selected={view.selected} onSelect={onSelect} />
          {view.selected ? <SelectedSummary receipt={view.selected} /> : null}
          <StreamBlock title="Football production" stream={view.production} kind="production" />
          <StreamBlock title="Market movement" stream={view.market} kind="market" />
          <p className="text-[12px]" style={{ color: "var(--ink-faint)" }}>
            These two are separate claims and are never combined into one figure. Being right about
            production would not make us right about price, and neither one on its own is evidence
            that a decision was improved.
          </p>
        </>
      )}
    </div>
  );
}

function SaveBar({
  onSave,
  saving,
  decision,
  boardDate,
  outcome,
}: {
  onSave: () => void;
  saving: boolean;
  decision: { enabled: boolean; reason: string };
  boardDate: string | null;
  outcome: string | null;
}) {
  return (
    <section className="rounded-md border p-4" style={{ borderColor: "var(--hairline)" }}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[13px] font-semibold tracking-tight">Save current board reading</p>
          <p className="label-caps mt-1">
            {boardDate
              ? `The board is showing our values from ${day(boardDate)}`
              : "The board has not loaded yet"}
          </p>
        </div>
        <button
          type="button"
          onClick={onSave}
          disabled={!decision.enabled || saving}
          className="label-caps rounded-sm border px-3 py-2"
          style={{
            borderColor: "var(--hairline)",
            minHeight: 44,
            opacity: decision.enabled ? 1 : 0.55,
            background: decision.enabled ? "var(--ours)" : undefined,
            color: decision.enabled ? "var(--background)" : undefined,
          }}
        >
          {saving ? "Saving…" : "Save current board reading"}
        </button>
      </div>
      {!decision.enabled && decision.reason ? (
        <p className="mt-2 text-sm text-[var(--ink-dim)]">{decision.reason}</p>
      ) : null}
      {outcome ? (
        <p role="status" className="mt-2 text-sm" style={{ color: "var(--foreground)" }}>
          {readingText(outcome)}
        </p>
      ) : null}
    </section>
  );
}

function Readings({
  receipts,
  selected,
  onSelect,
}: {
  receipts: SafeReceipt[];
  selected: SafeReceipt | null;
  onSelect: (id: string) => void;
}) {
  return (
    <section aria-label="Saved readings">
      <h2 className="text-[13px] font-semibold tracking-tight">Saved readings</h2>
      <p className="label-caps mt-1">{receipts.length} saved</p>
      <ul className="mt-2 space-y-1">
        {receipts.map((receipt) => {
          const active = selected?.snapshot_id === receipt.snapshot_id;
          return (
            <li key={receipt.snapshot_id}>
              <button
                type="button"
                onClick={() => onSelect(receipt.snapshot_id)}
                aria-pressed={active}
                className="row-grid w-full items-center text-left"
                style={{
                  gridTemplateColumns: "1fr auto",
                  gap: "0 10px",
                  minHeight: 44,
                  background: active ? "var(--surface)" : "transparent",
                }}
                aria-label={`Reading saved ${whenSaved(receipt, receipts)}`}
              >
                <span className="min-w-0">
                  <span className="block truncate text-[13px] font-semibold">
                    Saved {whenSaved(receipt, receipts)}
                  </span>
                  <span className="label-caps">
                    our values {day(receipt.forecast_date)} · market {day(receipt.market_as_of)}
                  </span>
                </span>
                <span className="label-caps">{receipt.counts["paired"] ?? dash} paired</span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function SelectedSummary({ receipt }: { receipt: SafeReceipt }) {
  return (
    <section className="rounded-md border p-4" style={{ borderColor: "var(--hairline)" }}>
      <h2 className="text-[13px] font-semibold tracking-tight">What this reading froze</h2>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-[13px]">
        <Fact term="Our values" value={day(receipt.forecast_date)} />
        <Fact term="Market prices" value={day(receipt.market_as_of)} />
        <Fact term="Ownership" value={day(receipt.ownership_as_of)} />
        <Fact
          term="Seasons"
          value={`${receipt.years[0]}–${receipt.years[receipt.years.length - 1]}`}
        />
        <Fact term="Players carrying both ranks" value={String(receipt.counts["paired"] ?? dash)} />
        <Fact term="On your roster" value={String(receipt.counts["roster"] ?? dash)} />
      </dl>
      <p className="mt-3 text-[12px]" style={{ color: "var(--ink-faint)" }}>
        Saving the same board twice records one reading, not two. A count of saved readings is never
        a count of predictions.
      </p>
    </section>
  );
}

function Fact({ term, value }: { term: string; value: string }) {
  return (
    <div>
      <dt className="label-caps">{term}</dt>
      <dd className="mt-0.5" style={{ color: "var(--foreground)" }}>
        {value}
      </dd>
    </div>
  );
}

type Column = { key: string; label: string; width: string; render: (row: ResultRow) => string };

function columnsFor(kind: "production" | "market", scored: boolean): Column[] {
  const value =
    (pick: (row: ResultRow) => number | null, unit: Unit): Column["render"] =>
    (row) =>
      num(pick(row), unit);
  if (kind === "market") {
    const columns: Column[] = [
      { key: "gap", label: "Rank gap", width: "110px", render: value((r) => r.forecast, "places") },
      {
        key: "momentum",
        label: "Price momentum",
        width: "130px",
        render: value((r) => r.baseline, "fraction"),
      },
    ];
    if (scored)
      columns.push({
        key: "return",
        label: "Adjusted return",
        width: "130px",
        render: value((r) => r.outcome, "fraction"),
      });
    return columns;
  }
  const columns: Column[] = [
    {
      key: "forecast",
      label: "Forecast",
      width: "100px",
      render: value((r) => r.forecast, "points"),
    },
    {
      key: "prior",
      label: "Prior season",
      width: "110px",
      render: value((r) => r.baseline, "points"),
    },
    {
      key: "median",
      label: "Position median",
      width: "120px",
      render: value((r) => r.baseline_position_median, "points"),
    },
  ];
  if (scored) {
    columns.push({
      key: "outcome",
      label: "Outcome",
      width: "100px",
      render: value((r) => r.outcome, "points"),
    });
    columns.push({
      key: "delta",
      label: "Difference",
      width: "100px",
      render: value((r) => r.error, "points"),
    });
  } else {
    columns.push({
      key: "source",
      label: "Source",
      width: "120px",
      render: (r) => producerLabel(r.producer),
    });
  }
  return columns;
}

function StreamBlock({
  title,
  stream,
  kind,
}: {
  title: string;
  stream: Stream;
  kind: "production" | "market";
}) {
  // A result is shown whenever there is one. An earlier version gated on state === "graded", which
  // hid an insufficient-evidence finding entirely — and "we looked and it is too thin to say" is a
  // result the manager is owed, not an absence.
  const result = stream.result;
  const sourceRows = result ? result.rows : stream.observations;
  const noPriorMarket =
    kind === "market" &&
    !result &&
    sourceRows.length > 0 &&
    sourceRows.every((row) => row.baseline === null);
  const rows = sourceRows.map((row) => ({
    ...row,
    reason: missingInputText(row.reason, noPriorMarket),
  }));
  const scored = rows.some((row) => row.outcome !== null);
  return (
    <section aria-label={title}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-[13px] font-semibold tracking-tight">{title}</h2>
        <span className="label-caps">{readingText(stream.window.label)}</span>
      </div>
      <p className="mt-1 text-sm" style={{ color: "var(--foreground)" }}>
        {STATE_COPY[stream.state]}
      </p>
      {stream.reason ? (
        <p className="mt-1 text-sm text-[var(--ink-dim)]">{readingText(stream.reason)}</p>
      ) : null}
      {noPriorMarket ? (
        <p className="mt-1 text-sm text-[var(--ink-dim)]">
          No frozen prior market comparison is available for this reading.
        </p>
      ) : null}
      <p className="label-caps mt-1">
        {stream.counts.eligible} eligible · {stream.counts.scored} scored · {stream.counts.missing}{" "}
        missing
        {stream.provenance_class === "reconstructed"
          ? " · inputs rebuilt after the fact, not captured at the time"
          : ""}
      </p>

      {result ? <Comparisons result={result} /> : null}

      {kind === "production" && rows.some((row) => row.producer) ? (
        <details className="mt-2 text-[12px] text-[var(--ink-dim)]">
          <summary className="min-h-11 cursor-pointer">Forecast sources</summary>
          <ul>
            {[...new Set(rows.map((row) => row.producer).filter((p): p is string => !!p))].map(
              (producer) => (
                <li key={producer} className="mb-2 break-words">
                  {producerLabel(producer)}: {producer}
                </li>
              ),
            )}
          </ul>
        </details>
      ) : null}

      {rows.length === 0 ? (
        <p className="mt-2 text-sm text-[var(--ink-dim)]">
          No player rows are available for this reading.
        </p>
      ) : (
        <PlayerRows rows={rows} scored={scored} kind={kind} />
      )}

      {result && result.details.length > 0 ? (
        <details className="mt-3">
          <summary className="label-caps cursor-pointer" style={{ minHeight: 44 }}>
            What this cannot tell you
          </summary>
          <dl className="mt-2 space-y-2 text-[13px] text-[var(--ink-dim)]">
            {result.details.map((detail) => (
              <div key={detail.label}>
                <dt className="label-caps">{detail.label}</dt>
                <dd className="mt-0.5" style={{ color: "var(--foreground)" }}>
                  {detail.value}
                </dd>
              </div>
            ))}
          </dl>
        </details>
      ) : null}
    </section>
  );
}

function Comparisons({ result }: { result: NonNullable<Stream["result"]> }) {
  const primary = result.comparisons.filter(
    (comparison) =>
      comparison.id.startsWith("production:aggregate:") ||
      comparison.id === "market:paired_difference",
  );
  const secondary = result.comparisons.filter((comparison) => !primary.includes(comparison));
  return (
    <div className="mt-2 space-y-2">
      <p className="text-sm" style={{ color: "var(--foreground)" }}>
        {result.summary}
      </p>
      <ComparisonFigures
        comparisons={primary.length ? primary : result.comparisons}
        result={result}
      />
      {primary.length > 0 && secondary.length > 0 ? (
        <details className="mt-3">
          <summary className="min-h-11 cursor-pointer text-sm">
            Position and baseline details
          </summary>
          <ComparisonFigures comparisons={secondary} result={result} />
        </details>
      ) : null}
    </div>
  );
}

function readableComparisonLabel(label: string, rows: ResultRow[]) {
  let value = label;
  for (const producer of new Set(rows.map((row) => row.producer).filter((p): p is string => !!p)))
    value = value.replaceAll(producer, producerLabel(producer));
  return value.replaceAll("_", " ");
}

function ComparisonFigures({
  comparisons,
  result,
}: {
  comparisons: NonNullable<Stream["result"]>["comparisons"];
  result: NonNullable<Stream["result"]>;
}) {
  return (
    <div className="space-y-2">
      {" "}
      {comparisons.map((comparison) => {
        const unit: Unit = /rank|place/i.test(comparison.units)
          ? "places"
          : /correlation/i.test(comparison.units)
            ? "correlation"
            : /fraction|return|%/i.test(comparison.units)
              ? "fraction"
              : "points";
        return (
          <div
            key={comparison.id}
            className="rounded-md border p-3"
            style={{ borderColor: "var(--hairline)" }}
          >
            <p className="text-[13px] font-semibold">
              {readableComparisonLabel(comparison.label, result.rows)}
            </p>
            <p className="num mt-1 text-[13px]">
              {num(comparison.estimate, unit)}
              {unit === "fraction" ? "" : ` ${comparison.units}`}
              {comparison.interval95
                ? ` · 95% interval ${num(comparison.interval95[0], unit)} to ${num(comparison.interval95[1], unit)}`
                : ""}
            </p>
            <p className="label-caps mt-1">
              {words(comparison.state)} · {comparison.scored} of {comparison.eligible} scored
            </p>
            <p className="mt-1 text-sm text-[var(--ink-dim)]">{comparison.note}</p>
          </div>
        );
      })}
    </div>
  );
}

const PAGE = 25;

/**
 * The full population reaches the client and none of it is dropped. Search, position and provenance
 * narrow what is DISPLAYED, and the stream's own counts above are never recomputed from the filter,
 * so narrowing the list can never look like a smaller graded cohort. A bounded page keeps a
 * 900-row reading from burying the block below it.
 */
function PlayerRows({
  rows,
  scored,
  kind,
}: {
  rows: ResultRow[];
  scored: boolean;
  kind: "production" | "market";
}) {
  const [query, setQuery] = useState("");
  const [position, setPosition] = useState("all");
  const [provenance, setProvenance] = useState("all");
  const [shown, setShown] = useState(PAGE);

  const positions = [...new Set(rows.map((row) => row.position))].sort();
  const provenances = [...new Set(rows.map((row) => row.provenance))].sort();
  const needle = query.trim().toLocaleLowerCase();
  const matching = rows.filter(
    (row) =>
      (needle === "" || row.name.toLocaleLowerCase().includes(needle)) &&
      (position === "all" || row.position === position) &&
      (provenance === "all" || row.provenance === provenance),
  );
  const visible = matching.slice(0, shown);
  const columns = columnsFor(kind, scored);
  const template = `minmax(150px,1.6fr) ${columns.map((c) => c.width).join(" ")}`;
  const reset = () => setShown(PAGE);

  return (
    <div className="mt-2">
      <div className="flex flex-wrap items-center gap-2">
        <label className="label-caps flex items-center gap-2">
          Find a player
          <input
            type="search"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              reset();
            }}
            placeholder="Name"
            className="rounded-sm border bg-transparent px-2 py-1 text-[13px]"
            style={{ borderColor: "var(--hairline)", minHeight: 44 }}
          />
        </label>
        <Picker
          label="Position"
          value={position}
          options={positions}
          onChange={(v) => {
            setPosition(v);
            reset();
          }}
        />
        <Picker
          label="Source"
          value={provenance}
          options={provenances}
          format={words}
          onChange={(v) => {
            setProvenance(v);
            reset();
          }}
        />
      </div>
      <p className="label-caps mt-2">
        Showing {visible.length} of {matching.length}
        {matching.length !== rows.length ? ` filtered from ${rows.length}` : ""} · filtering changes
        this list only, never the counts above
      </p>

      {/* Desktop: one dense grid. Phone: a stacked card per player, so nothing needs panning. */}
      <div className="mt-2 hidden md:block">
        <div
          className="row-grid label-caps"
          style={{ gridTemplateColumns: template, gap: "0 12px", minHeight: 34 }}
        >
          <span>Player</span>
          {columns.map((column) => (
            <span key={column.key}>{column.label}</span>
          ))}
        </div>
        {visible.map((row) => (
          <div
            key={row.sleeper_id}
            className="row-grid items-baseline"
            style={{ gridTemplateColumns: template, gap: "0 12px", minHeight: 40 }}
          >
            <Identity row={row} />
            {columns.map((column) => (
              <span key={column.key} className="num text-[13px]">
                {column.render(row)}
              </span>
            ))}
          </div>
        ))}
      </div>

      <ul className="mt-2 space-y-2 md:hidden">
        {visible.map((row) => (
          <li
            key={row.sleeper_id}
            className="rounded-md border p-3"
            style={{ borderColor: "var(--hairline)" }}
          >
            <Identity row={row} />
            <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[13px]">
              {columns.map((column) => (
                <div key={column.key} className="flex items-baseline justify-between gap-2">
                  <dt className="label-caps">{column.label}</dt>
                  <dd className="num">{column.render(row)}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>

      {visible.length < matching.length ? (
        <button
          type="button"
          className="label-caps mt-2 rounded-sm border px-2 py-1"
          style={{ borderColor: "var(--hairline)", minHeight: 44 }}
          onClick={() => setShown((n) => n + PAGE)}
        >
          Show {PAGE} more
        </button>
      ) : null}
      {matching.length === 0 ? (
        <p className="mt-2 text-sm text-[var(--ink-dim)]">
          No player in this reading matches that.
        </p>
      ) : null}
    </div>
  );
}

function Identity({ row }: { row: ResultRow }) {
  return (
    <span className="min-w-0">
      <span className="block truncate text-[13px]">{row.name}</span>
      <span className="label-caps">
        {row.position}
        {row.provenance !== "original" ? ` · ${words(row.provenance)}` : ""}
      </span>
      {row.reason ? <span className="label-caps block">{row.reason}</span> : null}
    </span>
  );
}

function Picker({
  label,
  value,
  options,
  onChange,
  format = (v: string) => v,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
  format?: (value: string) => string;
}) {
  return (
    <label className="label-caps flex items-center gap-2">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-label={label}
        className="rounded-sm border bg-transparent px-2 py-1 text-[13px]"
        style={{ borderColor: "var(--hairline)", minHeight: 44 }}
      >
        <option value="all">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {format(option)}
          </option>
        ))}
      </select>
    </label>
  );
}
