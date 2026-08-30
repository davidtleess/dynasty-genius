// Model Trust Console — ProvenanceFooter (T9). Provenance + the QUARANTINED grade.
//
// Small, neutral, copyable provenance: run id/date, model version, artifact hash, git sha,
// market source label, and per-season snapshot dates (nullable fields show a neutral
// "not available"). This is also where overall_grade lives: the grade vocabulary reads as
// a success tier (e.g. WR's ACTIVE_B_VALIDATED), so it is DEMOTED out of the truth panel
// (spec §4.1) to here, rendered as neutral text permanently bound to a fixed qualifier —
// never a colored/graded badge, never the lede.
//
// DG-109 review fix: commit e9a4d932 claimed the trust STRIP carried "the last
// two pipeline keys on David's screen". It did not — this footer, one nav click
// away on the Model Trust surface, still printed `ACTIVE_B` as the grade and
// `dynastyprocess_ecr_2qb` as the market source, from a component the
// enforcement test never mounted. Two different corrections apply here, and
// they are not the same correction:
//
//   The provenance ROWS (run id, artifact hash, git sha, source key, snapshot
//   dates) ARE the receipt layer — spec §1 permits the raw key here and only
//   here, because a receipt that renamed the artifact it cites would stop being
//   a receipt. They are now DECLARED as such with `data-receipt` instead of
//   quietly violating a rule they were always exempt from.
//
//   The GRADE is not a receipt. It is a claim a person reads, so it goes through
//   the same dictionary the shell strip uses and sits outside the declared
//   receipt subtree. Its raw value still rides `data-grade` for CSS and tests.
import { trustGradeWord, valueWord } from "../lib/copy";
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
      {/* The receipt sheet, declared. Everything inside cites a run, a hash or a
          source key by its real name — that is the point of it. */}
      <div className="dg-trust-prov__receipts" data-receipt>
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
      </div>

      {/* The market source in words, outside the receipt — the same sentence the
          shell strip shows, so the two surfaces cannot drift. */}
      <div className="dg-trust-prov__row">
        <span className="dg-trust-prov__label">Benchmarked against</span>
        <span className="dg-trust-prov__value">{valueWord(market.label)}</span>
      </div>

      {/* Demoted grade — neutral text, bound to its qualifier, never a badge or the lede. */}
      <div className="dg-trust-prov__grade" data-grade={overallGrade}>
        <span className="dg-trust-prov__value">{trustGradeWord(overallGrade)}</span>
        <span className="dg-trust-prov__qualifier">{MODEL_GRADE_QUALIFIER}</span>
      </div>
    </footer>
  );
}
