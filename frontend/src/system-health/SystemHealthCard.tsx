import { useEffect, useState } from "react";
import type { z } from "zod";

import { zSystemHealthErrorResponse, zSystemHealthResponse } from "../lib/api/zod.gen";
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

const REPORT_STATUS_ORDER: ReportRow["status"][] = [
  "fresh",
  "freshness_overdue",
  "stale",
  "corrupt_or_empty",
  "dormant",
  "missing",
];

// Severity accents apply only to statuses the backend rollup treats as degrading,
// and never to auxiliary-tier rows (auxiliary can never drive overall_status).
const DEGRADING_REPORT_STATUSES: ReadonlySet<ReportRow["status"]> = new Set([
  "stale",
  "corrupt_or_empty",
  "missing",
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
      aria-label="System diagnostics"
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
        <span className="dg-syshealth__loading">Loading system diagnostics…</span>
      )}
      {state.status === "unavailable" && (
        <div className="dg-syshealth__unavailable">
          <span>System diagnostics unavailable — pipeline status unknown</span>
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
        <span className="dg-syshealth__title">System Diagnostics</span>
        <span className="dg-syshealth__subtitle">
          pipeline &amp; data freshness — not model accuracy
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
      <footer className="dg-syshealth__footer">
        <span className="dg-syshealth__disclaimer">{data.disclaimer}</span>
        <span className="dg-syshealth__decision">
          Descriptive only — not decision-grade.
        </span>
      </footer>
    </div>
  );
}

// Verbatim enum, never editorial copy; when degraded the worst tier leads so a
// core failure cannot read benign inside a mostly-fresh count.
function overallLine(data: SystemHealth): string {
  if (data.overall_status === "degraded" && data.worst_affected_tier !== null) {
    return `degraded · ${data.worst_affected_tier} affected`;
  }
  return data.overall_status;
}

function countsLine(reports: ReportRow[]): string {
  if (reports.length === 0) return "no report freshness rows reported";
  const counts = new Map<ReportRow["status"], number>();
  for (const row of reports) {
    counts.set(row.status, (counts.get(row.status) ?? 0) + 1);
  }
  const parts = REPORT_STATUS_ORDER.filter((status) => counts.has(status)).map(
    (status) => `${counts.get(status)} ${status}`,
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
          <span className="dg-syshealth__subsystem-id">{row.subsystem_id}</span>{" "}
          <span className="dg-syshealth__subsystem-status">({row.status})</span>{" "}
          <span className="dg-syshealth__meta">{row.basis}</span>
        </li>
      ))}
      {missing.map((id) => (
        <li
          key={id}
          className="dg-syshealth__subsystem"
          data-health-status="not_reported"
        >
          {`${id} — not reported (unverified)`}
        </li>
      ))}
    </ul>
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
      <span className="dg-syshealth__report-id">{row.artifact_id}</span>{" "}
      <span className="dg-syshealth__report-status">
        {reportStatusLabel(row.status)}
      </span>{" "}
      <ReportTimestamp row={row} now={now} />{" "}
      <span className="dg-syshealth__meta">{row.basis}</span>{" "}
      <span className="dg-syshealth__meta">{row.tier}</span>{" "}
      <span className="dg-syshealth__meta">{row.producer}</span>{" "}
      <span className="dg-syshealth__meta">{row.artifact_path}</span>
      {row.disclosures.map((disclosure) => (
        <span key={disclosure} className="dg-syshealth__meta">
          {" "}
          {disclosure}
        </span>
      ))}
    </li>
  );
}

// Verbatim enum plus the honesty qualifier where a bare enum could mislead:
// overdue-within-grace is pending (not fresh, not degraded); dormant is the
// expected healthy off-season state.
function reportStatusLabel(status: ReportRow["status"]): string {
  if (status === "freshness_overdue") return "freshness_overdue (within grace)";
  if (status === "dormant") return "dormant (off-season expected)";
  return status;
}

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
