// The player card body: identity, the two valuation lanes, and the evidence.
//
// DG-111 (David, 2026-08-29): the card used to open with a stamp — "Descriptive
// only — not decision-grade." — and, for an unscored player, an "Experimental"
// badge over the bare words "No active model score". Both are retired. What
// replaces them is what a person would actually say: an unscored player is
// told, in a sentence, that he is unscored and what that means for the numbers
// below; and the model's standing is stated ONCE at the foot of the card,
// where it belongs, instead of stamped at the top of every region.
import type { ReactNode } from "react";
import type { z } from "zod";
import type { zPlayerDetailResponse } from "../lib/api/zod.gen";
import {
  FREE_AGENT_LABEL,
  LEAGUE_FREE_AGENT_LABEL,
  LEAGUE_FREE_AGENT_SENTENCE,
  LEAGUE_OWNERSHIP_UNKNOWN_SENTENCE,
  LEAGUE_ROSTERED_BY_PREFIX,
  LEAGUE_ROSTERED_WITHOUT_MANAGER,
  LEAGUE_TEAM_LABEL,
  LEAGUE_TEAM_UNKNOWN,
  LEAGUE_TEAM_UNNAMED_NOTE,
  leagueRosterAsOf,
  MODEL_STANDING_SENTENCE,
  nflTeamLabel,
} from "../lib/copy";
import { ReceiptCitation } from "../ui/Receipt";
import { EvidenceSection } from "./EvidenceSection";
import { FrozenPredictionStatus } from "./FrozenPredictionStatus";
import "./PlayerDetail.css";
import { ValuationTwoLane } from "./ValuationTwoLane";

type PlayerDetail = z.infer<typeof zPlayerDetailResponse>;
type LeagueOwnership = PlayerDetail["league_ownership"];

// DG-145 (David, 2026-09-03): "free agents should show 'FA' on the card", and
// "free agent" means "nobody in the league owns" — a LEAGUE fact, not an NFL one.
// The API serves that fact dated by the league roster capture it came from
// (rostered by whom / free agent / unknown); this line says it with the capture
// time on screen, so the age of the fact is stated, never guessed. The word
// "FA" comes from the copy dictionary and nowhere else. An unknown is said as
// unknown — the capture did not vouch for him — with no label and no date.
function leagueOwnershipLine(ownership: LeagueOwnership): ReactNode {
  const asOfIso = ownership.as_of ?? null;
  const asOf = asOfIso === null ? "" : ` · ${leagueRosterAsOf(asOfIso)}`;
  // The route already collapses an undated snapshot to "unknown"; the card
  // holds the same line at its own boundary, because the contract's as_of is
  // nullable for every status and "FA" with no capture time behind it would be
  // a claim nobody can date.
  if (ownership.status === "free_agent" && asOfIso !== null) {
    return (
      <>
        <span className="dg-player-detail__fa">{LEAGUE_FREE_AGENT_LABEL}</span>
        {` · ${LEAGUE_FREE_AGENT_SENTENCE}${asOf}`}
      </>
    );
  }
  if (ownership.status === "rostered") {
    const name = ownership.owner_display_name;
    if (name === null || name === undefined || name === "") {
      return `${LEAGUE_ROSTERED_WITHOUT_MANAGER}${asOf}`;
    }
    return (
      <>
        {`${LEAGUE_ROSTERED_BY_PREFIX} `}
        {/* The manager's handle is text the league wrote, not our vocabulary —
            DG-109's render rule exempts it by this marker. */}
        <span data-user-text="">{name}</span>
        {asOf}
      </>
    );
  }
  return LEAGUE_OWNERSHIP_UNKNOWN_SENTENCE;
}

// DG-149: the league TEAM he plays for, in its own labelled spot apart from the
// NFL team in the header. The team name is the manager's own text; a manager
// who never named his team is shown by his handle, and the line says so. "FA"
// here is the same word as the header's, from the same dictionary entry.
function leagueTeamLine(ownership: LeagueOwnership): ReactNode {
  const dated = ownership.as_of !== null && ownership.as_of !== undefined;
  if (ownership.status === "free_agent" && dated) {
    return <span className="dg-player-detail__fa">{FREE_AGENT_LABEL}</span>;
  }
  if (ownership.status === "rostered") {
    const teamName = ownership.team_name;
    if (teamName !== null && teamName !== undefined && teamName !== "") {
      return <span data-user-text="">{teamName}</span>;
    }
    const owner = ownership.owner_display_name;
    if (owner !== null && owner !== undefined && owner !== "") {
      return (
        <>
          <span data-user-text="">{owner}</span>
          {` · ${LEAGUE_TEAM_UNNAMED_NOTE}`}
        </>
      );
    }
    return LEAGUE_ROSTERED_WITHOUT_MANAGER;
  }
  return LEAGUE_TEAM_UNKNOWN;
}

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
          {detail.identity.position} · {nflTeamLabel(detail.identity.team)} · age{" "}
          {detail.identity.age}
        </p>
        <p className="dg-player-detail__league-team" data-testid="league-team">
          {`${LEAGUE_TEAM_LABEL}: `}
          {leagueTeamLine(detail.league_ownership)}
        </p>
        <p className="dg-player-detail__league" data-testid="league-ownership">
          {leagueOwnershipLine(detail.league_ownership)}
        </p>
        {/* DG-109 put the bare Sleeper id in the receipt layer, labelled, on the
            inspector preview: it is a lookup key, not information about the
            player, and it stays on screen saying what it is. DG-114 retired that
            preview, so the receipt comes here — the card is the only place a
            player is read now, and a fact does not leave with its furniture. */}
        <p className="dg-player-detail__id" data-receipt>
          <ReceiptCitation label="Sleeper id" raw={detail.sleeper_id} />
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
