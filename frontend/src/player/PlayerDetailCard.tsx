// The player card body: identity, the two valuation lanes, and the evidence.
//
// DG-111 (David, 2026-08-29): the card used to open with a stamp — "Descriptive
// only — not decision-grade." — and, for an unscored player, an "Experimental"
// badge over the bare words "No active model score". Both are retired. What
// replaces them is what a person would actually say: an unscored player is
// told, in a sentence, that he is unscored and what that means for the numbers
// below; and the model's standing is stated ONCE at the foot of the card,
// where it belongs, instead of stamped at the top of every region.
import type { z } from "zod";
import type { zPlayerDetailResponse } from "../lib/api/zod.gen";
import { MODEL_STANDING_SENTENCE, receiptLine } from "../lib/copy";
import { EvidenceSection } from "./EvidenceSection";
import { FrozenPredictionStatus } from "./FrozenPredictionStatus";
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
        {/* DG-109 put the bare Sleeper id in the receipt layer, labelled, on the
            inspector preview: it is a lookup key, not information about the
            player, and it stays on screen saying what it is. DG-114 retired that
            preview, so the receipt comes here — the card is the only place a
            player is read now, and a fact does not leave with its furniture. */}
        <p className="dg-player-detail__id" data-receipt>
          {receiptLine("Sleeper id", detail.sleeper_id)}
        </p>
      </header>

      {/* THE FACT, not the badge: this player has no model score. The sentence
          says what that means for what follows, and the producer's own reason
          is carried through verbatim rather than swallowed by our copy. */}
      {!modeled && (
        <div className="dg-player-detail__experimental" data-testid="player-unscored">
          <p>
            Not scored yet — we don't have a model score for {detail.identity.name}.
            Anything the market says below is real; the projection stays blank until our
            next model run.
          </p>
          {detail.degradation?.message && <p>{detail.degradation.message}</p>}
        </div>
      )}

      <FrozenPredictionStatus frozen={detail.frozen_prediction} />

      <ValuationTwoLane
        model={detail.model}
        market={detail.market}
        divergence={detail.divergence}
      />
      <EvidenceSection evidence={detail.evidence} />

      {/* The honest reading of decision_supported=false, said once, in plain
          words, at the bottom — where it colours the numbers you have just
          read instead of shouting before you have read any. */}
      <p className="dg-player-detail__standing" data-testid="model-standing">
        {MODEL_STANDING_SENTENCE}
      </p>
    </article>
  );
}
