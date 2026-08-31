import type { LeaguePulseResponse } from "../lib/api";
import { ReceiptCitation } from "../ui/Receipt";
import { SnapshotStamp } from "./SnapshotStamp";

// Header band for the League Pulse surface.
//
// DG-111: three stamps stood here — "EXPERIMENTAL — a read-only league
// snapshot.", the "Diagnostic Workspace…" paragraph, and "Descriptive only —
// not decision-grade." They said the same thing three ways in the system's own
// vocabulary. One sentence replaces all three, and it keeps the two facts that
// were load-bearing: this is a read-only snapshot of the league, and reading a
// team's situation off its roster is not the same as knowing what its manager
// will do.
//
// DG-114 REVIEW FIX: "and who to call" left with the panel that answered it.
// Partner Rankings is on Trades now, so this sentence was promising a section
// the page no longer contains — a false sentence on a live surface. The
// replacement keeps both load-bearing facts and adds a plain pointer to where
// the partner panel went, which is a navigation fact and asserts nothing about
// the ranking itself (it still declines to be a validated one).
const LEAGUE_SNAPSHOT_COPY =
  "Your league at a glance — who's contending and who's rebuilding. It's a read-only snapshot: we read each roster, we don't read minds. Partner rankings now sit under Trades, beside the trade builder.";

// The panels THIS page renders. `dropped.partner_rankings` is deliberately not
// summed here: the sentence below says the records "are not shown below", and
// since DG-114 the partner panel is not below — it is on Trades, where that
// counter is now disclosed against the panel it belongs to (TradePartners.tsx).
// Summing it here would attach a count to a page whose content it does not
// describe; dropping it entirely would lose the fact. It moved with its panel.
function withheldTotal(dropped: LeaguePulseResponse["dropped"]): number {
  return (
    (dropped.market_overlay_cards ?? 0) +
    (dropped.model_native_cards ?? 0) +
    (dropped.roster_capacity_candidate_pools ?? 0) +
    (dropped.team_postures ?? 0) +
    (dropped.team_values ?? 0)
  );
}

function schemaVersion(source: Record<string, unknown>): string {
  return String(source.schema_version ?? "");
}

export function LeaguePulseHeader({ data }: { data: LeaguePulseResponse }) {
  const withheld = withheldTotal(data.dropped);
  const sources = data.source_artifacts;

  return (
    // DG-118: this was `<header role="banner">`. A banner is THE page's banner,
    // and the shell already has one (`.dg-shell__trust`), so on League Pulse the
    // document carried two banners and one of them was nested inside `main` —
    // axe: landmark-no-duplicate-banner + landmark-banner-is-top-level, measured
    // on the built bundle at both widths. Nobody knew, because the gate had
    // never visited this surface. A labelled <section> is a `region`: still a
    // named landmark a screen-reader user can jump to, without claiming to be
    // the banner of a page it is one panel of.
    <section aria-label="League Pulse status" className="dg-league-pulse__header">
      <h2 className="dg-league-pulse__heading">League Pulse</h2>
      <p className="dg-league-pulse__diagnostic">{LEAGUE_SNAPSHOT_COPY}</p>
      <SnapshotStamp capturedAt={data.captured_at} caveats={data.caveats} />
      {withheld > 0 ? (
        // The count is exact; the CAUSE is not one thing. The five counters
        // summed above fail for different reasons — most are genuine mapping
        // failures, and opportunity cards also drop fail-closed on model-native
        // purity rules (league_pulse_assembler.py:176-185). So the sentence
        // reports the number and the consequence, and asserts no cause the data
        // does not carry.
        <p className="dg-league-pulse__withheld">
          {withheld} records could not be matched up and are not shown below.
        </p>
      ) : null}
      {/* The three artifact schema versions are a receipt: they name exactly
          which producer output this page was built from. DG-120: each version
          is now DECLARED an identifier rather than riding a blanket exemption
          on the list — the label is our words, the version is the artifact's,
          and the render rule can finally tell the two apart. The bytes and the
          line a manager reads are unchanged. */}
      <ul className="dg-league-pulse__sources" data-receipt>
        <li>
          <ReceiptCitation
            label="Team posture data"
            raw={schemaVersion(sources.team_posture)}
          />
        </li>
        <li>
          <ReceiptCitation
            label="Team value data"
            raw={schemaVersion(sources.team_value_matrix)}
          />
        </li>
        <li>
          <ReceiptCitation
            label="League opportunity data"
            raw={schemaVersion(sources.league_opportunity)}
          />
        </li>
      </ul>
    </section>
  );
}
