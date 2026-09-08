// DG primitive: player identity — the human face of every row (benchmark
// §2.1). Increment 0 (rethink v3 §5): local cached headshot rendering, team
// identity mark, positional rank. The fallback chain is headshot → initials
// disc → named placeholder; a broken image never paints — onError swaps to
// the accessible fallback. Team accent derives from the DB team id, never
// from image metadata.
import { useState } from "react";
import "./ui.css";

/** The one place the local headshot URL is spelled. Root serves this path from the private cache;
 *  it is never a remote hotlink. An id that could not safely address a file yields nothing at all
 *  rather than a malformed URL, so a bad id degrades to initials instead of a broken request. */
export function headshotSrc(sleeperId: string): string | undefined {
  const id = sleeperId.trim();
  if (id === "" || !/^[A-Za-z0-9_-]+$/.test(id)) return undefined;
  return `/assets/headshots/${id}.jpg`;
}

/** The rendered box, in CSS pixels. Set on the element so the row reserves space before the photo
 *  arrives and nothing shifts underneath the reader. */
const HEADSHOT_PX = 32;

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
  // DG-194: the failure belongs to the SOURCE that failed, not to this component instance.
  // React reuses an instance when a list re-renders with different data, so instance-scoped
  // failure state hid a good photo for the next player who landed in this slot, and suppressed a
  // retry when the same player was given a different source. Keyed by src, neither can happen.
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  // A blank or whitespace-only source is no source: never render an empty <img>.
  const resolvedSrc =
    imageSrc !== undefined && imageSrc.trim() !== "" ? imageSrc : undefined;
  const imageFailed = resolvedSrc !== undefined && failedSrc === resolvedSrc;
  const showImage =
    imageStatus === "available" && resolvedSrc !== undefined && !imageFailed;
  const showFallback = !showImage;

  return (
    // DG-109: everything this primitive renders is somebody else's proper noun
    // — the player's name, his NFL team code, his position. The copy dictionary
    // does not translate names, so the subtree declares itself user text and the
    // render rule leaves it alone.
    <span className="dg-ui-player-id" data-user-text>
      {showImage ? (
        <img
          className="dg-ui-player-id__headshot"
          src={resolvedSrc}
          alt={name}
          width={HEADSHOT_PX}
          height={HEADSHOT_PX}
          loading="lazy"
          decoding="async"
          onError={() => setFailedSrc(resolvedSrc ?? null)}
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
