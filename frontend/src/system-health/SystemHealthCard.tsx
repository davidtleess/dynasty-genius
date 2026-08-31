import { useEffect, useState } from "react";
import type { z } from "zod";

import { zSystemHealthErrorResponse, zSystemHealthResponse } from "../lib/api/zod.gen";
import {
  artifactName,
  disclosureSentence,
  reportBasisMessage,
  reportCountLabel,
  reportStateLabel,
  subsystemBasisMessage,
  subsystemName,
  subsystemStateLabel,
  tierName,
} from "../lib/copy";
import { ReceiptRow } from "../ui/Receipt";
import "./SystemHealthCard.css";

// The validated shape IS the generated Zod schema's output (validated at the SDK
// boundary), so derive types from it rather than the parallel generated TS type.
type SystemHealth = z.infer<typeof zSystemHealthResponse>;
type ReportRow = SystemHealth["reports"][number];
type SubsystemRow = SystemHealth["subsystems"][number];

type CardState =
  | { status: "loading" }
  | { status: "unavailable"; message: string | null }
  | { status: "ready"; data: SystemHealth };

// The trio the card must account for even when the payload omits them: an absent
// guard renders as explicitly unverified, never as silently healthy.
const EXPECTED_SUBSYSTEMS = [
  "model_provenance",
  "capture_health",
  "tier_readiness",
] as const;

// DG-109: `inputs_degraded` is in the contract (zod.gen.ts:973) and was missing
// here, so a report in that state was silently DROPPED from the summary — the
// live card said "9 reports: 6 fresh · 2 stale" over nine rows. Every status the
// contract can carry now appears in the count.
const REPORT_STATUS_ORDER: ReportRow["status"][] = [
  "fresh",
  "freshness_overdue",
  "inputs_degraded",
  "stale",
  "corrupt_or_empty",
  "dormant",
  "missing",
  "producer_failed",
];

// Severity accents apply only to statuses the backend rollup treats as degrading,
// and never to auxiliary-tier rows (auxiliary can never drive overall_status).
const DEGRADING_REPORT_STATUSES: ReadonlySet<ReportRow["status"]> = new Set([
  "stale",
  "corrupt_or_empty",
  "missing",
  "producer_failed",
  // Mirrors _DEGRADING_STATUSES in app/api/routes/system_health_models.py:360.
  // It was absent here, so a report the backend counted as degrading rendered
  // without the severity accent.
  "inputs_degraded",
]);

export function SystemHealthCard({ now }: { now?: Date }) {
  const [state, setState] = useState<CardState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch("/api/health");
        if (response.status === 503) {
          // The sanitized error message renders only if the body matches the
          // generated error contract; anything else stays behind the fixed copy.
          let message: string | null = null;
          try {
            message = zSystemHealthErrorResponse.parse(await response.json()).message;
          } catch {
            message = null;
          }
          if (!cancelled) setState({ status: "unavailable", message });
          return;
        }
        if (!response.ok) {
          if (!cancelled) setState({ status: "unavailable", message: null });
          return;
        }
        // A 200 whose shape drifts from the contract (unknown enum, wrong type,
        // disclaimer drift) degrades — it never renders raw/unverified.
        let data: SystemHealth;
        try {
          data = zSystemHealthResponse.parse(await response.json());
        } catch {
          if (!cancelled) setState({ status: "unavailable", message: null });
          return;
        }
        if (!cancelled) setState({ status: "ready", data });
      } catch {
        if (!cancelled) setState({ status: "unavailable", message: null });
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div
      className="dg-syshealth"
      role="status"
      aria-label="Data freshness"
      data-health-status={
        state.status === "ready" ? state.data.overall_status : undefined
      }
      data-affected-tier={
        state.status === "ready"
          ? (state.data.worst_affected_tier ?? undefined)
          : undefined
      }
    >
      {state.status === "loading" && (
        <span className="dg-syshealth__loading">Loading data freshness…</span>
      )}
      {state.status === "unavailable" && (
        <div className="dg-syshealth__unavailable">
          <span>Data freshness unavailable — update status unknown</span>
          {state.message !== null && (
            <span className="dg-syshealth__unavailable-detail">{state.message}</span>
          )}
        </div>
      )}
      {state.status === "ready" && (
        <HealthBody data={state.data} now={now ?? new Date()} />
      )}
    </div>
  );
}

function HealthBody({ data, now }: { data: SystemHealth; now: Date }) {
  return (
    <div className="dg-syshealth__body">
      <div className="dg-syshealth__headline">
        <span className="dg-syshealth__title">Data freshness</span>
        <span className="dg-syshealth__subtitle">
          when each daily update last ran — not model accuracy
        </span>
        <span className="dg-syshealth__overall">{overallLine(data)}</span>
        <span className="dg-syshealth__counts">{countsLine(data.reports)}</span>
        <CheckedAt raw={data.checked_at} now={now} />
      </div>
      <SubsystemList subsystems={data.subsystems} />
      <details className="dg-syshealth__details">
        <summary className="dg-syshealth__details-summary">report freshness</summary>
        <ul className="dg-syshealth__reports">
          {data.reports.map((row) => (
            <ReportItem key={`${row.artifact_id}:${row.status}`} row={row} now={now} />
          ))}
        </ul>
      </details>
      {/* DG-111: the backend's own disclaimer stays — it is data this endpoint
          publishes. The stamped "Descriptive only — not decision-grade." line
          beside it was ours, repeated from every other surface, and is gone.

          DG-120: this was a `<footer>`, which is a CONTENTINFO landmark unless
          it sits inside an article/section/aside/main/nav — and this card's
          root is a `<div role="status">`, inside the shell's
          `<header role="banner">`. So the drawer was publishing "the footer of
          the whole page", nested inside another landmark: axe
          landmark-contentinfo-is-top-level, measured on the built bundle at
          both widths. Nobody knew, because the gate had never opened the
          drawer — the same shape of miss DG-118 found on Model Trust, and the
          same fix. A div is what this always was: one sentence, styled. */}
      <div className="dg-syshealth__footer">
        <span className="dg-syshealth__disclaimer">{data.disclaimer}</span>
      </div>
    </div>
  );
}

// When degraded the worst tier leads so a core failure cannot read benign inside
// a mostly-fresh count. Describes state; never a verdict or a prescribed action.
// The raw taxonomy (`core_substrate`) still rides the `data-affected-tier`
// attribute for CSS and tests; it just no longer surfaces as snake_case.
//
// THE ROLLUP IS NARROWER THAN IT LOOKS, and this line must not be wider than the
// rollup. `rollup_health_status` (system_health_models.py:683-704) returns "ok"
// whenever no CORE-or-DAILY report is stale/unreadable/missing/failed/degraded-
// input: `_TIER_SEVERITY` (:363) has no `auxiliary` key, so an auxiliary report
// scores rank 0 and can never degrade the root — the backend knows it is
// suppressing those and tags them `auxiliary_info_only` (:653-654). Neither
// `freshness_overdue` nor `dormant` degrades anything either. An earlier draft
// printed "Nothing needs attention" for that state, which the card's own rows
// can contradict on the same screen (a failed auxiliary feed prints "Last run
// failed. Earlier values may still be in use." two lines below). So: the ok line
// claims only what the rollup actually checked, and when a feed outside that
// scope IS in a bad state, it says so instead of swallowing it.
function overallLine(data: SystemHealth): string {
  if (data.overall_status === "degraded" && data.worst_affected_tier !== null) {
    return `Something needs attention — ${tierName(data.worst_affected_tier)} affected`;
  }
  if (data.overall_status !== "ok") return subsystemStateLabel(data.overall_status);
  // Reachable only when the rollup said ok, so by its own logic every one of
  // these sits outside the tiers it scores.
  const quiet = data.reports.filter((row) => DEGRADING_REPORT_STATUSES.has(row.status));
  if (quiet.length === 1) {
    return "Main feeds are healthy — one feed outside them is not; it is listed below";
  }
  if (quiet.length > 1) {
    return `Main feeds are healthy — ${quiet.length} feeds outside them are not; they are listed below`;
  }
  return "No main feed is stale, missing or failed";
}

function countsLine(reports: ReportRow[]): string {
  if (reports.length === 0) return "no report freshness rows reported";
  const counts = new Map<ReportRow["status"], number>();
  for (const row of reports) {
    counts.set(row.status, (counts.get(row.status) ?? 0) + 1);
  }
  const parts = REPORT_STATUS_ORDER.filter((status) => counts.has(status)).map(
    (status) => `${counts.get(status)} ${reportCountLabel(status)}`,
  );
  return `${reports.length} reports: ${parts.join(" · ")}`;
}

function CheckedAt({ raw, now }: { raw: string; now: Date }) {
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    return (
      <span className="dg-syshealth__checked">
        <span>checked at</span> <span>{raw}</span> <span>timestamp unavailable</span>
      </span>
    );
  }
  const ageSeconds = Math.floor((now.getTime() - parsed.getTime()) / 1000);
  if (ageSeconds < 0) {
    // A future check timestamp gets the absolute value verbatim, never a
    // negative relative age.
    return (
      <span className="dg-syshealth__checked" title={raw}>
        {raw}
      </span>
    );
  }
  return (
    <span className="dg-syshealth__checked" title={raw}>
      checked {relativeAge(ageSeconds)}
    </span>
  );
}

function relativeAge(seconds: number): string {
  if (seconds < 60) return "under 1 min ago";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hr ago`;
  return `${Math.floor(seconds / 86400)} days ago`;
}

function SubsystemList({ subsystems }: { subsystems: SubsystemRow[] }) {
  const presentIds = new Set(subsystems.map((row) => row.subsystem_id));
  const missing = EXPECTED_SUBSYSTEMS.filter((id) => !presentIds.has(id));
  return (
    <ul className="dg-syshealth__subsystems">
      {/* Every payload row renders — duplicate ids surface as visible conflict,
          never a silent first/last winner. */}
      {subsystems.map((row) => (
        <li
          key={`${row.subsystem_id}:${row.status}:${row.basis}`}
          className="dg-syshealth__subsystem"
          data-health-status={row.status}
          data-tier={row.tier}
          data-severity={
            row.status !== "ok" && row.tier !== "auxiliary" ? "degraded" : undefined
          }
        >
          <span className="dg-syshealth__report-line">
            <span className="dg-syshealth__report-name">
              {subsystemName(row.subsystem_id)}
            </span>
            <span className="dg-syshealth__subsystem-status">
              {subsystemStateLabel(row.status)}
            </span>
          </span>
          <SubsystemReceipt row={row} />
        </li>
      ))}
      {missing.map((id) => (
        <li
          key={id}
          className="dg-syshealth__subsystem"
          data-health-status="not_reported"
        >
          <span className="dg-syshealth__report-name">{subsystemName(id)}</span>
          <span className="dg-syshealth__subsystem-status">
            Not reported — we could not verify it
          </span>
        </li>
      ))}
    </ul>
  );
}

/**
 * DG-120 — one guard's receipt.
 *
 * Two of the three guards write a COMPOUND basis: a summary followed by one
 * entry per degraded store (system_health.py:139-141) or per not-ready surface
 * (:66-69). Rendered as one string, five surfaces each repeating
 * `live_precondition_not_ok:capture_health_ok=degraded` was 340 characters of
 * unbroken machinery, and the fact inside it — every one of them is waiting on
 * the SAME capture-health check — was invisible. Broken into rows, each entry
 * keeps its own name and its own id, and the repetition reads as what it is.
 */
function SubsystemReceipt({ row }: { row: SubsystemRow }) {
  const { summary, lines } = subsystemBasisMessage(row.basis);
  return (
    <span className="dg-syshealth__receipt dg-syshealth__meta" data-receipt>
      {/* A "Why" with nothing under it promises a reason and delivers none, and
          an empty `basis` is a shape the boundary accepts (zod.gen.ts:1329 is a
          bare `z.string()`). Absence renders nothing. */}
      {summary.length > 0 && <ReceiptRow label="Why" message={summary} />}
      {lines.length > 0 && (
        <span className="dg-syshealth__receipt-lines">
          {lines.map((line) => (
            <ReceiptRow
              key={line.identifier}
              label={line.label}
              message={line.message}
              identifier={line.identifier}
            />
          ))}
        </span>
      )}
      <ReceiptRow label="Check id" identifier={row.subsystem_id} />
    </span>
  );
}

function ReportItem({ row, now }: { row: ReportRow; now: Date }) {
  const severityDegraded =
    DEGRADING_REPORT_STATUSES.has(row.status) && row.tier !== "auxiliary";
  return (
    <li
      className="dg-syshealth__report"
      data-testid={`health-report-${row.artifact_id}`}
      data-health-status={row.status}
      data-tier={row.tier}
      data-severity={severityDegraded ? "degraded" : undefined}
    >
      <span className="dg-syshealth__report-line">
        <span className="dg-syshealth__report-name">
          {artifactName(row.artifact_id)}
        </span>
        <span className="dg-syshealth__report-status">
          {reportStateLabel(row.status)}
        </span>
        <ReportTimestamp row={row} now={now} />
      </span>
      {/* DG-120. Every fact this receipt carried before, it carries now — the
          basis, the tier, the artifact id, the producer, the path, every
          disclosure. What changed is that the four MESSAGES among them are
          sentences and the three ADDRESSES are labelled and byte-exact. Nothing
          was dropped: `basis` was the one string here that no test could see,
          and it is now the row a manager actually reads. */}
      <span className="dg-syshealth__receipt dg-syshealth__meta" data-receipt>
        <ReceiptRow label="Why" message={reportBasisMessage(row.basis)} />
        {row.disclosures.map((disclosure) => (
          <ReceiptRow
            key={disclosure}
            label="Also"
            message={disclosureSentence(disclosure)}
          />
        ))}
        {/* The tier is a CLASSIFICATION, not an address — nothing in the
            product is reachable by `core_substrate`, and the row already
            carries it raw on `data-tier` for CSS and for the tests. So it is
            said in words, and no fact leaves with the underscore. */}
        <ReceiptRow
          label="Data group"
          message={[{ kind: "prose", text: tierName(row.tier) }]}
        />
        <ReceiptRow label="Report id" identifier={row.artifact_id} />
        <ReceiptRow label="Written by" identifier={row.producer} />
        <ReceiptRow label="File" identifier={row.artifact_path} />
      </span>
    </li>
  );
}

// DG-109: the eight report states, their count phrases and the artifact /
// subsystem / tier display names all moved into the one copy dictionary
// (lib/copy.ts). The reasoning that shaped them is preserved there:
//
// `producer_failed` keeps its full sentence: it is the one state whose
// consequence a manager acts on — the board in front of them is not today's. It
// names no date, because the contract carries no last-successful-run timestamp;
// `observed_at` here is when the run FAILED, and printing that as "last
// successful" would be a build-clock lie. DG-033: it also names no SUBSYSTEM,
// because the row already carries its own name and timestamp and the sentence
// only has to be true of all of them.

function ReportTimestamp({ row, now }: { row: ReportRow; now: Date }) {
  if (row.observed_at === null) {
    return <span className="dg-syshealth__timestamp">no observable timestamp</span>;
  }
  const parsed = new Date(row.observed_at);
  if (Number.isNaN(parsed.getTime())) {
    return (
      <span className="dg-syshealth__timestamp">
        <span>{row.observed_at}</span> <span>timestamp unavailable</span>
      </span>
    );
  }
  const negativeAge = row.age_seconds !== null && row.age_seconds < 0;
  const future = parsed.getTime() > now.getTime();
  if (negativeAge || future) {
    // Absolute value verbatim — never a negative or absurd relative age.
    return <span className="dg-syshealth__timestamp">{row.observed_at}</span>;
  }
  const seconds =
    row.age_seconds ?? Math.floor((now.getTime() - parsed.getTime()) / 1000);
  return <span className="dg-syshealth__timestamp">{relativeAge(seconds)}</span>;
}
