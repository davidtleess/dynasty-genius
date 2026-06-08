// Surface-3 T8 — the full Decision-Evidence-Card body. Header + universal,
// non-dismissible "Decision support only" state + two-lane valuation + evidence.
// Decision-grade card body: it DOES render the real values/text, but never a
// verdict, buy/sell/favors/recommendation language, or verdict hues.
import type { z } from "zod";

import type { zPlayerDetailResponse } from "../lib/api/zod.gen";
import { EvidenceSection } from "./EvidenceSection";
import "./PlayerDetail.css";
import { ValuationTwoLane } from "./ValuationTwoLane";

type PlayerDetail = z.infer<typeof zPlayerDetailResponse>;

export function PlayerDetailCard({ detail }: { detail: PlayerDetail }) {
  const modeled = detail.model_status === "modeled";

  return (
    <article
      className="dg-player-detail"
      aria-label={`Player detail for ${detail.identity.name}`}
    >
      <header className="dg-player-detail__header">
        <h2 className="dg-player-detail__title">{detail.identity.name}</h2>
        <p className="dg-player-detail__meta">
          {detail.identity.position} · {detail.identity.team} · age{" "}
          {detail.identity.age}
        </p>
        {/* Universal, non-dismissible decision_supported=false state. */}
        <p className="dg-player-detail__banner">Decision support only</p>
      </header>

      {!modeled && (
        <div className="dg-player-detail__experimental">
          <span className="dg-player-detail__experimental-badge">Experimental</span>
          <p>No active model score</p>
          {detail.degradation?.message && <p>{detail.degradation.message}</p>}
        </div>
      )}

      <ValuationTwoLane
        model={detail.model}
        market={detail.market}
        divergence={detail.divergence}
      />
      <EvidenceSection evidence={detail.evidence} />
    </article>
  );
}
