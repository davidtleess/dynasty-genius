// DG primitive: player identity — the human face of every row (benchmark
// §2.1). Increment 0 (rethink v3 §5): local cached headshot rendering, team
// identity mark, positional rank. The fallback chain is headshot → initials
// disc → named placeholder; a broken image never paints — onError swaps to
// the accessible fallback. Team accent derives from the DB team id, never
// from image metadata.
import { useState } from "react";
import "./ui.css";

function initialsFor(name: string): string {
  // Stable rule (Increment-0 RED): words up to the first abbreviated word
  // (contains "."); single word → its first two characters. Uppercase, and
  // unicode-preserving.
  const words = name.split(" ").filter((word) => word.length > 0);
  const cut = words.findIndex((word) => word.includes("."));
  const scope = cut === -1 ? words : words.slice(0, cut);
  const first = scope[0];
  const last = scope[scope.length - 1];
  if (first === undefined) return "";
  if (scope.length === 1 || last === undefined) return first.slice(0, 2).toUpperCase();
  return `${first.charAt(0)}${last.charAt(0)}`.toUpperCase();
}

export function PlayerIdentity({
  name,
  team,
  position,
  imageStatus,
  imageSrc,
  teamId,
  positionRank,
  teamAccent,
}: {
  name: string;
  team: string;
  position: string;
  imageStatus: "available" | "missing";
  /** Local cache path only (asset pipeline) — never a remote hotlink. */
  imageSrc?: string | undefined;
  /** Canonical DB team id — drives the identity mark, never the image. */
  teamId?: string | undefined;
  positionRank?: string | undefined;
  /** Identity accent from the GENERATED team-color module (consumer-supplied;
   *  ui.css stays token-only and the mark stays identity-only — never a
   *  status/lane/verdict carrier). */
  teamAccent?: string | undefined;
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const showImage =
    imageStatus === "available" && imageSrc !== undefined && !imageFailed;
  const showFallback = imageStatus === "missing" || imageFailed;

  return (
    <span className="dg-ui-player-id">
      {showImage ? (
        <img
          className="dg-ui-player-id__headshot"
          src={imageSrc}
          alt={name}
          onError={() => setImageFailed(true)}
        />
      ) : null}
      {showFallback ? (
        <span
          className="dg-ui-player-id__headshot dg-ui-player-id__headshot--fallback"
          role="img"
          aria-label={`${name} headshot unavailable`}
        >
          {initialsFor(name)}
        </span>
      ) : null}
      <span className="dg-ui-player-id__name">{name}</span>
      {teamId !== undefined && teamId !== "" ? (
        <span
          className="dg-ui-player-id__team-mark"
          data-team-id={teamId}
          aria-hidden="true"
          {...(teamAccent !== undefined ? { style: { background: teamAccent } } : {})}
        />
      ) : null}
      {team !== "" ? (
        <span className="dg-ui-player-id__team" data-team-color-basis={team}>
          {team}
        </span>
      ) : null}
      <span className="dg-ui-player-id__position">{position}</span>
      {positionRank !== undefined && positionRank !== "" ? (
        <span className="dg-ui-player-id__pos-rank">{positionRank}</span>
      ) : null}
    </span>
  );
}
