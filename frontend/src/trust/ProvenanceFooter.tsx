// Model Trust Console — ProvenanceFooter (T9). Provenance + the QUARANTINED grade.
//
// Small, neutral, copyable provenance: run id/date, model version, artifact hash, git sha,
// market source label, and per-season snapshot dates (nullable fields show a neutral
// "not available"). This is also where overall_grade lives: the grade vocabulary reads as
// a success tier (e.g. WR's ACTIVE_B_VALIDATED), so it is DEMOTED out of the truth panel
// (spec §4.1) to here, rendered as neutral text permanently bound to a fixed qualifier —
// never a colored/graded badge, never the lede.
import { MODEL_GRADE_QUALIFIER } from "../lib/trustCopy";
import type { TrustConsoleViewModel } from "./trustViewModel";

const orNA = (v: string | null | undefined): string =>
  v === null || v === undefined || v === "" ? "not available" : v;

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="dg-trust-prov__row">
      <span className="dg-trust-prov__label">{label}</span>
      <span className="dg-trust-prov__value">{value}</span>
    </div>
  );
}

export function ProvenanceFooter({
  provenance,
  market,
  overallGrade,
}: {
  provenance: TrustConsoleViewModel["provenance"];
  market: TrustConsoleViewModel["market"];
  overallGrade: string;
}) {
  const snapshotEntries = market.snapshot_dates
    ? Object.entries(market.snapshot_dates)
    : [];

  return (
    <footer
      className="dg-trust-prov"
      role="contentinfo"
      aria-label="Model trust provenance"
    >
      <Field label="Run ID" value={orNA(provenance.run_id)} />
      <Field label="Run date" value={provenance.run_date} />
      <Field label="Model version" value={provenance.model_version} />
      <Field label="Artifact hash" value={provenance.model_artifact_hash} />
      <Field label="Git SHA" value={orNA(provenance.git_sha)} />
      <Field label="Market source" value={market.label} />

      <div className="dg-trust-prov__row">
        <span className="dg-trust-prov__label">Market snapshots</span>
        {snapshotEntries.length === 0 ? (
          <span className="dg-trust-prov__value">not available</span>
        ) : (
          <ul className="dg-trust-prov__snapshots">
            {snapshotEntries.map(([season, date]) => (
              <li key={season}>
                {season}: {date}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Demoted grade — neutral text, bound to its qualifier, never a badge or the lede. */}
      <div className="dg-trust-prov__grade">
        <span className="dg-trust-prov__value">{overallGrade}</span>
        <span className="dg-trust-prov__qualifier">{MODEL_GRADE_QUALIFIER}</span>
      </div>
    </footer>
  );
}
