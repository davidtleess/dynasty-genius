// H1 §1b: parked surfaces stay VISIBLE with an honest educational card —
// what the surface will be, why it is parked (evidence-cited), and what
// unparks it. Neutral tone; no dates promised, no verdict language.
import "./ParkedSurfaceCard.css";

type ParkedCopy = {
  heading: string;
  body: string;
  evidencePath: string;
  unpark: string;
};

export const PARKED_SURFACES: Record<string, ParkedCopy> = {
  "Rookie Board": {
    heading: "Rookie Board — parked",
    body: "Rookie valuation stands on the draft-capital + age prior and the ratified cohort-prior table. The college-enrichment path failed its pre-registered promotion gates (0 of 2 positions), so a richer board surface is parked rather than built on an unproven signal. The legacy rookie_board.html remains available outside the app.",
    evidencePath: "docs/validation/engine_a_v2_cfbd_backtest_report.md",
    unpark:
      "Unparks on: a David-ratified spec for a React rookie surface over the existing prior.",
  },
  "Waiver Radar": {
    heading: "Waiver Radar — parked",
    body: "This surface needs in-season usage signals (routes, snaps) that only accrue while games are played; building it now would ship an empty surface.",
    evidencePath: "docs/governance/01-north-star-architecture.md",
    unpark: "Unparks on: In-season 2026 usage accrual plus a David-ratified spec.",
  },
  "Research Assistant": {
    heading: "Research Assistant — parked",
    body: "A north-star surface with no active design yet — parked honestly rather than stubbed.",
    evidencePath: "docs/governance/01-north-star-architecture.md",
    unpark: "Unparks on: a David-prioritized design cycle.",
  },
};

export function ParkedSurfaceCard({ surface }: { surface: string }) {
  const copy = PARKED_SURFACES[surface];
  if (!copy) {
    return null;
  }
  return (
    <section className="dg-parked-card" aria-label={copy.heading}>
      <h2 className="dg-parked-card__heading">{copy.heading}</h2>
      <p className="dg-parked-card__body">{copy.body}</p>
      <p className="dg-parked-card__unpark">{copy.unpark}</p>
      <p className="dg-parked-card__evidence">
        Evidence: <span>{copy.evidencePath}</span>
      </p>
    </section>
  );
}
